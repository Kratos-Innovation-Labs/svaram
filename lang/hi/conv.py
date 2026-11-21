# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""Hindi language pack for Svaram: typed or translated Hindi -> what the Hindi voice should say.

Same contract as every other pack's prepare():

    from conv import prepare
    p = prepare("मुझे 2.5 ml सिरप 10:30 बजे चाहिए, ₹250 दूँगा")
    p.ok            # False if something could not be said
    p.spoken        # Devanagari and punctuation only
    p.unspeakable   # [(start, end), ...] spans in the ORIGINAL text that would be skipped

Reads: numbers in the Indian system (हज़ार, लाख, करोड़), 1.5/2.5/x.5 as डेढ़/ढाई/साढ़े,
phone numbers digit by digit, times (साढ़े दस बजे, सवा, पौने), dates (पंद्रह अगस्त),
rupees and paise, units (kg, ml, mg, %), acronyms letter by letter (बी पी), and common
English and medicine words written in Latin letters (doctor, Paracetamol, Dolo ...).
Anything else in Latin letters is reported, never dropped silently (FR-14).
Standard library only.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

ONES = ("शून्य एक दो तीन चार पाँच छह सात आठ नौ दस ग्यारह बारह तेरह चौदह पंद्रह सोलह सत्रह अठारह उन्नीस "
        "बीस इक्कीस बाईस तेईस चौबीस पच्चीस छब्बीस सत्ताईस अट्ठाईस उनतीस तीस इकतीस बत्तीस तैंतीस चौंतीस "
        "पैंतीस छत्तीस सैंतीस अड़तीस उनतालीस चालीस इकतालीस बयालीस तैंतालीस चवालीस पैंतालीस छियालीस "
        "सैंतालीस अड़तालीस उनचास पचास इक्यावन बावन तिरपन चौवन पचपन छप्पन सत्तावन अट्ठावन उनसठ साठ "
        "इकसठ बासठ तिरसठ चौंसठ पैंसठ छियासठ सड़सठ अड़सठ उनहत्तर सत्तर इकहत्तर बहत्तर तिहत्तर चौहत्तर "
        "पचहत्तर छिहत्तर सतहत्तर अठहत्तर उन्यासी अस्सी इक्यासी बयासी तिरासी चौरासी पचासी छियासी "
        "सत्तासी अट्ठासी नवासी नब्बे इक्यानबे बानबे तिरानबे चौरानबे पंचानबे छियानबे सत्तानबे "
        "अट्ठानबे निन्यानबे").split()
assert len(ONES) == 100
DIGIT = ONES[:10]
MONTH = "जनवरी फ़रवरी मार्च अप्रैल मई जून जुलाई अगस्त सितंबर अक्टूबर नवंबर दिसंबर".split()
LETTER = dict(zip("abcdefghijklmnopqrstuvwxyz",
                  "ए बी सी डी ई एफ़ जी एच आई जे के एल एम एन ओ पी क्यू आर एस टी यू वी डब्ल्यू एक्स वाई ज़ेड".split()))
UNIT = {"%": "प्रतिशत", "kg": "किलो", "km": "किलोमीटर", "ml": "एम एल", "mg": "एम जी", "cm": "सेंटीमीटर",
        "g": "ग्राम", "l": "लीटर"}
