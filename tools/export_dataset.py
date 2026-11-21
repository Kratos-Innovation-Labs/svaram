#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""Export the language packs' phrases and test sentences as the svaram-phrases dataset.

    python3 tools/export_dataset.py --out /tmp/svaram-phrases

Writes phrases.{parquet,csv}, test_sentences.{parquet,csv} and the dataset card (README.md),
all built from lang/*/phrases.yaml and lang/*/tests.yaml, so anyone can rebuild the dataset from
the repository. Parquet needs pyarrow (pip install pyarrow); CSV needs nothing extra.
The dataset is CC-BY-4.0; the code that builds it is Apache-2.0.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "core"))
from packs import list_codes, read_meta, read_phrases  # noqa: E402

CARD = """---
license: cc-by-4.0
language:
{langs}
pretty_name: Svaram phrases and test sentences
size_categories:
- n<1K
task_categories:
- text-to-speech
- translation
tags:
- assistive-technology
- aac
- accessibility
- indic
configs:
- config_name: phrases
  data_files: phrases.parquet
  default: true
- config_name: test_sentences
  data_files: test_sentences.parquet
---

# Svaram phrases and test sentences

The quick phrases and test sentences from [Svaram](https://svaram.live), a free type-to-speech
service for people who cannot speak, in {n} Indian languages. They come straight from the language
packs in the [Svaram repository](https://github.com/Kratos-Innovation-Labs/svaram) and are rebuilt
from them by `tools/export_dataset.py`.

## Parts

**phrases** ({np} rows): the quick phrases Svaram shows on its page, with their English meaning.

| Column | Meaning |
|---|---|
| lang | language code (te, hi, ta, ...) |
| language | language name in English |
| id | phrase id, the same across languages (help, doctor, ...) |
| english | the phrase in English |
| text | the phrase in the language, as written |
| core | true for the six phrases on Svaram's main screen; false for the extra ones |

**test_sentences** ({nt} rows): sentences used to check each language pack, with the form the
voice actually reads after Svaram has prepared the text.

| Column | Meaning |
|---|---|
| lang, language | as above |
| text | the sentence as typed |
| spoken | the sentence as the voice reads it: numbers, short forms and symbols written out as words |
| ok | true when every part of the sentence can be spoken |

## Uses

- Starter phrase sets for communication aids (AAC) in Indian languages.
- Test cases for anyone building Indian-language speech or text preparation.

## Limits

- Small: {per_lang} phrases and 30 test sentences per language.
- Written text only, not recordings.
- Written by the Svaram team for a communication aid, so it leans towards needs, health and
  courtesy; it is not a balanced sample of any language.

## Licence and credit

CC-BY-4.0. Please credit "Svaram, Kratos Innovation Labs" and link to
https://github.com/Kratos-Innovation-Labs/svaram.

Languages: {names}.
"""


def rows() -> tuple[list[dict], list[dict]]:
    phrases, tests = [], []
    for code in list_codes():
        meta = read_meta(code)
        if meta["status"] != "live":
            continue
        for p in read_phrases(code):
            phrases.append({"lang": code, "language": meta["name"], "id": p["id"], "english": p["english"],
                            "text": p["text"], "core": not p.get("extra", False)})
        path = os.path.join(ROOT, "lang", code, "tests.yaml")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                for t in yaml.safe_load(f) or []:
                    tests.append({"lang": code, "language": meta["name"], "text": t["text"],
                                  "spoken": t.get("spoken", ""), "ok": bool(t.get("ok", True))})
    return phrases, tests


def write(out: str, name: str, data: list[dict], parquet: bool) -> None:
    with open(os.path.join(out, f"{name}.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(data[0]))
        w.writeheader()
        w.writerows(data)
    if parquet:
        import pyarrow as pa  # noqa: PLC0415
        import pyarrow.parquet as pq  # noqa: PLC0415
        pq.write_table(pa.Table.from_pylist(data), os.path.join(out, f"{name}.parquet"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-parquet", action="store_true", help="CSV only (no pyarrow needed)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    phrases, tests = rows()
    write(a.out, "phrases", phrases, not a.no_parquet)
    write(a.out, "test_sentences", tests, not a.no_parquet)
    codes = sorted({r["lang"] for r in phrases})
    names = sorted({r["language"] for r in phrases})
    card = CARD.format(langs="\n".join(f"- {c}" for c in codes), n=len(codes), np=len(phrases),
                       nt=len(tests), per_lang=len(phrases) // max(len(codes), 1), names=", ".join(names))
    with open(os.path.join(a.out, "README.md"), "w", encoding="utf-8") as f:
        f.write(card)
    print(f"{len(phrases)} phrases, {len(tests)} test sentences, {len(codes)} languages -> {a.out}")


if __name__ == "__main__":
    main()
