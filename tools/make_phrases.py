#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""Make the quick-phrase audio files from the language packs, using a running Svaram.

    python3 tools/make_phrases.py --out /var/www/svaram            # every live pack, missing files only
    python3 tools/make_phrases.py --out /var/www/svaram --lang ta --force

Each phrase goes through the same steps as a typed message (svaram-api /api/prepare, then
/api/speak), so a phrase sounds exactly like the same words typed. Files are written to
<out>/phrases/<code>/<id>.mp3. Needs svaram-api and the voice services running on this machine.
Standard library plus PyYAML.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "core"))
from packs import load_all  # noqa: E402


def post(api: str, path: str, body: dict) -> tuple[int, bytes]:
    rq = urllib.request.Request(api + path, data=json.dumps(body).encode(),
                                headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(rq, timeout=60) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def make(api: str, code: str, text: str) -> bytes:
    st, body = post(api, "/api/prepare", {"text": text, "lang": code})
    p = json.loads(body)
    if st != 200 or not p.get("ok"):
        raise RuntimeError(f"prepare failed ({st}): {p}")
    audio = b""
    for seg in p["segments"]:
        st, data = post(api, "/api/speak", {"text": seg, "lang": code, "rate": 1.0})
        if st != 200:
            raise RuntimeError(f"speak failed ({st}): {data[:200]!r}")
        audio += data                                  # MP3 frames join cleanly
    return audio


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="the web folder (phrases/ is written inside it)")
    ap.add_argument("--api", default="http://127.0.0.1:8200", help="where svaram-api listens")
    ap.add_argument("--lang", action="append", help="only these packs (repeatable)")
    ap.add_argument("--force", action="store_true", help="remake files that already exist")
    a = ap.parse_args()
    packs = load_all(with_prepare=False)
    codes = a.lang or list(packs)
    made = skipped = 0
    for code in codes:
        folder = os.path.join(a.out, "phrases", code)
        os.makedirs(folder, exist_ok=True)
        for p in packs[code].phrases:
            path = os.path.join(folder, f"{p['id']}.mp3")
            if os.path.exists(path) and not a.force:
                skipped += 1
                continue
            data = make(a.api, code, p["text"])
            tmp = path + ".part"
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, path)
            made += 1
            print(f"{code}/{p['id']}.mp3  {len(data)} bytes")
    print(f"made {made}, kept {skipped} existing")


if __name__ == "__main__":
    main()
