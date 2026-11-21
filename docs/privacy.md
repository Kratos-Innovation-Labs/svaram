# Privacy

Svaram is used for private, sometimes medical, conversations. Its privacy promises are enforced in
the code, so every copy run with the default setup keeps them.

## What Svaram never does

- **Store what people type.** Text lives in memory for one request: it is prepared, translated or
  spoken, and discarded when the answer is sent. Nothing is written to disk.
- **Log what people type.** Every service logs codes, sizes and timings only. Errors are logged by
  type, never with their message, because messages from libraries can contain input.
- **Echo text in errors.** Invalid requests get a bare code (`REQUEST_INVALID`); FastAPI's default
  validation response, which repeats the input, is replaced. When some words cannot be spoken, the
  API returns their *positions*; the page highlights them from its own copy.
- **Send text anywhere else.** Translation and speech run on the same server. No outside API.
- **Track people.** No accounts, cookies, analytics, ads, third-party scripts or third-party fonts.
- **Phone home.** A copy of Svaram never reports anything to Kratos Innovation Labs.

## What is kept

- **In the person's own browser:** the language they picked and the last few languages they used
  (`localStorage`). Nothing else.
- **On the server, in the web server's access log** (`deploy/nginx.sample.conf`): a shortened IP
  address (last part removed), the time, the method and path (no query string), the status, the size
  and the time taken. No request bodies and no user agent. Keep the log only as long as you need for
  security and capacity.

## How the code enforces it

| Where | What |
| --- | --- |
| `api/svaram_api.py` | `clean()` keeps text in memory; validation and unhandled errors return bare codes; logs carry exception types only |
| `voices/*/` | Engine loggers silenced; the rasa engine's messages never include characters; audio is built in memory |
| `translate/` | Library loggers silenced; text never logged; model files checked by SHA-256 |
| systemd units | `StandardOutput=null`, private /tmp, no write access to the code, network limited to localhost |
| nginx | No request bodies or query strings in logs, shortened addresses, bodies never spill to temporary files |

## If you run Svaram

- Keep the nginx log format from the sample, or one that logs no more.
- Do not add analytics or error-reporting services that capture requests.
- If you need usage numbers, count without identifying anyone (see the design notes on anonymous
  counters in the issues), and publish what you count.
- Tell your users, in their language, what you keep and for how long. Start from
  `web/templates/about.html`.
