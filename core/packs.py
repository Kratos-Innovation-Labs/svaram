# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""Language packs: one folder per language under lang/ (see docs/adding-a-language.md).

    from packs import load_all
    packs = load_all()                 # {"te": Pack, "hi": Pack, ...}, live packs only
    p = packs["te"].prepare("నాకు 2 మాత్రలు కావాలి")
    packs["te"].meta["voice"]          # {"service": "rasa", "voice": "19:4"}

A pack folder holds:
    language.yaml   code, names, voice, translation target, segment sizes, page words
    conv.py         either SPEC (an indic_conv.Spec: words only) or prepare(text) -> Prepared
    phrases.yaml    the quick phrases
    tests.yaml      sentences for checking the pack (optional)

Every prepare() has the same contract: .spoken (what the voice says), .unspeakable
(spans of the original text that cannot be said), .ok.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from dataclasses import dataclass, field
from typing import Callable

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANG_DIR = os.environ.get("SVARAM_LANG_DIR", os.path.join(ROOT, "lang"))
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)

from indic_conv import Lang  # noqa: E402

REQUIRED = ("code", "name", "native", "script_block", "status", "voice", "segments", "ui")
VOICE_SERVICES = ("rasa", "kokoro", "indictts")


class PackError(ValueError):
    pass


@dataclass
class Pack:
    code: str
    meta: dict
    phrases: list = field(default_factory=list)
    prepare: Callable | None = None


def read_meta(code: str, lang_dir: str = LANG_DIR) -> dict:
    path = os.path.join(lang_dir, code, "language.yaml")
    with open(path, encoding="utf-8") as f:
        meta = yaml.safe_load(f) or {}
    missing = [k for k in REQUIRED if k not in meta]
    if missing:
        raise PackError(f"{path}: missing {', '.join(missing)}")
    if meta["code"] != code:
        raise PackError(f"{path}: code is {meta['code']!r} but the folder is {code!r}")
    if meta["voice"].get("service") not in VOICE_SERVICES:
        raise PackError(f"{path}: voice.service must be one of {', '.join(VOICE_SERVICES)}")
    if meta["status"] not in ("live", "testing"):
        raise PackError(f"{path}: status must be live or testing")
    sb = meta.get("script_block")
    if not (isinstance(sb, list) and len(sb) == 2 and all(isinstance(x, str) for x in sb)):
        raise PackError(f"{path}: script_block must be two quoted hex values, e.g. [\"0C00\", \"0C7F\"]")
    return meta


def script_range(meta: dict) -> tuple[str, str]:
    """The pack's Unicode block as two characters, e.g. ("\u0c00", "\u0c7f")."""
    lo, hi = meta["script_block"]
    return chr(int(lo, 16)), chr(int(hi, 16))


def script_zero(meta: dict) -> int:
    """Code point of the script's own digit zero (every Indic block keeps it at +0x66)."""
    return int(meta["script_block"][0], 16) + 0x66


def read_phrases(code: str, lang_dir: str = LANG_DIR) -> list:
    path = os.path.join(lang_dir, code, "phrases.yaml")
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as f:
        items = yaml.safe_load(f) or []
    for it in items:
        if not {"id", "english", "text"} <= set(it):
            raise PackError(f"{path}: every phrase needs id, english and text")
    return items


def load_prepare(code: str, lang_dir: str = LANG_DIR) -> Callable:
    """The pack's prepare(): its own function, or the shared rules applied to its SPEC."""
    path = os.path.join(lang_dir, code, "conv.py")
    name = f"svaram_lang_{code}"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod                        # dataclasses need the module registered
    spec.loader.exec_module(mod)
    if hasattr(mod, "prepare"):
        return mod.prepare
    if hasattr(mod, "SPEC"):
        return Lang(mod.SPEC).prepare
    raise PackError(f"{path}: defines neither prepare() nor SPEC")


def list_codes(lang_dir: str = LANG_DIR) -> list[str]:
    return sorted(d for d in os.listdir(lang_dir)
                  if os.path.isfile(os.path.join(lang_dir, d, "language.yaml")))


def load_all(lang_dir: str = LANG_DIR, include_testing: bool = False, with_prepare: bool = True) -> dict[str, Pack]:
    out: dict[str, Pack] = {}
    for code in list_codes(lang_dir):
        meta = read_meta(code, lang_dir)
        if meta["status"] != "live" and not include_testing:
            continue
        out[code] = Pack(code=code, meta=meta, phrases=read_phrases(code, lang_dir),
                         prepare=load_prepare(code, lang_dir) if with_prepare else None)
    return out