# Common English words in Latin letters, including medicines (spoken the way pharmacists say them).
LEXICON = {
    "ok": "ओके", "okay": "ओके", "hello": "हेलो", "hi": "हाय", "bye": "बाय", "please": "प्लीज़", "sorry": "सॉरी",
    "thanks": "थैंक्स", "yes": "यस", "no": "नो", "doctor": "डॉक्टर", "dr": "डॉक्टर", "nurse": "नर्स",
    "hospital": "हॉस्पिटल", "clinic": "क्लिनिक", "medical": "मेडिकल", "medicine": "मेडिसिन", "tablet": "टैबलेट",
    "tablets": "टैबलेट", "capsule": "कैप्सूल", "syrup": "सिरप", "injection": "इंजेक्शन", "drip": "ड्रिप",
    "ambulance": "एम्बुलेंस", "emergency": "इमरजेंसी", "police": "पुलिस", "bus": "बस", "auto": "ऑटो",
    "metro": "मेट्रो", "train": "ट्रेन", "station": "स्टेशन", "ticket": "टिकट", "toilet": "टॉयलेट",
    "phone": "फ़ोन", "mobile": "मोबाइल", "bank": "बैंक", "card": "कार्ड", "cash": "कैश", "bill": "बिल",
    "sugar": "शुगर", "diabetes": "डायबिटीज़", "pressure": "प्रेशर", "fever": "फ़ीवर", "cough": "कफ़",
    "allergy": "एलर्जी", "allergic": "एलर्जिक", "test": "टेस्ट", "report": "रिपोर्ट", "scan": "स्कैन",
    "paracetamol": "पैरासिटामोल", "dolo": "डोलो", "crocin": "क्रोसिन", "calpol": "कैलपोल", "penicillin": "पेनिसिलिन",
    "amoxicillin": "एमोक्सिसिलिन", "azithromycin": "एज़िथ्रोमाइसिन", "ibuprofen": "आइबुप्रोफ़ेन",
    "cetirizine": "सेटिरिज़िन", "insulin": "इंसुलिन", "metformin": "मेटफ़ॉर्मिन", "aspirin": "एस्पिरिन",
    "pantoprazole": "पैंटोप्राज़ोल", "omeprazole": "ओमेप्राज़ोल", "vicks": "विक्स", "betadine": "बीटाडीन",
    "dettol": "डेटॉल", "eno": "ईनो", "digene": "डाइजीन", "benadryl": "बेनाड्रिल", "volini": "वोलिनी",
}
PHRASES = {"thank you": "थैंक यू", "good morning": "गुड मॉर्निंग", "good night": "गुड नाइट"}
PUNCT = set(" \n\t.,?!;:-'\"()")


