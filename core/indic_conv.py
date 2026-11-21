# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""indic_conv — shared text preparation for Svaram language packs.

Each language pack (lang/<code>/conv.py) describes its words in a Spec; this module turns
typed or translated text into what the voice should say, with the same contract as te_conv and
hi_conv, so every language is called the same way:

    from indic_conv import load
    ta = load("ta")
    p = ta.prepare("எனக்கு 2 மாத்திரை 10:30 மணிக்கு வேண்டும், ₹250")
    p.ok            # False if something could not be said
    p.spoken        # the language's letters and punctuation only
    p.unspeakable   # [(start, end), ...] spans in the ORIGINAL text that would be skipped
    p.numbers       # the readings made from digits (used by the listening test)

Reads: numbers in the Indian system, decimals, phone numbers digit by digit, times, dates,
rupees and paise, units, short forms letter by letter (BP, ATM) and common English and medicine
words written in Latin letters. Anything else in Latin letters is reported, never dropped
silently (FR-14). A suffix written straight after a number (10:30க்கு, 2ಕ್ಕೆ) stays attached
to the reading. Standard library only.
"""
from __future__ import annotations

import importlib.util
import os
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Callable

PUNCT = set(" \n\t.,?!;:-\"()")          # no apostrophe: the voice cannot say it
JOINERS = {"‌", "‍"}


@dataclass
class Prepared:
    spoken: str
    unspeakable: list[tuple[int, int]] = field(default_factory=list)
    numbers: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.unspeakable


@dataclass
class Spec:
    code: str                       # "ta"
    name: str                       # "Tamil"
    native: str                     # "தமிழ்"
    block: tuple[str, str]          # the script's Unicode block
    digit0: str                     # the script's own zero (its digits become ASCII first)
    num: Callable[[int], str]       # integer -> words
    digits: list[str]               # 0..9 as words, for phone numbers and decimals
    point: str                      # decimal point word
    minus: str
    months: list[str]
    letters: dict[str, str]         # a..z as said in this language
    units: dict[str, str]
    unit_before: set[str]           # units said before the number (Kannada ಶೇಕಡಾ)
    lexicon: dict[str, str]
    phrases: dict[str, str]
    rupee: tuple[str, str]          # (one rupee, rupees)
    paise: str
    hour: str                       # o'clock word
    minute: str
    dayparts: dict[str, str]        # am, noon, eve, night
    hour_words: tuple[str, ...] = ()   # a following hour word is absorbed after a time
    hour_min: str = ""                 # hour word when minutes follow, if different (Marathi वाजून, Punjabi ਵੱਜ ਕੇ)
    hour_glue: bool = False            # hour word written onto the number (Bengali দশটা)
    abbrev: dict = field(default_factory=dict)   # unit short forms in the script, said in full (மி.கி -> மில்லிகிராம்)
    apostrophe_vowel: str = ""         # Assamese: ক'ত (where) is said কোত, not কত (how many)
    extra_ok: str = ""             # other characters that may stay (e.g. Tamil ஃ is in the block anyway)


class Lang:
    def __init__(self, s: Spec):
        self.s = s
        lo, hi = s.block
        z = ord(s.digit0)
        self._digits = {z + i: ord("0") + i for i in range(10)}
        self._lo, self._hi, self._z = lo, hi, z
        self._virama = chr(ord(lo) + 0x4D)              # same place in every Indic block
        hour_alt = "|".join(re.escape(w) for w in s.hour_words)
        absorb = rf"(?:\s*(?:{hour_alt}))?" if hour_alt else ""
        self.patterns = [
            ("phone", re.compile(r"(?<![\d])(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?![\d])"
                                 r"|(?<![\d])0\d{2,4}[\s-]?\d{6,8}(?![\d])")),
            ("time", re.compile(r"(?<![\d])(?P<h>[01]?\d|2[0-3]):(?P<m>[0-5]\d)"
                                r"(?:\s?(?P<ampm>[AaPp]\.?[Mm]\.?))?(?![\d])" + absorb)),
            ("date", re.compile(r"(?<![\d.])(?:(?P<d>\d{1,2})[/\-](?P<mo>\d{1,2})(?:[/\-](?P<y>\d{4}|\d{2}))?"
                                r"|(?P<d2>\d{1,2})\.(?P<mo2>\d{1,2})\.(?P<y2>\d{4}))(?![\d])")),
            ("money", re.compile(r"(?:₹|\bRs\.?|\bINR)\s?(?P<r>\d[\d,]*)(?:\.(?P<p>\d{1,2}))?(?![\d])")),
            ("numunit", re.compile(r"(?<![\d])(?P<n>\d[\d,]*(?:\.\d+)?)\s?(?P<u>%|kg|km|ml|mg|cm|g|l)(?![A-Za-z])", re.I)),
            ("number", re.compile(r"(?<![\d])\d[\d,]*(?:\.\d+)?(?![\d])")),
            ("phrase", re.compile(r"(?i)(?<![A-Za-z])(?:" + "|".join(re.escape(p) for p in s.phrases) + r")(?![A-Za-z])")
             if s.phrases else None),
            ("latin", re.compile(r"[A-Za-z][A-Za-z.'’]*")),
        ]
        self.patterns = [(n, rx) for n, rx in self.patterns if rx is not None]
        self._number_rx = dict(self.patterns)["number"]

    # ---------------------------------------------------------- letters --
    def is_letter(self, c: str) -> bool:
        if c in self.s.extra_ok:
            return True
        return self._lo <= c <= self._hi and not (self._z <= ord(c) <= self._z + 9)

    def speakable(self, text: str) -> bool:
        return all(self.is_letter(c) or c in PUNCT or c in JOINERS for c in text)

    # ---------------------------------------------------------- numbers --
    def number_words(self, s: str) -> str:
        s = s.replace(",", "")
        if "." in s:
            whole, frac = s.split(".", 1)
            return f"{self.s.num(int(whole or 0))} {self.s.point} " + " ".join(self.s.digits[int(c)] for c in frac)
        n = int(s)
        if len(s) > 1 and s.startswith("0"):                 # 007, PIN-like codes: digit by digit
            return self._digit_run(s)
        return self.s.num(n)

    def _digit_run(self, s: str) -> str:
        return " ".join(self.s.digits[int(c)] for c in s if c.isdigit())

    # ---------------------------------------------------------- handlers --
    def _phone(self, m: re.Match) -> str:
        raw = m.group(0)
        groups = [g for g in re.split(r"[\s-]+", raw.replace("+", " ").strip()) if g]
        return ", ".join(self._digit_run(g) for g in groups)          # +91 is read "nine one"

    def _time(self, m: re.Match) -> str:
        s = self.s
        h, mi = int(m.group("h")), int(m.group("m"))
        ampm = (m.group("ampm") or "").lower().replace(".", "")
        part = ""
        if ampm == "am":
            part = s.dayparts["am"]
        elif ampm == "pm":
            part = s.dayparts["noon"] if h in (12, 1, 2, 3) else s.dayparts["eve"] if h in (4, 5, 6, 7) else s.dayparts["night"]
        elif h > 12:
            part = s.dayparts["noon"] if h < 16 else s.dayparts["eve"] if h < 20 else s.dayparts["night"]
        h12 = h % 12 or 12
        sep = "" if s.hour_glue else " "
        if mi:
            out = f"{s.num(h12)}{sep}{s.hour_min or s.hour} {s.num(mi)} {s.minute}"
        else:
            out = f"{s.num(h12)}{sep}{s.hour}"
        return f"{part} {out}".strip()

    def _date(self, m: re.Match) -> str | None:
        d = int(m.group("d") or m.group("d2"))
        mo = int(m.group("mo") or m.group("mo2"))
        if not (1 <= d <= 31 and 1 <= mo <= 12):
            return None
        out = f"{self.s.months[mo - 1]} {self.s.num(d)}"
        y = m.group("y") or m.group("y2")
        if y:
            out += f" {self.s.num(int(y) + (2000 if len(y) == 2 else 0))}"
        return out

    def _money(self, m: re.Match) -> str:
        r = int(m.group("r").replace(",", ""))
        out = f"{self.s.num(r)} {self.s.rupee[0] if r == 1 else self.s.rupee[1]}"
        p = m.group("p")
        if p and int(p):
            out += f" {self.s.num(int(p.ljust(2, '0')[:2]))} {self.s.paise}"
        return out

    def _numunit(self, m: re.Match) -> str:
        unit = m.group("u").lower()
        word, n = self.s.units[unit], self.number_words(m.group("n"))
        return f"{word} {n}" if unit in self.s.unit_before else f"{n} {word}"

    def _acronym(self, word: str) -> str | None:
        w = word.replace(".", "")
        if w.isalpha() and w.isupper() and 2 <= len(w) <= 5:
            return " ".join(self.s.letters[c.lower()] for c in w)
        return None

    def _first(self, text: str, pos: int):
        best = None
        for name, rx in self.patterns:
            m = rx.search(text, pos)
            if m and (best is None or m.start() < best[1].start()):
                best = (name, m)
        return best

    # ---------------------------------------------------------- prepare --
    def prepare(self, text: str) -> Prepared:
        text = unicodedata.normalize("NFC", text or "")
        text = "".join(c for c in text if c in "\n\t" or unicodedata.category(c) != "Cc")
        text = text.translate(self._digits).translate({0x0966 + i: ord("0") + i for i in range(10)})
        if self.s.apostrophe_vowel:                                     # s300-023: ক'ত -> কোত
            text = re.sub(r"(?<=[\u0995-\u09b9\u09dc-\u09df\u09f0\u09f1])['’]", self.s.apostrophe_vowel, text)
        for k in sorted(self.s.abbrev, key=len, reverse=True):          # s300-021
            text = text.replace(unicodedata.normalize("NFC", k), unicodedata.normalize("NFC", self.s.abbrev[k]))
        out: list[str] = []
        bad: list[tuple[int, int]] = []
        nums: list[str] = []
        pos = 0
        while pos < len(text):
            hit = self._first(text, pos)
            end_plain = hit[1].start() if hit else len(text)
            for i in range(pos, end_plain):
                c = text[i]
                if c in "।॥":
                    out.append(".")
                elif c == "/":                         # 140/90, and/or: a short pause
                    out.append(" ")
                elif c in "'’‘`":                     # দু'বার -> দুবার, 'ਤੇ -> ਤੇ
                    pass
                elif self.is_letter(c) or c in PUNCT or c in JOINERS:
                    out.append(" " if c.isspace() else c)
                elif unicodedata.category(c) in ("So", "Sk", "Mn", "Cf") and not c.isalnum():
                    pass
                else:
                    bad.append((i, i + 1))
            if not hit:
                break
            name, m = hit
            rep: str | None
            is_num = True
            if name == "phone":
                rep = self._phone(m)
            elif name == "time":
                rep = self._time(m)
            elif name == "date":
                rep = self._date(m)
                if rep is None:
                    m = self._number_rx.match(text, m.start())
                    rep = self.number_words(m.group(0))
            elif name == "money":
                rep = self._money(m)
            elif name == "numunit":
                rep = self._numunit(m)
            elif name == "number":
                rep = self.number_words(m.group(0))
            elif name == "phrase":
                rep, is_num = self.s.phrases[m.group(0).lower()], False
            else:
                is_num = False
                w = m.group(0).rstrip(".")
                rep = self.s.lexicon.get(w.lower().strip("'")) or self._acronym(w)
                if rep is None:
                    bad.append((m.start(), m.start() + len(w)))
            if rep is not None:
                if is_num:
                    nums.append(rep)
                end = m.end()
                glue = end < len(text) and self.is_letter(text[end])           # 10:30க்கு: keep the suffix on
                if not glue and is_num:                                        # "10:30 ಕ್ಕೆ": a suffix written apart
                    sfx = re.match(r"[ \t]+(\S{2,5})", text[end:])
                    sx = sfx.group(1) if sfx else ""                            # s300-025: only a doubled consonant
                    if sx and self.is_letter(sx[0]) and sx[1] == self._virama and len(sx) > 2 and sx[2] == sx[0]:
                        glue, end = True, end + sfx.start(1)
                out.append(f" {rep}" + ("" if glue else " "))
                pos = end
                continue
            pos = m.end()
        spoken = unicodedata.normalize("NFC", "".join(out))      # pack words may be typed in either form (য়, ਸ਼)
        spoken = re.sub(r"\s+([,.;:?!])", r"\1", spoken)
        spoken = re.sub(r"\.{2,}", ".", spoken)
        spoken = re.sub(r"\s+", " ", spoken).strip()
        if not self.speakable(spoken):
            spoken = "".join(c for c in spoken if self.is_letter(c) or c in PUNCT or c in JOINERS)
        return Prepared(spoken=spoken, unspeakable=sorted(set(bad)), numbers=nums)


# ------------------------------------------------------------- loading -----
_CACHE: dict[str, Lang] = {}
LANG_DIR = os.environ.get("SVARAM_LANG_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lang"))


def load(code: str) -> Lang:
    """The language pack in LANG_DIR/<code>/conv.py, as a Lang with .prepare()."""
    if code not in _CACHE:
        path = os.path.join(LANG_DIR, code, "conv.py")
        spec = importlib.util.spec_from_file_location(f"svaram_lang_{code}", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _CACHE[code] = Lang(mod.SPEC)
    return _CACHE[code]


def glue_vowel(stem: str, word: str, vowels: dict[str, str]) -> str:
    """Join a stem ending in a consonant with inherent 'a' to a word: a leading vowel letter
    becomes its vowel sign (ಇಪ್ಪತ್ತ + ಒಂದು -> ಇಪ್ಪತ್ತೊಂದು)."""
    if word and word[0] in vowels:
        return stem + vowels[word[0]] + word[1:]
    return stem + word


if __name__ == "__main__":
    import sys
    code, lines = sys.argv[1], sys.argv[2:] or sys.stdin.read().splitlines()
    L = load(code)
    for line in lines:
        p = L.prepare(line)
        print(("OK  " if p.ok else "SKIP"), repr(line), "->", repr(p.spoken), p.unspeakable, p.numbers)
