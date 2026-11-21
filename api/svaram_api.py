# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""svaram-api: the public side of Svaram. Sits between the web page and the voice and translation services.

Every endpoint takes "lang": the code of a live language pack in lang/ (te, hi, ta, ...). Which voice
service speaks it, with which voice, and where translation goes are read from the pack's language.yaml.

  POST /api/prepare  {"text": typed text, "skip_unspeakable": false, "lang": "te"}
      -> {"ok": true,  "segments": ["...", "..."]}           ready to speak
      -> {"ok": false, "unspeakable": [[start, end], ...]}    words the voice cannot say, as
         UTF-16 offsets into the text the page sent (the page highlights them from its own
         copy; the server never echoes them).
      With skip_unspeakable=true (the person pressed "Speak the rest") those words are left
      out and the rest is returned as segments.

  POST /api/speak    {"text": one segment from /api/prepare, "rate": 1.0, "lang": "te"}
      -> audio/mpeg. The voice is fixed by the pack, not chosen by the page. Busy, invalid
         and unspeakable answers pass through as codes.

  POST /api/convey   {"text": English typed text, "skip_unspeakable": false, "lang": "te"}
      English -> the pack's language on svaram-translate (self-hosted IndicTrans2), then the
      same preparation as /api/prepare.
      -> {"ok": true, "telugu", "segments", "numbers_ok", "translated"}
      -> {"ok": false, "telugu", "unspeakable": [[s, e], ...]}  offsets into "telugu"
      "telugu" holds the translation in whichever language was asked (the name is kept so
      existing pages keep working). numbers_ok is false when the digits differ from the English.

  GET  /api/health   {"status": "ok" | "degraded", ...}  (no internals)

Segments: the first one is kept short (about 2-3 s of speech) so sound starts quickly; each
later one may be at most twice the previous, so the next segment is ready before the current
one finishes playing.

Privacy: text exists in memory for one request. It never reaches a log, an error message or
an error body. Validation errors are a bare code. Nothing is written to disk.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.request

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, field_validator

