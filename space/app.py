# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
"""Svaram demo page for Hugging Face Spaces: type in English, hear it in an Indian language.

The page is a thin Gradio front on the same Svaram API that svaram.live runs (api/svaram_api.py),
started inside this container by start.sh together with the translator and the three voices.
English goes to /api/convey (IndicTrans2, then the language pack), each returned segment to
/api/speak, and the audio pieces are joined into one MP3.

Privacy: the text lives in memory for one request. Nothing here logs it, there is no flagging,
Gradio analytics are off, and the audio files Gradio needs for playback are deleted after a few
minutes.
"""
from __future__ import annotations

import os
import tempfile
import threading
import time
import uuid

import gradio as gr
import requests
import yaml

API = os.environ.get("SVARAM_SPACE_API", "http://127.0.0.1:8200")
SRC = os.environ.get("SVARAM_SRC", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAX_CHARS = int(os.environ.get("SVARAM_SPACE_MAX_CHARS", "300"))
KEEP_AUDIO_S = 300
ORDER = ["te", "hi", "ta", "kn", "ml", "mr", "bn", "gu", "or", "pa", "as", "doi"]
SVARAM_LIVE = "https://svaram.live"
GITHUB = "https://github.com/Kratos-Innovation-Labs/svaram"
DATASET = "https://huggingface.co/datasets/kratos-innovation-labs/svaram-phrases"


def _load_langs() -> dict[str, dict]:
    out = {}
    for code in ORDER:
        d = os.path.join(SRC, "lang", code)
        if not os.path.isfile(os.path.join(d, "language.yaml")):
            continue
        with open(os.path.join(d, "language.yaml"), encoding="utf-8") as f:
            meta = yaml.safe_load(f)
        with open(os.path.join(d, "phrases.yaml"), encoding="utf-8") as f:
            phrases = [p for p in yaml.safe_load(f) if not p.get("extra")]
        out[code] = {"name": meta["name"], "native": meta["native"], "phrases": phrases}
    return out


LANGS = _load_langs()
CHOICES = [(f"{v['native']}  {v['name']}", k) for k, v in LANGS.items()]
FIRST = next(iter(LANGS))
PHRASE_LABELS = [p["english"] for p in LANGS[FIRST]["phrases"]]

# ------------------------------------------------------------------ audio files
AUDIO_DIR = os.path.join(tempfile.gettempdir(), "svaram-audio")
os.makedirs(AUDIO_DIR, exist_ok=True)


def _sweep() -> None:
    """Delete our audio files once they are a few minutes old."""
    while True:
        cut = time.time() - KEEP_AUDIO_S
        for name in os.listdir(AUDIO_DIR):
            p = os.path.join(AUDIO_DIR, name)
            try:
                if os.path.getmtime(p) < cut:
                    os.remove(p)
            except OSError:
                pass
        time.sleep(60)


threading.Thread(target=_sweep, daemon=True).start()


# ------------------------------------------------------------------ the API
class Busy(Exception):
    pass


def _post(path: str, body: dict, timeout: float = 60):
    """POST to the Svaram API; one retry when a service says it is busy."""
    for attempt in (1, 2):
        r = requests.post(API + path, json=body, timeout=timeout)
        if r.status_code == 503 and attempt == 1:
            try:
                wait = r.json()["error"].get("retry_after_ms", 1500) / 1000
            except Exception:                                  # noqa: BLE001
                wait = 1.5
            time.sleep(min(wait, 4))
            continue
        return r
    return r


def _code(r) -> str:
    try:
        return r.json()["error"]["code"]
    except Exception:                                          # noqa: BLE001
        return f"HTTP_{r.status_code}"


MESSAGES = {
    "TEXT_EMPTY": "Type something first.",
    "TEXT_TOO_LONG": f"Please keep it under {MAX_CHARS} characters.",
    "ENGINE_BUSY": "The demo is busy. Try again in a few seconds.",
    "TRANSLATE_UNAVAILABLE": "The translator is still starting. Try again in a minute.",
    "VOICE_UNAVAILABLE": "The voice is still starting. Try again in a minute.",
}


def speak(text: str, lang: str):
    """English (or the language itself) -> (text shown, MP3 path)."""
    name = LANGS[lang]["name"]
    text = (text or "").strip()
    if not text:
        raise gr.Error(MESSAGES["TEXT_EMPTY"])
    if len(text) > MAX_CHARS:
        raise gr.Error(MESSAGES["TEXT_TOO_LONG"])
    try:
        r = _post("/api/convey", {"text": text, "lang": lang})
        if r.status_code != 200:
            raise gr.Error(MESSAGES.get(_code(r), "Something went wrong. Try again."))
        j = r.json()
        if not j.get("ok") and j.get("unspeakable"):
            r = _post("/api/convey", {"text": text, "lang": lang, "skip_unspeakable": True})
            j = r.json() if r.status_code == 200 else {}
            if j.get("ok"):
                gr.Info(f"Some words can't be spoken in {name}, so they were left out.")
        if not j.get("ok"):
            raise gr.Error(f"Nothing here can be spoken in {name}. Type in English or in {name}.")
        if j.get("translated") and not j.get("numbers_ok", True):
            gr.Info("Check the numbers: the translation may have changed them.")
        audio = b""
        for seg in j["segments"]:
            s = _post("/api/speak", {"text": seg, "lang": lang, "rate": 1.0})
            if s.status_code != 200:
                raise gr.Error(MESSAGES.get(_code(s), "The voice could not say this. Try again."))
            audio += s.content                                 # MP3 frames join end to end
    except requests.RequestException as e:
        raise gr.Error("The demo is starting or busy. Try again in a minute.") from e
    path = os.path.join(AUDIO_DIR, f"{uuid.uuid4().hex}.mp3")
    with open(path, "wb") as f:
        f.write(audio)
    return j.get("telugu", ""), path                           # "telugu" = the text in the chosen language


def speak_phrase(i: int):
    def run(lang: str):
        p = LANGS[lang]["phrases"][i]
        _, path = speak(p["text"], lang)
        return p["english"], p["text"], path
    return run


# ------------------------------------------------------------------ the page
INTRO = f"""
# स्वरम् Svaram: type in English, be heard in 12 Indian languages

Free type-to-speech for people who cannot speak. This is a demo of the
[open-source engine]({GITHUB}); for everyday use go to **[svaram.live]({SVARAM_LIVE})**.
"""

FOOTER = f"""
---
Nothing you type is saved or logged. This demo runs on Hugging Face's servers; for everyday use go to
[svaram.live]({SVARAM_LIVE}). Code on [GitHub]({GITHUB}) (Apache-2.0) · [Phrases dataset]({DATASET}) (CC-BY-4.0)

Translation: AI4Bharat IndicTrans2 (MIT) · Voices: AI4Bharat vits_rasa_13 (CC-BY-4.0), Kokoro-82M (Apache-2.0),
AI4Bharat Indic-TTS (see CREDITS.md) · Built by Kratos Innovation Labs
"""

CSS = ".phrase button {min-height: 44px} #shown textarea {font-size: 20px}"

with gr.Blocks(title="Svaram: type in English, be heard", analytics_enabled=False,
               delete_cache=(60, KEEP_AUDIO_S)) as demo:
    gr.Markdown(INTRO)
    text = gr.Textbox(label="Type in English", placeholder="I need some water, please.",
                      lines=3, max_length=MAX_CHARS)
    with gr.Row(equal_height=True):
        lang = gr.Dropdown(choices=CHOICES, value=FIRST, label="Speak in", scale=4)
        go = gr.Button("Speak", variant="primary", scale=1)
    shown = gr.Textbox(label="In the chosen language", interactive=False, lines=2, elem_id="shown")
    audio = gr.Audio(label="Audio", type="filepath", autoplay=True, interactive=False)
    gr.Markdown("**Quick phrases** · tap to hear")
    buttons = []
    for row in range(0, len(PHRASE_LABELS), 3):
        with gr.Row(elem_classes="phrase"):
            buttons += [gr.Button(label, size="sm") for label in PHRASE_LABELS[row:row + 3]]
    gr.Markdown(FOOTER)

    go.click(speak, [text, lang], [shown, audio], api_name="speak", concurrency_limit=2)
    text.submit(speak, [text, lang], [shown, audio], api_name=False, concurrency_limit=2)
    for i, b in enumerate(buttons):
        b.click(speak_phrase(i), [lang], [text, shown, audio], api_name=False, concurrency_limit=2)

if __name__ == "__main__":
    demo.queue(max_size=20).launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", "7860")),
                                   css=CSS, ssr_mode=False, show_error=False, quiet=True)
