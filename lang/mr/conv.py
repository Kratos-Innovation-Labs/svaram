# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""Marathi language pack for Svaram.
Number words 0-99 are irregular and listed in full: draft for a Marathi reviewer."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "core"))
from indic_conv import Spec  # noqa: E402

U = ("शून्य एक दोन तीन चार पाच सहा सात आठ नऊ दहा अकरा बारा तेरा चौदा पंधरा सोळा सतरा अठरा एकोणीस "
     "वीस एकवीस बावीस तेवीस चोवीस पंचवीस सव्वीस सत्तावीस अठ्ठावीस एकोणतीस "
     "तीस एकतीस बत्तीस तेहतीस चौतीस पस्तीस छत्तीस सदतीस अडतीस एकोणचाळीस "
     "चाळीस एक्केचाळीस बेचाळीस त्रेचाळीस चव्वेचाळीस पंचेचाळीस सेहेचाळीस सत्तेचाळीस अठ्ठेचाळीस एकोणपन्नास "
     "पन्नास एक्कावन्न बावन्न त्रेपन्न चोपन्न पंचावन्न छप्पन्न सत्तावन्न अठ्ठावन्न एकोणसाठ "
     "साठ एकसष्ट बासष्ट त्रेसष्ट चौसष्ट पासष्ट सहासष्ट सदुसष्ट अडुसष्ट एकोणसत्तर "
     "सत्तर एकाहत्तर बाहत्तर त्र्याहत्तर चौर्याहत्तर पंच्याहत्तर शहात्तर सत्त्याहत्तर अठ्ठ्याहत्तर एकोणऐंशी "
     "ऐंशी एक्याऐंशी ब्याऐंशी त्र्याऐंशी चौर्याऐंशी पंच्याऐंशी शहाऐंशी सत्त्याऐंशी अठ्ठ्याऐंशी एकोणनव्वद "
     "नव्वद एक्याण्णव ब्याण्णव त्र्याण्णव चौर्याण्णव पंच्याण्णव शहाण्णव सत्त्याण्णव अठ्ठ्याण्णव नव्व्याण्णव").split()
assert len(U) == 100
HUND = dict(zip(range(2, 10), "दोनशे तीनशे चारशे पाचशे सहाशे सातशे आठशे नऊशे".split()))


def _u1000(n):
    h, r = divmod(n, 100)
    if not h:
        return U[r]
    if h == 1:
        return "शंभर" if not r else f"एकशे {U[r]}"
    return HUND[h] + (f" {U[r]}" if r else "")


def num(n: int) -> str:
    if n < 0:
        return "उणे " + num(-n)
    parts = []
    cr, n = divmod(n, 10 ** 7)
    lk, n = divmod(n, 10 ** 5)
    th, n = divmod(n, 1000)
    if cr:
        parts.append(f"{num(cr)} कोटी")
    if lk:
        parts.append(f"{U[lk]} लाख")
    if th:
        parts.append(f"{U[th]} हजार")
    if n or not parts:
        parts.append(_u1000(n))
    return " ".join(parts)


SPEC = Spec(
    code="mr", name="Marathi", native="मराठी", block=("ऀ", "ॿ"), digit0="०",
    num=num, digits=U[:10], point="पॉइंट", minus="उणे",
    months="जानेवारी फेब्रुवारी मार्च एप्रिल मे जून जुलै ऑगस्ट सप्टेंबर ऑक्टोबर नोव्हेंबर डिसेंबर".split(),
    letters=dict(zip("abcdefghijklmnopqrstuvwxyz",
                     "ए बी सी डी ई एफ जी एच आय जे के एल एम एन ओ पी क्यू आर एस टी यू व्ही डब्ल्यू एक्स वाय झेड".split())),
    units={"%": "टक्के", "kg": "किलो", "km": "किलोमीटर", "ml": "मिली", "mg": "मिलीग्रॅम",
           "cm": "सेंटीमीटर", "g": "ग्रॅम", "l": "लिटर"},
    unit_before=set(),
    lexicon={
        "ok": "ओके", "okay": "ओके", "hello": "हॅलो", "please": "प्लीज", "sorry": "सॉरी", "thanks": "थँक्स",
        "doctor": "डॉक्टर", "dr": "डॉक्टर", "nurse": "नर्स", "hospital": "हॉस्पिटल", "clinic": "क्लिनिक",
        "medical": "मेडिकल", "tablet": "टॅबलेट", "tablets": "टॅबलेट", "capsule": "कॅप्सूल", "syrup": "सिरप",
        "injection": "इंजेक्शन", "ambulance": "अँब्युलन्स", "emergency": "इमर्जन्सी", "police": "पोलीस",
        "bus": "बस", "auto": "ऑटो", "metro": "मेट्रो", "train": "ट्रेन", "station": "स्टेशन", "ticket": "तिकीट",
        "toilet": "टॉयलेट", "phone": "फोन", "mobile": "मोबाईल", "bank": "बँक", "card": "कार्ड", "cash": "कॅश",
        "bill": "बिल", "sugar": "शुगर", "diabetes": "डायबिटीस", "pressure": "प्रेशर", "fever": "ताप",
        "allergy": "एलर्जी", "test": "टेस्ट", "report": "रिपोर्ट", "scan": "स्कॅन",
        "paracetamol": "पॅरासिटामॉल", "dolo": "डोलो", "crocin": "क्रोसिन", "calpol": "कॅलपॉल",
        "penicillin": "पेनिसिलिन", "amoxicillin": "अमॉक्सिसिलिन", "azithromycin": "अझिथ्रोमायसिन",
        "ibuprofen": "आयबुप्रोफेन", "cetirizine": "सेटिरिझिन", "insulin": "इन्सुलिन", "metformin": "मेटफॉर्मिन",
        "aspirin": "अस्पिरिन", "pantoprazole": "पॅन्टोप्राझोल", "omeprazole": "ओमेप्राझोल", "vicks": "व्हिक्स",
        "dettol": "डेटॉल",
    },
    phrases={"thank you": "थँक यू", "good morning": "गुड मॉर्निंग", "good night": "गुड नाईट"},
    rupee=("रुपया", "रुपये"), paise="पैसे", hour="वाजता", hour_min="वाजून", minute="मिनिटे",
    dayparts={"am": "सकाळी", "noon": "दुपारी", "eve": "संध्याकाळी", "night": "रात्री"},
    hour_words=("वाजता", "वाजे"),
    abbrev={"मि.ग्रॅ.": "मिलीग्रॅम", "मि.ग्रॅ": "मिलीग्रॅम", "कि.ग्रॅ.": "किलोग्रॅम", "कि.मी.": "किलोमीटर", "मि.ली.": "मिलीलिटर"},
)
