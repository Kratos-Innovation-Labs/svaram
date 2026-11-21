# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""The site builds, every language page is written, and nothing tracks or blocks search by accident."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_build(tmp_path):
    out = tmp_path / "site"
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "build_site.py"), "--out", str(out), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    for code in ["te", "hi", "ta", "kn", "mr", "bn", "pa", "ml", "as", "gu", "or", "doi"]:
        page = (out / code / "index.html").read_text(encoding="utf-8")
        assert f'data-lang="{code}"' in page and "{{" not in page
    home = (out / "index.html").read_text(encoding="utf-8")
    assert "{{" not in home and "googletagmanager" not in home and "analytics" not in home
    assert (out / "robots.txt").exists() and (out / "sitemap.xml").exists()
