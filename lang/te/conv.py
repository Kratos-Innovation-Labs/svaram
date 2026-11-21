# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""Telugu language pack for Svaram: typed text -> what the Telugu voice can say.

Reports anything it cannot say instead of dropping it (FR-14).

    from conv import prepare
    p = prepare("నాకు Dolo 650 కావాలి. 98480 12345 కి ఫోన్ చేయండి.")
    p.spoken        # text for the voice, Telugu script and punctuation only
    p.unspeakable   # [(start, end), ...] spans in the ORIGINAL text that would be skipped
    p.ok            # True when nothing would be skipped

Telugu supplies its own prepare() rather than an indic_conv Spec, because it reads a few
things differently from the shared rules:

  * Phone numbers and service numbers (112, 108, 100 ...) are read digit by
    digit, in groups, never as quantities; "+" is said.
  * Times (10:30) are clock times, with the dative when a suffix follows
    (10:30కి); dates (15/08, 15-08-2026) are day + month.
  * Money with paise (₹99.50) is rupees and paise.
  * A small conversational lexicon (thank you, sorry, doctor, sugar, bus,
    common medicine names) is spoken in Telugu script.
  * Upper-case acronyms (BP, ATM, OTP) are spelled letter by letter.
  * Every other Latin word, and any symbol it cannot read, is REPORTED, never
    silently removed. Names are reported too: rule-based transliteration of
    names mispronounces too often.

