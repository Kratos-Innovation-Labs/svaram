# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""Assamese language pack for Svaram.
Assamese is written in the Bengali block with ৰ and ৱ. Number words 0-99 are irregular and listed in
full: a draft with the least certainty of all packs; an Assamese reviewer must check it before launch."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "core"))
from indic_conv import Spec  # noqa: E402

U = ("শূন্য এক দুই তিনি চাৰি পাঁচ ছয় সাত আঠ ন দহ এঘাৰ বাৰ তেৰ চৈধ্য পোন্ধৰ ষোল্ল সোতৰ ওঠৰ ঊনৈছ "
     "বিছ একৈছ বাইছ তেইছ চৌবিছ পঁচিছ ছাব্বিছ সাতাইছ আঠাইছ ঊনত্ৰিশ "
     "ত্ৰিশ একত্ৰিশ বত্ৰিশ তেত্ৰিশ চৌত্ৰিশ পঁয়ত্ৰিশ ছয়ত্ৰিশ সাতত্ৰিশ আঠত্ৰিশ ঊনচল্লিশ "
     "চল্লিশ একচল্লিশ বিয়াল্লিশ তেতাল্লিশ চৌৱাল্লিশ পঁয়তাল্লিশ ছয়চল্লিশ সাতচল্লিশ আঠচল্লিশ ঊনপঞ্চাশ "
     "পঞ্চাশ একাৱন্ন বাৱন্ন তিপ্পন্ন চৌৱন্ন পঞ্চন্ন ছাপ্পন্ন সাতাৱন্ন আঠাৱন্ন ঊনষাঠি "
     "ষাঠি একষষ্ঠি বাষষ্ঠি তেষষ্ঠি চৌষষ্ঠি পঁয়ষষ্ঠি ছয়ষষ্ঠি সাতষষ্ঠি আঠষষ্ঠি ঊনসত্তৰ "
     "সত্তৰ একসত্তৰ বাসত্তৰ তিয়াত্তৰ চৌসত্তৰ পঁচাত্তৰ ছয়সত্তৰ সাতসত্তৰ আঠসত্তৰ ঊনাশী "
     "আশী একাশী বিৰাশী তিৰাশী চৌৰাশী পঁচাশী ছয়াশী সাতাশী অষ্টাশী ঊননব্বৈ "
     "নব্বৈ একানব্বৈ বিৰানব্বৈ তিৰানব্বৈ চৌৰানব্বৈ পঁচানব্বৈ ছয়ানব্বৈ সাতানব্বৈ আঠানব্বৈ নিৰানব্বৈ").split()
assert len(U) == 100
HUND = dict(zip(range(1, 10), "এশ দুশ তিনিশ চাৰিশ পাঁচশ ছয়শ সাতশ আঠশ নশ".split()))


def _u1000(n):
    h, r = divmod(n, 100)
    if not h:
        return U[r]
    return HUND[h] + (f" {U[r]}" if r else "")


def num(n: int) -> str:
    if n < 0:
        return "মাইনাছ " + num(-n)
    parts = []
    cr, n = divmod(n, 10 ** 7)
    lk, n = divmod(n, 10 ** 5)
    th, n = divmod(n, 1000)
    if cr:
        parts.append(f"{num(cr)} কোটি")
    if lk:
        parts.append(f"{U[lk]} লাখ")
    if th:
        parts.append(f"{U[th]} হাজাৰ")
    if n or not parts:
        parts.append(_u1000(n))
    return " ".join(parts)


SPEC = Spec(
    code="as", name="Assamese", native="অসমীয়া", block=("ঀ", "৿"), digit0="০",
    num=num, digits=U[:10], point="দশমিক", minus="মাইনাছ",
    months="জানুৱাৰী ফেব্ৰুৱাৰী মাৰ্চ এপ্ৰিল মে জুন জুলাই আগষ্ট ছেপ্তেম্বৰ অক্টোবৰ নৱেম্বৰ ডিচেম্বৰ".split(),
    letters=dict(zip("abcdefghijklmnopqrstuvwxyz",
                     "এ বি চি ডি ই এফ জি এইচ আই জে কে এল এম এন অ পি কিউ আৰ এছ টি ইউ ভি ডাব্লিউ এক্স ৱাই জেড".split())),
    units={"%": "শতাংশ", "kg": "কিলো", "km": "কিলোমিটাৰ", "ml": "মিলি", "mg": "মিলিগ্ৰাম",
           "cm": "চেণ্টিমিটাৰ", "g": "গ্ৰাম", "l": "লিটাৰ"},
    unit_before=set(),
    lexicon={
        "ok": "অকে", "okay": "অকে", "hello": "হেল্লো", "please": "প্লীজ", "sorry": "চৰি", "thanks": "থেংকছ",
        "doctor": "ডাক্তৰ", "dr": "ডাক্তৰ", "nurse": "নাৰ্চ", "hospital": "হাস্পতাল", "clinic": "ক্লিনিক",
        "medical": "মেডিকেল", "tablet": "টেবলেট", "tablets": "টেবলেট", "capsule": "কেপচুল", "syrup": "চিৰাপ",
        "injection": "বেজী", "ambulance": "এম্বুলেন্স", "emergency": "জৰুৰীকালীন", "police": "পুলিচ",
        "bus": "বাছ", "auto": "অটো", "metro": "মেট্ৰো", "train": "ৰেল", "station": "ষ্টেচন", "ticket": "টিকট",
        "toilet": "শৌচালয়", "phone": "ফোন", "mobile": "মোবাইল", "bank": "বেংক", "card": "কাৰ্ড", "cash": "নগদ",
        "bill": "বিল", "sugar": "চুগাৰ", "diabetes": "ডায়েবেটিছ", "pressure": "প্ৰেচাৰ", "fever": "জ্বৰ",
        "allergy": "এলাৰ্জী", "test": "পৰীক্ষা", "report": "ৰিপৰ্ট", "scan": "স্কেন",
        "paracetamol": "পেৰাচিটামল", "dolo": "ডোলো", "crocin": "ক্ৰোচিন", "calpol": "কেলপল",
        "penicillin": "পেনিচিলিন", "amoxicillin": "এমক্সিচিলিন", "azithromycin": "এজিথ্ৰোমাইচিন",
        "ibuprofen": "আইবুপ্ৰোফেন", "cetirizine": "চেটিৰিজিন", "insulin": "ইনচুলিন", "metformin": "মেটফৰমিন",
        "aspirin": "এস্পিৰিন", "pantoprazole": "পেণ্টোপ্ৰাজোল", "omeprazole": "অমেপ্ৰাজোল", "vicks": "ভিক্স",
        "dettol": "ডেটল",
    },
    phrases={"thank you": "থেংক ইউ", "good morning": "গুড মৰ্নিং", "good night": "গুড নাইট"},
    rupee=("টকা", "টকা"), paise="পইচা", hour="বজা", hour_min="বাজি", minute="মিনিট",
    dayparts={"am": "ৰাতিপুৱা", "noon": "দুপৰীয়া", "eve": "সন্ধিয়া", "night": "ৰাতি"},
    hour_words=("বজাত", "বজা"),
    abbrev={"মি.গ্ৰা.": "মিলিগ্ৰাম", "মি.গ্ৰা": "মিলিগ্ৰাম", "কি.গ্ৰা.": "কিলোগ্ৰাম", "কি.মি.": "কিলোমিটাৰ", "মি.লি.": "মিলিলিটাৰ"},
    apostrophe_vowel="\u09cb",
)
