---
title: Svaram
emoji: 🗣️
colorFrom: indigo
colorTo: green
sdk: docker
app_port: 7860
pinned: true
startup_duration_timeout: 1h
license: apache-2.0
short_description: Type in English, be heard in 12 Indian languages
models:
  - ai4bharat/indictrans2-en-indic-dist-200M
  - MatiasLin/sherpa-onnx-vits-rasa-13
  - hexgrad/Kokoro-82M
datasets:
  - kratos-innovation-labs/svaram-phrases
tags:
  - text-to-speech
  - assistive-technology
  - accessibility
  - aac
  - indic
---

# Svaram (स्वरम्)

Free type-to-speech for people who cannot speak. Type in English, pick one of 12 Indian languages,
and Svaram shows the sentence in that language and speaks it aloud.

This Space is a demo of the open-source engine. **For everyday use, go to [svaram.live](https://svaram.live).**

| | |
|---|---|
| Languages | Assamese, Bengali, Dogri, Gujarati, Hindi, Kannada, Malayalam, Marathi, Odia, Punjabi, Tamil, Telugu |
| Translation | AI4Bharat IndicTrans2, English to Indic, distilled 200M (MIT) |
| Voices | AI4Bharat vits_rasa_13 (CC-BY-4.0) for nine languages, Kokoro-82M (Apache-2.0) for Hindi, AI4Bharat Indic-TTS for Gujarati and Odia |
| Code | [github.com/Kratos-Innovation-Labs/svaram](https://github.com/Kratos-Innovation-Labs/svaram) (Apache-2.0) |
| Phrases | [kratos-innovation-labs/svaram-phrases](https://huggingface.co/datasets/kratos-innovation-labs/svaram-phrases) (CC-BY-4.0) |

## How it works

English text goes to IndicTrans2, the translation is prepared by that language's pack (numbers,
short forms and symbols become words), and the matching voice speaks it. This Space runs the same
five services as svaram.live, with the same pinned versions; the models are downloaded from their
publishers when the Space starts and every file is checked against its SHA-256.

## Privacy

Nothing you type is saved or logged. The audio files the page needs for playback are deleted after
a few minutes. The demo runs on Hugging Face's servers.

## Credits

Translation and the Rasa and Indic-TTS voices are by [AI4Bharat](https://ai4bharat.iitm.ac.in/) (IIT Madras);
Kokoro-82M is by hexgrad. Full credits and licences: [CREDITS.md](https://github.com/Kratos-Innovation-Labs/svaram/blob/main/CREDITS.md).
Svaram is built by Kratos Innovation Labs.
