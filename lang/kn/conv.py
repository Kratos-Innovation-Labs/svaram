# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""Kannada language pack for Svaram . Words only; the logic is in indic_conv."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "core"))
from indic_conv import Spec, glue_vowel  # noqa: E402

ONES = ("ಸೊನ್ನೆ ಒಂದು ಎರಡು ಮೂರು ನಾಲ್ಕು ಐದು ಆರು ಏಳು ಎಂಟು ಒಂಬತ್ತು ಹತ್ತು ಹನ್ನೊಂದು ಹನ್ನೆರಡು ಹದಿಮೂರು "
        "ಹದಿನಾಲ್ಕು ಹದಿನೈದು ಹದಿನಾರು ಹದಿನೇಳು ಹದಿನೆಂಟು ಹತ್ತೊಂಬತ್ತು").split()
TENS = dict(zip(range(2, 10), "ಇಪ್ಪತ್ತು ಮೂವತ್ತು ನಲವತ್ತು ಐವತ್ತು ಅರವತ್ತು ಎಪ್ಪತ್ತು ಎಂಬತ್ತು ತೊಂಬತ್ತು".split()))
HUND = dict(zip(range(1, 10), "ನೂರು ಇನ್ನೂರು ಮುನ್ನೂರು ನಾನೂರು ಐನೂರು ಆರುನೂರು ಏಳುನೂರು ಎಂಟುನೂರು ಒಂಬೈನೂರು".split()))
V = {"ಅ": "", "ಆ": "ಾ", "ಇ": "ಿ", "ಈ": "ೀ", "ಉ": "ು", "ಊ": "ೂ", "ಎ": "ೆ", "ಏ": "ೇ", "ಐ": "ೈ", "ಒ": "ೊ", "ಓ": "ೋ"}


def _stem(w):                       # ಇಪ್ಪತ್ತು -> ಇಪ್ಪತ್ತ, ನೂರು -> ನೂರ
    return w[:-1] if w.endswith("ು") else w


def _u100(n):
    if n < 20:
        return ONES[n]
    t, u = divmod(n, 10)
    return TENS[t] if not u else glue_vowel(_stem(TENS[t]), ONES[u], V)   # ಇಪ್ಪತ್ತೊಂದು


def _u1000(n):
    h, r = divmod(n, 100)
    if not h:
        return _u100(r)
    if not r:
        return HUND[h]
    rest = _u100(r)
    if rest[0] in V:
        return glue_vowel(_stem(HUND[h]), rest, V)        # ನೂರೈವತ್ತು
    return f"{_stem(HUND[h])} {rest}"                     # ನೂರ ನಲವತ್ತು


def num(n: int) -> str:
    if n < 0:
        return "ಮೈನಸ್ " + num(-n)
    if n < 1000:
        return _u1000(n)
    parts = []
    cr, n = divmod(n, 10 ** 7)
    lk, n = divmod(n, 10 ** 5)
    th, n = divmod(n, 1000)
    if cr:
        parts.append(f"{num(cr)} ಕೋಟಿ")
    if lk:
        parts.append(f"{_u1000(lk)} " + ("ಲಕ್ಷದ" if (th or n) else "ಲಕ್ಷ"))
    if th:
        parts.append(f"{_u1000(th)} " + ("ಸಾವಿರದ" if n else "ಸಾವಿರ"))
    if n:
        parts.append(_u1000(n))
    return " ".join(parts)


