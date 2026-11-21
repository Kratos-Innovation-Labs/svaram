# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""Odia language pack for Svaram.
Number words 0-99 are irregular and listed in full: draft, checked by the machine review."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "core"))
from indic_conv import Spec  # noqa: E402

U = ("ଶୂନ ଏକ ଦୁଇ ତିନି ଚାରି ପାଞ୍ଚ ଛଅ ସାତ ଆଠ ନଅ "
     "ଦଶ ଏଗାର ବାର ତେର ଚଉଦ ପନ୍ଦର ଷୋହଳ ସତର ଅଠର ଊଣେଇଶି "
     "କୋଡ଼ିଏ ଏକେଇଶି ବାଇଶି ତେଇଶି ଚବିଶି ପଚିଶି ଛବିଶି ସତେଇଶି ଅଠେଇଶି ଅଣତିରିଶି "
     "ତିରିଶି ଏକତିରିଶି ବତିଶି ତେତିଶି ଚଉତିରିଶି ପଞ୍ଚତିରିଶି ଛତିଶି ସଇଁତିରିଶି ଅଠତିରିଶି ଅଣଚାଳିଶି "
     "ଚାଳିଶି ଏକଚାଳିଶି ବୟାଳିଶି ତେୟାଳିଶି ଚଉରାଳିଶି ପଞ୍ଚଚାଳିଶି ଛୟାଳିଶି ସତଚାଳିଶି ଅଠଚାଳିଶି ଅଣଚାଶ "
     "ପଚାଶ ଏକାବନ ବାଉନ ତେପନ ଚଉବନ ପଞ୍ଚାବନ ଛପନ ସତାବନ ଅଠାବନ ଅଣଷଠି "
     "ଷାଠିଏ ଏକଷଠି ବାଷଠି ତେଷଠି ଚଉଷଠି ପଞ୍ଚଷଠି ଛଅଷଠି ସତଷଠି ଅଠଷଠି ଅଣସ୍ତରି "
     "ସତୁରି ଏକସ୍ତରି ବାସ୍ତରି ତେସ୍ତରି ଚଉସ୍ତରି ପଞ୍ଚସ୍ତରି ଛଅସ୍ତରି ସତସ୍ତରି ଅଠସ୍ତରି ଅଣାଅଶୀ "
     "ଅଶୀ ଏକାଅଶୀ ବୟାଅଶୀ ତେୟାଅଶୀ ଚଉରାଅଶୀ ପଞ୍ଚାଅଶୀ ଛୟାଅଶୀ ସତାଅଶୀ ଅଠାଅଶୀ ଅଣାନବେ "
     "ନବେ ଏକାନବେ ବାନବେ ତେନବେ ଚଉରାନବେ ପଞ୍ଚାନବେ ଛୟାନବେ ସତାନବେ ଅଠାନବେ ଅନେଶତ").split()
assert len(U) == 100


def _u1000(n):
    h, r = divmod(n, 100)
    if not h:
        return U[r]
    head = "ଶହେ" if h == 1 else f"{U[h]} ଶହ"
    return head + (f" {U[r]}" if r else "")


def num(n: int) -> str:
    if n < 0:
        return "ମାଇନସ " + num(-n)
    parts = []
    cr, n = divmod(n, 10 ** 7)
    lk, n = divmod(n, 10 ** 5)
    th, n = divmod(n, 1000)
    if cr:
        parts.append(f"{num(cr)} କୋଟି")
    if lk:
        parts.append(f"{U[lk]} ଲକ୍ଷ")
    if th:
        parts.append(f"{U[th]} ହଜାର")
    if n or not parts:
        parts.append(_u1000(n))
    return " ".join(parts)


