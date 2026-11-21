# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""svaram-voice-hi (kokoro): Hindi speech, in memory.

Same interface as the other voice services, so every voice is called the same way:

  POST /v1/synth {"text": Devanagari, "lang": "hi", "voice": "hf_alpha", "format": "mp3", "rate": 1.0}
      -> audio/mpeg (or audio/wav), headers X-Audio-Duration-Ms, Server-Timing (queue, synth, encode)
      -> 422 UNSPEAKABLE_CHARS {positions} for characters outside Devanagari and punctuation
      -> 503 ENGINE_BUSY {retry_after_ms} when the short queue is full
  GET  /health

Engine: Kokoro-82M (Apache-2.0) through kokoro-onnx (MIT), fp32 ONNX, 2 CPU threads.
Hindi pronunciation uses espeak-ng (GPL-3.0), installed separately by the espeakng-loader package;
Svaram's code does not contain or modify it.

Privacy (as svaram-voice): text in memory for one request; never in a log, error message or
error body; validation errors are a bare code; nothing written to disk. The model files must
match their recorded SHA-256 or the service refuses to start.
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import logging
import os
import sys
import time
import wave
from contextlib import asynccontextmanager
from typing import Literal

import numpy as np

MODEL_DIR = os.environ.get("SVARAM_VOICE_HI_MODEL_DIR", "/opt/svaram/voice-hi/model")
MODEL_FILE = os.environ.get("SVARAM_VOICE_HI_MODEL", "kokoro-v1.0.onnx")
MODEL_SHA = os.environ.get("SVARAM_VOICE_HI_MODEL_SHA256", "").strip().lower()
VOICES_SHA = os.environ.get("SVARAM_VOICE_HI_VOICES_SHA256", "").strip().lower()
THREADS = int(os.environ.get("SVARAM_VOICE_HI_THREADS", "2"))
QUEUE_MAX = int(os.environ.get("SVARAM_VOICE_HI_QUEUE", "2"))
QUEUE_WAIT_MS = int(os.environ.get("SVARAM_VOICE_HI_QUEUE_WAIT_MS", "1200"))
MAX_CHARS = int(os.environ.get("SVARAM_VOICE_HI_MAX_CHARS", "400"))
MP3_KBPS = int(os.environ.get("SVARAM_VOICE_HI_MP3_KBPS", "48"))
VOICES = {"hf_alpha", "hf_beta", "hm_omega", "hm_psi"}          # Kokoro's Hindi voices
PUNCT = set(" .,?!;:-'\"()")

logging.basicConfig(level=logging.WARNING, stream=sys.stderr,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("svaram.voice_hi")
for noisy in ("phonemizer", "kokoro_onnx", "onnxruntime"):
    logging.getLogger(noisy).setLevel(logging.ERROR)


def _sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def config_problems() -> list[str]:
    p = []
    m, v = os.path.join(MODEL_DIR, MODEL_FILE), os.path.join(MODEL_DIR, "voices-v1.0.bin")
    if not os.path.isfile(m) or not os.path.isfile(v):
        return [f"MODEL_MISSING in {MODEL_DIR}"]
    if not MODEL_SHA or _sha(m) != MODEL_SHA:
        p.append("MODEL_SHA_MISMATCH")
    if not VOICES_SHA or _sha(v) != VOICES_SHA:
        p.append("VOICES_SHA_MISMATCH")
    return p


_K = None


def _load():
    global _K
    import onnxruntime as ort
    from kokoro_onnx import Kokoro
    so = ort.SessionOptions()
    so.intra_op_num_threads = THREADS
    so.inter_op_num_threads = 1
    sess = ort.InferenceSession(os.path.join(MODEL_DIR, MODEL_FILE), so, providers=["CPUExecutionProvider"])
    _K = Kokoro.from_session(sess, os.path.join(MODEL_DIR, "voices-v1.0.bin"))


def _unknown_positions(text: str) -> list[int]:
    return [i for i, c in enumerate(text)
            if not (("ऀ" <= c <= "ॿ") or c in PUNCT or c in "‌‍")]


def _encode(pcm: np.ndarray, sr: int, fmt: str) -> bytes:
    peak = float(np.max(np.abs(pcm))) if pcm.size else 0.0
    if peak > 0.97:
        pcm = pcm * (0.97 / peak)
    pcm16 = (np.clip(pcm, -1, 1) * 32767).astype("<i2").tobytes()
    if fmt == "wav":
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm16)
        return buf.getvalue()
    import lameenc
    enc = lameenc.Encoder()
    enc.set_bit_rate(MP3_KBPS); enc.set_in_sample_rate(sr); enc.set_channels(1); enc.set_quality(2)
    return bytes(enc.encode(pcm16) + enc.flush())


