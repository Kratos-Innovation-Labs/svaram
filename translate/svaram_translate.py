# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""svaram-translate: English to the languages of Svaram's live language packs, on Svaram's own server.

AI4Bharat IndicTrans2, English->Indic, distilled 200M, MIT licence, on CPU. No paid API, no
outside service: the text never leaves this machine.

Endpoints (127.0.0.1 only):
  POST /v1/translate {"text": "...", "tgt": "<translate_target of a live pack, e.g. tel_Telu>"}
      -> {"telugu", "translated", "sentences", "ms", "tgt"}
      ("telugu" holds the translation in whichever target was asked; the name is kept for compatibility)
  GET  /health

The targets, and the script each must come out in, are read from lang/*/language.yaml.

Privacy rules (same as the voices):
  * Text lives in memory for one request; nothing is written to disk.
  * Text never reaches a log, an error message or an error body. Validation
    errors are a bare code. Library loggers are silenced.

Safety rules:
  * The model must match SVARAM_TRANSLATE_MODEL_SHA256 or the process refuses
    to start, and every target's warm-up translation must come out in its script.
  * One translation at a time (the toolkit's placeholder queue is not
    thread-safe); a short bounded queue, then ENGINE_BUSY.
"""
from __future__ import annotations

import asyncio
import contextlib
import hashlib
import logging
import os
import re
import sys
import threading
import time
import unicodedata
from collections import Counter

MODEL_DIR = os.environ.get("SVARAM_TRANSLATE_MODEL_DIR", "/opt/svaram/translate/model")
MODEL_SHA = os.environ.get("SVARAM_TRANSLATE_MODEL_SHA256", "").strip().lower()
THREADS = int(os.environ.get("SVARAM_TRANSLATE_THREADS", "2"))
BEAMS = int(os.environ.get("SVARAM_TRANSLATE_BEAMS", "4"))
INT8 = os.environ.get("SVARAM_TRANSLATE_INT8", "0") == "1"
USE_CACHE = os.environ.get("SVARAM_TRANSLATE_USE_CACHE", "auto")      # auto | 1 | 0
MAX_CHARS = int(os.environ.get("SVARAM_TRANSLATE_MAX_CHARS", "500"))
QUEUE_MAX = int(os.environ.get("SVARAM_TRANSLATE_QUEUE", "4"))
QUEUE_WAIT_MS = int(os.environ.get("SVARAM_TRANSLATE_QUEUE_WAIT_MS", "4000"))
SRC_ROOT = os.environ.get("SVARAM_SRC", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(SRC_ROOT, "core"))
from packs import load_all, script_range  # noqa: E402

#: translate_target -> the Unicode block its output must be written in, from the live packs.
TARGETS = {p.meta["translate_target"]: script_range(p.meta)
           for p in load_all(with_prepare=False).values() if p.meta.get("translate_target")}
SRC = "eng_Latn"
TGT = "tel_Telu" if "tel_Telu" in TARGETS else sorted(TARGETS)[0]
WEIGHT_FILES = ("model.safetensors", "pytorch_model.bin")

logging.basicConfig(level=logging.WARNING, stream=sys.stderr,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("svaram.translate")
for noisy in ("transformers", "torch", "sacremoses", "indicnlp", "huggingface_hub"):
    logging.getLogger(noisy).setLevel(logging.ERROR)


# ---------------------------------------------------------------- helpers --
def weight_file(model_dir: str = MODEL_DIR) -> str | None:
    for name in WEIGHT_FILES:
        p = os.path.join(model_dir, name)
        if os.path.isfile(p):
            return p
    return None


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def config_problems() -> list[str]:
    p = []
    w = weight_file()
    if not w:
        p.append(f"MODEL_MISSING: no weights in {MODEL_DIR}")
    elif not MODEL_SHA:
        p.append("MODEL_SHA_UNSET: SVARAM_TRANSLATE_MODEL_SHA256 must be set")
    elif sha256_file(w) != MODEL_SHA:
        p.append("MODEL_SHA_MISMATCH: weights do not match SVARAM_TRANSLATE_MODEL_SHA256")
    if not os.path.isfile(os.path.join(MODEL_DIR, "config.json")):
        p.append("CONFIG_MISSING")
    return p


_ABBREV = {"dr", "mr", "mrs", "ms", "st", "no", "vs", "sr", "jr", "prof", "approx", "etc", "e.g", "i.e", "tab", "inj", "syp"}
_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


def split_sentences(text: str) -> list[str]:
    """English text -> sentences. Keeps 'Dr. Rao' and '2.5' together."""
    parts, out = _SPLIT.split(text.strip()), []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if out:
            last = out[-1].rstrip(".").split()[-1].lower() if out[-1].split() else ""
            if out[-1].endswith(".") and last in _ABBREV:
                out[-1] = f"{out[-1]} {p}"
                continue
        out.append(p)
    return out


_TE_DIGITS = {0x0C66 + i: ord("0") + i for i in range(10)}
for _z in (0x0966, 0x0BE6, 0x0CE6, 0x09E6, 0x0A66, 0x0D66, 0x0AE6, 0x0B66):   # Devanagari, Tamil, Kannada, Bengali, Gurmukhi, Malayalam, Gujarati, Odia digits
    _TE_DIGITS.update({_z + i: ord("0") + i for i in range(10)})


def numbers_in(text: str) -> Counter:
    """Every number written in digits, commas removed (so 1,500 == 1500)."""
    t = (text or "").translate(_TE_DIGITS)
    return Counter(m.replace(",", "") for m in re.findall(r"\d[\d,]*(?:\.\d+)?", t))


def numbers_match(english: str, telugu: str) -> bool:
    return numbers_in(english) == numbers_in(telugu)


def has_latin_letters(text: str) -> bool:
    return bool(re.search(r"[A-Za-z]", text or ""))


def script_share(text: str, tgt: str = TGT) -> float:
    lo, hi = TARGETS[tgt]
    letters = [c for c in text if unicodedata.category(c).startswith("L") or lo <= c <= hi]
    if not letters:
        return 0.0
    return sum(1 for c in letters if lo <= c <= hi) / len(letters)


def telugu_share(text: str) -> float:
    return script_share(text, TGT)


# ----------------------------------------------------------------- engine --
class Translator:
    """IndicTrans2 through transformers + IndicTransToolkit, CPU only."""

    def __init__(self, model_dir: str = MODEL_DIR, threads: int = THREADS,
                 int8: bool = INT8, use_cache: str = USE_CACHE):
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        try:
            from IndicTransToolkit.processor import IndicProcessor
        except ImportError:                                  # older layout
            from IndicTransToolkit import IndicProcessor
        torch.set_num_threads(threads)
        self.torch = torch
        self.lock = threading.Lock()
        self.tok = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_dir, trust_remote_code=True,
                                                      torch_dtype=torch.float32)
        model.eval()
        if int8:
            model = torch.quantization.quantize_dynamic(model, {torch.nn.Linear}, dtype=torch.qint8)
        self.model = model
        self._ip_cls = IndicProcessor
        self.ip = IndicProcessor(inference=True)
        self.int8 = int8
        self.diag = {}
        self._select(use_cache)

    # -- choosing a working configuration ---------------------------------
    def _ids_info(self) -> dict:
        cfg, gc = self.model.config, getattr(self.model, "generation_config", None)
        g = lambda o, k: getattr(o, k, None) if o is not None else None   # noqa: E731
        return {"cfg_decoder_start": g(cfg, "decoder_start_token_id"), "cfg_bos": g(cfg, "bos_token_id"),
                "cfg_eos": g(cfg, "eos_token_id"), "cfg_pad": g(cfg, "pad_token_id"),
                "gen_decoder_start": g(gc, "decoder_start_token_id"), "gen_bos": g(gc, "bos_token_id"),
                "gen_eos": g(gc, "eos_token_id"), "gen_max_new_tokens": g(gc, "max_new_tokens"),
                "gen_max_length": g(gc, "max_length"), "gen_forced_bos": g(gc, "forced_bos_token_id"),
                "tok_eos": getattr(self.tok, "eos_token_id", None), "tok_bos": getattr(self.tok, "bos_token_id", None)}

    def _select(self, use_cache: str):
        """Try generation settings and decoding methods on a fixed warm-up sentence.

        IndicTrans2 is a fairseq-style model: decoding conventionally starts from
        the end-of-sentence token. Newer transformers read the start token from the
        generation config, which this checkpoint may not set, and a wrong start
        token makes the model stop at once (empty output). So candidates are tried
        in order, and the first that gives Telugu script is kept. Last resort: a
        plain greedy loop that does not depend on generate() at all.
        """
        info = self._ids_info()
        self.diag["_ids"] = info
        starts = [None]
        for k in ("cfg_decoder_start", "gen_decoder_start", "cfg_eos", "tok_eos", "cfg_bos", "cfg_pad"):
            v = info.get(k)
            if isinstance(v, int) and v not in starts:
                starts.append(v)
        modes = []
        if hasattr(self.tok, "_switch_to_target_mode"):
            modes.append("switch")
        if hasattr(self.tok, "as_target_tokenizer"):
            modes.append("context")
        modes.append("plain")
        caches = {"1": [True], "0": [False]}.get(use_cache, [True, False])
        self.manual = None
        for start in starts:
            for cache in caches:
                for mode in modes:
                    self.gen_kwargs = {"use_cache": cache}
                    if start is not None:
                        self.gen_kwargs["decoder_start_token_id"] = start
                    self.decode_mode, self.use_cache = mode, cache
                    out = self._try()
                    self.diag[f"generate start={start} cache={cache} {mode}"] = out
                    if telugu_share(out) > 0.5:
                        return
        eos = info.get("cfg_eos") if isinstance(info.get("cfg_eos"), int) else info.get("tok_eos")
        for start in [s for s in starts if s is not None] or [eos]:
            for mode in modes:
                self.manual, self.decode_mode, self.use_cache = (start, eos), mode, False
                out = self._try()
                self.diag[f"greedy start={start} {mode}"] = out
                if telugu_share(out) > 0.5:
                    return
        self.decode_mode = self.manual = None
        import json as _json                                  # diag holds only the fixed warm-up sentence
        raise RuntimeError("NO_TELUGU_OUTPUT " + _json.dumps(self.diag, ensure_ascii=False))

    def _try(self) -> str:
        self._last_ids = None
        try:
            out = self._run(["Hello, how are you?"], 1)[0]
        except Exception as exc:                              # noqa: BLE001
            return f"<{type(exc).__name__}: {str(exc)[:120]}>"
        if not out.strip() and self._last_ids is not None:   # show the raw ids when nothing came out
            return f"<empty; ids={self._last_ids[:24]}>"
        return out[:80]

    # -- running ------------------------------------------------------------
    def _decode(self, ids):
        kw = {"skip_special_tokens": True, "clean_up_tokenization_spaces": True}
        tok = self.tok
        if self.decode_mode == "switch":
            tok._switch_to_target_mode()
            try:
                return tok.batch_decode(ids, **kw)
            finally:
                tok._switch_to_input_mode()
        if self.decode_mode == "context":
            with tok.as_target_tokenizer():
                return tok.batch_decode(ids, **kw)
        return tok.batch_decode(ids, **kw)

    def _greedy(self, enc, start: int, eos: int, max_len: int = 256):
        torch = self.torch
        bs = enc["input_ids"].shape[0]
        dec = torch.full((bs, 1), start, dtype=torch.long)
        done = torch.zeros(bs, dtype=torch.bool)
        enc_out = self.model.get_encoder()(input_ids=enc["input_ids"], attention_mask=enc["attention_mask"])
        for _ in range(max_len):
            logits = self.model(encoder_outputs=enc_out, attention_mask=enc["attention_mask"],
                                decoder_input_ids=dec, use_cache=False).logits[:, -1, :]
            nxt = logits.argmax(-1)
            nxt = torch.where(done, torch.full_like(nxt, eos), nxt)
            dec = torch.cat([dec, nxt[:, None]], dim=1)
            done |= nxt == eos
            if bool(done.all()):
                break
        return dec

    def _run(self, sentences: list[str], beams: int, tgt: str = TGT) -> list[str]:
        torch = self.torch
        with self.lock:
            try:
                batch = self.ip.preprocess_batch(sentences, src_lang=SRC, tgt_lang=tgt)
                enc = self.tok(batch, padding="longest", truncation=True, max_length=256, return_tensors="pt")
                with torch.inference_mode():
                    if self.manual is not None:
                        out = self._greedy(enc, *self.manual)
                    else:
                        out = self.model.generate(**enc, num_beams=beams, num_return_sequences=1,
                                                  max_length=256, **self.gen_kwargs)
                ids = out.detach().cpu().tolist()
                self._last_ids = ids[0] if ids else None
                dec = self._decode(ids)
                return self.ip.postprocess_batch(dec, lang=tgt)
            except Exception:
                # preprocess queued placeholder maps that postprocess never took:
                # start a fresh processor so the next request is not misaligned.
                self.ip = self._ip_cls(inference=True)
                raise

    def translate(self, text: str, beams: int = BEAMS, tgt: str = TGT) -> tuple[str, bool, int]:
        """English text -> (translation in tgt, translated?, sentence count)."""
        text = unicodedata.normalize("NFC", text or "").strip()
        if not has_latin_letters(text):                       # already Telugu (or digits only)
            return text, False, 0
        sents = split_sentences(text)
        out = self._run(sents, beams, tgt)
        return " ".join(s.strip() for s in out if s.strip()), True, len(sents)


# --------------------------------------------------------------------- api --
from fastapi import FastAPI  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from pydantic import BaseModel, Field, field_validator  # noqa: E402
from contextlib import asynccontextmanager  # noqa: E402

_T: Translator | None = None
_sem: asyncio.Semaphore | None = None
_waiting = 0
_served = 0
NO_STORE = {"Cache-Control": "no-store"}


@asynccontextmanager
async def lifespan(_app):
    global _T, _sem
    problems = config_problems()
    if problems:
        for p in problems:
            log.error("refusing to start: %s", p)
        raise RuntimeError("svaram-translate configuration refused")
    _T = Translator()
    for tgt in sorted(TARGETS, key=lambda t: t != TGT):      # every target must come out in its script
        w, _, _ = _T.translate("Hello, how are you?", tgt=tgt)
        if script_share(w, tgt) < 0.5:
            log.error("refusing to start: warm-up translation is not in the %s script", tgt)
            raise RuntimeError("svaram-translate warm-up failed")
    _sem = asyncio.Semaphore(1)
    log.warning("svaram-translate ready: beams=%d int8=%s threads=%d use_cache=%s decode=%s gen=%s greedy=%s",
                BEAMS, INT8, THREADS, _T.use_cache, _T.decode_mode, _T.gen_kwargs, _T.manual)
    yield


app = FastAPI(title="svaram-translate", version="0.1.0", lifespan=lifespan,
              docs_url=None, redoc_url=None, openapi_url=None)


def _err(status: int, code: str, **extra) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, **extra}}, headers=NO_STORE)


@app.exception_handler(RequestValidationError)
async def _validation(_req, _exc):
    return _err(400, "REQUEST_INVALID")


@app.exception_handler(Exception)
async def _unhandled(_req, exc):
    log.error("unhandled %s", type(exc).__name__)
    return _err(500, "INTERNAL")


class TranslateRequest(BaseModel):
    text: str = Field(..., max_length=4 * 500)
    tgt: str = TGT

    @field_validator("tgt")
    @classmethod
    def _known(cls, v: str) -> str:
        if v not in TARGETS:
            raise ValueError("unknown target")
        return v


@app.post("/v1/translate")
async def translate(req: TranslateRequest):
    global _waiting, _served
    try:
        text = req.text.strip()
        if not text:
            return _err(400, "TEXT_EMPTY")
        if len(text) > MAX_CHARS:
            return _err(413, "TEXT_TOO_LONG", max_chars=MAX_CHARS)
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
            t0 = time.perf_counter()
            te, done, n = await asyncio.to_thread(_T.translate, text, BEAMS, req.tgt)
            ms = int((time.perf_counter() - t0) * 1000)
        finally:
            _sem.release()
        _served += 1
        return JSONResponse({"telugu": te, "translated": done, "sentences": n, "ms": ms, "tgt": req.tgt},
                            headers={**NO_STORE, "Server-Timing": f"translate;dur={ms}"})
    except Exception as exc:                                  # noqa: BLE001
        log.error("translate failed: %s", type(exc).__name__)
        return _err(500, "INTERNAL")


@app.get("/health")
async def health():
    return JSONResponse({
        "status": "ok" if _T is not None else "loading",
        "model": "ai4bharat/indictrans2-en-indic-dist-200M", "targets": sorted(TARGETS),
        "licence": "MIT",
        "model_sha256": MODEL_SHA[:16],
        "beams": BEAMS, "int8": INT8, "threads": THREADS,
        "use_cache": getattr(_T, "use_cache", None),
        "decode_mode": getattr(_T, "decode_mode", None),
        "generate": getattr(_T, "gen_kwargs", None), "greedy_fallback": getattr(_T, "manual", None),
        "waiting": _waiting, "served_since_start": _served,
    }, headers=NO_STORE)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--check-config":
        probs = config_problems()
        for p in probs:
            print(p)
        print("CONFIG_OK" if not probs else "CONFIG_REFUSED")
        sys.exit(0 if not probs else 2)
    print("usage: svaram_translate.py --check-config   (run the service with uvicorn)")
    sys.exit(1)
