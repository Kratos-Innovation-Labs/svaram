# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""Malayalam language pack for Svaram . Words only; the logic is in indic_conv."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "core"))
from indic_conv import Spec  # noqa: E402

ONES = ("പൂജ്യം ഒന്ന് രണ്ട് മൂന്ന് നാല് അഞ്ച് ആറ് ഏഴ് എട്ട് ഒമ്പത് പത്ത് പതിനൊന്ന് പന്ത്രണ്ട് പതിമൂന്ന് "
        "പതിനാല് പതിനഞ്ച് പതിനാറ് പതിനേഴ് പതിനെട്ട് പത്തൊമ്പത്").split()
TENS = dict(zip(range(2, 10), "ഇരുപത് മുപ്പത് നാൽപ്പത് അമ്പത് അറുപത് എഴുപത് എൺപത് തൊണ്ണൂറ്".split()))
TENS_C = dict(zip(range(2, 10), "ഇരുപത്തി മുപ്പത്തി നാൽപ്പത്തി അമ്പത്തി അറുപത്തി എഴുപത്തി എൺപത്തി തൊണ്ണൂറ്റി".split()))
HUND = dict(zip(range(1, 10), "നൂറ് ഇരുനൂറ് മുന്നൂറ് നാനൂറ് അഞ്ഞൂറ് അറുനൂറ് എഴുനൂറ് എണ്ണൂറ് തൊള്ളായിരം".split()))
HUND_C = dict(zip(range(1, 10), "നൂറ്റി ഇരുനൂറ്റി മുന്നൂറ്റി നാനൂറ്റി അഞ്ഞൂറ്റി അറുനൂറ്റി എഴുനൂറ്റി എണ്ണൂറ്റി തൊള്ളായിരത്തി".split()))
THOUS = dict(zip(range(1, 11), "ആയിരം രണ്ടായിരം മൂവായിരം നാലായിരം അയ്യായിരം ആറായിരം ഏഴായിരം എണ്ണായിരം ഒമ്പതിനായിരം പതിനായിരം".split()))
# after a stem ending in -ി, a word starting with a vowel takes a glide: ഇരുപത്തി + ഒന്ന് -> ഇരുപത്തിയൊന്ന്
Y = {"അ": "യ", "ആ": "യാ", "ഇ": "യി", "ഈ": "യീ", "ഉ": "യു", "ഊ": "യൂ", "എ": "യെ", "ഏ": "യേ", "ഐ": "യൈ", "ഒ": "യൊ", "ഓ": "യോ"}


def _join(stem, word):
    return stem + (Y[word[0]] + word[1:] if word and word[0] in Y else word)


def _u100(n):
    if n < 20:
        return ONES[n]
    t, u = divmod(n, 10)
    return TENS[t] if not u else _join(TENS_C[t], ONES[u])


def _u1000(n):
    h, r = divmod(n, 100)
    if not h:
        return _u100(r)
    return HUND[h] if not r else _join(HUND_C[h], _u100(r))


def num(n: int) -> str:
    if n < 0:
        return "മൈനസ് " + num(-n)
    if n < 1000:
        return _u1000(n)
    parts = []
    cr, n = divmod(n, 10 ** 7)
    lk, n = divmod(n, 10 ** 5)
    th, n = divmod(n, 1000)
    if cr:
        parts.append(("ഒരു" if cr == 1 else num(cr)) + " കോടി")
    if lk:
        parts.append(("ഒരു" if lk == 1 else _u1000(lk)) + (" ലക്ഷത്തി" if (th or n) else " ലക്ഷം"))
    tail = ""
    if th:
        w = THOUS.get(th) or f"{_u1000(th)} ആയിരം"
        tail = _join(w[:-1] + "ത്തി", _u1000(n)) if n else w          # ആയിരം -> ആയിരത്തി...
    elif n:
        tail = _u1000(n)
    if tail:
        parts.append(tail)
    return " ".join(parts)


