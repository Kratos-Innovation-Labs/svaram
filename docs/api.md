# API

svaram-api answers on `/api/` (through nginx) or `http://127.0.0.1:8200` (on the server). Every
request is JSON; `lang` is the code of a live language pack (`te`, `hi`, `ta`, ...). Errors are
`{"error": {"code": "...", ...}}` and never contain the text that was sent.

## POST /api/prepare

Text typed in the language itself.

```json
{"text": "నాకు 2 మాత్రలు కావాలి", "lang": "te", "skip_unspeakable": false}
```

| Answer | Meaning |
| --- | --- |
| `{"ok": true, "segments": ["...", "..."], "skipped": 0}` | Ready: speak each segment in order |
| `{"ok": false, "unspeakable": [[start, end], ...]}` | Words the voice cannot say, as UTF-16 offsets into the text you sent. Send again with `skip_unspeakable: true` to speak the rest |
| `{"ok": false, "nothing_to_say": true}` | Nothing speakable (only symbols, for example) |

## POST /api/convey

Text typed in English: translated, then prepared as above.

```json
{"text": "I need 2 tablets at 10:30", "lang": "ta"}
```

`{"ok": true, "telugu": "<the translation>", "translated": true, "numbers_ok": true, "segments": [...]}`

`telugu` holds the translation in whichever language was asked (the name is kept for compatibility).
`numbers_ok` is false when the digits in the translation differ from the English: show the person a
warning before speaking. `TRANSLATE_NOT_OFFERED` (400) means the pack has no translation target.

## POST /api/speak

One segment from `prepare` or `convey`.

```json
{"text": "<segment>", "lang": "te", "rate": 1.0}
```

Returns `audio/mpeg`, with `X-Audio-Duration-Ms`. `rate` is 0.8 to 1.25.

## GET /api/health

`{"status": "ok" | "degraded", "translate": "ok" | "unavailable", ...}` with one entry per extra voice
service in use. No internals.

## Error codes

| Code | Status | Meaning |
| --- | --- | --- |
| `REQUEST_INVALID` | 400 | Malformed request or unknown language |
| `TEXT_EMPTY` | 400 | Nothing typed |
| `TEXT_TOO_LONG` | 413 | Over `max_chars` (500 by default) |
| `TRANSLATE_UNAVAILABLE` | 503 | Translator down or busy; `retry_after_ms` given |
| `VOICE_UNAVAILABLE` | 503 | Voice service down |
| `ENGINE_BUSY` | 503 | Voice queue full; `retry_after_ms` given |
| `UNSPEAKABLE_CHARS` | 422 | The voice found characters it cannot say; `positions` given |
| `RATE_LIMITED` | 429 | nginx limit reached; `retry_after_ms` given |
| `INTERNAL` | 500 | Anything else |

## Voice services (internal)

Each voice service answers `POST /v1/synth {"text", "lang", "voice", "format": "mp3"|"wav", "rate"}`
and `GET /health` on 127.0.0.1 only. svaram-translate answers
`POST /v1/translate {"text", "tgt"}`. They are not exposed through nginx.
