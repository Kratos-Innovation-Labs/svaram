#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""Check language packs: their files, their phrases, and their test sentences.

    python3 tools/check_pack.py            # check every pack in lang/
    python3 tools/check_pack.py te ta      # check some packs
    python3 tools/check_pack.py xx --init  # write tests.yaml for a new pack from what it says now

tests.yaml is a list of {text, spoken, ok}: for each text, what the voice will be given and
whether every word could be said. After a deliberate change to a pack, review the differences
this tool prints, then run it with --init to record the new answers.
No voice is needed: this checks the text side only. Standard library plus PyYAML.
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "core"))
import yaml  # noqa: E402
from packs import LANG_DIR, PackError, list_codes, load_prepare, read_meta, read_phrases  # noqa: E402

#: Sentences every pack is tried on, besides its own phrases: numbers, times, money, phone
#: numbers, short forms, and English words (which must be reported, never dropped).
COMMON = ["2", "15", "250", "1,45,622", "2.5", "10:30", "9:05 PM", "₹250", "₹99.50", "98480 12345",
          "15/08/2026", "50%", "500 mg", "BP", "ATM", "doctor", "Ramesh", "108"]

UI_KEYS = ("speak", "stop", "speaking", "translating", "busy", "ready", "first", "typeHere", "typeNative")
PAGE_KEYS = ("title", "step1", "step2", "phrases_head", "more", "less", "placeholder")


def check(code: str, init: bool) -> list[str]:
    problems: list[str] = []
    try:
        meta = read_meta(code)
        phrases = read_phrases(code)
        prepare = load_prepare(code)
    except (PackError, OSError, SyntaxError) as e:
        return [str(e)]
    for k in UI_KEYS:
        if not meta["ui"].get(k):
            problems.append(f"language.yaml: ui.{k} is missing")
    for k in PAGE_KEYS:
        if not (meta.get("page") or {}).get(k):
            problems.append(f"language.yaml: page.{k} is missing")
    font = os.path.join(ROOT, "web", "static", "fonts", meta.get("script_font", ""))
    if not os.path.isfile(font):
        problems.append(f"language.yaml: script_font {meta.get('script_font')!r} is not in web/static/fonts")
    for p in phrases:
        r = prepare(p["text"])
        if not r.ok:
            problems.append(f"phrase {p['id']!r} has words the voice cannot say: {p['text']!r}")

    path = os.path.join(LANG_DIR, code, "tests.yaml")
    texts = [p["text"] for p in phrases] + COMMON
    if init or not os.path.isfile(path):
        if init:
            rows = []
            for t in texts:
                r = prepare(t)
                rows.append({"text": t, "spoken": r.spoken, "ok": r.ok})
            with open(path, "w", encoding="utf-8") as f:
                yaml.safe_dump(rows, f, allow_unicode=True, sort_keys=False, width=200)
            print(f"{code}: wrote {len(rows)} tests to {path}")
        else:
            problems.append("tests.yaml is missing (run with --init to create it)")
        return problems
    with open(path, encoding="utf-8") as f:
        rows = yaml.safe_load(f) or []
    for row in rows:
        r = prepare(row["text"])
        if (r.spoken, r.ok) != (row["spoken"], row["ok"]):
            problems.append(f"tests.yaml: {row['text']!r}\n      expected {row['spoken']!r} ok={row['ok']}"
                            f"\n      now      {r.spoken!r} ok={r.ok}")
    return problems


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("codes", nargs="*", help="pack codes (default: all)")
    ap.add_argument("--init", action="store_true", help="(re)write tests.yaml from what the pack says now")
    a = ap.parse_args()
    codes = a.codes or list_codes()
    failed = 0
    for code in codes:
        probs = check(code, a.init)
        if probs:
            failed += 1
            print(f"{code}: {len(probs)} problem(s)")
            for p in probs:
                print("   ", p)
        elif not a.init:
            print(f"{code}: ok")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
