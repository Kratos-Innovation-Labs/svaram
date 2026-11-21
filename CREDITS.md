# Credits and licences

Svaram's own code is licensed under the Apache License 2.0 (see `LICENSE`). Svaram does **not**
contain any of the models below: `deploy/install.sh` downloads each one from its publisher. Each
keeps its own licence, and Apache-2.0 on Svaram's code does not relicense any of them.

If you run Svaram, you must show the attributions marked **Required** where your users can see
them. The page footers and the About page that `tools/build_site.py` writes already do this; keep
them if you change the pages.

## Voices

| Model | Used for | Licence | Attribution |
| --- | --- | --- | --- |
| [AI4Bharat vits_rasa_13](https://huggingface.co/ai4bharat/vits_rasa_13) | Telugu, Tamil, Kannada, Marathi, Bengali, Punjabi, Malayalam, Assamese and Dogri | CC-BY-4.0 (from the model card's metadata) | **Required.** "Speech synthesis uses the VITS Rasa model by AI4Bharat (https://huggingface.co/ai4bharat/vits_rasa_13), licensed under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)." |
| [MatiasLin/sherpa-onnx-vits-rasa-13](https://huggingface.co/MatiasLin/sherpa-onnx-vits-rasa-13) | The ONNX conversion of vits_rasa_13 that Svaram runs | Follows vits_rasa_13 | Name it as a third-party conversion, not AI4Bharat's own files |
| [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) by hexgrad | Hindi | Apache-2.0 | Keep the licence notice |
| [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) by thewh1teagle | Runs Kokoro | MIT | Keep the copyright notice |
| [AI4Bharat Indic-TTS](https://github.com/AI4Bharat/Indic-TTS) | Gujarati and Odia | Code MIT. Voices trained on the [IIT Madras Indic TTS database](https://www.iitm.ac.in/donlab/indictts/), © TTS Consortium, TDIL, MeitY | **Required.** Name AI4Bharat and the IIT Madras Indic TTS database, as the About page does |

## Translation

| Model | Used for | Licence | Attribution |
| --- | --- | --- | --- |
| [IndicTrans2 en-indic distilled 200M](https://huggingface.co/ai4bharat/indictrans2-en-indic-dist-200M) by AI4Bharat | English to every language | MIT | Keep the copyright notice |
| [IndicTransToolkit](https://github.com/VarunGumma/IndicTransToolkit) | Pre- and post-processing for IndicTrans2 | MIT | Keep the copyright notice |

## Libraries installed alongside, never copied into this repository

| Library | Licence | Note |
| --- | --- | --- |
| [eSpeak NG](https://github.com/espeak-ng/espeak-ng), installed by the `espeakng-loader` package | GPL-3.0 | Works out Hindi pronunciation for Kokoro. Svaram calls it as a separately installed library and does not modify it. |
| [Coqui TTS (Idiap fork)](https://github.com/idiap/coqui-ai-TTS) | MPL-2.0 | Runs the Indic-TTS voices. Changes to its own files would have to stay open; Svaram does not change them. |
| PyTorch | BSD-3-Clause | Indic-TTS and IndicTrans2 run on it |
| ONNX Runtime | MIT | Runs vits_rasa_13 and Kokoro |
| FastAPI, Uvicorn, Pydantic, NumPy, PyYAML, lameenc, transformers | MIT, BSD, Apache-2.0 or LGPL (lameenc: LGPL-3.0, used as an unmodified library) | Installed from PyPI by the installer |

## Fonts

Noto Sans (Bengali, Devanagari, Gujarati, Gurmukhi, Kannada, Malayalam, Oriya, Tamil, Telugu) by
Google, SIL Open Font License 1.1. The fonts and `OFL.txt` are in `web/static/fonts/`.

## Never use

These are licensed for non-commercial or research use only, which would stop others from freely
using and redistributing Svaram. Pull requests that add them are refused.

- `facebook/mms-tts-*` (all languages): CC-BY-NC-4.0.
- Piper voices descended from `en_US-lessac` (including `en_US-amy`, `en_GB-alan`, `en_GB-alba`, both `hfc` voices and `te_IN-maya`): research-only dataset licence.
- `ai4bharat/IndicF5`: tagged MIT, but its relationship to the CC-BY-NC F5-TTS checkpoints is not stated.

## Open questions

- vits_rasa_13's CC-BY-4.0 rests on the Hugging Face metadata tag; the repository has no LICENSE
  file and the card does not name the training data. AI4Bharat has been asked to confirm on the
  model's discussion page.
