# Architecture

Five small services on one machine, behind nginx. Each is a FastAPI app run by uvicorn under its own
system user, listening on 127.0.0.1 only.

| Service | Folder | Port | Memory cap | Job |
| --- | --- | --- | --- | --- |
| svaram-api | `api/` | 8200 | 256 MB | The public API: prepares text, splits it, calls translation and voices |
| svaram-voice (rasa) | `voices/rasa/` | 8199 | 2 GB | vits_rasa_13 through ONNX Runtime: 9 languages |
| svaram-voice-hi (kokoro) | `voices/kokoro/` | 8202 | 1.5 GB | Kokoro-82M through kokoro-onnx: Hindi |
| svaram-voice-itts (indictts) | `voices/indictts/` | 8203 | 3.5 GB | Indic-TTS through Coqui TTS on PyTorch: Gujarati, Odia |
| svaram-translate | `translate/` | 8201 | 2 GB | IndicTrans2 200M on PyTorch: English to every language |

The caps are the systemd `MemoryMax` values svaram.live uses. Only the voices a site's languages need
are installed: a site with only rasa languages and no translation runs two services.

## A typed message

1. The page sends the text and the language code to `/api/prepare` (or `/api/convey` for English).
2. svaram-api finds the language pack and runs its `prepare()`: numbers, times, dates, money, phone
   numbers, units and short forms become words; English words from the pack's lexicon are written in
   the script; anything else is reported by position, never dropped.
3. For English, svaram-translate translates first, and the API checks that the numbers survived.
4. The spoken text is cut into segments: a short first one so sound starts within about a second,
   each next one at most twice as long, so the next is ready before the current one ends.
5. The page calls `/api/speak` for each segment; svaram-api forwards it to the language's voice
   service, which checks every character against the script and the model's table and returns MP3.

## A quick phrase

Phrase audio is made once, at install, by `tools/make_phrases.py` through the same steps, and served
as plain files from `/phrases/<code>/<id>.mp3`. A tap costs the server nothing.

## Language packs

`core/packs.py` loads every folder in `lang/`. `language.yaml` tells the API which voice service and
voice to use, the translation target and the segment sizes; the voice services read it for the
script each language may contain; `tools/build_site.py` reads it for the page words and phrases.
See [adding-a-language.md](adding-a-language.md).

## Safety rails

- Every service refuses to start unless its model files match their recorded SHA-256.
- Each voice has a short bounded queue; when it is full the answer is `ENGINE_BUSY` with a wait,
  which the page shows as a countdown, rather than piling up requests.
- nginx limits requests per address (generously: many mobile users share one address), accepts only
  same-origin calls to the API, and caps body size at 8 KB.
