---
title: Svaram
emoji: 🗣️
colorFrom: indigo
colorTo: green
sdk: static
pinned: true
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

This page is a demo; the speech comes from [svaram.live](https://svaram.live), which runs the
open-source engine on its own CPU server. **For everyday use, go to svaram.live.**

| | |
|---|---|
| Languages | Assamese, Bengali, Dogri, Gujarati, Hindi, Kannada, Malayalam, Marathi, Odia, Punjabi, Tamil, Telugu |
| Translation | AI4Bharat IndicTrans2, English to Indic, distilled 200M (MIT) |
| Voices | AI4Bharat vits_rasa_13 (CC-BY-4.0) for nine languages, Kokoro-82M (Apache-2.0) for Hindi, AI4Bharat Indic-TTS for Gujarati and Odia |
| Code | [github.com/Kratos-Innovation-Labs/svaram](https://github.com/Kratos-Innovation-Labs/svaram) (Apache-2.0) |
| Phrases | [kratos-innovation-labs/svaram-phrases](https://huggingface.co/datasets/kratos-innovation-labs/svaram-phrases) (CC-BY-4.0) |

## Privacy

Your text goes from your browser straight to svaram.live, which speaks it and keeps nothing. This
page has no cookies, no storage and no analytics.

## Run it yourself

Everything behind this page is open source: one CPU-only Linux server runs it all
(`deploy/install.sh` in the repository). The repository also has a Docker version of this demo
(`space/`) that runs the models inside the Space itself.

Credits: translation and the Rasa and Indic-TTS voices are by [AI4Bharat](https://ai4bharat.iitm.ac.in/)
(IIT Madras); Kokoro-82M is by hexgrad. Full credits: [CREDITS.md](https://github.com/Kratos-Innovation-Labs/svaram/blob/main/CREDITS.md).
Svaram is built by Kratos Innovation Labs.
