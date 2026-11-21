#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""Check a running Svaram end to end: every language prepares, speaks and (if offered) translates.

    python3 tools/selftest.py                 # against svaram-api on 127.0.0.1:8200
    python3 tools/selftest.py --save /tmp/st  # also keep one MP3 per language to listen to

Uses each pack's first phrase and one fixed English sentence: never anything a user typed.
Exit code 0 when every language passes. Standard library plus PyYAML.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "core"))
from packs import load_all  # noqa: E402

ENGLISH = "Please call the nurse, I need 2 tablets."


def call(api: str, path: str, body: dict, tries: int = 6):
    for i in range(tries):
        rq = urllib.request.Request(api + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(rq, timeout=90) as r:
                return r.status, r.headers.get("Content-Type", ""), r.read()
        except urllib.error.HTTPError as e:
            data = e.read()
            if e.code == 503 and i < tries - 1:
                time.sleep(2 + i)
                continue
            return e.code, e.headers.get("Content-Type", ""), data
    return 0, "", b""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--api", default="http://127.0.0.1:8200")
    ap.add_argument("--save", help="folder to keep one MP3 per language")
    ap.add_argument("--lang", action="append", help="only these languages")
    a = ap.parse_args()
    packs = load_all(with_prepare=False)
    codes = a.lang or list(packs)
    failed = 0
    print(f"{'lang':5} {'prepare':8} {'speak':16} {'translate':10}")
    for code in codes:
        row = []
        text = packs[code].phrases[0]["text"] if packs[code].phrases else "1"
        st, _, body = call(a.api, "/api/prepare", {"text": text, "lang": code})
        ok = st == 200 and json.loads(body).get("ok")
        row.append("ok" if ok else f"FAIL {st}")
        seg = json.loads(body).get("segments", ["-"])[0] if ok else "-"
        t0 = time.time()
        st, ctype, audio = call(a.api, "/api/speak", {"text": seg, "lang": code, "rate": 1.0})
        ms = int((time.time() - t0) * 1000)
        sok = st == 200 and ctype.startswith("audio/") and len(audio) > 1000
        row.append(f"ok {ms} ms" if sok else f"FAIL {st}")
        if sok and a.save:
            os.makedirs(a.save, exist_ok=True)
            with open(os.path.join(a.save, f"{code}.mp3"), "wb") as f:
                f.write(audio)
        if packs[code].meta.get("translate_target"):
            st, _, body = call(a.api, "/api/convey", {"text": ENGLISH, "lang": code})
            tok = st == 200 and json.loads(body).get("ok")
            row.append("ok" if tok else f"FAIL {st}")
        else:
            tok = True
            row.append("-")
        failed += not (ok and sok and tok)
        print(f"{code:5} {row[0]:8} {row[1]:16} {row[2]:10}")
    print(f"{len(codes) - failed} of {len(codes)} languages pass")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
