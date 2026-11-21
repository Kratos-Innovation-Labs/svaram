# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""svaram-api with the voice and translation services replaced by fakes: behaviour and privacy."""
import io
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "api"))
import svaram_api as api  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

SECRET = "రహస్య సందేశం"          # stands in for something private a person typed


class _Resp(io.BytesIO):
    def __init__(self, status, body, headers):
        super().__init__(body)
        self.status, self.headers = status, headers

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass


def _fake(rq, timeout=None):
    url = rq if isinstance(rq, str) else rq.full_url
    if url.endswith("/health"):
        return _Resp(200, b'{"status":"ok"}', {})
    body = json.loads(rq.data)
    if url.endswith("/v1/translate"):
        return _Resp(200, json.dumps({"telugu": "నాకు 2 మాత్రలు కావాలి.", "translated": True}).encode(), {})
    return _Resp(200, b"ID3" + b"\0" * 2000, {"X-Audio-Duration-Ms": "900"})


urllib.request.urlopen = _fake
client = TestClient(api.app)


def test_prepare_segments():
    r = client.post("/api/prepare", json={"text": "నాకు 2 మాత్రలు కావాలి", "lang": "te"}).json()
    assert r["ok"] and r["segments"] == ["నాకు రెండు మాత్రలు కావాలి"]


def test_unspeakable_words_are_positions_not_text():
    r = client.post("/api/prepare", json={"text": SECRET + " Ramesh", "lang": "te"})
    assert r.json() == {"ok": False, "unspeakable": [[len(SECRET) + 1, len(SECRET) + 7]]}
    assert SECRET not in r.text


def test_errors_never_echo_text():
    for body in ({"text": SECRET, "lang": "zz"}, {"text": SECRET * 200, "lang": "te"}):
        for path in ("/api/prepare", "/api/convey", "/api/speak"):
            r = client.post(path, json=body)
            assert r.status_code >= 400 and SECRET not in r.text, (path, r.text)
    r = client.post("/api/speak", json={"text": SECRET, "lang": "te", "rate": 9})
    assert r.status_code == 400 and SECRET not in r.text


def test_convey_checks_numbers():
    r = client.post("/api/convey", json={"text": "I need 2 tablets", "lang": "te"}).json()
    assert r["ok"] and r["numbers_ok"] is True


def test_speak_returns_audio():
    r = client.post("/api/speak", json={"text": "నమస్కారం", "lang": "te"})
    assert r.status_code == 200 and r.headers["content-type"] == "audio/mpeg"


def test_every_live_pack_is_served():
    for code in api.LANGS:
        r = client.post("/api/prepare", json={"text": "1", "lang": code}).json()
        assert r["ok"], code
