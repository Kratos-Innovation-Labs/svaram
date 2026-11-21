# Svaram: give everyone a voice

Svaram (स्वरम्) is a free, open-source assistive communication platform. A person who cannot speak
types a sentence, or taps a ready phrase, and Svaram says it aloud in their language. They can also
type in English and have it translated and spoken in their language.

It runs today at **[svaram.live](https://svaram.live)** in twelve Indian languages: Telugu, Hindi,
Tamil, Kannada, Marathi, Bengali, Punjabi, Malayalam, Assamese, Gujarati, Odia and Dogri.
Try the engine on Hugging Face: [kratos-innovation-labs/svaram](https://huggingface.co/spaces/kratos-innovation-labs/svaram)
(demo) and [svaram-phrases](https://huggingface.co/datasets/kratos-innovation-labs/svaram-phrases) (dataset).

Communication should never be a privilege. Svaram is released as a public good: a hospital, an NGO,
a university or a developer anywhere can run it, add their own languages and offer it to the people
who need it.

> Svaram suits people who can read and use a phone. It is not yet for every speech or language
> impairment, it is not a medical device, and it is not an emergency alarm.

## Principles

1. **Free to use.** No subscriptions, no compulsory registration, no per-user fees.
2. **Open source.** Anyone can inspect, deploy, modify and redistribute Svaram (Apache-2.0).
3. **Open to every language.** A language is a folder: add one without touching the core.
4. **Self-hostable.** One ordinary CPU-only Linux server. No GPU, no paid services.
5. **Privacy first.** Nothing a person types is stored, logged or sent to anyone else.

## How it works

```
phone (svaram.live page)
  ├── tap a phrase ──────────► ready-made audio file, plays at once
  └── type a sentence ──► svaram-api ──► (English only) svaram-translate: IndicTrans2
                              │
                              └──► voice service for the language ──► audio back to the phone
                                   rasa: vits_rasa_13 · kokoro: Kokoro-82M · indictts: Indic-TTS
```

The API tidies the text, reads numbers, times, money and short forms as words, reports any word the
voice cannot say (it never drops one silently), and splits long messages so sound starts quickly.
See [docs/architecture.md](docs/architecture.md).

## Repository

| Folder | What is in it |
| --- | --- |
| `lang/` | One **language pack** per language: names, voice, phrases, number words, tests |
| `core/` | Shared text rules (`indic_conv.py`) and the pack loader (`packs.py`) |
| `api/` | svaram-api, the public API the page calls |
| `translate/` | svaram-translate (IndicTrans2) |
| `voices/` | The three voice services: `rasa`, `kokoro`, `indictts` |
| `web/` | Page templates, styles, script, fonts and `site.yaml` |
| `tools/` | `build_site.py`, `make_phrases.py`, `check_pack.py`, `fetch_models.py`, `selftest.py`, `build_space.py`, `export_dataset.py` |
| `space/` | The Hugging Face demo: Gradio page, start script, Dockerfile |
| `deploy/` | Installer, sample systemd units, nginx site and settings |
| `docs/` | Architecture, API, deploying, adding a language, privacy |

## Quick start

On a fresh Ubuntu server (24.04 tested) with 4 CPU cores and about 6 GB of free memory for all twelve languages (3.5 GB without Gujarati and Odia):

```bash
git clone https://github.com/Kratos-Innovation-Labs/svaram.git
cd svaram
sudo bash deploy/install.sh --languages te,hi --domain your.domain   # or leave out --languages for all
```

The installer creates one Python environment per service, downloads only the models the chosen
languages need, checks every file against its SHA-256, sets up systemd and nginx, builds the pages
and makes the phrase audio. Details: [docs/deploying.md](docs/deploying.md).

## Add a language

Copy a pack in `lang/`, translate its words and phrases, run `python3 tools/check_pack.py <code>`,
and open a pull request. Step by step: [docs/adding-a-language.md](docs/adding-a-language.md).

## Privacy

Typed text lives in memory for one request and is never written to disk or to any log; error
messages never contain it; the web server logs shortened addresses and no request bodies.
Anyone running the default setup gets the same protection. See [docs/privacy.md](docs/privacy.md).

## Credits

Svaram stands on open models and tools by AI4Bharat, IIT Madras, hexgrad and others.
**Their licences and the attribution they require are in [CREDITS.md](CREDITS.md).**

## Contributing

Issues and pull requests are welcome. Every commit needs a `Signed-off-by` line
(`git commit -s`); see [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

Svaram's code is licensed under the Apache License 2.0. Copyright 2026 Kratos Innovation Labs Limited.
Svaram is an initiative of [Kratos Innovation Labs](https://svaram.live/about/).
