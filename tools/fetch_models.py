#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""Download the models Svaram needs from their publishers and check every file's SHA-256.

    python3 tools/fetch_models.py rasa kokoro translate indictts
    python3 tools/fetch_models.py --check rasa          # only check what is already there

Reads deploy/models.yaml. A file whose checksum differs is deleted and the run stops: Svaram never
runs a model it has not checked. If Hugging Face asks for a login (some models need their terms
accepted first), the token is asked for once, hidden, used for these downloads only, and never
written anywhere. Where nobody can type it (a container), it is read from the HF_TOKEN environment
variable instead, and is still only sent to huggingface.co. Standard library plus PyYAML.
"""
from __future__ import annotations

import argparse
import fnmatch
import getpass
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import yaml  # noqa: E402

UA = {"User-Agent": "svaram-installer"}
_token: str | None = os.environ.get("HF_TOKEN", "").strip() or None


class FetchError(RuntimeError):
    pass


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _open(url: str, auth: bool = False):
    headers = dict(UA)
    if auth and _token:
        headers["Authorization"] = f"Bearer {_token}"
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60)


def _hf(url: str):
    """Open a Hugging Face URL; on 401/403 ask once for a token and try again."""
    global _token
    try:
        return _open(url, auth=True)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403) and _token is None and sys.stdin.isatty():
            print("  This model needs a Hugging Face login (accept its terms on huggingface.co first).")
            _token = getpass.getpass("  Hugging Face token (hidden, not saved): ").strip() or None
            if _token:
                return _open(url, auth=True)
        raise FetchError(f"{url} answered {e.code}") from e


def download(url: str, dest: str, hf: bool = False) -> None:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    with (_hf(url) if hf else _open(url)) as r, open(tmp, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        for chunk in iter(lambda: r.read(1 << 20), b""):
            f.write(chunk)
            done += len(chunk)
            if total and sys.stdout.isatty():
                print(f"\r  {os.path.basename(dest)}: {done * 100 // total}%", end="", flush=True)
    if total and sys.stdout.isatty():
        print()
    os.replace(tmp, dest)


def verify(path: str, want: str | None) -> str:
    got = sha256(path)
    if want and got != want.lower():
        os.remove(path)
        raise FetchError(f"{path}: SHA-256 {got} does not match {want}; file removed")
    return got


def _real_sha(v) -> str | None:
    """A listed SHA-256 only if it is one (64 hex digits); anything else is ignored."""
    v = (v or "").strip().lower()
    return v if len(v) == 64 and all(c in "0123456789abcdef" for c in v) else None


def hf_files(repo: str) -> list[dict]:
    with _hf(f"https://huggingface.co/api/models/{repo}/tree/main?recursive=1") as r:
        return [f for f in json.load(r) if f.get("type") == "file"]


def fetch_rasa(m: dict, check_only: bool) -> None:
    listing = None if check_only else hf_files(m["huggingface"])
    for name, spec in m["files"].items():
        dest = os.path.join(m["dir"], name)
        if os.path.isfile(dest) and sha256(dest) == spec["sha256"]:
            print(f"  {name}: already there, checksum ok")
            continue
        if check_only:
            raise FetchError(f"{dest} missing or wrong")
        pick = [f["path"] for f in listing if fnmatch.fnmatch(os.path.basename(f["path"]), spec["pick"])]
        exact = [p for p in pick if _real_sha((next(f for f in listing if f["path"] == p).get("lfs") or {}).get("oid")) == spec["sha256"]]
        src = (exact or pick or [None])[0]
        if not src:
            raise FetchError(f"{m['huggingface']} has no file matching {spec['pick']}")
        print(f"  {name} <- {m['huggingface']}/{src}")
        download(f"https://huggingface.co/{m['huggingface']}/resolve/main/{src}", dest, hf=True)
        verify(dest, spec["sha256"])
        print(f"  {name}: checksum ok")


def fetch_urls(m: dict, check_only: bool) -> None:
    for name, spec in m["files"].items():
        dest = os.path.join(m["dir"], name)
        if os.path.isfile(dest) and sha256(dest) == spec["sha256"]:
            print(f"  {name}: already there, checksum ok")
            continue
        if check_only:
            raise FetchError(f"{dest} missing or wrong")
        print(f"  {name} <- {spec['url']}")
        download(spec["url"], dest)
        verify(dest, spec["sha256"])
        print(f"  {name}: checksum ok")


def fetch_translate(m: dict, check_only: bool) -> None:
    pinned = m["files"]
    if not check_only:
        for f in hf_files(m["huggingface"]):
            p = f["path"]
            if p in m.get("skip", []):
                continue
            dest = os.path.join(m["dir"], p)
            oid = _real_sha((f.get("lfs") or {}).get("oid"))     # gated repos may list a placeholder
            if os.path.isfile(dest) and (not oid or sha256(dest) == oid):
                continue
            print(f"  {p}")
            download(f"https://huggingface.co/{m['huggingface']}/resolve/main/{p}", dest, hf=True)
            if oid:
                verify(dest, oid)
    for name, spec in pinned.items():
        verify(os.path.join(m["dir"], name), spec["sha256"])
        print(f"  {name}: checksum ok")


def _local_config(src: str, dst: str, folder: str) -> None:
    """Make config.svaram.json from the released config.json: every file path from training
    points at the file in this folder, and text_cleaner is no_cleaners, because Svaram's
    language pack has already prepared the text (as on svaram.live)."""
    with open(src, encoding="utf-8") as f:
        cfg = json.load(f)
    local = set(os.listdir(folder))

    def fix(v):
        if isinstance(v, dict):
            return {k: fix(x) for k, x in v.items()}
        if isinstance(v, list):
            return [fix(x) for x in v]
        if isinstance(v, str) and ("/" in v or "\\" in v) and os.path.basename(v) in local:
            return os.path.join(folder, os.path.basename(v))
        return v
    cfg = fix(cfg)
    if "text_cleaner" in cfg:
        cfg["text_cleaner"] = "no_cleaners"
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def fetch_indictts(m: dict, check_only: bool, langs: list[str], itts_python: str = sys.executable) -> str:
    base = m["dir"]
    manifest = os.path.join(base, "manifest.json")
    if check_only:
        files = json.load(open(manifest, encoding="utf-8"))["files"]
        for rel, sha in files.items():
            verify(os.path.join(base, rel), sha)
        return sha256(manifest)
    with _open(f"https://api.github.com/repos/{m['github_release']}/releases") as r:
        releases = json.load(r)
    assets = {a["name"]: a["browser_download_url"] for rel in releases for a in rel.get("assets", [])}
    files: dict[str, str] = {}
    zips: dict[str, str] = {}
    pins = m.get("files", {})
    for lang in langs:
        url = assets.get(f"{lang}.zip")
        if not url:
            raise FetchError(f"no {lang}.zip in the {m['github_release']} releases")
        print(f"  {lang} <- {url}")
        with tempfile.TemporaryDirectory() as tmp:
            z = os.path.join(tmp, f"{lang}.zip")
            download(url, z)
            zips[lang] = verify(z, m.get("zips", {}).get(lang))
            with zipfile.ZipFile(z) as zf:
                zf.extractall(tmp)
            found = None
            for dirpath, dirnames, _ in os.walk(tmp):
                if "fastpitch" in dirnames and "hifigan" in dirnames:
                    found = dirpath
                    break
            if not found:
                raise FetchError(f"{lang}.zip has no fastpitch/ and hifigan/ folders")
            dest = os.path.join(base, lang)
            if os.path.isdir(dest):
                shutil.rmtree(dest)
            os.makedirs(dest)
            for rel in [k for k in pins if k.startswith(f"{lang}/")] or [
                    f"{lang}/{sub}/{n}" for sub in ("fastpitch", "hifigan") for n in os.listdir(os.path.join(found, sub))]:
                sub_rel = rel.split("/", 1)[1]
                src = os.path.join(found, sub_rel)
                if not os.path.isfile(src):
                    raise FetchError(f"{lang}.zip has no {sub_rel}")
                out = os.path.join(base, rel)
                os.makedirs(os.path.dirname(out), exist_ok=True)
                if rel.endswith("best_model.pth"):
                    # the release checkpoints carry training state too: keep config + weights only
                    verify(src, m.get("release_files", {}).get(rel))
                    r = subprocess.run([itts_python, os.path.join(ROOT, "tools", "slim_checkpoint.py"), src, out,
                                        *(["--want", pins[rel]] if pins.get(rel) else [])],
                                       capture_output=True, text=True)
                    if r.returncode != 0:
                        raise FetchError(f"slimming {rel} failed: {(r.stderr or r.stdout).strip()[-300:]}")
                    how = r.stdout.strip().splitlines()[-1]
                    files[rel] = sha256(out)
                    print(f"  {rel}: slimmed, " + ("identical to svaram.live" if how == "exact"
                                                    else "same weights as the release (file bytes differ from svaram.live)"))
                else:
                    shutil.copy2(src, out)
                    files[rel] = verify(out, pins.get(rel))
        fp = os.path.join(base, lang, "fastpitch")
        _local_config(os.path.join(fp, "config.json"), os.path.join(fp, "config.svaram.json"), fp)
        files[f"{lang}/fastpitch/config.svaram.json"] = sha256(os.path.join(fp, "config.svaram.json"))
        print(f"  {lang}: every file checked")
    with open(manifest, "w", encoding="utf-8") as f:
        json.dump({"engine": "AI4Bharat Indic-TTS v1 (github.com/AI4Bharat/Indic-TTS, MIT); IIT Madras Indic TTS database",
                   "files": files, "source_zip_sha256": zips}, f, indent=1, sort_keys=True)
    print(f"  manifest.json: {len(files)} files recorded")
    return sha256(manifest)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("services", nargs="+", choices=["rasa", "kokoro", "translate", "indictts"])
    ap.add_argument("--check", action="store_true", help="only check files already downloaded")
    ap.add_argument("--indictts-langs", default="gu,or")
    ap.add_argument("--manifest-sha-out", help="write the indictts manifest SHA-256 to this file")
    ap.add_argument("--models-root", help="put the models under this folder instead of /opt/svaram")
    ap.add_argument("--itts-python", default="/opt/svaram/voice-itts/venv/bin/python",
                    help="Python with torch, used to slim the Indic-TTS checkpoints")
    a = ap.parse_args()
    with open(os.path.join(ROOT, "deploy", "models.yaml"), encoding="utf-8") as f:
        models = yaml.safe_load(f)
    try:
        for s in a.services:
            print(f"{s}:")
            m = models[s]
            if a.models_root:
                m["dir"] = m["dir"].replace("/opt/svaram", a.models_root.rstrip("/"), 1)
            os.makedirs(m["dir"], exist_ok=True)
            if s == "rasa":
                fetch_rasa(m, a.check)
            elif s == "kokoro":
                fetch_urls(m, a.check)
            elif s == "translate":
                fetch_translate(m, a.check)
            else:
                sha = fetch_indictts(m, a.check, [x for x in a.indictts_langs.split(",") if x], a.itts_python)
                if a.manifest_sha_out:
                    with open(a.manifest_sha_out, "w") as f:
                        f.write(sha + "\n")
    except (FetchError, urllib.error.URLError, OSError) as e:
        print(f"STOP: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
