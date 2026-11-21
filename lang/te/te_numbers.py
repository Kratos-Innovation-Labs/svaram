# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""Telugu number words for the Telugu language pack.

Integers in the Indian system (వేలు, లక్షలు, కోట్లు), decimals read digit by digit after
the point, percentages and the short units a person types (kg, g, mg, l, ml, km, cm).

say_number() is used by conv.py for a number, or a number with a unit or a percent sign,
that conv.py has already found in the text. Standard library only.
"""
from __future__ import annotations

import re

ONES = {
    0: "సున్నా", 1: "ఒకటి", 2: "రెండు", 3: "మూడు", 4: "నాలుగు",
    5: "ఐదు", 6: "ఆరు", 7: "ఏడు", 8: "ఎనిమిది", 9: "తొమ్మిది",
    10: "పది", 11: "పదకొండు", 12: "పన్నెండు", 13: "పదమూడు", 14: "పద్నాలుగు",
    15: "పదిహేను", 16: "పదహారు", 17: "పదిహేడు", 18: "పద్దెనిమిది", 19: "పందొమ్మిది",
}
TENS = {
    2: "ఇరవై", 3: "ముప్పై", 4: "నలభై", 5: "యాభై",
    6: "అరవై", 7: "డెబ్బై", 8: "ఎనభై", 9: "తొంభై",
}

#: Units conv.py recognises after a number, in their plural (counted) form.
UNITS = {
    "kg": "కిలోలు", "g": "గ్రాములు", "mg": "మిల్లీగ్రాములు",
    "cm": "సెంటీమీటర్లు", "km": "కిలోమీటర్లు",
    "l": "లీటర్లు", "ml": "మిల్లీలీటర్లు",
}

#: Latin letters as said in Telugu, for acronyms spelled letter by letter (BP, ATM).
LATIN_LETTER_TE = {
    "a": "ఏ", "b": "బి", "c": "సి", "d": "డి", "e": "ఈ", "f": "ఎఫ్",
    "g": "జి", "h": "హెచ్", "i": "ఐ", "j": "జె", "k": "కే", "l": "ఎల్",
    "m": "ఎం", "n": "ఎన్", "o": "ఓ", "p": "పి", "q": "క్యూ", "r": "ఆర్",
    "s": "ఎస్", "t": "టి", "u": "యు", "v": "వి", "w": "డబ్ల్యూ",
    "x": "ఎక్స్", "y": "వై", "z": "జెడ్",
}


def _under_100(n: int) -> str:
    if n < 20:
        return ONES[n]
    t, r = divmod(n, 10)
    return TENS[t] if r == 0 else f"{TENS[t]} {ONES[r]}"


def _under_1000(n: int) -> str:
    if n < 100:
        return _under_100(n)
    h, r = divmod(n, 100)
    head = "వంద" if h == 1 else f"{ONES[h]} వందల"
    if r == 0:
        return "వంద" if h == 1 else f"{ONES[h]} వందలు"
    return f"{head} {_under_100(r)}"


def num_to_te(n: int) -> str:
    """Integer -> Telugu words, Indian numbering (lakh, crore)."""
    if n < 0:
        return "మైనస్ " + num_to_te(-n)
    if n == 0:
        return ONES[0]
    parts: list[str] = []
    crore, n = divmod(n, 10_000_000)
    lakh, n = divmod(n, 100_000)
    thousand, rest = divmod(n, 1000)
    if crore:
        parts.append(f"{_under_1000(crore)} కోట్ల" if crore > 1 else "ఒక కోటి")
    if lakh:
        parts.append(f"{_under_1000(lakh)} లక్షల" if lakh > 1 else "ఒక లక్ష")
    if thousand:
        parts.append("వెయ్యి" if thousand == 1 else f"{_under_1000(thousand)} వేల")
    if rest:
        parts.append(_under_1000(rest))
    out = " ".join(parts)
    # the genitive form is only right when something follows it
    out = re.sub(r"\bకోట్ల$", "కోట్లు", out)
    out = re.sub(r"\bలక్షల$", "లక్షలు", out)
    out = re.sub(r"\bవేల$", "వేలు", out)
    return out


def decimal_to_te(s: str) -> str:
    """'0.35' -> 'సున్నా పాయింట్ మూడు ఐదు': digits after the point one by one."""
    s = s.replace(",", "")
    neg = s.startswith("-")
    s = s.lstrip("-+")
    whole, _, frac = s.partition(".")
    out = num_to_te(int(whole or 0))
    if frac:
        out = f"{out} పాయింట్ " + " ".join(ONES[int(d)] for d in frac)
    return ("మైనస్ " + out) if neg else out


_NUM = r"\d+(?:,\d{2,3})*(?:\.\d+)?"
_PERCENT = re.compile(rf"({_NUM})\s*%")
_NUMUNIT = re.compile(r"(\d+(?:[\d,]*\.?\d*))\s*([A-Za-z]+)\b")
_BARE = re.compile(r"(?<![\d.,])\d(?:[\d,]*\d)?(?:\.\d+)?")


def say_number(s: str) -> str:
    """A number, or a number with %, kg, g, mg, l, ml, km or cm, as Telugu words.

    '1,500' -> 'వెయ్యి ఐదు వందలు', '2.5 ml' -> 'రెండు పాయింట్ ఐదు మిల్లీలీటర్లు',
    '50%' -> 'యాభై శాతం'. A trailing comma stays, so a list keeps its pauses.
    """
    t = _PERCENT.sub(lambda m: f" {decimal_to_te(m.group(1))} శాతం ", s)

    def _numunit(m: re.Match) -> str:
        n, u = m.group(1), m.group(2).lower()
        return f" {decimal_to_te(n)} {UNITS[u]} " if u in UNITS else m.group(0)

    t = _NUMUNIT.sub(_numunit, t)

    def _bare(m: re.Match) -> str:
        nxt = m.string[m.end():m.end() + 1]
        return f" {decimal_to_te(m.group(0))}" + ("" if "ఀ" <= nxt <= "౿" else " ")

    t = _BARE.sub(_bare, t)
    t = re.sub(r"\s*([,.;:?!])\s*", r"\1 ", t)
    t = re.sub(r"(,\s*){2,}", ", ", t)
    return re.sub(r"\s+", " ", t).strip()
