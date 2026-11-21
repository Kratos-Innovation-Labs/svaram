# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""Punjabi (Gurmukhi) language pack for Svaram.
Number words 0-99 are irregular and listed in full: draft for a Punjabi reviewer."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "core"))
from indic_conv import Spec  # noqa: E402

U = ("ਸਿਫ਼ਰ ਇੱਕ ਦੋ ਤਿੰਨ ਚਾਰ ਪੰਜ ਛੇ ਸੱਤ ਅੱਠ ਨੌਂ ਦਸ ਗਿਆਰਾਂ ਬਾਰਾਂ ਤੇਰਾਂ ਚੌਦਾਂ ਪੰਦਰਾਂ ਸੋਲਾਂ ਸਤਾਰਾਂ ਅਠਾਰਾਂ ਉੱਨੀ "
     "ਵੀਹ ਇੱਕੀ ਬਾਈ ਤੇਈ ਚੌਵੀ ਪੱਚੀ ਛੱਬੀ ਸਤਾਈ ਅਠਾਈ ਉਨੱਤੀ "
     "ਤੀਹ ਇਕੱਤੀ ਬੱਤੀ ਤੇਤੀ ਚੌਂਤੀ ਪੈਂਤੀ ਛੱਤੀ ਸੈਂਤੀ ਅਠੱਤੀ ਉਨਤਾਲੀ "
     "ਚਾਲੀ ਇਕਤਾਲੀ ਬਿਆਲੀ ਤਰਤਾਲੀ ਚੁਤਾਲੀ ਪੰਤਾਲੀ ਛਿਆਲੀ ਸੰਤਾਲੀ ਅਠਤਾਲੀ ਉਨੰਜਾ "
     "ਪੰਜਾਹ ਇਕਵੰਜਾ ਬਵੰਜਾ ਤਰਵੰਜਾ ਚਰਵੰਜਾ ਪਚਵੰਜਾ ਛਪੰਜਾ ਸਤਵੰਜਾ ਅਠਵੰਜਾ ਉਨਾਹਠ "
     "ਸੱਠ ਇਕਾਹਠ ਬਾਹਠ ਤਰੇਹਠ ਚੌਂਹਠ ਪੈਂਹਠ ਛਿਆਹਠ ਸਤਾਹਠ ਅਠਾਹਠ ਉਨੱਤਰ "
     "ਸੱਤਰ ਇਕਹੱਤਰ ਬਹੱਤਰ ਤਿਹੱਤਰ ਚੌਹੱਤਰ ਪਚੱਤਰ ਛਿਹੱਤਰ ਸਤੱਤਰ ਅਠੱਤਰ ਉਨਾਸੀ "
     "ਅੱਸੀ ਇਕਾਸੀ ਬਿਆਸੀ ਤਿਰਾਸੀ ਚੁਰਾਸੀ ਪਚਾਸੀ ਛਿਆਸੀ ਸਤਾਸੀ ਅਠਾਸੀ ਉਨੱਨਵੇਂ "
     "ਨੱਬੇ ਇਕਾਨਵੇਂ ਬਾਨਵੇਂ ਤਿਰਾਨਵੇਂ ਚੁਰਾਨਵੇਂ ਪਚਾਨਵੇਂ ਛਿਆਨਵੇਂ ਸਤਾਨਵੇਂ ਅਠਾਨਵੇਂ ਨੜਿੰਨਵੇਂ").split()
assert len(U) == 100


def _u1000(n):
    h, r = divmod(n, 100)
    if not h:
        return U[r]
    return f"{U[h]} ਸੌ" + (f" {U[r]}" if r else "")


def num(n: int) -> str:
    if n < 0:
        return "ਮਾਈਨਸ " + num(-n)
    parts = []
    cr, n = divmod(n, 10 ** 7)
    lk, n = divmod(n, 10 ** 5)
    th, n = divmod(n, 1000)
    if cr:
        parts.append(f"{num(cr)} ਕਰੋੜ")
    if lk:
        parts.append(f"{U[lk]} ਲੱਖ")
    if th:
        parts.append(f"{U[th]} ਹਜ਼ਾਰ")
    if n or not parts:
        parts.append(_u1000(n))
    return " ".join(parts)


