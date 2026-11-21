# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""Every language pack loads, says its phrases, and still gives the answers recorded in tests.yaml."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "core"))
from packs import load_all  # noqa: E402


def test_check_pack_passes():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "check_pack.py")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_same_phrase_ids_everywhere():
    packs = load_all(with_prepare=False)
    ids = {c: [p["id"] for p in pk.phrases] for c, pk in packs.items()}
    first = next(iter(ids.values()))
    assert all(v == first for v in ids.values())


def test_english_words_are_reported_not_dropped():
    for code, pack in load_all().items():
        p = pack.prepare("Ramesh")
        assert not p.ok and p.unspeakable == [(0, 6)], code
