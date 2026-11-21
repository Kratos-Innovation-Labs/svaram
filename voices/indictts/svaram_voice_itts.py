# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""svaram-voice-itts (indictts): Gujarati and Odia speech, in memory.

Same interface as the other voice services, so every voice is called the same way:

  POST /v1/synth {"text": Gujarati or Odia text, "lang": "gu" | "or", "voice": "female" | "male",
                  "format": "mp3" | "wav", "rate": 1.0}
      -> audio/mpeg (or audio/wav), headers X-Audio-Duration-Ms, Server-Timing (queue, synth, encode)
      -> 422 UNSPEAKABLE_CHARS {positions} for letters the voice does not know
      -> 503 ENGINE_BUSY {retry_after_ms} when the short queue is full
  GET  /health

Engine: AI4Bharat Indic-TTS (FastPitch + HiFi-GAN; code MIT; voices trained on the IIT Madras Indic TTS
database, copyright TTS Consortium, TDIL, MeitY) through Coqui TTS 0.28 (MPL-2.0) on PyTorch 2.7.1, CPU.

What testing taught, applied here:
  * Odia letters the voices were trained on as single letters (ୟ ଡ଼ ଢ଼) are given back as single letters;
    Unicode normalisation splits them, and the voice then said ଯ "ja" (ସାହାଯ୍ୟ, ଦୟାକରି).
  * text is spoken in pieces of at most 60 letters, cut at punctuation, joined by a 0.12 s pause;
  * every piece ends with a full stop, or the last word is clipped; for Odia the danda । (with "." the
    recogniser twice heard a "not" that was never said). Odia questions also end with ।: with "?" the last
    word was lost (ଏ ଖର୍ଚ୍ଚ କେତେ?), so the question tune is traded for the word.
  * oneDNN stays on (3x faster); 2 CPU threads.

Privacy (as the other voices): text in memory for one request; never in a log, error message or error body;
the engine's own printing of the text is swallowed; nothing written to disk. Every model file must match the
SHA-256 in the manifest, and the manifest must match SVARAM_VOICE_ITTS_MANIFEST_SHA256, or the service refuses
to start.
"""
from __future__ import annotations

import asyncio
import contextlib
import hashlib
import io
import json
import logging
import os
import re
import sys
import time
import unicodedata
import wave
from contextlib import asynccontextmanager
from typing import Literal

import numpy as np

MODEL_DIR = os.environ.get("SVARAM_VOICE_ITTS_MODEL_DIR", "/opt/svaram/voice-itts/model")
MANIFEST_SHA = os.environ.get("SVARAM_VOICE_ITTS_MANIFEST_SHA256", "").strip().lower()
LANGS = [x for x in os.environ.get("SVARAM_VOICE_ITTS_LANGS", "gu,or").split(",") if x]
THREADS = int(os.environ.get("SVARAM_VOICE_ITTS_THREADS", "2"))
QUEUE_MAX = int(os.environ.get("SVARAM_VOICE_ITTS_QUEUE", "2"))
QUEUE_WAIT_MS = int(os.environ.get("SVARAM_VOICE_ITTS_QUEUE_WAIT_MS", "1500"))
MAX_CHARS = int(os.environ.get("SVARAM_VOICE_ITTS_MAX_CHARS", "400"))
PIECE = int(os.environ.get("SVARAM_VOICE_ITTS_PIECE", "60"))
MP3_KBPS = int(os.environ.get("SVARAM_VOICE_ITTS_MP3_KBPS", "48"))
VOICES = {"female", "male"}
STOP = {"gu": ".", "or": "।"}
WARM = {"gu": "નમસ્તે.", "or": "ନମସ୍କାର।"}
RECOMPOSE = {"ଯ଼": "ୟ", "ଡ଼": "ଡ଼", "ଢ଼": "ଢ଼"}
BLOCK = {"gu": ("઀", "૿"), "or": ("଀", "୿")}

logging.basicConfig(level=logging.WARNING, stream=sys.stderr,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("svaram.voice_itts")
for noisy in ("TTS", "trainer", "numba", "matplotlib", "fsspec"):
    logging.getLogger(noisy).setLevel(logging.ERROR)


def _sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def config_problems() -> list[str]:
    m = os.path.join(MODEL_DIR, "manifest.json")
    if not os.path.isfile(m):
        return [f"MANIFEST_MISSING in {MODEL_DIR}"]
    if not MANIFEST_SHA or _sha(m) != MANIFEST_SHA:
        return ["MANIFEST_SHA_MISMATCH"]
    files = json.load(open(m, encoding="utf-8"))["files"]
    p = []
    for lang in LANGS:
        need = [k for k in files if k.startswith(f"{lang}/")]
        if not need:
            p.append(f"LANG_NOT_IN_MANIFEST {lang}")
    for rel, sha in files.items():
        f = os.path.join(MODEL_DIR, rel)
        if not os.path.isfile(f):
            p.append(f"MODEL_MISSING {rel}")
        elif _sha(f) != sha:
            p.append(f"MODEL_SHA_MISMATCH {rel}")
    return p


_S: dict = {}        # lang -> (Synthesizer, known letters, sample rate)


def _load():
    import torch
    torch.set_num_threads(THREADS)
    from TTS.utils.synthesizer import Synthesizer
    for lang in LANGS:
        d = os.path.join(MODEL_DIR, lang)
        with contextlib.redirect_stdout(io.StringIO()):
            s = Synthesizer(tts_checkpoint=f"{d}/fastpitch/best_model.pth", tts_config_path=f"{d}/fastpitch/config.svaram.json",
                            tts_speakers_file=f"{d}/fastpitch/speakers.pth", vocoder_checkpoint=f"{d}/hifigan/best_model.pth",
                            vocoder_config=f"{d}/hifigan/config.json", use_cuda=False)
        known = set(s.tts_config.characters.characters) | set(s.tts_config.characters.punctuations)
        _S[lang] = (s, known, s.output_sample_rate)


def _letters(text: str, lang: str) -> str:
    t = unicodedata.normalize("NFC", text)
    for a, b in RECOMPOSE.items():
        t = t.replace(a, b)
    return t.replace("‌", "").replace("‍", "")


def _unknown_positions(text: str, lang: str) -> list[int]:
    """Positions in the caller's text of letters this voice cannot say (a nukta it lacks is simply dropped)."""
    known = _S[lang][1]
    out = []
    for i, c in enumerate(unicodedata.normalize("NFC", text)):
        if c in known or c in " .,?!;:-'\"()।‌‍" or unicodedata.category(c) == "Mn":
            continue
        if c in "ଯଡଢ":              # recomposed with the following nukta
            continue
        out.append(i)
    return out


