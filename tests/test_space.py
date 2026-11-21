# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""The Hugging Face pieces: the dataset export and the Space build."""
import csv
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_dataset_export_matches_packs():
    with tempfile.TemporaryDirectory() as out:
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "export_dataset.py"), "--out", out,
                        "--no-parquet"], check=True, capture_output=True)
        phrases = list(csv.DictReader(open(os.path.join(out, "phrases.csv"), encoding="utf-8")))
        langs = {r["lang"] for r in phrases}
        # every language has the same six core phrase ids, which the Space's buttons rely on
        core = {lang: [r["id"] for r in phrases if r["lang"] == lang and r["core"] == "True"] for lang in langs}
        assert len({tuple(v) for v in core.values()}) == 1 and len(next(iter(core.values()))) == 6
        card = open(os.path.join(out, "README.md"), encoding="utf-8").read()
        assert "license: cc-by-4.0" in card and f"({len(phrases)} rows)" in card


def test_space_build_has_what_start_needs():
    with tempfile.TemporaryDirectory() as out:
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "build_space.py"), "--out", out],
                       check=True, capture_output=True)
        for need in ("README.md", "Dockerfile", "SOURCE", "space/app.py", "space/start.sh", "api/svaram_api.py",
                     "translate/svaram_translate.py", "voices/rasa/svaram_voice.py", "voices/kokoro/svaram_voice_hi.py",
                     "voices/indictts/svaram_voice_itts.py", "tools/fetch_models.py", "tools/slim_checkpoint.py",
                     "deploy/models.yaml", "deploy/requirements/space.lock", "lang/te/language.yaml", "CREDITS.md"):
            assert os.path.isfile(os.path.join(out, need)), need
        assert "sdk: docker" in open(os.path.join(out, "README.md"), encoding="utf-8").read()
        assert not os.path.exists(os.path.join(out, "web")) and not os.path.exists(os.path.join(out, "tests"))


def test_static_space_build():
    import json
    with tempfile.TemporaryDirectory() as out:
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "build_static_space.py"), "--out", out],
                       check=True, capture_output=True)
        data = json.load(open(os.path.join(out, "phrases.json"), encoding="utf-8"))
        assert len(data["languages"]) == 12
        assert all(len(L["phrases"]) == 6 for L in data["languages"])
        assert "sdk: static" in open(os.path.join(out, "README.md"), encoding="utf-8").read()
        js = open(os.path.join(out, "app.js"), encoding="utf-8").read()
        assert 'var API = "https://svaram.live";' in js
        assert "localStorage" not in js and "document.cookie" not in js


def test_nginx_allows_exactly_the_static_space():
    conf = open(os.path.join(ROOT, "deploy", "nginx.sample.conf"), encoding="utf-8").read()
    assert conf.count("kratos-innovation-labs-svaram\\.static\\.hf\\.space$") == 2
    assert conf.count("limit_except POST OPTIONS { deny all; }") == 2
    proxy = open(os.path.join(ROOT, "deploy", "nginx.api-proxy.conf"), encoding="utf-8").read()
    assert "if ($request_method = OPTIONS) { return 204; }" in proxy
