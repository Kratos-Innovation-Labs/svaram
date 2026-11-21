# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""AI4Bharat vits_rasa_13 run as ONNX: Indic text in, 24 kHz mono audio out.

vits_rasa_13 is CC-BY-4.0 (commercial use permitted, attribution required). Svaram runs an
ONNX conversion of it (MatiasLin/sherpa-onnx-vits-rasa-13); see CREDITS.md.

  * onnxruntime only: no torch, no transformers, no tokenizers.
  * frontend=characters: no phonemiser, so no espeak-ng and no GPL code in this path.
    Letters map straight to token ids from tokens.txt.
  * ONNX Runtime's run() is thread-safe, so there is no global lock.

The graph's inputs, as read from the model:

    x              int64  ['N','L']     token ids
    x_length       int64  ['N']         sequence length
    noise_scale    float  []            scalar
    length_scale   float  []            scalar, >1 is SLOWER
    noise_scale_w  float  []            scalar
    sid            int64  ['N']         speaker
    emotion_id     int64  ['N']         style
    -> y           float  ['N',1,'T']

Error messages never contain the text or its characters: they may reach a log.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

log = logging.getLogger("svaram.voice.rasa")

TOKEN_LINE = re.compile(r"^(.*?)\s+(\d+)\s*$")

#: Characters that may be missing from the table without harming the audio:
#: ZWNJ/ZWJ are rendering joiners and carry no sound.
SILENT_OK = {"‌", "‍", "﻿"}

#: If more than this share of a text's characters are unknown, the token table does not
#: match the text and synthesising would produce confident nonsense.
MAX_UNKNOWN_SHARE = 0.10


@dataclass
class Audio:
    pcm: np.ndarray      # float32, mono, range [-1, 1]
    sr: int


class EngineError(RuntimeError):
    """An engine-level failure. The message never includes the text."""


def load_tokens(path: Path) -> dict[str, int]:
    """tokens.txt is '<token> <id>' per line. The token itself may be a space, so the id is
    taken from the end rather than by splitting on whitespace."""
    table: dict[str, int] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        m = TOKEN_LINE.match(raw)
        if not m:
            continue
        table[m.group(1) or " "] = int(m.group(2))
    if not table:
        raise EngineError(f"{path} contained no usable token lines")
    return table


def encode(text: str, table: dict[str, int], add_blank: bool,
           blank_id: int = 0) -> tuple[list[int], list[str]]:
    """Characters to token ids, interleaving the blank when the model was trained that way.
    Unknown characters are left out and returned, so the caller can refuse the text."""
    ids: list[int] = []
    unknown: list[str] = []
    for ch in text:
        tid = table.get(ch)
        if tid is not None:
            ids.append(tid)
        elif ch not in SILENT_OK:
            unknown.append(ch)
    if add_blank:
        spaced = [blank_id]
        for i in ids:
            spaced.extend((i, blank_id))
        ids = spaced
    return ids, unknown


class VitsRasaEngine:
    name = "vits_rasa"

    def __init__(self, model_dir: str, threads: int = 2, speaker: int = 19, emotion: int = 4,
                 noise: float = 0.667, noise_w: float = 0.8) -> None:
        self.model_dir = Path(model_dir)
        self.threads = threads
        self.speaker, self.emotion = speaker, emotion
        self.noise, self.noise_w = noise, noise_w
        self._sess = None
        self._table: dict[str, int] = {}
        self._sr = 24000
        self._add_blank = True
        self._meta: dict[str, str] = {}
        self._inputs: dict[str, object] = {}

    def warmup(self) -> None:
        if self._sess is not None:
            return
        import onnxruntime as ort  # noqa: PLC0415

        model, tokens = self.model_dir / "model.onnx", self.model_dir / "tokens.txt"
        for f in (model, tokens):
            if not f.is_file():
                raise EngineError(f"{f} is missing; run deploy/install.sh to fetch the model")
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = self.threads
        sess = ort.InferenceSession(str(model), opts, providers=["CPUExecutionProvider"])
        meta = dict(sess.get_modelmeta().custom_metadata_map or {})
        self._sr = int(meta.get("sample_rate", 24000))
        self._add_blank = str(meta.get("add_blank", "1")).strip().lower() in ("1", "true", "yes")
        self._meta = meta
        self._inputs = {i.name: i for i in sess.get_inputs()}
        self._table = load_tokens(tokens)
        self._sess = sess
        missing = {"x", "x_length", "sid", "emotion_id"} - set(self._inputs)
        if missing:                       # better to fail at load than to feed a graph we misunderstand
            raise EngineError(f"{model} does not declare the expected inputs; missing {sorted(missing)}")
        log.info("vits_rasa ready: sr=%s add_blank=%s tokens=%d threads=%s",
                 self._sr, self._add_blank, len(self._table), self.threads)

    def synthesize(self, text: str, *, speed: float = 1.0, voice: str | None = None) -> Audio:
        self.warmup()
        speaker, emotion = self.speaker, self.emotion
        if voice:                                          # "11" or "11:4" = speaker[:emotion]
            try:
                parts = str(voice).split(":")
                speaker = int(parts[0])
                if len(parts) > 1:
                    emotion = int(parts[1])
            except ValueError as e:
                raise EngineError("voice must be 'speaker' or 'speaker:emotion'") from e
        ids, unknown = encode(text, self._table, self._add_blank)
        if not ids or len(ids) <= 1:
            raise EngineError("no speakable characters in the text")
        if unknown:
            share = len(unknown) / max(len(text), 1)
            if share > MAX_UNKNOWN_SHARE:
                raise EngineError(f"{share:.0%} of the characters are not in the token table")
            log.warning("left out %d unknown character(s)", len(unknown))

        seq = np.array([ids], dtype=np.int64)
        # length_scale is a duration multiplier: >1 stretches, so it is the inverse of speed.
        length_scale = 1.0 / float(np.clip(speed, 0.5, 2.0))
        feed = {"x": seq,
                "x_length": np.array([seq.shape[1]], dtype=np.int64),
                "sid": np.array([speaker], dtype=np.int64),
                "emotion_id": np.array([emotion], dtype=np.int64)}
        if "noise_scale" in self._inputs:
            feed["noise_scale"] = np.array(self.noise, dtype=np.float32)
        if "noise_scale_w" in self._inputs:
            feed["noise_scale_w"] = np.array(self.noise_w, dtype=np.float32)
        if "length_scale" in self._inputs:
            feed["length_scale"] = np.array(length_scale, dtype=np.float32)
        try:
            out = self._sess.run(None, feed)
        except Exception as e:                             # pragma: no cover
            raise EngineError(f"onnx inference failed: {type(e).__name__}") from e
        pcm = np.asarray(out[0], dtype=np.float32).squeeze()
        if pcm.size == 0:
            raise EngineError("model returned an empty waveform")
        peak = float(np.max(np.abs(pcm))) or 1.0
        if peak > 1.0:                                     # guard against a clipped render
            pcm = pcm / peak
        return Audio(pcm=pcm.astype(np.float32), sr=self._sr)