SPEC = Spec(
    code="pa", name="Punjabi", native="ਪੰਜਾਬੀ", block=("਀", "੿"), digit0="੦",
    num=num, digits=U[:10], point="ਦਸ਼ਮਲਵ", minus="ਮਾਈਨਸ",
    months="ਜਨਵਰੀ ਫ਼ਰਵਰੀ ਮਾਰਚ ਅਪ੍ਰੈਲ ਮਈ ਜੂਨ ਜੁਲਾਈ ਅਗਸਤ ਸਤੰਬਰ ਅਕਤੂਬਰ ਨਵੰਬਰ ਦਸੰਬਰ".split(),
    letters=dict(zip("abcdefghijklmnopqrstuvwxyz",
                     "ਏ ਬੀ ਸੀ ਡੀ ਈ ਐੱਫ ਜੀ ਐੱਚ ਆਈ ਜੇ ਕੇ ਐੱਲ ਐੱਮ ਐੱਨ ਓ ਪੀ ਕਿਊ ਆਰ ਐੱਸ ਟੀ ਯੂ ਵੀ ਡਬਲਯੂ ਐਕਸ ਵਾਈ ਜ਼ੈੱਡ".split())),
    units={"%": "ਪ੍ਰਤੀਸ਼ਤ", "kg": "ਕਿਲੋ", "km": "ਕਿਲੋਮੀਟਰ", "ml": "ਮਿਲੀ", "mg": "ਮਿਲੀਗ੍ਰਾਮ",
           "cm": "ਸੈਂਟੀਮੀਟਰ", "g": "ਗ੍ਰਾਮ", "l": "ਲੀਟਰ"},
    unit_before=set(),
    lexicon={
        "ok": "ਓਕੇ", "okay": "ਓਕੇ", "hello": "ਹੈਲੋ", "please": "ਪਲੀਜ਼", "sorry": "ਸੌਰੀ", "thanks": "ਥੈਂਕਸ",
        "doctor": "ਡਾਕਟਰ", "dr": "ਡਾਕਟਰ", "nurse": "ਨਰਸ", "hospital": "ਹਸਪਤਾਲ", "clinic": "ਕਲੀਨਿਕ",
        "medical": "ਮੈਡੀਕਲ", "tablet": "ਟੈਬਲੇਟ", "tablets": "ਟੈਬਲੇਟ", "capsule": "ਕੈਪਸੂਲ", "syrup": "ਸਿਰਪ",
        "injection": "ਇੰਜੈਕਸ਼ਨ", "ambulance": "ਐਂਬੂਲੈਂਸ", "emergency": "ਐਮਰਜੈਂਸੀ", "police": "ਪੁਲਿਸ",
        "bus": "ਬੱਸ", "auto": "ਆਟੋ", "metro": "ਮੈਟਰੋ", "train": "ਟ੍ਰੇਨ", "station": "ਸਟੇਸ਼ਨ", "ticket": "ਟਿਕਟ",
        "toilet": "ਟਾਇਲਟ", "phone": "ਫ਼ੋਨ", "mobile": "ਮੋਬਾਈਲ", "bank": "ਬੈਂਕ", "card": "ਕਾਰਡ", "cash": "ਕੈਸ਼",
        "bill": "ਬਿੱਲ", "sugar": "ਸ਼ੂਗਰ", "diabetes": "ਡਾਇਬਟੀਜ਼", "pressure": "ਪ੍ਰੈਸ਼ਰ", "fever": "ਬੁਖ਼ਾਰ",
        "allergy": "ਐਲਰਜੀ", "test": "ਟੈਸਟ", "report": "ਰਿਪੋਰਟ", "scan": "ਸਕੈਨ",
        "paracetamol": "ਪੈਰਾਸੀਟਾਮੋਲ", "dolo": "ਡੋਲੋ", "crocin": "ਕ੍ਰੋਸਿਨ", "calpol": "ਕੈਲਪੋਲ",
        "penicillin": "ਪੈਨਿਸਿਲਿਨ", "amoxicillin": "ਅਮੋਕਸੀਸਿਲਿਨ", "azithromycin": "ਐਜ਼ੀਥ੍ਰੋਮਾਈਸਿਨ",
        "ibuprofen": "ਆਈਬਿਊਪ੍ਰੋਫ਼ੈਨ", "cetirizine": "ਸੈਟਿਰਿਜ਼ੀਨ", "insulin": "ਇਨਸੁਲਿਨ", "metformin": "ਮੈਟਫਾਰਮਿਨ",
        "aspirin": "ਐਸਪਰੀਨ", "pantoprazole": "ਪੈਂਟੋਪ੍ਰਾਜ਼ੋਲ", "omeprazole": "ਓਮੇਪ੍ਰਾਜ਼ੋਲ", "vicks": "ਵਿਕਸ",
        "dettol": "ਡੈਟੋਲ",
    },
    phrases={"thank you": "ਥੈਂਕ ਯੂ", "good morning": "ਗੁੱਡ ਮਾਰਨਿੰਗ", "good night": "ਗੁੱਡ ਨਾਈਟ"},
    rupee=("ਰੁਪਈਆ", "ਰੁਪਏ"), paise="ਪੈਸੇ", hour="ਵਜੇ", hour_min="ਵੱਜ ਕੇ", minute="ਮਿੰਟ",
    dayparts={"am": "ਸਵੇਰੇ", "noon": "ਦੁਪਹਿਰ", "eve": "ਸ਼ਾਮ", "night": "ਰਾਤ"},
    hour_words=("ਵਜੇ",),
)
