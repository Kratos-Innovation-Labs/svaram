# Contributing to Svaram

Thank you for helping. Svaram is used by people who cannot speak, so every change is judged by one
question: does it help someone be understood, safely and privately?

## What helps most

- **Languages.** A new language pack, or better words, numbers or phrases for an existing one
  (see [docs/adding-a-language.md](docs/adding-a-language.md)).
- **Pronunciation fixes.** A word a voice says wrongly: open an issue with the language, the text,
  and what it should sound like.
- **Accessibility.** Larger touch targets, screen-reader behaviour, low-end phones.
- **Deployment.** Notes from running Svaram in a hospital, school or NGO.

## Rules that keep Svaram safe

1. **Never log typed text.** Not in a log line, an error message, an error response or a test
   fixture taken from a real person. Logs carry codes, sizes and timings only.
2. **Never drop a word silently.** If the voice cannot say something, report its position so the
   page can show it.
3. **Only commercially usable, redistributable models and data.** Nothing licensed
   non-commercially or for research only (see the "Never use" list in [CREDITS.md](CREDITS.md)).
4. **No paid or outside services** in the default path: no hosted translation or speech APIs.
5. **No tracking.** No analytics, no third-party scripts or fonts, no "phone home".

## How to send a change

1. Open an issue first for anything larger than a small fix, so we can agree the approach.
2. Fork, make the change, and run the checks:
   ```bash
   pip install pyyaml fastapi httpx pytest
   python3 tools/check_pack.py
   python3 -m pytest tests
   python3 tools/build_site.py --out /tmp/site --check
   ```
3. Sign off every commit (`git commit -s`). This adds
   `Signed-off-by: Your Name <you@example.com>` and certifies the
   [Developer Certificate of Origin](https://developercertificate.org/): that you wrote the change
   or have the right to submit it under the Apache License 2.0. There is no separate contributor
   agreement.
4. Open a pull request describing what changes for the person using Svaram.

## Language review

A language pack is merged when its phrases have been read by at least one fluent speaker (say so in
the pull request) and `tools/check_pack.py` passes. Voice quality is checked by machine
(speech-recogniser round trip) before a language goes live on svaram.live.

## Code of conduct

Be respectful. Speak about people who cannot speak with dignity: "people who cannot speak" or "people
who have lost their voice", never "mute", "dumb" or "suffers from". Harassment of any kind is not
tolerated; report it to the maintainers through a GitHub issue marked private, or by email to the
address in the repository profile.