Number words come from te_numbers.py in this folder. Standard library only.
"""
from __future__ import annotations

import os
import re
import sys
import unicodedata
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from te_numbers import LATIN_LETTER_TE as LETTER, num_to_te, say_number  # noqa: E402
# ------------------------------------------------------------------ tables --
DIGIT = ["సున్నా", "ఒకటి", "రెండు", "మూడు", "నాలుగు", "ఐదు", "ఆరు", "ఏడు", "ఎనిమిది", "తొమ్మిది"]
MONTH = ["జనవరి", "ఫిబ్రవరి", "మార్చి", "ఏప్రిల్", "మే", "జూన్", "జులై", "ఆగస్టు",
         "సెప్టెంబర్", "అక్టోబర్", "నవంబర్", "డిసెంబర్"]

#: Short numbers people say digit by digit. 3-4 digits only, matched whole.
SERVICE_NUMBERS = {"100", "101", "102", "104", "108", "112", "181", "1098", "1930", "14567"}

#: Conversational English words heard in everyday Telugu, in Telugu script.
#: Lower-case keys; multi-word phrases are matched before single words.
#: DRAFT spellings — to be checked by the native-speaker panel.
LEXICON = {
    "thank you": "థాంక్యూ", "thanks": "థాంక్స్", "sorry": "సారీ", "please": "ప్లీజ్",
    "ok": "ఓకే", "okay": "ఓకే", "hello": "హలో", "hi": "హాయ్", "bye": "బై",
    "good morning": "గుడ్ మార్నింగ్", "good night": "గుడ్ నైట్",
    "excuse me": "ఎక్స్‌క్యూజ్ మీ", "no problem": "నో ప్రాబ్లమ్",
    "yes": "ఎస్", "no": "నో", "sir": "సార్", "madam": "మేడమ్",
    "doctor": "డాక్టర్", "hospital": "హాస్పిటల్", "clinic": "క్లినిక్",
    "medicine": "మెడిసిన్", "medicines": "మెడిసిన్స్", "tablet": "టాబ్లెట్",
    "tablets": "టాబ్లెట్లు", "injection": "ఇంజెక్షన్", "sugar": "షుగర్",
    "fever": "ఫీవర్", "pain": "పెయిన్", "scan": "స్కాన్", "report": "రిపోర్ట్",
    "bus": "బస్", "auto": "ఆటో", "train": "ట్రైన్", "ticket": "టికెట్",
    "station": "స్టేషన్", "stop": "స్టాప్", "phone": "ఫోన్", "mobile": "మొబైల్",
    "number": "నంబర్", "police": "పోలీస్", "ambulance": "అంబులెన్స్",
    "emergency": "ఎమర్జెన్సీ", "help": "హెల్ప్", "water": "వాటర్",
    "toilet": "టాయిలెట్", "bathroom": "బాత్‌రూమ్", "office": "ఆఫీస్",
    "bank": "బ్యాంక్", "card": "కార్డ్", "cash": "క్యాష్", "shop": "షాప్",
    "market": "మార్కెట్", "school": "స్కూల్", "college": "కాలేజ్",
    "address": "అడ్రస్", "left": "లెఫ్ట్", "right": "రైట్", "wait": "వెయిట్",
    # common medicine names
    "dolo": "డోలో", "crocin": "క్రోసిన్", "paracetamol": "పారాసిటమాల్",
}
_PHRASES = sorted((k for k in LEXICON if " " in k), key=len, reverse=True)

#: Punctuation the voice accepts (matches svaram-voice's LANG_CHARS["te"]).
PUNCT = set(" .,?!;:'\"-()।॥\n")
ZW = {"‌", "‍"}


def _is_te(ch: str) -> bool:
    return ("ఀ" <= ch <= "౿" and not "౦" <= ch <= "౯") or ch in ZW


def speakable(text: str) -> bool:
    return all(_is_te(c) or c in PUNCT for c in text)


# ------------------------------------------------------------------ result --
@dataclass
class Prepared:
    spoken: str
    unspeakable: list[tuple[int, int]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.unspeakable


# --------------------------------------------------------------- handlers --
def _digits(s: str) -> str:
    return " ".join(DIGIT[int(c)] for c in s if c.isdigit())


def _phone(m: re.Match) -> str:
    raw = m.group(0)
    parts = []
    if raw.lstrip().startswith("+"):
        parts.append("ప్లస్")
    groups = [g for g in re.split(r"[\s-]+", raw.replace("+", " ").strip()) if g]
    parts.append(", ".join(_digits(g) for g in groups))
    return " ".join(parts)


def _hour_words(h: int) -> str:
    return num_to_te(h)


_DAYPART = ("ఉదయం", "మధ్యాహ్నం", "సాయంత్రం", "రాత్రి", "తెల్లవారుజామున")


def _time(m: re.Match, suffix: str) -> str:
    h, mi = int(m.group("h")), int(m.group("m"))
    ampm = (m.group("ampm") or "").lower().replace(".", "")
    lead = {"am": "ఉదయం ", "pm": "సాయంత్రం "}.get(ampm, "")
    before = m.string[max(0, m.start() - 20):m.start()]
    if lead and any(w in before for w in _DAYPART):
        lead = ""                                  # the user already said it
    if mi == 0:
        return lead + (f"{_hour_words(h)} గంటలకు" if suffix else f"{_hour_words(h)} గంటలు")
    tail = "నిమిషాలకు" if suffix else "నిమిషాలు"
    return lead + f"{_hour_words(h)} గంటల {num_to_te(mi)} {tail}"


def _date(m: re.Match) -> str | None:
    d = int(m.group("d") or m.group("d2"))
    mo = int(m.group("mo") or m.group("mo2"))
    if not (1 <= d <= 31 and 1 <= mo <= 12):
        return None
    out = f"{num_to_te(d)} {MONTH[mo - 1]}"
    y = m.group("y") or m.group("y2")
    if y:
        yi = int(y)
        if len(y) == 2:
            yi += 2000
        out += f" {num_to_te(yi)}"
    return out


def _money(m: re.Match) -> str:
    rupees = int(m.group("r").replace(",", ""))
    paise = m.group("p")
    out = f"{num_to_te(rupees)} రూపాయలు"
    if paise and int(paise):
        p = int(paise.ljust(2, "0")[:2])
        out = f"{num_to_te(rupees)} రూపాయల {num_to_te(p)} పైసలు"
    return out


def _acronym(word: str) -> str | None:
    w = word.replace(".", "")
    if w.isalpha() and w.isupper() and 2 <= len(w) <= 5:
        letters = [LETTER.get(c.lower()) for c in w]
        if all(letters):
            return ".".join(letters) + "."
    return None


# ----------------------------------------------------------------- master --
_SUFFIX = r"(?:\s?(?:కి|కు))?"
PATTERNS = [
    ("phone", re.compile(r"(?<![\d])(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?![\d])"
                         r"|(?<![\d])0\d{2,4}[\s-]?\d{6,8}(?![\d])")),
    ("time", re.compile(r"(?<![\d])(?P<h>[01]?\d|2[0-3]):(?P<m>[0-5]\d)"
                        r"(?:\s?(?P<ampm>[AaPp]\.?[Mm]\.?))?(?![\d])(?P<suf>" + _SUFFIX + ")")),
    # dd/mm, dd-mm, dd/mm/yyyy; with dots only when a year is present, so that
    # decimals such as 3.5 are never read as dates.
    ("date", re.compile(r"(?<![\d.])(?:(?P<d>\d{1,2})[/\-](?P<mo>\d{1,2})(?:[/\-](?P<y>\d{4}|\d{2}))?"
                        r"|(?P<d2>\d{1,2})\.(?P<mo2>\d{1,2})\.(?P<y2>\d{4}))(?![\d])")),
    ("money", re.compile(r"(?:₹|\bRs\.?|\bINR)\s?(?P<r>\d[\d,]*)(?:\.(?P<p>\d{1,2}))?(?![\d])")),
    ("service", re.compile(r"(?<![\d])(?:" + "|".join(sorted(SERVICE_NUMBERS, key=len, reverse=True))
                           + r")(?![\d])")),
    ("numunit", re.compile(r"(?<![\d])\d[\d,]*(?:\.\d+)?\s?(?:%|kg|km|ml|mg|cm|g|l)(?![A-Za-z])", re.I)),
    ("number", re.compile(r"(?<![\d])\d[\d,]*(?:\.\d+)?(?![\d])")),
    ("phrase", re.compile(r"(?i)(?<![A-Za-z])(?:" + "|".join(re.escape(p) for p in _PHRASES)
                          + r")(?![A-Za-z])")),
    ("latin", re.compile(r"[A-Za-z][A-Za-z.']*")),
]


_NUMBER = dict(PATTERNS)["number"]


def _first_match(text: str, pos: int):
    best = None
    for name, rx in PATTERNS:
        m = rx.search(text, pos)
        if m and (best is None or m.start() < best[1].start()):
            best = (name, m)
    return best


def prepare(text: str) -> Prepared:
    """Typed text -> what the Telugu voice says, plus spans it cannot say."""
    text = unicodedata.normalize("NFC", text or "")
    text = "".join(c for c in text if c in "\n\t" or unicodedata.category(c) != "Cc")
    # Telugu digits behave like ASCII digits from here on.
    text = text.translate({0x0C66 + i: ord("0") + i for i in range(10)})

    out: list[str] = []
    bad: list[tuple[int, int]] = []
    pos = 0
    while pos < len(text):
        hit = _first_match(text, pos)
        end_plain = hit[1].start() if hit else len(text)
        # Plain stretch: keep Telugu and punctuation, report anything else.
        for i in range(pos, end_plain):
            c = text[i]
            if _is_te(c) or c in PUNCT:
                out.append(c)
            elif c.isspace():
                out.append(" ")
            elif unicodedata.category(c) in ("So", "Sk", "Mn", "Cf") and not c.isalnum():
                pass                                # emoji and decoration: nothing to say
            else:
                bad.append((i, i + 1))
        if not hit:
            break
        name, m = hit
        rep: str | None
        if name == "phone":
            rep = _phone(m)
        elif name == "time":
            rep = _time(m, m.group("suf").strip())
        elif name == "date":
            rep = _date(m)
            if rep is None:                       # e.g. 31/31 is not a date: read the numbers
                m = _NUMBER.match(text, m.start())
                rep = say_number(m.group(0))
        elif name == "money":
            rep = _money(m)
        elif name == "service":
            rep = _digits(m.group(0))
        elif name in ("numunit", "number"):
            rep = say_number(m.group(0))
        elif name == "phrase":
            rep = LEXICON[m.group(0).lower()]
        else:                                     # latin word
            w = m.group(0).rstrip(".")
            rep = LEXICON.get(w.lower().strip("'")) or _acronym(w)
            if rep is None:
                bad.append((m.start(), m.start() + len(w)))
        if rep is not None:
            nxt = text[m.end():m.end() + 1]
            out.append(f" {rep}" + ("" if nxt and _is_te(nxt) else " "))
        pos = m.end()

    spoken = "".join(out)
    spoken = re.sub(r"\s+([,.;:?!])", r"\1", spoken)
    spoken = re.sub(r"\s+", " ", spoken).strip()
    # Last line of defence: anything still unspeakable is reported, not sent.
    if not speakable(spoken):
        spoken = "".join(c for c in spoken if _is_te(c) or c in PUNCT)
        if not bad:
            bad.append((0, len(text)))
    return Prepared(spoken=spoken, unspeakable=sorted(set(bad)))


if __name__ == "__main__":
    for line in sys.argv[1:] or sys.stdin.read().splitlines():
        p = prepare(line)
        flag = "OK " if p.ok else "FR14"
        print(f"{flag} {line!r}\n     -> {p.spoken!r}  skip={p.unspeakable}")
