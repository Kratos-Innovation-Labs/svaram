# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""Gujarati language pack for Svaram.
Number words 0-99 are irregular and listed in full: draft, checked by the machine review."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "core"))
from indic_conv import Spec  # noqa: E402

U = ("શૂન્ય એક બે ત્રણ ચાર પાંચ છ સાત આઠ નવ "
     "દસ અગિયાર બાર તેર ચૌદ પંદર સોળ સત્તર અઢાર ઓગણીસ "
     "વીસ એકવીસ બાવીસ તેવીસ ચોવીસ પચ્ચીસ છવ્વીસ સત્તાવીસ અઠ્ઠાવીસ ઓગણત્રીસ "
     "ત્રીસ એકત્રીસ બત્રીસ તેત્રીસ ચોત્રીસ પાંત્રીસ છત્રીસ સાડત્રીસ આડત્રીસ ઓગણચાલીસ "
     "ચાલીસ એકતાલીસ બેતાલીસ તેતાલીસ ચુંમાલીસ પિસ્તાલીસ છેતાલીસ સુડતાલીસ અડતાલીસ ઓગણપચાસ "
     "પચાસ એકાવન બાવન ત્રેપન ચોપન પંચાવન છપ્પન સત્તાવન અઠ્ઠાવન ઓગણસાઠ "
     "સાઠ એકસઠ બાસઠ ત્રેસઠ ચોસઠ પાંસઠ છાસઠ સડસઠ અડસઠ ઓગણસિત્તેર "
     "સિત્તેર એકોતેર બોતેર તોતેર ચુમોતેર પંચોતેર છોતેર સિત્યોતેર ઇઠ્યોતેર ઓગણએંસી "
     "એંસી એક્યાસી બ્યાસી ત્યાસી ચોર્યાસી પંચ્યાસી છ્યાસી સિત્યાસી ઇઠ્યાસી નેવ્યાસી "
     "નેવું એકાણું બાણું ત્રાણું ચોરાણું પંચાણું છન્નું સત્તાણું અઠ્ઠાણું નવ્વાણું").split()
assert len(U) == 100
HUND = dict(zip(range(2, 10), "બસો ત્રણસો ચારસો પાંચસો છસો સાતસો આઠસો નવસો".split()))


def _u1000(n):
    h, r = divmod(n, 100)
    if not h:
        return U[r]
    if h == 1:
        return "સો" if not r else f"એકસો {U[r]}"
    return HUND[h] + (f" {U[r]}" if r else "")


def num(n: int) -> str:
    if n < 0:
        return "માઇનસ " + num(-n)
    parts = []
    cr, n = divmod(n, 10 ** 7)
    lk, n = divmod(n, 10 ** 5)
    th, n = divmod(n, 1000)
    if cr:
        parts.append(f"{num(cr)} કરોડ")
    if lk:
        parts.append(f"{U[lk]} લાખ")
    if th:
        parts.append(f"{U[th]} હજાર")
    if n or not parts:
        parts.append(_u1000(n))
    return " ".join(parts)


SPEC = Spec(
    code="gu", name="Gujarati", native="ગુજરાતી", block=("઀", "૿"), digit0="૦",
    num=num, digits=U[:10], point="પોઇન્ટ", minus="માઇનસ",
    months="જાન્યુઆરી ફેબ્રુઆરી માર્ચ એપ્રિલ મે જૂન જુલાઈ ઓગસ્ટ સપ્ટેમ્બર ઓક્ટોબર નવેમ્બર ડિસેમ્બર".split(),
    letters=dict(zip("abcdefghijklmnopqrstuvwxyz",
                     "એ બી સી ડી ઈ એફ જી એચ આઈ જે કે એલ એમ એન ઓ પી ક્યુ આર એસ ટી યુ વી ડબલ્યુ એક્સ વાય ઝેડ".split())),
    units={"%": "ટકા", "kg": "કિલો", "km": "કિલોમીટર", "ml": "મિલી", "mg": "મિલિગ્રામ",
           "cm": "સેન્ટિમીટર", "g": "ગ્રામ", "l": "લિટર"},
    unit_before=set(),
    lexicon={
        "ok": "ઓકે", "okay": "ઓકે", "hello": "હેલો", "please": "પ્લીઝ", "sorry": "સોરી", "thanks": "થેન્ક્સ",
        "doctor": "ડૉક્ટર", "dr": "ડૉક્ટર", "nurse": "નર્સ", "hospital": "હૉસ્પિટલ", "clinic": "ક્લિનિક",
        "medical": "મેડિકલ", "tablet": "ટેબ્લેટ", "tablets": "ટેબ્લેટ", "capsule": "કેપ્સ્યુલ", "syrup": "સિરપ",
        "injection": "ઇન્જેક્શન", "ambulance": "એમ્બ્યુલન્સ", "emergency": "ઇમરજન્સી", "police": "પોલીસ",
        "bus": "બસ", "auto": "ઑટો", "metro": "મેટ્રો", "train": "ટ્રેન", "station": "સ્ટેશન", "ticket": "ટિકિટ",
        "toilet": "ટૉઇલેટ", "phone": "ફોન", "mobile": "મોબાઇલ", "bank": "બેંક", "card": "કાર્ડ", "cash": "કેશ",
        "bill": "બિલ", "sugar": "સુગર", "diabetes": "ડાયાબિટીસ", "pressure": "પ્રેશર", "fever": "તાવ",
        "allergy": "એલર્જી", "test": "ટેસ્ટ", "report": "રિપોર્ટ", "scan": "સ્કેન",
        "paracetamol": "પેરાસિટામોલ", "dolo": "ડોલો", "crocin": "ક્રોસિન", "calpol": "કેલપોલ",
        "penicillin": "પેનિસિલિન", "amoxicillin": "એમોક્સિસિલિન", "azithromycin": "એઝિથ્રોમાયસિન",
        "ibuprofen": "આઇબુપ્રોફેન", "cetirizine": "સેટિરિઝિન", "insulin": "ઇન્સ્યુલિન", "metformin": "મેટફોર્મિન",
        "aspirin": "એસ્પિરિન", "pantoprazole": "પેન્ટોપ્રાઝોલ", "omeprazole": "ઓમેપ્રાઝોલ", "vicks": "વિક્સ",
        "dettol": "ડેટોલ",
    },
    phrases={"thank you": "થેન્ક યુ", "good morning": "ગુડ મોર્નિંગ", "good night": "ગુડ નાઇટ"},
    rupee=("રૂપિયો", "રૂપિયા"), paise="પૈસા", hour="વાગ્યે", hour_min="વાગીને", minute="મિનિટે",
    dayparts={"am": "સવારે", "noon": "બપોરે", "eve": "સાંજે", "night": "રાત્રે"},
    hour_words=("વાગ્યે", "વાગે"),
    abbrev={"મિ. ગ્રા.": "મિલિગ્રામ", "મિ. ગ્રા": "મિલિગ્રામ", "કિ. ગ્રા.": "કિલોગ્રામ", "કિ. મી.": "કિલોમીટર", "મિ. લિ.": "મિલીલિટર", "મિ.ગ્રા.": "મિલિગ્રામ", "મિ.ગ્રા": "મિલિગ્રામ", "કિ.ગ્રા.": "કિલોગ્રામ", "કિ.મી.": "કિલોમીટર", "મિ.લિ.": "મિલીલિટર"},
)
