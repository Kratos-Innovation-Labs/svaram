# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""Tamil language pack for Svaram . Words only; the logic is in indic_conv."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "core"))
from indic_conv import Spec  # noqa: E402

ONES = ("பூஜ்ஜியம் ஒன்று இரண்டு மூன்று நான்கு ஐந்து ஆறு ஏழு எட்டு ஒன்பது பத்து பதினொன்று பன்னிரண்டு "
        "பதின்மூன்று பதினான்கு பதினைந்து பதினாறு பதினேழு பதினெட்டு பத்தொன்பது").split()
TENS = dict(zip(range(2, 10), "இருபது முப்பது நாற்பது ஐம்பது அறுபது எழுபது எண்பது தொண்ணூறு".split()))
TENS_C = dict(zip(range(2, 10), "இருபத்து முப்பத்து நாற்பத்து ஐம்பத்து அறுபத்து எழுபத்து எண்பத்து தொண்ணூற்று".split()))
HUND = dict(zip(range(1, 10), "நூறு இருநூறு முந்நூறு நானூறு ஐந்நூறு அறுநூறு எழுநூறு எண்ணூறு தொள்ளாயிரம்".split()))
HUND_C = dict(zip(range(1, 10), "நூற்று இருநூற்று முந்நூற்று நானூற்று ஐந்நூற்று அறுநூற்று எழுநூற்று எண்ணூற்று தொள்ளாயிரத்து".split()))
THOUS = dict(zip(range(1, 11), "ஆயிரம் இரண்டாயிரம் மூவாயிரம் நாலாயிரம் ஐயாயிரம் ஆறாயிரம் ஏழாயிரம் எட்டாயிரம் ஒன்பதாயிரம் பத்தாயிரம்".split()))


def _u100(n):
    if n < 20:
        return ONES[n]
    t, u = divmod(n, 10)
    return TENS[t] if not u else f"{TENS_C[t]} {ONES[u]}"


def _u1000(n):
    h, r = divmod(n, 100)
    if not h:
        return _u100(r)
    return HUND[h] if not r else f"{HUND_C[h]} {_u100(r)}"


def num(n: int) -> str:
    if n < 0:
        return "மைனஸ் " + num(-n)
    if n < 1000:
        return _u1000(n)
    parts = []
    cr, n = divmod(n, 10 ** 7)
    lk, n = divmod(n, 10 ** 5)
    th, n = divmod(n, 1000)
    if cr:
        parts.append(("ஒரு" if cr == 1 else num(cr)) + (" கோடியே" if (lk or th or n) else " கோடி"))
    if lk:
        parts.append(("ஒரு" if lk == 1 else _u1000(lk)) + (" லட்சத்து" if (th or n) else " லட்சம்"))
    if th:
        w = THOUS.get(th) or f"{_u1000(th)} ஆயிரம்"
        parts.append(w[:-2] + "த்து" if n else w)                   # ஆயிரம் -> ஆயிரத்து
    if n:
        parts.append(_u1000(n))
    return " ".join(parts)


SPEC = Spec(
    code="ta", name="Tamil", native="தமிழ்", block=("஀", "௿"), digit0="௦",
    num=num, digits=ONES[:10], point="புள்ளி", minus="மைனஸ்",
    months="ஜனவரி பிப்ரவரி மார்ச் ஏப்ரல் மே ஜூன் ஜூலை ஆகஸ்ட் செப்டம்பர் அக்டோபர் நவம்பர் டிசம்பர்".split(),
    letters=dict(zip("abcdefghijklmnopqrstuvwxyz",
                     "ஏ பி சி டி ஈ எஃப் ஜி ஹெச் ஐ ஜே கே எல் எம் என் ஓ பி க்யூ ஆர் எஸ் டி யு வி டபிள்யூ எக்ஸ் வை இசட்".split())),
    units={"%": "சதவீதம்", "kg": "கிலோ", "km": "கிலோமீட்டர்", "ml": "மில்லி", "mg": "மில்லிகிராம்",
           "cm": "சென்டிமீட்டர்", "g": "கிராம்", "l": "லிட்டர்"},
    unit_before=set(),
    lexicon={
        "ok": "ஓகே", "okay": "ஓகே", "hello": "ஹலோ", "please": "ப்ளீஸ்", "sorry": "சாரி", "thanks": "தேங்க்ஸ்",
        "doctor": "டாக்டர்", "dr": "டாக்டர்", "nurse": "நர்ஸ்", "hospital": "ஹாஸ்பிடல்", "clinic": "கிளினிக்",
        "medical": "மெடிக்கல்", "tablet": "டேப்லெட்", "tablets": "டேப்லெட்", "capsule": "கேப்சூல்", "syrup": "சிரப்",
        "injection": "இன்ஜெக்ஷன்", "ambulance": "ஆம்புலன்ஸ்", "emergency": "எமர்ஜென்சி", "police": "போலீஸ்",
        "bus": "பஸ்", "auto": "ஆட்டோ", "metro": "மெட்ரோ", "train": "ட்ரெயின்", "station": "ஸ்டேஷன்",
        "ticket": "டிக்கெட்", "toilet": "டாய்லெட்", "phone": "போன்", "mobile": "மொபைல்", "bank": "பேங்க்",
        "card": "கார்டு", "cash": "கேஷ்", "bill": "பில்", "sugar": "சுகர்", "diabetes": "டயாபடீஸ்",
        "pressure": "பிரஷர்", "fever": "ஃபீவர்", "allergy": "அலர்ஜி", "test": "டெஸ்ட்", "report": "ரிப்போர்ட்",
        "scan": "ஸ்கேன்", "paracetamol": "பாராசிட்டமால்", "dolo": "டோலோ", "crocin": "க்ரோசின்", "calpol": "கால்பால்",
        "penicillin": "பென்சிலின்", "amoxicillin": "அமோக்ஸிசிலின்", "azithromycin": "அசித்ரோமைசின்",
        "ibuprofen": "ஐபுப்ரோஃபென்", "cetirizine": "செட்டிரிசின்", "insulin": "இன்சுலின்", "metformin": "மெட்ஃபார்மின்",
        "aspirin": "ஆஸ்பிரின்", "pantoprazole": "பான்டோபிரசோல்", "omeprazole": "ஒமேப்ரசோல்", "vicks": "விக்ஸ்",
        "dettol": "டெட்டால்",
    },
    phrases={"thank you": "தேங்க் யூ", "good morning": "குட் மார்னிங்", "good night": "குட் நைட்"},
    rupee=("ரூபாய்", "ரூபாய்"), paise="பைசா", hour="மணி", minute="நிமிடம்",
    dayparts={"am": "காலை", "noon": "மதியம்", "eve": "மாலை", "night": "இரவு"},
    hour_words=("மணி",),
    abbrev={"மி.கி.": "மில்லிகிராம்", "மி.கி": "மில்லிகிராம்", "கி.கி.": "கிலோகிராம்", "கி.கி": "கிலோகிராம்", "கி.மீ.": "கிலோமீட்டர்", "கி.மீ": "கிலோமீட்டர்", "மி.லி.": "மில்லிலிட்டர்", "மி.லி": "மில்லிலிட்டர்"},
)