SPEC = Spec(
    code="or", name="Odia", native="ଓଡ଼ିଆ", block=("଀", "୿"), digit0="୦",
    num=num, digits=U[:10], point="ଦଶମିକ", minus="ମାଇନସ",
    months="ଜାନୁଆରୀ ଫେବୃଆରୀ ମାର୍ଚ୍ଚ ଅପ୍ରେଲ ମଇ ଜୁନ ଜୁଲାଇ ଅଗଷ୍ଟ ସେପ୍ଟେମ୍ବର ଅକ୍ଟୋବର ନଭେମ୍ବର ଡିସେମ୍ବର".split(),
    letters=dict(zip("abcdefghijklmnopqrstuvwxyz",
                     "ଏ ବି ସି ଡି ଇ ଏଫ ଜି ଏଚ ଆଇ ଜେ କେ ଏଲ ଏମ ଏନ ଓ ପି କ୍ୟୁ ଆର ଏସ ଟି ୟୁ ଭି ଡବ୍ଲ୍ୟୁ ଏକ୍ସ ୱାଇ ଜେଡ".split())),
    units={"%": "ପ୍ରତିଶତ", "kg": "କିଲୋ", "km": "କିଲୋମିଟର", "ml": "ମିଲି", "mg": "ମିଲିଗ୍ରାମ",
           "cm": "ସେଣ୍ଟିମିଟର", "g": "ଗ୍ରାମ", "l": "ଲିଟର"},
    unit_before=set(),
    lexicon={
        "ok": "ଓକେ", "okay": "ଓକେ", "hello": "ହେଲୋ", "please": "ପ୍ଲିଜ", "sorry": "ସରି", "thanks": "ଥ୍ୟାଙ୍କସ",
        "doctor": "ଡାକ୍ତର", "dr": "ଡାକ୍ତର", "nurse": "ନର୍ସ", "hospital": "ହସପିଟାଲ", "clinic": "କ୍ଲିନିକ",
        "medical": "ମେଡିକାଲ", "tablet": "ଟାବଲେଟ", "tablets": "ଟାବଲେଟ", "capsule": "କ୍ୟାପସୁଲ", "syrup": "ସିରପ",
        "injection": "ଇଞ୍ଜେକସନ", "ambulance": "ଆମ୍ବୁଲାନ୍ସ", "emergency": "ଇମର୍ଜେନ୍ସି", "police": "ପୋଲିସ",
        "bus": "ବସ", "auto": "ଅଟୋ", "metro": "ମେଟ୍ରୋ", "train": "ଟ୍ରେନ", "station": "ଷ୍ଟେସନ", "ticket": "ଟିକେଟ",
        "toilet": "ଟଏଲେଟ", "phone": "ଫୋନ", "mobile": "ମୋବାଇଲ", "bank": "ବ୍ୟାଙ୍କ", "card": "କାର୍ଡ", "cash": "କ୍ୟାସ",
        "bill": "ବିଲ", "sugar": "ସୁଗାର", "diabetes": "ଡାଇବେଟିସ", "pressure": "ପ୍ରେସର", "fever": "ଜ୍ୱର",
        "allergy": "ଆଲର୍ଜି", "test": "ଟେଷ୍ଟ", "report": "ରିପୋର୍ଟ", "scan": "ସ୍କାନ",
        "paracetamol": "ପାରାସିଟାମଲ", "dolo": "ଡୋଲୋ", "crocin": "କ୍ରୋସିନ", "calpol": "କାଲପୋଲ",
        "penicillin": "ପେନିସିଲିନ", "amoxicillin": "ଆମୋକ୍ସିସିଲିନ", "azithromycin": "ଆଜିଥ୍ରୋମାଇସିନ",
        "ibuprofen": "ଆଇବୁପ୍ରୋଫେନ", "cetirizine": "ସେଟିରିଜିନ", "insulin": "ଇନସୁଲିନ", "metformin": "ମେଟଫର୍ମିନ",
        "aspirin": "ଆସପିରିନ", "pantoprazole": "ପାଣ୍ଟୋପ୍ରାଜୋଲ", "omeprazole": "ଓମେପ୍ରାଜୋଲ", "vicks": "ଭିକ୍ସ",
        "dettol": "ଡେଟଲ",
    },
    phrases={"thank you": "ଥ୍ୟାଙ୍କ ୟୁ", "good morning": "ଗୁଡ ମର୍ଣ୍ଣିଂ", "good night": "ଗୁଡ ନାଇଟ"},
    rupee=("ଟଙ୍କା", "ଟଙ୍କା"), paise="ପଇସା", hour="ଟା", hour_min="ଟା", minute="ମିନିଟ", hour_glue=True,
    dayparts={"am": "ସକାଳ", "noon": "ଦିନ", "eve": "ସନ୍ଧ୍ୟା", "night": "ରାତି"},
    hour_words=("ଟାରେ", "ଟା"),
    abbrev={"ମି. ଗ୍ରା.": "ମିଲିଗ୍ରାମ", "ମି. ଗ୍ରା": "ମିଲିଗ୍ରାମ", "କି. ଗ୍ରା.": "କିଲୋଗ୍ରାମ", "କି. ମି.": "କିଲୋମିଟର", "ମି. ଲି.": "ମିଲିଲିଟର", "ମି.ଗ୍ରା.": "ମିଲିଗ୍ରାମ", "ମି.ଗ୍ରା": "ମିଲିଗ୍ରାମ", "କି.ଗ୍ରା.": "କିଲୋଗ୍ରାମ", "କି.ମି.": "କିଲୋମିଟର", "ମି.ଲି.": "ମିଲିଲିଟର"},
)