SPEC = Spec(
    code="ml", name="Malayalam", native="മലയാളം", block=("ഀ", "ൿ"), digit0="൦",
    num=num, digits=ONES[:10], point="പോയിന്റ്", minus="മൈനസ്",
    months="ജനുവരി ഫെബ്രുവരി മാർച്ച് ഏപ്രിൽ മേയ് ജൂൺ ജൂലൈ ഓഗസ്റ്റ് സെപ്റ്റംബർ ഒക്ടോബർ നവംബർ ഡിസംബർ".split(),
    letters=dict(zip("abcdefghijklmnopqrstuvwxyz",
                     "എ ബി സി ഡി ഇ എഫ് ജി എച്ച് ഐ ജെ കെ എൽ എം എൻ ഒ പി ക്യു ആർ എസ് ടി യു വി ഡബ്ല്യു എക്സ് വൈ ഇസഡ്".split())),
    units={"%": "ശതമാനം", "kg": "കിലോ", "km": "കിലോമീറ്റർ", "ml": "മില്ലി", "mg": "മില്ലിഗ്രാം",
           "cm": "സെന്റിമീറ്റർ", "g": "ഗ്രാം", "l": "ലിറ്റർ"},
    unit_before=set(),
    lexicon={
        "ok": "ഓക്കെ", "okay": "ഓക്കെ", "hello": "ഹലോ", "please": "പ്ലീസ്", "sorry": "സോറി", "thanks": "താങ്ക്സ്",
        "doctor": "ഡോക്ടർ", "dr": "ഡോക്ടർ", "nurse": "നഴ്സ്", "hospital": "ഹോസ്പിറ്റൽ", "clinic": "ക്ലിനിക്",
        "medical": "മെഡിക്കൽ", "tablet": "ടാബ്‌ലെറ്റ്", "tablets": "ടാബ്‌ലെറ്റ്", "capsule": "ക്യാപ്സ്യൂൾ", "syrup": "സിറപ്പ്",
        "injection": "ഇൻജക്ഷൻ", "ambulance": "ആംബുലൻസ്", "emergency": "എമർജൻസി", "police": "പോലീസ്",
        "bus": "ബസ്", "auto": "ഓട്ടോ", "metro": "മെട്രോ", "train": "ട്രെയിൻ", "station": "സ്റ്റേഷൻ",
        "ticket": "ടിക്കറ്റ്", "toilet": "ടോയ്‌ലറ്റ്", "phone": "ഫോൺ", "mobile": "മൊബൈൽ", "bank": "ബാങ്ക്",
        "card": "കാർഡ്", "cash": "ക്യാഷ്", "bill": "ബിൽ", "sugar": "ഷുഗർ", "diabetes": "ഡയബറ്റിസ്",
        "pressure": "പ്രഷർ", "fever": "ഫീവർ", "allergy": "അലർജി", "test": "ടെസ്റ്റ്", "report": "റിപ്പോർട്ട്",
        "scan": "സ്കാൻ", "paracetamol": "പാരസെറ്റമോൾ", "dolo": "ഡോളോ", "crocin": "ക്രോസിൻ", "calpol": "കാൽപോൾ",
        "penicillin": "പെൻസിലിൻ", "amoxicillin": "അമോക്സിസില്ലിൻ", "azithromycin": "അസിത്രോമൈസിൻ",
        "ibuprofen": "ഐബുപ്രോഫെൻ", "cetirizine": "സെറ്റിറിസിൻ", "insulin": "ഇൻസുലിൻ", "metformin": "മെറ്റ്ഫോർമിൻ",
        "aspirin": "ആസ്പിരിൻ", "pantoprazole": "പാന്റോപ്രസോൾ", "omeprazole": "ഒമേപ്രസോൾ", "vicks": "വിക്സ്",
        "dettol": "ഡെറ്റോൾ",
    },
    phrases={"thank you": "താങ്ക് യൂ", "good morning": "ഗുഡ് മോർണിംഗ്", "good night": "ഗുഡ് നൈറ്റ്"},
    rupee=("രൂപ", "രൂപ"), paise="പൈസ", hour="മണി", minute="മിനിറ്റ്",
    dayparts={"am": "രാവിലെ", "noon": "ഉച്ചയ്ക്ക്", "eve": "വൈകുന്നേരം", "night": "രാത്രി"},
    hour_words=("മണി",),
    abbrev={"മി.ഗ്രാം": "മില്ലിഗ്രാം", "മി.ഗ്രാ.": "മില്ലിഗ്രാം", "കി.ഗ്രാം": "കിലോഗ്രാം", "കി.മീ.": "കിലോമീറ്റർ", "കി.മീ": "കിലോമീറ്റർ", "മി.ലി.": "മില്ലിലിറ്റർ", "മി.ലി": "മില്ലിലിറ്റർ"},
)