SRC_ROOT = os.environ.get("SVARAM_SRC", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CORE = os.path.join(SRC_ROOT, "core")
if CORE not in sys.path:
    sys.path.insert(0, CORE)
from packs import load_all, script_zero  # noqa: E402

MAX_TEXT = int(os.environ.get("SVARAM_API_MAX_TEXT", "500"))
SEG_CAP = int(os.environ.get("SVARAM_API_SEG_CAP", "200"))          # voices accept 400
VOICE_TIMEOUT_S = float(os.environ.get("SVARAM_API_VOICE_TIMEOUT_S", "12"))
TRANSLATE_URL = os.environ.get("SVARAM_API_TRANSLATE_URL", "http://127.0.0.1:8201")
TRANSLATE_TIMEOUT_S = float(os.environ.get("SVARAM_API_TRANSLATE_TIMEOUT_S", "15"))

#: Where each voice service listens. The variable names are the ones svaram.live has always used.
SERVICE_URLS = {
    "rasa": os.environ.get("SVARAM_API_VOICE_URL", "http://127.0.0.1:8199"),
    "kokoro": os.environ.get("SVARAM_API_VOICE_HI_URL", "http://127.0.0.1:8202"),
    "indictts": os.environ.get("SVARAM_API_VOICE_ITTS_URL", "http://127.0.0.1:8203"),
}
#: Older per-language variable names, still honoured so an existing api.env keeps working.
_LEGACY = {("te", "VOICE"): "SVARAM_API_VOICE", ("te", "FIRST_MAX"): "SVARAM_API_FIRST_MAX",
           ("te", "FIRST_SPLIT"): "SVARAM_API_FIRST_SPLIT", ("hi", "VOICE"): "SVARAM_API_VOICE_HI"}


def _setting(code: str, what: str, default):
    """SVARAM_API_VOICE_TA, SVARAM_API_TA_FIRST_MAX ... override the pack, as before."""
    names = [_LEGACY.get((code, what)),
             f"SVARAM_API_VOICE_{code.upper()}" if what == "VOICE" else f"SVARAM_API_{code.upper()}_{what}"]
    for n in names:
        if n and n in os.environ:
            v = os.environ[n]
            return type(default)(v) if not isinstance(default, str) else v
    return default


def _build_langs() -> dict:
    out = {}
    for code, pack in load_all().items():
        m = pack.meta
        seg = m["segments"]
        out[code] = {"prepare": pack.prepare,
                     "service": m["voice"]["service"],
                     "voice_url": SERVICE_URLS[m["voice"]["service"]],
                     "voice": _setting(code, "VOICE", str(m["voice"]["voice"])),
                     "tgt": m.get("translate_target"),
                     "first_max": _setting(code, "FIRST_MAX", int(seg["first_max"])),
                     "first_split": _setting(code, "FIRST_SPLIT", int(seg["first_split"]))}
    return out


LANGS = _build_langs()
DEFAULT_LANG = os.environ.get("SVARAM_API_DEFAULT_LANG", "te" if "te" in LANGS else sorted(LANGS)[0])
prepare = LANGS[DEFAULT_LANG]["prepare"]                  # kept for the --segments helper

logging.basicConfig(level=logging.WARNING, stream=sys.stderr,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("svaram.api")
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)


# ---------------------------------------------------------------- helpers --
def clean(text: str) -> str:
    """The same clean-up te_conv does first, so offsets line up with the page.

    The page applies the identical rule (NFC, drop control characters except
    tab and newline) before sending, so the text here equals the page's copy.
    """
    text = unicodedata.normalize("NFC", text or "")
    return "".join(c for c in text if c in "\n\t" or unicodedata.category(c) != "Cc")


def utf16_offsets(text: str, spans: list[tuple[int, int]]) -> list[list[int]]:
    """Python indexes code points; the page indexes UTF-16 units (emoji differ)."""
    pref = [0]
    for c in text:
        pref.append(pref[-1] + (2 if ord(c) > 0xFFFF else 1))
    return [[pref[min(s, len(text))], pref[min(e, len(text))]] for s, e in spans]


def merge_word_spans(text: str, spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Widen character spans to whole words and merge neighbours, for display."""
    out: list[list[int]] = []
    for s, e in sorted(spans):
        while s > 0 and not text[s - 1].isspace() and not _is_break(text[s - 1]):
            s -= 1
        while e < len(text) and not text[e].isspace() and not _is_break(text[e]):
            e += 1
        if out and s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return [(s, e) for s, e in out]


def _is_break(ch: str) -> bool:
    return ch in ".,?!;:()\"।॥"


_SENT = re.compile(r"[^.?!।॥\n]+[.?!।॥]*|[.?!।॥]+")


def _cut(unit: str, limit: int) -> tuple[str, str]:
    """Cut a too-long piece at the last comma, else the last space, within limit."""
    if len(unit) - limit <= 6:                                  # s300-026: never leave a tiny tail ("છે.") on its own
        return unit.strip(), ""
    head = unit[:limit + 1]
    for sep in (",", ";", ":", " "):
        i = head.rfind(sep)
        if i >= limit // 3:
            return unit[:i + 1].strip(), unit[i + 1:].strip()
    return unit[:limit].strip(), unit[limit:].strip()           # no break: hard cut


def segment(spoken: str, lang: str = DEFAULT_LANG) -> list[str]:
    FIRST_MAX, FIRST_SPLIT = LANGS[lang]["first_max"], LANGS[lang]["first_split"]   # noqa: N806
    """Spoken text -> segments: short first, then each at most 2x the previous."""
    units = [u.strip() for u in _SENT.findall(spoken) if u.strip(" .?!।॥")]
    if not units:
        return []
    segs: list[str] = []
    cur = ""
    limit = FIRST_MAX
    while units:
        u = units.pop(0)
        if not cur and len(u) > limit:
            head, rest = _cut(u, FIRST_SPLIT if not segs else limit)
            if rest:
                units.insert(0, rest)
            segs.append(head)
            limit = min(SEG_CAP, max(FIRST_MAX, 2 * len(head)))
            continue
        if cur and len(cur) + 1 + len(u) > limit:
            segs.append(cur)
            limit = min(SEG_CAP, max(FIRST_MAX, 2 * len(cur)))
            cur = ""
            units.insert(0, u)
            continue
        cur = f"{cur} {u}".strip()
        if not segs and len(cur) >= FIRST_SPLIT:                 # first segment: stop early
            segs.append(cur)
            limit = min(SEG_CAP, max(FIRST_MAX, 2 * len(cur)))
            cur = ""
    if cur:
        segs.append(cur)
    return segs


# --------------------------------------------------------------------- api --
app = FastAPI(title="svaram-api", version="0.1.0", docs_url=None, redoc_url=None, openapi_url=None)
NO_STORE = {"Cache-Control": "no-store"}


def _err(status: int, code: str, **extra) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, **extra}}, headers=NO_STORE)


@app.exception_handler(RequestValidationError)
async def _validation(_req, _exc):
    return _err(400, "REQUEST_INVALID")                     # default body would echo the text


@app.exception_handler(Exception)
async def _unhandled(_req, exc):
    log.error("unhandled %s", type(exc).__name__)          # type only, never the message
    return _err(500, "INTERNAL")


class PrepareRequest(BaseModel):
    text: str = Field(..., max_length=4 * 500)
    skip_unspeakable: bool = False
    lang: str = DEFAULT_LANG

    @field_validator("lang")
    @classmethod
    def _known(cls, v: str) -> str:
        if v not in LANGS:
            raise ValueError("unknown language")
        return v


class ConveyRequest(BaseModel):
    text: str = Field(..., max_length=4 * 500)
    skip_unspeakable: bool = False
    lang: str = DEFAULT_LANG

    @field_validator("lang")
    @classmethod
    def _known(cls, v: str) -> str:
        if v not in LANGS:
            raise ValueError("unknown language")
        return v


#: Every live pack's own digits read as ASCII digits, so numbers can be compared across scripts.
_TE_DIGITS = {script_zero(p.meta) + i: ord("0") + i for p in load_all(with_prepare=False).values() for i in range(10)}


def numbers_in(text: str) -> list[str]:
    t = (text or "").translate(_TE_DIGITS)
    return sorted(m.replace(",", "") for m in re.findall(r"\d[\d,]*(?:\.\d+)?", t))


class SpeakRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=400)
    rate: float = Field(1.0, ge=0.8, le=1.25)
    lang: str = DEFAULT_LANG

    @field_validator("lang")
    @classmethod
    def _known(cls, v: str) -> str:
        if v not in LANGS:
            raise ValueError("unknown language")
        return v


@app.post("/api/prepare")
async def api_prepare(req: PrepareRequest):
    try:
        text = clean(req.text)
        if not text.strip():
            return _err(400, "TEXT_EMPTY")
        if len(text) > MAX_TEXT:
            return _err(413, "TEXT_TOO_LONG", max_chars=MAX_TEXT)
        p = LANGS[req.lang]["prepare"](text)
        if not p.ok and not req.skip_unspeakable:
            spans = merge_word_spans(text, p.unspeakable)
            return JSONResponse({"ok": False, "unspeakable": utf16_offsets(text, spans)}, headers=NO_STORE)
        segs = segment(p.spoken, req.lang)
        if not segs:
            return JSONResponse({"ok": False, "nothing_to_say": True}, headers=NO_STORE)
        return JSONResponse({"ok": True, "segments": segs, "skipped": 0 if p.ok else len(
            merge_word_spans(text, p.unspeakable))}, headers=NO_STORE)
    except Exception as exc:                                 # noqa: BLE001
        log.error("prepare failed: %s", type(exc).__name__)
        return _err(500, "INTERNAL")


def _translate_call(text: str, tgt: str) -> tuple[int, dict]:
    body = json.dumps({"text": text, "tgt": tgt}).encode()
    rq = urllib.request.Request(f"{TRANSLATE_URL}/v1/translate", data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(rq, timeout=TRANSLATE_TIMEOUT_S) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:                                    # noqa: BLE001
            return e.code, {}


@app.post("/api/convey")
async def api_convey(req: ConveyRequest):
    try:
        text = clean(req.text)
        if not text.strip():
            return _err(400, "TEXT_EMPTY")
        if len(text) > MAX_TEXT:
            return _err(413, "TEXT_TOO_LONG", max_chars=MAX_TEXT)
        if not LANGS[req.lang]["tgt"]:
            return _err(400, "TRANSLATE_NOT_OFFERED")
        try:
            status, body = await asyncio.to_thread(_translate_call, text, LANGS[req.lang]["tgt"])
        except Exception as exc:                             # noqa: BLE001
            log.error("translator unreachable: %s", type(exc).__name__)
            return _err(503, "TRANSLATE_UNAVAILABLE", retry_after_ms=3000)
        if status != 200:
            code = (body.get("error") or {}).get("code", "TRANSLATE_UNAVAILABLE")
            extra = {k: v for k, v in (body.get("error") or {}).items() if k == "retry_after_ms"}
            return _err(503 if status in (0, 500, 502, 503) else status, code, **extra)
        te = clean(body.get("telugu", ""))
        numbers_ok = numbers_in(text) == numbers_in(te)
        base = {"telugu": te, "translated": bool(body.get("translated")), "numbers_ok": numbers_ok}
        p = LANGS[req.lang]["prepare"](te)
        if not p.ok and not req.skip_unspeakable:
            spans = merge_word_spans(te, p.unspeakable)
            return JSONResponse({"ok": False, **base, "unspeakable": utf16_offsets(te, spans)}, headers=NO_STORE)
        segs = segment(p.spoken, req.lang)
        if not segs:
            return JSONResponse({"ok": False, **base, "nothing_to_say": True}, headers=NO_STORE)
        return JSONResponse({"ok": True, **base, "segments": segs}, headers=NO_STORE)
    except Exception as exc:                                 # noqa: BLE001
        log.error("convey failed: %s", type(exc).__name__)
        return _err(500, "INTERNAL")


def _voice_call(text: str, rate: float, lang: str = DEFAULT_LANG) -> tuple[int, bytes, dict]:
    L = LANGS[lang]                                                                   # noqa: N806
    body = json.dumps({"text": text, "lang": lang, "voice": L["voice"], "format": "mp3", "rate": rate}).encode()
    rq = urllib.request.Request(f"{L['voice_url']}/v1/synth", data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(rq, timeout=VOICE_TIMEOUT_S) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers or {})


@app.post("/api/speak")
async def api_speak(req: SpeakRequest):
    try:
        status, data, hdr = await asyncio.to_thread(_voice_call, req.text.strip(), req.rate, req.lang)
    except Exception as exc:                                 # noqa: BLE001
        log.error("voice unreachable: %s", type(exc).__name__)
        return _err(503, "VOICE_UNAVAILABLE", retry_after_ms=2000)
    if status == 200:
        keep = {k: v for k, v in hdr.items() if k.lower() in ("x-audio-duration-ms", "server-timing")}
        return Response(content=data, media_type="audio/mpeg", headers={**NO_STORE, **keep})
    try:                                                     # pass the voice's code, never its body text
        code = json.loads(data)["error"]["code"]
        extra = {k: v for k, v in json.loads(data)["error"].items() if k in ("retry_after_ms", "positions")}
    except Exception:                                        # noqa: BLE001
        code, extra = "VOICE_ERROR", {}
    return _err(status if status in (413, 422, 429, 502, 503) else 502, code, **extra)


def _ping(url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{url}/health", timeout=3) as r:
            return json.loads(r.read()).get("status") == "ok"
    except Exception:                                        # noqa: BLE001
        return False


#: Health keys per voice service, as svaram.live has always reported them.
_HEALTH_KEYS = {"kokoro": "hindi_voice", "indictts": "gujarati_odia_voice"}


@app.get("/api/health")
async def api_health():
    used = sorted({L["service"] for L in LANGS.values()})
    checks = {s: asyncio.to_thread(_ping, SERVICE_URLS[s]) for s in used}
    tr = asyncio.to_thread(_ping, TRANSLATE_URL)
    results = dict(zip(checks, await asyncio.gather(*checks.values())))
    tr_ok = await tr
    main = "rasa" if "rasa" in results else (used[0] if used else None)
    body = {"status": "ok" if main and results[main] else "degraded",
            "translate": "ok" if tr_ok else "unavailable"}
    for s, key in _HEALTH_KEYS.items():
        if s in results:
            body[key] = "ok" if results[s] else "unavailable"
    return JSONResponse(body, headers=NO_STORE)


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "--segments":
    for line in sys.argv[2:] or sys.stdin.read().splitlines():
        p = prepare(clean(line))
        print(p.ok, [len(s) for s in segment(p.spoken)], segment(p.spoken))
