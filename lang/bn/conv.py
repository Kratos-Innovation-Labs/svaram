# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""Bengali language pack for Svaram.
Number words 0-99 are irregular and listed in full (checked against num2words 'bn')."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "core"))
from indic_conv import Spec  # noqa: E402

U = ("শূন্য এক দুই তিন চার পাঁচ ছয় সাত আট নয় দশ এগারো বারো তেরো চোদ্দ পনেরো ষোলো সতেরো আঠারো উনিশ "
     "কুড়ি একুশ বাইশ তেইশ চব্বিশ পঁচিশ ছাব্বিশ সাতাশ আঠাশ উনত্রিশ "
     "তিরিশ একত্রিশ বত্রিশ তেত্রিশ চৌত্রিশ পঁয়ত্রিশ ছত্রিশ সাঁইত্রিশ আটত্রিশ উনচল্লিশ "
     "চল্লিশ একচল্লিশ বিয়াল্লিশ তেতাল্লিশ চুয়াল্লিশ পঁয়তাল্লিশ ছেচল্লিশ সাতচল্লিশ আটচল্লিশ উনপঞ্চাশ "
     "পঞ্চাশ একান্ন বাহান্ন তিপ্পান্ন চুয়ান্ন পঞ্চান্ন ছাপ্পান্ন সাতান্ন আটান্ন উনষাট "
     "ষাট একষট্টি বাষট্টি তেষট্টি চৌষট্টি পঁয়ষট্টি ছেষট্টি সাতষট্টি আটষট্টি উনসত্তর "
     "সত্তর একাত্তর বাহাত্তর তিয়াত্তর চুয়াত্তর পঁচাত্তর ছিয়াত্তর সাতাত্তর আটাত্তর উনআশি "
     "আশি একাশি বিরাশি তিরাশি চুরাশি পঁচাশি ছিয়াশি সাতাশি অষ্টাশি উননব্বই "
     "নব্বই একানব্বই বিরানব্বই তিরানব্বই চুরানব্বই পঁচানব্বই ছিয়ানব্বই সাতানব্বই আটানব্বই নিরানব্বই").split()
assert len(U) == 100
HUND = dict(zip(range(1, 10), "একশো দুশো তিনশো চারশো পাঁচশো ছশো সাতশো আটশো নশো".split()))


def _u1000(n):
    h, r = divmod(n, 100)
    if not h:
        return U[r]
    return HUND[h] + (f" {U[r]}" if r else "")


def num(n: int) -> str:
    if n < 0:
        return "মাইনাস " + num(-n)
    parts = []
    cr, n = divmod(n, 10 ** 7)
    lk, n = divmod(n, 10 ** 5)
    th, n = divmod(n, 1000)
    if cr:
        parts.append(f"{num(cr)} কোটি")
    if lk:
        parts.append(f"{U[lk]} লাখ")
    if th:
        parts.append(f"{U[th]} হাজার")
    if n or not parts:
        parts.append(_u1000(n))
    return " ".join(parts)


SPEC = Spec(
    code="bn", name="Bengali", native="বাংলা", block=("ঀ", "৿"), digit0="০",
    num=num, digits=U[:10], point="দশমিক", minus="মাইনাস",
    months="জানুয়ারি ফেব্রুয়ারি মার্চ এপ্রিল মে জুন জুলাই আগস্ট সেপ্টেম্বর অক্টোবর নভেম্বর ডিসেম্বর".split(),
    letters=dict(zip("abcdefghijklmnopqrstuvwxyz",
                     "এ বি সি ডি ই এফ জি এইচ আই জে কে এল এম এন ও পি কিউ আর এস টি ইউ ভি ডাবলিউ এক্স ওয়াই জেড".split())),
    units={"%": "শতাংশ", "kg": "কেজি", "km": "কিলোমিটার", "ml": "মিলি", "mg": "মিলিগ্রাম",
           "cm": "সেন্টিমিটার", "g": "গ্রাম", "l": "লিটার"},
    unit_before=set(),
    lexicon={
        "ok": "ওকে", "okay": "ওকে", "hello": "হ্যালো", "please": "প্লিজ", "sorry": "সরি", "thanks": "থ্যাংকস",
        "doctor": "ডাক্তার", "dr": "ডাক্তার", "nurse": "নার্স", "hospital": "হাসপাতাল", "clinic": "ক্লিনিক",
        "medical": "মেডিকেল", "tablet": "ট্যাবলেট", "tablets": "ট্যাবলেট", "capsule": "ক্যাপসুল", "syrup": "সিরাপ",
        "injection": "ইনজেকশন", "ambulance": "অ্যাম্বুলেন্স", "emergency": "ইমার্জেন্সি", "police": "পুলিশ",
        "bus": "বাস", "auto": "অটো", "metro": "মেট্রো", "train": "ট্রেন", "station": "স্টেশন", "ticket": "টিকিট",
        "toilet": "টয়লেট", "phone": "ফোন", "mobile": "মোবাইল", "bank": "ব্যাংক", "card": "কার্ড", "cash": "ক্যাশ",
        "bill": "বিল", "sugar": "সুগার", "diabetes": "ডায়াবেটিস", "pressure": "প্রেশার", "fever": "জ্বর",
        "allergy": "অ্যালার্জি", "test": "টেস্ট", "report": "রিপোর্ট", "scan": "স্ক্যান",
        "paracetamol": "প্যারাসিটামল", "dolo": "ডোলো", "crocin": "ক্রোসিন", "calpol": "ক্যালপল",
        "penicillin": "পেনিসিলিন", "amoxicillin": "অ্যামোক্সিসিলিন", "azithromycin": "অ্যাজিথ্রোমাইসিন",
        "ibuprofen": "আইবুপ্রোফেন", "cetirizine": "সেটিরিজিন", "insulin": "ইনসুলিন", "metformin": "মেটফরমিন",
        "aspirin": "অ্যাসপিরিন", "pantoprazole": "প্যান্টোপ্রাজোল", "omeprazole": "ওমেপ্রাজোল", "vicks": "ভিক্স",
        "dettol": "ডেটল",
    },
    phrases={"thank you": "থ্যাংক ইউ", "good morning": "গুড মর্নিং", "good night": "গুড নাইট"},
    rupee=("টাকা", "টাকা"), paise="পয়সা", hour="টা", hour_min="টা বেজে", minute="মিনিট", hour_glue=True,
    dayparts={"am": "সকাল", "noon": "দুপুর", "eve": "সন্ধ্যা", "night": "রাত"},
    hour_words=("টায়", "টা"),
    abbrev={"মি.গ্রা.": "মিলিগ্রাম", "মি.গ্রা": "মিলিগ্রাম", "কি.গ্রা.": "কিলোগ্রাম", "কি.মি.": "কিলোমিটার", "মি.লি.": "মিলিলিটার"},
)
