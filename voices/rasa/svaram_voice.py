# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""svaram-voice (rasa): speech for every live language pack whose voice.service is "rasa".

One job: take one segment of already-prepared text and return audio bytes.

Privacy rules this file enforces:
  * Nothing is written to disk: no cache, no temp files. Audio lives in memory
    for the length of one request.
  * Text never reaches a log, an error message or an error response. Logs carry
    codes, sizes and timings only. FastAPI's validation errors, which normally
    echo the input, are replaced by a bare code.
  * The engine's own logger is silenced.

Safety rules:
  * No default engine. SVARAM_VOICE_ENGINE must name an allow-listed engine and
    the model checksum must match SVARAM_MODEL_SHA256, or the process refuses
    to start.
  * A word is never dropped silently: if any character is not in the model's
    token table, or not in the language's script, the request is refused with
    the positions of those characters, never the characters themselves.
  * Bounded queue: at most SVARAM_VOICE_QUEUE requests wait, for at most
    SVARAM_VOICE_QUEUE_WAIT_MS; then ENGINE_BUSY. A request whose client has
    gone away is dropped before it reaches the engine.

Endpoints (127.0.0.1 only):
  POST /v1/synth   {"text", "lang": "te", "voice": "19:4", "format": "mp3"|"wav", "rate": 1.0}
  GET  /health
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import logging
import os
import re
import sys
import time
import wave
from contextlib import asynccontextmanager
from typing import Literal

import numpy as np

# ------------------------------------------------------------------ config --
ALLOWED_ENGINES = {"vits_rasa": "CC-BY-4.0, attribution required (ai4bharat/vits_rasa_13)"}

ENGINE = os.environ.get("SVARAM_VOICE_ENGINE", "").strip()
MODEL_DIR = os.environ.get("SVARAM_VOICE_MODEL_DIR", "/opt/svaram/voice/model")
NOISE = float(os.environ.get("SVARAM_VOICE_NOISE", os.environ.get("FH_TTS_NOISE", "0.667")))
NOISE_W = float(os.environ.get("SVARAM_VOICE_NOISE_W", os.environ.get("FH_TTS_NOISE_W", "0.8")))
WARMUP = os.environ.get("SVARAM_VOICE_WARMUP", "నమస్కారం.")       # a fixed sentence, never user text
MODEL_SHA = os.environ.get("SVARAM_MODEL_SHA256", "").strip().lower()
THREADS = int(os.environ.get("SVARAM_VOICE_THREADS", "2"))
CONC = max(1, int(os.environ.get("SVARAM_VOICE_CONCURRENCY", "1")))
QUEUE_MAX = int(os.environ.get("SVARAM_VOICE_QUEUE", str(2 * CONC)))
QUEUE_WAIT_MS = int(os.environ.get("SVARAM_VOICE_QUEUE_WAIT_MS", "800"))
MAX_CHARS = int(os.environ.get("SVARAM_VOICE_MAX_CHARS", "400"))
GAIN_DB = float(os.environ.get("SVARAM_VOICE_GAIN_DB", "0"))
MP3_KBPS = int(os.environ.get("SVARAM_VOICE_MP3_KBPS", "48"))

#: Speakers and styles documented on the model card (7 Nov 2026). The ONNX
#: graph accepts more, but undocumented IDs are not voices.
DOC_SPEAKERS = set(range(20))
DOC_STYLES = {0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 14, 15, 16}
VOICE_RE = re.compile(r"^(\d{1,2}):(\d{1,2})$")

#: Characters each language may contain once normalised: its script block (without its own
#: digits: numbers must already be words), the punctuation below and the zero-width joiners.
#: Being in the model's token table is NOT enough: the table also holds Latin letters and other
#: scripts, and Latin text through an Indic voice is unintelligible.
_PUNCT = set(" .,?!;:'\"-()\u0964\u0965\n")
def _block(lo: str, hi: str, d0: str):
    """A script block without its own digits (numbers must already be words)."""
    d9 = chr(ord(d0) + 9)
    return lambda ch: ((lo <= ch <= hi and not d0 <= ch <= d9) or ch in _PUNCT or ch in {"\u200c", "\u200d"})


SRC_ROOT = os.environ.get("SVARAM_SRC", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(SRC_ROOT, "core"))
from packs import load_all, script_range, script_zero  # noqa: E402

LANG_CHARS = {code: _block(*script_range(p.meta), chr(script_zero(p.meta)))
              for code, p in load_all(with_prepare=False).items() if p.meta["voice"]["service"] == "rasa"}