class AudioInvalid(Exception):
    pass


def _synth(text: str, voice: str, rate: float, fmt: str):
    t0 = time.perf_counter()
    pcm, sr = _K.create(text, voice=voice, speed=rate, lang="hi")
    t1 = time.perf_counter()
    pcm = np.asarray(pcm, dtype=np.float32)
    dur = pcm.size / sr
    if dur < 0.15 or (float(np.sqrt(np.mean(pcm ** 2))) if pcm.size else 0.0) < 1e-3:
        raise AudioInvalid()
    data = _encode(pcm, sr, fmt)
    return data, int(dur * 1000), t1 - t0, time.perf_counter() - t1


# --------------------------------------------------------------------- api --
from fastapi import FastAPI, Request  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.responses import JSONResponse, Response  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

_sem: asyncio.Semaphore | None = None
_waiting = 0
_served = 0


@asynccontextmanager
async def lifespan(_app):
    global _sem
    problems = config_problems()
    if problems:
        for p in problems:
            log.error("refusing to start: %s", p)
        raise RuntimeError("svaram-voice-hi configuration refused")
    _load()
    _synth("नमस्ते।".replace("।", "."), "hf_alpha", 1.0, "wav")       # fixed warm-up sentence
    _sem = asyncio.Semaphore(1)
    log.warning("svaram-voice-hi ready: kokoro %s threads=%d queue=%d", MODEL_FILE, THREADS, QUEUE_MAX)
    yield


app = FastAPI(title="svaram-voice-hi", version="0.1.0", lifespan=lifespan,
              docs_url=None, redoc_url=None, openapi_url=None)


def _err(status: int, code: str, **extra) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, **extra}},
                        headers={"Cache-Control": "no-store"})


@app.exception_handler(RequestValidationError)
async def _validation(_req, _exc):
    return _err(400, "REQUEST_INVALID")


@app.exception_handler(Exception)
async def _unhandled(_req, exc):
    log.error("unhandled %s", type(exc).__name__)
    return _err(500, "INTERNAL")


class SynthRequest(BaseModel):
    text: str = Field(..., min_length=1)
    lang: Literal["hi"] = "hi"
    voice: str = "hf_alpha"
    format: Literal["mp3", "wav"] = "mp3"
    rate: float = Field(1.0, ge=0.8, le=1.25)


@app.post("/v1/synth")
async def synth(req: SynthRequest, request: Request):
    try:
        return await _endpoint(req, request)
    except Exception as exc:                                  # noqa: BLE001
        log.error("synth failed: %s", type(exc).__name__)
        return _err(500, "INTERNAL")


async def _endpoint(req: SynthRequest, request: Request):
    global _waiting, _served
    text = req.text.strip()
    if not text or len(text) > MAX_CHARS:
        return _err(413 if text else 400, "SEGMENT_TOO_LONG" if text else "TEXT_INVALID")
    if req.voice not in VOICES:
        return _err(422, "VOICE_UNAVAILABLE")
    bad = _unknown_positions(text)
    if bad:
        return _err(422, "UNSPEAKABLE_CHARS", positions=bad[:50])
    t_arrive = time.perf_counter()
    if _sem.locked() and _waiting >= QUEUE_MAX:
        return _err(503, "ENGINE_BUSY", retry_after_ms=1200)
    _waiting += 1
    try:
        await asyncio.wait_for(_sem.acquire(), QUEUE_WAIT_MS / 1000)
    except asyncio.TimeoutError:
        return _err(503, "ENGINE_BUSY", retry_after_ms=1200)
    finally:
        _waiting -= 1
    try:
        if await request.is_disconnected():
            return Response(status_code=499)
        queue_s = time.perf_counter() - t_arrive
        try:
            data, dur_ms, synth_s, enc_s = await asyncio.to_thread(_synth, text, req.voice, req.rate, req.format)
        except AudioInvalid:
            return _err(502, "AUDIO_INVALID")
    finally:
        _sem.release()
    _served += 1
    return Response(content=data, media_type="audio/mpeg" if req.format == "mp3" else "audio/wav", headers={
        "Cache-Control": "no-store", "X-Engine": "kokoro-hi", "X-Audio-Duration-Ms": str(dur_ms),
        "Server-Timing": f"queue;dur={queue_s*1000:.0f}, synth;dur={synth_s*1000:.0f}, encode;dur={enc_s*1000:.0f}"})


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok" if _K is not None else "loading", "engine": "kokoro-82M (Apache-2.0)",
                         "lang": "hi", "voices": sorted(VOICES), "threads": THREADS,
                         "waiting": _waiting, "served_since_start": _served}, headers={"Cache-Control": "no-store"})