def _pieces(text: str) -> list[str]:
    out = []
    for sent in re.split(r"(?<=[.!?।])\s+", text):
        for part in re.split(r"(?<=[,;])\s+", sent):
            cur = ""
            for w in part.split():
                if cur and len(cur) + 1 + len(w) > PIECE:
                    out.append(cur)
                    cur = w
                else:
                    cur = f"{cur} {w}".strip()
            if cur and out and len(cur) < 12 and len(out[-1]) + len(cur) < PIECE + 15:
                out[-1] = f"{out[-1]} {cur}"
            elif cur:
                out.append(cur)
    return [p for p in out if p.strip(" .,;:!?।")]


def _ended(piece: str, stop: str, keep_question: bool = True) -> str:
    piece = piece.rstrip()
    if piece[-1] in ".।":
        return piece[:-1] + stop
    if piece[-1] in "?!":
        return piece if keep_question else piece[:-1] + stop
    return piece.rstrip(",;:") + stop


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


def _synth(text: str, lang: str, voice: str, fmt: str):
    import torch
    s, known, sr = _S[lang]
    t0 = time.perf_counter()
    said = "".join(c for c in _letters(text, lang) if c in known or c == " ")
    pieces = _pieces(re.sub(r"\s+", " ", said).strip())
    if not pieces:
        raise AudioInvalid()
    gap = np.zeros(int(0.12 * sr), dtype=np.float32)
    parts = []
    with contextlib.redirect_stdout(io.StringIO()), torch.inference_mode():   # the engine prints the text: swallow it
        for i, p in enumerate(pieces):
            parts.append(np.asarray(s.tts(_ended(p, STOP[lang], lang != "or"), speaker_name=voice), dtype=np.float32))
            if i < len(pieces) - 1:
                parts.append(gap)
    pcm = np.concatenate(parts)
    t1 = time.perf_counter()
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
        raise RuntimeError("svaram-voice-itts configuration refused")
    _load()
    for lang in LANGS:
        _synth(WARM[lang], lang, "female", "wav")                      # fixed warm-up sentence per language
    _sem = asyncio.Semaphore(1)
    log.warning("svaram-voice-itts ready: indic-tts %s threads=%d queue=%d", ",".join(LANGS), THREADS, QUEUE_MAX)
    yield


app = FastAPI(title="svaram-voice-itts", version="0.1.0", lifespan=lifespan,
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
    lang: Literal["gu", "or"] = "gu"
    voice: str = "female"
    format: Literal["mp3", "wav"] = "mp3"
    rate: float = Field(1.0, ge=0.8, le=1.25)       # accepted for the common interface; this engine speaks at 1.0


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
    if req.lang not in _S:
        return _err(422, "LANG_UNAVAILABLE")
    if req.voice not in VOICES:
        return _err(422, "VOICE_UNAVAILABLE")
    bad = _unknown_positions(text, req.lang)
    if bad:
        return _err(422, "UNSPEAKABLE_CHARS", positions=bad[:50])
    t_arrive = time.perf_counter()
    if _sem.locked() and _waiting >= QUEUE_MAX:
        return _err(503, "ENGINE_BUSY", retry_after_ms=1500)
    _waiting += 1
    try:
        await asyncio.wait_for(_sem.acquire(), QUEUE_WAIT_MS / 1000)
    except asyncio.TimeoutError:
        return _err(503, "ENGINE_BUSY", retry_after_ms=1500)
    finally:
        _waiting -= 1
    try:
        if await request.is_disconnected():
            return Response(status_code=499)
        queue_s = time.perf_counter() - t_arrive
        try:
            data, dur_ms, synth_s, enc_s = await asyncio.to_thread(_synth, text, req.lang, req.voice, req.format)
        except AudioInvalid:
            return _err(502, "AUDIO_INVALID")
    finally:
        _sem.release()
    _served += 1
    return Response(content=data, media_type="audio/mpeg" if req.format == "mp3" else "audio/wav", headers={
        "Cache-Control": "no-store", "X-Engine": "indic-tts", "X-Audio-Duration-Ms": str(dur_ms),
        "Server-Timing": f"queue;dur={queue_s*1000:.0f}, synth;dur={synth_s*1000:.0f}, encode;dur={enc_s*1000:.0f}"})


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok" if len(_S) == len(LANGS) and _sem is not None else "loading",
                         "engine": "AI4Bharat Indic-TTS (MIT; IIT Madras Indic TTS database)",
                         "langs": sorted(_S), "voices": sorted(VOICES), "threads": THREADS,
                         "waiting": _waiting, "served_since_start": _served}, headers={"Cache-Control": "no-store"})