logging.basicConfig(level=logging.WARNING, stream=sys.stderr,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("svaram.voice")


def config_problems() -> list[str]:
    """Everything that must be true before this process may speak."""
    p = []
    if ENGINE not in ALLOWED_ENGINES:
        p.append(f"ENGINE_NOT_ALLOWED: SVARAM_VOICE_ENGINE={ENGINE or '(unset)'}; "
                 f"allowed: {sorted(ALLOWED_ENGINES)}")
    model = os.path.join(MODEL_DIR, "model.onnx")
    if not os.path.isfile(model):
        p.append(f"MODEL_MISSING: {model}")
    elif not MODEL_SHA:
        p.append("MODEL_SHA_UNSET: SVARAM_MODEL_SHA256 must be set")
    else:
        h = hashlib.sha256()
        with open(model, "rb") as f:
            for block in iter(lambda: f.read(1 << 20), b""):
                h.update(block)
        if h.hexdigest() != MODEL_SHA:
            p.append("MODEL_SHA_MISMATCH: model.onnx does not match SVARAM_MODEL_SHA256")
    if not os.path.isfile(os.path.join(MODEL_DIR, "tokens.txt")):
        p.append("TOKENS_MISSING")
    return p


# ------------------------------------------------------------------ engine --
_ENGINE = None
_ENCODE = None


def _load_engine():
    """Load the vits_rasa engine from rasa_engine.py, in memory only."""
    global _ENGINE, _ENCODE
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from rasa_engine import VitsRasaEngine, encode  # noqa: PLC0415
    logging.getLogger("svaram.voice.rasa").setLevel(logging.CRITICAL + 1)
    logging.getLogger("svaram.voice.rasa").propagate = False
    eng = VitsRasaEngine(MODEL_DIR, threads=THREADS, noise=NOISE, noise_w=NOISE_W)
    eng.warmup()
    _ENGINE, _ENCODE = eng, encode


def _unknown_positions(text: str, lang: str) -> list[int]:
    """Positions of characters this voice cannot say (FR-14). Never the characters."""
    table = _ENGINE._table                                    # noqa: SLF001
    ok = LANG_CHARS[lang]
    silent = {"‌", "‍"}
    return [i for i, ch in enumerate(text)
            if not ok(ch) or (ch not in table and ch not in silent)]


def _to_int16(pcm: np.ndarray) -> bytes:
    if GAIN_DB:
        pcm = pcm * (10 ** (GAIN_DB / 20))
    peak = float(np.max(np.abs(pcm))) if pcm.size else 0.0
    if peak > 0.97:
        pcm = pcm * (0.97 / peak)
    return (np.clip(pcm, -1, 1) * 32767).astype("<i2").tobytes()


def _encode(pcm16: bytes, sr: int, fmt: str) -> bytes:
    if fmt == "wav":
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes(pcm16)
        return buf.getvalue()
    import lameenc  # noqa: PLC0415
    enc = lameenc.Encoder()
    enc.set_bit_rate(MP3_KBPS)
    enc.set_in_sample_rate(sr)
    enc.set_channels(1)
    enc.set_quality(2)
    return bytes(enc.encode(pcm16) + enc.flush())


def _synth(text: str, voice: str, rate: float, fmt: str) -> tuple[bytes, int, float, float]:
    """-> (audio bytes, duration ms, synth s, encode s). Runs in a worker thread."""
    t0 = time.perf_counter()
    a = _ENGINE.synthesize(text, speed=rate, voice=voice)
    t1 = time.perf_counter()
    pcm = np.asarray(a.pcm, dtype=np.float32)
    dur = pcm.size / a.sr
    rms = float(np.sqrt(np.mean(pcm ** 2))) if pcm.size else 0.0
    if dur < 0.15 or rms < 1e-3:
        raise AudioInvalid()
    data = _encode(_to_int16(pcm), a.sr, fmt)
    t2 = time.perf_counter()
    return data, int(dur * 1000), t1 - t0, t2 - t1


class AudioInvalid(Exception):
    pass


# --------------------------------------------------------------------- api --
from fastapi import FastAPI, Request  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.responses import JSONResponse, Response  # noqa: E402
from pydantic import BaseModel, Field, field_validator  # noqa: E402

_sem: asyncio.Semaphore | None = None
_waiting = 0
_running = 0
_served = 0


@asynccontextmanager
async def lifespan(_app):
    global _sem
    problems = config_problems()
    if problems:
        for p in problems:
            log.error("refusing to start: %s", p)
        raise RuntimeError("svaram-voice configuration refused")
    _load_engine()
    # Warm-up with a fixed, non-user sentence so the first real request is warm.
    _synth(WARMUP, os.environ.get("SVARAM_VOICE_WARMUP_VOICE", "19:4"), 1.0, "wav")
    _sem = asyncio.Semaphore(CONC)
    log.warning("svaram-voice ready: engine=%s threads=%d concurrency=%d queue=%d",
                ENGINE, THREADS, CONC, QUEUE_MAX)
    yield


app = FastAPI(title="svaram-voice", version="0.1.0", lifespan=lifespan,
              docs_url=None, redoc_url=None, openapi_url=None)


def _err(status: int, code: str, **extra) -> JSONResponse:
    body = {"error": {"code": code, **extra}}
    return JSONResponse(status_code=status, content=body, headers={"Cache-Control": "no-store"})


@app.exception_handler(RequestValidationError)
async def _validation(_req, _exc):
    # FastAPI's default body echoes the input, i.e. the user's text. Never.
    return _err(400, "REQUEST_INVALID")


@app.exception_handler(Exception)
async def _unhandled(_req, exc):
    log.error("unhandled %s", type(exc).__name__)          # type only, never the message
    return _err(500, "INTERNAL")


class SynthRequest(BaseModel):
    text: str = Field(..., min_length=1)
    lang: str = "te"

    @field_validator("lang")
    @classmethod
    def _known(cls, v: str) -> str:
        if v not in LANG_CHARS:
            raise ValueError("unknown language")
        return v
    voice: str = Field(..., description="speaker:style, e.g. 19:4")
    format: Literal["mp3", "wav"] = "mp3"
    rate: float = Field(1.0, ge=0.8, le=1.25)


@app.post("/v1/synth")
async def synth(req: SynthRequest, request: Request):
    # Catch everything here: an exception that escaped to the server would be
    # logged with its message, and engine messages can contain user text.
    try:
        return await _synth_endpoint(req, request)
    except Exception as exc:                                 # noqa: BLE001
        log.error("synth failed: %s", type(exc).__name__)
        return _err(500, "INTERNAL")


async def _synth_endpoint(req: SynthRequest, request: Request):
    global _waiting, _running, _served
    text = req.text.strip()
    if not text or len(text) > MAX_CHARS:
        return _err(413 if text else 400, "SEGMENT_TOO_LONG" if text else "TEXT_INVALID")
    m = VOICE_RE.match(req.voice)
    if not m or int(m.group(1)) not in DOC_SPEAKERS or int(m.group(2)) not in DOC_STYLES:
        return _err(422, "VOICE_UNAVAILABLE")
    bad = _unknown_positions(text, req.lang)
    if bad:
        return _err(422, "UNSPEAKABLE_CHARS", positions=bad[:50])

    t_arrive = time.perf_counter()
    if _sem.locked() and _waiting >= QUEUE_MAX:
        return _err(503, "ENGINE_BUSY", retry_after_ms=1000)
    _waiting += 1
    try:
        await asyncio.wait_for(_sem.acquire(), QUEUE_WAIT_MS / 1000)
    except asyncio.TimeoutError:
        return _err(503, "ENGINE_BUSY", retry_after_ms=1000)
    finally:
        _waiting -= 1
    try:
        if await request.is_disconnected():
            return Response(status_code=499)                 # client left: skip the work
        queue_s = time.perf_counter() - t_arrive
        _running += 1
        try:
            data, dur_ms, synth_s, enc_s = await asyncio.to_thread(
                _synth, text, req.voice, req.rate, req.format)
        except AudioInvalid:
            return _err(502, "AUDIO_INVALID")
        finally:
            _running -= 1
    finally:
        _sem.release()
    _served += 1
    return Response(
        content=data,
        media_type="audio/mpeg" if req.format == "mp3" else "audio/wav",
        headers={
            "Cache-Control": "no-store",
            "X-Engine": ENGINE,
            "X-Audio-Duration-Ms": str(dur_ms),
            "Server-Timing": f"queue;dur={queue_s*1000:.0f}, synth;dur={synth_s*1000:.0f}, "
                             f"encode;dur={enc_s*1000:.0f}",
        },
    )


@app.get("/health")
async def health():
    return JSONResponse({
        "status": "ok" if _ENGINE is not None else "loading",
        "engine": ENGINE,
        "licence": ALLOWED_ENGINES.get(ENGINE, "?"),
        "model_sha256": MODEL_SHA,
        "threads": THREADS,
        "concurrency": CONC,
        "queue_max": QUEUE_MAX,
        "waiting": _waiting,
        "running": _running,
        "served_since_start": _served,
        "documented_speakers": len(DOC_SPEAKERS),
    }, headers={"Cache-Control": "no-store"})


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--check-config":
        probs = config_problems()
        for p in probs:
            print(p)
        print("CONFIG_OK" if not probs else "CONFIG_REFUSED")
        sys.exit(0 if not probs else 2)
    print("usage: svaram_voice.py --check-config   (run the service with uvicorn)")
    sys.exit(1)