SPEC = Spec(
    code="kn", name="Kannada", native="ಕನ್ನಡ", block=("ಀ", "೿"), digit0="೦",
    num=num, digits=ONES[:10], point="ಪಾಯಿಂಟ್", minus="ಮೈನಸ್",
    months="ಜನವರಿ ಫೆಬ್ರವರಿ ಮಾರ್ಚ್ ಏಪ್ರಿಲ್ ಮೇ ಜೂನ್ ಜುಲೈ ಆಗಸ್ಟ್ ಸೆಪ್ಟೆಂಬರ್ ಅಕ್ಟೋಬರ್ ನವೆಂಬರ್ ಡಿಸೆಂಬರ್".split(),
    letters=dict(zip("abcdefghijklmnopqrstuvwxyz",
                     "ಎ ಬಿ ಸಿ ಡಿ ಇ ಎಫ್ ಜಿ ಎಚ್ ಐ ಜೆ ಕೆ ಎಲ್ ಎಂ ಎನ್ ಒ ಪಿ ಕ್ಯೂ ಆರ್ ಎಸ್ ಟಿ ಯು ವಿ ಡಬ್ಲ್ಯೂ ಎಕ್ಸ್ ವೈ ಜೆಡ್".split())),
    units={"%": "ಶೇಕಡಾ", "kg": "ಕಿಲೋ", "km": "ಕಿಲೋಮೀಟರ್", "ml": "ಮಿಲಿ", "mg": "ಮಿಲಿಗ್ರಾಂ",
           "cm": "ಸೆಂಟಿಮೀಟರ್", "g": "ಗ್ರಾಂ", "l": "ಲೀಟರ್"},
    unit_before={"%"},
    lexicon={
        "ok": "ಓಕೆ", "okay": "ಓಕೆ", "hello": "ಹಲೋ", "please": "ಪ್ಲೀಸ್", "sorry": "ಸಾರಿ", "thanks": "ಥ್ಯಾಂಕ್ಸ್",
        "doctor": "ಡಾಕ್ಟರ್", "dr": "ಡಾಕ್ಟರ್", "nurse": "ನರ್ಸ್", "hospital": "ಹಾಸ್ಪಿಟಲ್", "clinic": "ಕ್ಲಿನಿಕ್",
        "medical": "ಮೆಡಿಕಲ್", "tablet": "ಟ್ಯಾಬ್ಲೆಟ್", "tablets": "ಟ್ಯಾಬ್ಲೆಟ್", "capsule": "ಕ್ಯಾಪ್ಸೂಲ್", "syrup": "ಸಿರಪ್",
        "injection": "ಇಂಜೆಕ್ಷನ್", "ambulance": "ಆಂಬ್ಯುಲೆನ್ಸ್", "emergency": "ಎಮರ್ಜೆನ್ಸಿ", "police": "ಪೊಲೀಸ್",
        "bus": "ಬಸ್", "auto": "ಆಟೋ", "metro": "ಮೆಟ್ರೋ", "train": "ಟ್ರೈನ್", "station": "ಸ್ಟೇಷನ್",
        "ticket": "ಟಿಕೆಟ್", "toilet": "ಟಾಯ್ಲೆಟ್", "phone": "ಫೋನ್", "mobile": "ಮೊಬೈಲ್", "bank": "ಬ್ಯಾಂಕ್",
        "card": "ಕಾರ್ಡ್", "cash": "ಕ್ಯಾಶ್", "bill": "ಬಿಲ್", "sugar": "ಶುಗರ್", "diabetes": "ಡಯಾಬಿಟೀಸ್",
        "pressure": "ಪ್ರೆಶರ್", "fever": "ಫೀವರ್", "allergy": "ಅಲರ್ಜಿ", "test": "ಟೆಸ್ಟ್", "report": "ರಿಪೋರ್ಟ್",
        "scan": "ಸ್ಕ್ಯಾನ್", "paracetamol": "ಪ್ಯಾರಸಿಟಮಾಲ್", "dolo": "ಡೋಲೋ", "crocin": "ಕ್ರೋಸಿನ್", "calpol": "ಕ್ಯಾಲ್ಪೋಲ್",
        "penicillin": "ಪೆನಿಸಿಲಿನ್", "amoxicillin": "ಅಮಾಕ್ಸಿಸಿಲಿನ್", "azithromycin": "ಅಜಿಥ್ರೋಮೈಸಿನ್",
        "ibuprofen": "ಐಬುಪ್ರೊಫೆನ್", "cetirizine": "ಸೆಟಿರಿಜಿನ್", "insulin": "ಇನ್ಸುಲಿನ್", "metformin": "ಮೆಟ್‌ಫಾರ್ಮಿನ್",
        "aspirin": "ಆಸ್ಪಿರಿನ್", "pantoprazole": "ಪ್ಯಾಂಟೊಪ್ರಜೋಲ್", "omeprazole": "ಒಮೆಪ್ರಜೋಲ್", "vicks": "ವಿಕ್ಸ್",
        "dettol": "ಡೆಟಾಲ್",
    },
    phrases={"thank you": "ಥ್ಯಾಂಕ್ ಯೂ", "good morning": "ಗುಡ್ ಮಾರ್ನಿಂಗ್", "good night": "ಗುಡ್ ನೈಟ್"},
    rupee=("ರೂಪಾಯಿ", "ರೂಪಾಯಿ"), paise="ಪೈಸೆ", hour="ಗಂಟೆ", minute="ನಿಮಿಷ",
    dayparts={"am": "ಬೆಳಿಗ್ಗೆ", "noon": "ಮಧ್ಯಾಹ್ನ", "eve": "ಸಂಜೆ", "night": "ರಾತ್ರಿ"},
    hour_words=("ಗಂಟೆ",),
    abbrev={"ಮಿ.ಗ್ರಾಂ": "ಮಿಲಿಗ್ರಾಂ", "ಮಿ.ಗ್ರಾ.": "ಮಿಲಿಗ್ರಾಂ", "ಕಿ.ಗ್ರಾಂ": "ಕಿಲೋಗ್ರಾಂ", "ಕಿ.ಮೀ.": "ಕಿಲೋಮೀಟರ್", "ಕಿ.ಮೀ": "ಕಿಲೋಮೀಟರ್", "ಮಿ.ಲೀ": "ಮಿಲಿಲೀಟರ್"},
)