@dataclass
class Prepared:
    spoken: str
    unspeakable: list[tuple[int, int]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.unspeakable


def _is_hi(c: str) -> bool:
    return "ऀ" <= c <= "ॿ" and c not in "।॥" and not ("०" <= c <= "९")


def speakable(text: str) -> bool:
    return all(_is_hi(c) or c in PUNCT for c in text)


# ---------------------------------------------------------------- numbers --
def num_to_hi(n: int) -> str:
    """Integer -> Hindi words, Indian grouping (हज़ार, लाख, करोड़)."""
    if n < 0:
        return "माइनस " + num_to_hi(-n)
    if n < 100:
        return ONES[n]
    parts = []
    for div, word in ((10 ** 7, "करोड़"), (10 ** 5, "लाख"), (1000, "हज़ार"), (100, "सौ")):
        q, n = divmod(n, div)
        if q:
            parts.append(f"{num_to_hi(q)} {word}")
    if n:
        parts.append(ONES[n])
    return " ".join(parts)


def year_to_hi(y: int) -> str:
    if 1100 <= y <= 1999:                       # 1958 -> उन्नीस सौ अट्ठावन
        hi, lo = divmod(y, 100)
        return f"{ONES[hi]} सौ" + (f" {ONES[lo]}" if lo else "")
    return num_to_hi(y)


def _half(whole: int) -> str:
    return {0: "आधा", 1: "डेढ़", 2: "ढाई"}.get(whole, f"साढ़े {num_to_hi(whole)}")


def number_words(s: str) -> str:
    s = s.replace(",", "")
    if "." in s:
        whole, frac = s.split(".", 1)
        w = int(whole or 0)
        if frac.rstrip("0") == "5":
            return _half(w)
        return f"{num_to_hi(w)} दशमलव " + " ".join(DIGIT[int(c)] for c in frac)
    return num_to_hi(int(s))


def _digits(s: str) -> str:
    return " ".join(DIGIT[int(c)] for c in s if c.isdigit())


# ---------------------------------------------------------------- handlers --
def _phone(m: re.Match) -> str:
    raw = m.group(0)
    lead = "प्लस " if raw.lstrip().startswith("+") else ""
    groups = [g for g in re.split(r"[\s-]+", raw.replace("+", " ").strip()) if g]
    return lead + ", ".join(_digits(g) for g in groups)


def _hour(h: int) -> str:
    return {1: "एक", 2: "दो"}.get(h, num_to_hi(h))


def _time(m: re.Match) -> str:
    h, mi = int(m.group("h")), int(m.group("m"))
    ampm = (m.group("ampm") or "").lower().replace(".", "")
    lead = ""
    if ampm == "am":
        lead = "सुबह "
    elif ampm == "pm":
        lead = "दोपहर " if h in (12, 1, 2, 3) else "शाम " if h in (4, 5, 6, 7) else "रात "
    elif h > 12:
        lead = "दोपहर " if h < 16 else "शाम " if h < 20 else "रात "
    h12 = h % 12 or 12
    nxt = h12 % 12 + 1
    if mi == 0:
        return f"{lead}{_hour(h12)} बजे"
    if mi == 30:
        return lead + ({1: "डेढ़", 2: "ढाई"}.get(h12) or f"साढ़े {_hour(h12)}") + " बजे"
    if mi == 15:
        return f"{lead}सवा {_hour(h12)} बजे"
    if mi == 45:
        return f"{lead}पौने {_hour(nxt)} बजे"
    return f"{lead}{_hour(h12)} बजकर {num_to_hi(mi)} मिनट"


def _date(m: re.Match) -> str | None:
    d = int(m.group("d") or m.group("d2"))
    mo = int(m.group("mo") or m.group("mo2"))
    if not (1 <= d <= 31 and 1 <= mo <= 12):
        return None
    out = f"{num_to_hi(d)} {MONTH[mo - 1]}"
    y = m.group("y") or m.group("y2")
    if y:
        yi = int(y) + (2000 if len(y) == 2 else 0)
        out += f" {year_to_hi(yi)}"
    return out


def _money(m: re.Match) -> str:
    r = int(m.group("r").replace(",", ""))
    p = m.group("p")
    out = f"{num_to_hi(r)} {'रुपया' if r == 1 else 'रुपये'}"
    if p and int(p):
        out += f" {num_to_hi(int(p.ljust(2, '0')[:2]))} पैसे"
    return out


def _numunit(m: re.Match) -> str:
    num, unit = m.group("n"), m.group("u").lower()
    return f"{number_words(num)} {UNIT[unit]}"


def _acronym(word: str) -> str | None:
    w = word.replace(".", "")
    if w.isalpha() and w.isupper() and 2 <= len(w) <= 5:
        return " ".join(LETTER[c.lower()] for c in w)
    return None


PATTERNS = [
    ("phone", re.compile(r"(?<![\d])(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?![\d])"
                         r"|(?<![\d])0\d{2,4}[\s-]?\d{6,8}(?![\d])")),
    # a following "बजे" is absorbed: the reading already ends with बजे / मिनट
    ("time", re.compile(r"(?<![\d])(?P<h>[01]?\d|2[0-3]):(?P<m>[0-5]\d)(?:\s?(?P<ampm>[AaPp]\.?[Mm]\.?))?(?![\d])(?:\s*बजे)?")),
    ("date", re.compile(r"(?<![\d.])(?:(?P<d>\d{1,2})[/\-](?P<mo>\d{1,2})(?:[/\-](?P<y>\d{4}|\d{2}))?"
                        r"|(?P<d2>\d{1,2})\.(?P<mo2>\d{1,2})\.(?P<y2>\d{4}))(?![\d])")),
    ("money", re.compile(r"(?:₹|\bRs\.?|\bINR)\s?(?P<r>\d[\d,]*)(?:\.(?P<p>\d{1,2}))?(?![\d])")),
    ("year", re.compile(r"(?<![\d])(?:1[1-9]\d\d|20\d\d)(?=\s*(?:में|से|तक|का|की|के|ई\.?)(?![ऀ-ॿ]))")),
    ("numunit", re.compile(r"(?<![\d])(?P<n>\d[\d,]*(?:\.\d+)?)\s?(?P<u>%|kg|km|ml|mg|cm|g|l)(?![A-Za-z])", re.I)),
    ("number", re.compile(r"(?<![\d])\d[\d,]*(?:\.\d+)?(?![\d])")),
    ("phrase", re.compile(r"(?i)(?<![A-Za-z])(?:" + "|".join(re.escape(p) for p in PHRASES) + r")(?![A-Za-z])")),
    ("latin", re.compile(r"[A-Za-z][A-Za-z.']*")),
]
_NUMBER = dict(PATTERNS)["number"]


def _first(text: str, pos: int):
    best = None
    for name, rx in PATTERNS:
        m = rx.search(text, pos)
        if m and (best is None or m.start() < best[1].start()):
            best = (name, m)
    return best


def prepare(text: str) -> Prepared:
    """Typed or translated Hindi -> what the Hindi voice says, plus spans it cannot say."""
    text = unicodedata.normalize("NFC", text or "")
    text = "".join(c for c in text if c in "\n\t" or unicodedata.category(c) != "Cc")
    text = text.translate({0x0966 + i: ord("0") + i for i in range(10)})      # Devanagari digits
    out: list[str] = []
    bad: list[tuple[int, int]] = []
    pos = 0
    while pos < len(text):
        hit = _first(text, pos)
        end_plain = hit[1].start() if hit else len(text)
        for i in range(pos, end_plain):
            c = text[i]
            if c in "।॥":                     # danda -> full stop
                out.append(".")
            elif _is_hi(c) or c in PUNCT:
                out.append(" " if c.isspace() else c)
            elif unicodedata.category(c) in ("So", "Sk", "Mn", "Cf") and not c.isalnum():
                pass                                    # emoji, ZWJ/ZWNJ outside words
            else:
                bad.append((i, i + 1))
        if not hit:
            break
        name, m = hit
        rep: str | None
        if name == "phone":
            rep = _phone(m)
        elif name == "time":
            rep = _time(m)
        elif name == "date":
            rep = _date(m)
            if rep is None:
                m = _NUMBER.match(text, m.start())
                rep = number_words(m.group(0))
        elif name == "money":
            rep = _money(m)
        elif name == "year":
            rep = year_to_hi(int(m.group(0)))
        elif name == "numunit":
            rep = _numunit(m)
        elif name == "number":
            rep = number_words(m.group(0))
        elif name == "phrase":
            rep = PHRASES[m.group(0).lower()]
        else:
            w = m.group(0).rstrip(".")
            rep = LEXICON.get(w.lower().strip("'")) or _acronym(w)
            if rep is None:
                bad.append((m.start(), m.start() + len(w)))
        if rep is not None:
            out.append(f" {rep} ")
        pos = m.end()
    spoken = "".join(out)
    spoken = re.sub(r"\s+([,.;:?!])", r"\1", spoken)
    spoken = re.sub(r"\.{2,}", ".", spoken)
    spoken = re.sub(r"\s+", " ", spoken).strip()
    if not speakable(spoken):
        spoken = "".join(c for c in spoken if _is_hi(c) or c in PUNCT)
    return Prepared(spoken=spoken, unspeakable=sorted(set(bad)))


if __name__ == "__main__":
    import sys
    for line in sys.argv[1:] or sys.stdin.read().splitlines():
        p = prepare(line)
        print(("OK  " if p.ok else "SKIP"), repr(line), "->", repr(p.spoken), p.unspeakable)
