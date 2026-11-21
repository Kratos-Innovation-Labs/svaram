# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""Dogri (Devanagari) language pack for Svaram.
Number words: anchors from published Dogri lists (1, 3, 9, 11-13, 18-30, 40, 50, 60, 70, 80, 90, 100, 1000),
the rest follows the closely related Punjabi pattern. Draft: checked by the machine review, and by a Dogri
speaker before Dogri is announced."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "core"))
from indic_conv import Spec  # noqa: E402

U = ("शून्य इक दो त्रै चार पंज छे सत्त अट्ठ नौ "
     "दस यारां बारां तेरां चौदां पंदरां सोलां सतारां ठारां उन्नी "
     "बीह इक्की बाई त्रेई चौबी पंझी छब्बी सताई ठाई उनत्ती "
     "त्रीह् इकत्ती बत्ती तेत्ती चौंत्ती पैंत्ती छत्ती सैंत्ती अठत्ती उनताली "
     "चाली इकताली बताली त्रताली चुताली पंताली छताली संताली अठताली उनंजा "
     "पंजाह् इकवंजा बवंजा त्रवंजा चरवंजा पचवंजा छवंजा सतवंजा अठवंजा उनाहठ "
     "सट्ठ इकाहठ बाहठ त्रेहठ चौंहठ पैंहठ छिआहठ सताहठ अठाहठ उनत्तर "
     "स्हत्तर इकहत्तर बहत्तर त्रेहत्तर चौहत्तर पचहत्तर छिहत्तर सतहत्तर अठहत्तर उनासी "
     "अस्सी इकासी बिआसी त्रेआसी चुरासी पचासी छिआसी सतासी अठासी उनानवें "
     "नब्बै इकानवें बानवें त्रानवें चुरानवें पचानवें छिआनवें सतानवें अठानवें नड़िनवें").split()
assert len(U) == 100


def _u1000(n):
    h, r = divmod(n, 100)
    if not h:
        return U[r]
    return ("सौ" if h == 1 else f"{U[h]} सौ") + (f" {U[r]}" if r else "")


def num(n: int) -> str:
    if n < 0:
        return "माइनस " + num(-n)
    parts = []
    cr, n = divmod(n, 10 ** 7)
    lk, n = divmod(n, 10 ** 5)
    th, n = divmod(n, 1000)
    if cr:
        parts.append(f"{num(cr)} करोड़")
    if lk:
        parts.append(f"{U[lk]} लक्ख")
    if th:
        parts.append(f"{U[th]} हजार")   # s300-027: ज्हार was heard as हजार; हजार is heard back as itself
    if n or not parts:
        parts.append(_u1000(n))
    return " ".join(parts)


SPEC = Spec(
    code="doi", name="Dogri", native="डोगरी", block=("ऀ", "ॿ"), digit0="०",
    num=num, digits=U[:10], point="दशमलव", minus="माइनस",
    months="जनवरी फरवरी मार्च अप्रैल मई जून जुलाई अगस्त सितंबर अक्तूबर नवंबर दिसंबर".split(),
    letters=dict(zip("abcdefghijklmnopqrstuvwxyz",
                     "ए बी सी डी ई एफ जी एच आई जे के एल एम एन ओ पी क्यू आर एस टी यू वी डब्ल्यू एक्स वाई ज़ेड".split())),
    units={"%": "फीसदी", "kg": "किलो", "km": "किलोमीटर", "ml": "मिलीलीटर", "mg": "मिलीग्राम",
           "cm": "सेंटीमीटर", "g": "ग्राम", "l": "लीटर"},
    unit_before=set(),
    lexicon={
        "ok": "ओके", "okay": "ओके", "hello": "हैलो", "please": "प्लीज़", "sorry": "सॉरी", "thanks": "थैंक्स",
        "doctor": "डाक्टर", "dr": "डाक्टर", "nurse": "नर्स", "hospital": "हस्पताल", "clinic": "क्लीनिक",
        "medical": "मेडिकल", "tablet": "गोली", "tablets": "गोलियां", "capsule": "कैप्सूल", "syrup": "सिरप",
        "injection": "टीका", "ambulance": "एंबुलेंस", "emergency": "एमरजेंसी", "police": "पुलिस",
        "bus": "बस", "auto": "ऑटो", "metro": "मेट्रो", "train": "रेल", "station": "स्टेशन", "ticket": "टिकट",
        "toilet": "शौचालय", "phone": "फोन", "mobile": "मोबाइल", "bank": "बैंक", "card": "कार्ड", "cash": "कैश",
        "bill": "बिल", "sugar": "शुगर", "diabetes": "शुगर", "pressure": "प्रेशर", "fever": "बुखार",
        "allergy": "एलर्जी", "test": "टेस्ट", "report": "रिपोर्ट", "scan": "स्कैन",
        "paracetamol": "पैरासिटामोल", "dolo": "डोलो", "crocin": "क्रोसिन", "calpol": "कैलपोल",
        "penicillin": "पेनिसिलिन", "amoxicillin": "एमोक्सिसिलिन", "azithromycin": "एज़िथ्रोमाइसिन",
        "ibuprofen": "आइबुप्रोफेन", "cetirizine": "सेटिरिज़िन", "insulin": "इंसुलिन", "metformin": "मेटफॉर्मिन",
        "aspirin": "एस्पिरिन", "pantoprazole": "पैंटोप्राज़ोल", "omeprazole": "ओमेप्राज़ोल", "vicks": "विक्स",
        "dettol": "डेटॉल",
    },
    phrases={"thank you": "थैंक यू", "good morning": "गुड मॉर्निंग", "good night": "गुड नाइट"},
    # rupees: s300-027-v2 heard रुपये back as itself, not रपे
    rupee=("रुपेआ", "रुपये"), paise="पैसे", hour="बजे", hour_min="बजियै", minute="मिंट",
    dayparts={"am": "सवेरे", "noon": "दपैहरीं", "eve": "संञां", "night": "रातीं"},
    hour_words=("बजे", "बजी"),
    abbrev={"मि.ग्रा.": "मिलीग्राम", "मि. ग्रा.": "मिलीग्राम", "मि.ग्रा": "मिलीग्राम", "कि.ग्रा.": "किलोग्राम",
            "कि.मी.": "किलोमीटर", "मि.ली.": "मिलीलीटर"},
)
