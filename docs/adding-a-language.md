# Adding a language

A language is one folder in `lang/`. Adding a language does not change the core: the API, the
translator, the pages and the phrase audio all read the folder.

## Before you start: is there a voice?

Svaram needs an open voice model that can speak the language and whose licence allows commercial
use and redistribution (no "non-commercial" or "research only"). Today Svaram has three voice
services:

| Service | Model | Languages it can speak |
| --- | --- | --- |
| `rasa` | AI4Bharat vits_rasa_13 | Assamese, Bengali, Bodo, Dogri, Kannada, Maithili, Malayalam, Marathi, Nepali, Punjabi, Sanskrit, Tamil, Telugu |
| `kokoro` | Kokoro-82M | Hindi (and English and a few others) |
| `indictts` | AI4Bharat Indic-TTS | Gujarati, Odia (more voices exist upstream) |

If the language is in one of these, you only write a pack. If not, a new voice service is needed
first: open an issue so we can plan it together.

## The pack

```
lang/xx/
  language.yaml   what the rest of Svaram needs to know
  conv.py         the words: number words, months, letters, units, a small lexicon
  phrases.yaml    the quick phrases
  tests.yaml      test sentences (made by the check tool)
  README.md       who made it, sources, known gaps
```

Start by copying the pack closest to yours (same script or same family), for example
`cp -r lang/kn lang/xx`.

### language.yaml

```yaml
code: ta                          # ISO 639 code; also the folder name and the page address /ta/
name: Tamil                       # in English
native: தமிழ்                     # in the language itself
script_block: ["0B80", "0BFF"]    # the Unicode block of the script (quoted hex)
status: testing                   # testing: built and checkable, but not shown on the site; live: shown
script_font: noto-sans-tamil-tamil-400-normal.woff2   # a file in web/static/fonts
translate_target: tam_Taml        # IndicTrans2 language code; leave out if translation is not offered
voice:
  service: rasa                   # rasa | kokoro | indictts
  voice: "18:4"                   # rasa: speaker:style. kokoro and indictts: a voice name
segments:                         # characters in the first piece of speech (about 3 s and about 2 s)
  first_max: 52
  first_split: 35
ui:                               # words on the page, in the language
  speak: ...                      # the verb on the speak button
  stop: ...
  speaking: ...
  translating: ...
  busy: ...                       # "please wait a moment"
  ready: ...                      # "getting ready"
  first: ...                      # "type something first"
  typeHere: "Type in Tamil instead · "
  typeNative: ...                 # "type in Tamil", in Tamil
page:
  title: ...                      # "type in Tamil", in Tamil
  step1: ...                      # "type what you want to say, in Tamil."
  step2: ...                      # "tap the speaker button."
  phrases_head: ...               # "quick phrases · tap to speak"
  more: ...                       # "more (12)"
  less: ...                       # "fewer"
  placeholder: ...                # "type here…"
```

### conv.py

Most packs only describe their words in a `Spec`; the rules that read numbers, times, dates, money,
phone numbers and short forms are shared in `core/indic_conv.py`. Look at `lang/ta/conv.py`: it
lists the number words, how to build numbers in the Indian system (thousand, lakh, crore), the
months, the 26 Latin letters as said in the language (for BP, ATM), units, and a small lexicon of
English words people type (doctor, hospital, common medicine names) written in the script.

If your language needs rules the shared code does not have, a pack may define its own
`prepare(text)` instead of `SPEC`, returning an object with `.spoken`, `.unspeakable` and `.ok`
(Telugu and Hindi do this).

The one rule that matters most: **never drop a word silently.** Anything the voice cannot say must
be reported in `.unspeakable` so the page can show it to the person.

### phrases.yaml

The same twelve phrases as every other pack, with the same `id`s, in your language:

```yaml
- id: cannot-speak
  english: I cannot speak
  text: என்னால் பேச முடியாது
- id: hello
  english: Hello
  text: வணக்கம்
  extra: true          # shown behind "More"
```

Write them as a fluent speaker would say them politely to a stranger, a nurse or a shopkeeper.

## Check it

```bash
python3 tools/check_pack.py xx --init   # first time: records what the pack says for the test sentences
python3 tools/check_pack.py xx          # after any change: shows every difference
python3 tools/build_site.py --out /tmp/site --check
```

Read `lang/xx/tests.yaml` carefully: it shows what the voice will be given for each phrase and for
numbers, times, money and phone numbers. Fix anything a speaker would not say.

## Hear it

On a server running Svaram, add the code to `languages` in `web/site.yaml`, set `status: live`,
rebuild the site, and make the phrase audio:

```bash
python3 tools/make_phrases.py --out /var/www/svaram --lang xx
```

## Send it

Open a pull request with the pack. Say who reviewed the phrases and in which language, and note any
known gaps in the pack's README.md.
