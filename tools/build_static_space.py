#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""Build the static Hugging Face Space (space-static/) with its phrases.json from the language packs.

    python3 tools/build_static_space.py --out /tmp/svaram-static

The page calls svaram.live's public API, which allows this Space's origin (deploy/nginx.sample.conf).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "core"))
from packs import read_meta, read_phrases  # noqa: E402

ORDER = ["te", "hi", "ta", "kn", "ml", "mr", "bn", "gu", "or", "pa", "as", "doi"]
FILES = ["index.html", "app.js", "style.css", "README.md"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="folder to write; replaced if it exists")
    a = ap.parse_args()
    if os.path.isdir(a.out):
        shutil.rmtree(a.out)
    os.makedirs(a.out)
    for f in FILES:
        shutil.copy2(os.path.join(ROOT, "space-static", f), os.path.join(a.out, f))
    langs = []
    for code in ORDER:
        meta = read_meta(code)
        if meta["status"] != "live":
            continue
        langs.append({"code": code, "name": meta["name"], "native": meta["native"],
                      "phrases": [{"english": p["english"], "text": p["text"]}
                                  for p in read_phrases(code) if not p.get("extra")]})
    with open(os.path.join(a.out, "phrases.json"), "w", encoding="utf-8") as f:
        json.dump({"languages": langs}, f, ensure_ascii=False, indent=1)
    commit = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True).stdout.strip() or "unknown"
    print(f"{len(FILES) + 1} files, {len(langs)} languages (commit {commit}) -> {a.out}")


if __name__ == "__main__":
    main()
