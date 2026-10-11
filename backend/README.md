# Backend API (Agent 1)

FastAPI app that joins the voice, extract and knowledge modules into one endpoint.

## Run

```bash
pip install -e ".[dev]"
USE_STUBS=true uvicorn backend.main:app --reload     # http://localhost:8000/docs
pytest backend
```

## Endpoints

### `GET /health`

```json
{"status": "ok", "version": "0.1.0", "stubs": []}
```

`stubs` lists the modules currently replaced by stubs. An empty list means the real modules are in use.

### `POST /api/check`

Multipart form. Send at least one field.

| Field | Type | Accepted |
| --- | --- | --- |
| `image` | file | JPG, PNG or PDF (checked by file signature, not by file name) |
| `audio` | file | `audio/webm`, `audio/ogg`, `audio/mpeg`, `audio/wav` (checked by content type) |
| `text` | string | typed description of the offer |
| `?save=` | query, bool | default `false`. Reserved: nothing is stored yet, whatever the value. |

Returns `CheckResponse` (see `probashi/schemas.py`).

```bash
curl -X POST localhost:8000/api/check -F 'text=সৌদি আরবে ক্লিনারের চাকরি' -F 'image=@offer.jpg'
```

Steps:

1. `audio` → `voice.transcribe_bn` → `transcript_bn`. If `text` is also sent, the two are joined with a newline.
2. `extract.extract_offer(image, text)` → `knowledge.evaluate(offer)`.
3. Spoken summary = level sentence + first 2 `reasons[].message_bn` + first `next_steps_bn` → `voice.synthesize_bn` → `audio_base64`.

### Errors

Every error has the same shape, with Bangla ready to show the user:

```json
{"detail": {"code": "NO_INPUT", "message_bn": "কিছু পাওয়া যায়নি। ছবি দিন, কথা বলুন, অথবা লিখে দিন।", "message_en": "Nothing was sent. Provide at least one of: image, audio or text."}}
```

| Status | `code` | When |
| --- | --- | --- |
| 422 | `NO_INPUT` | No image, audio or text (empty files and blank text count as nothing) |
| 422 | `INVALID_REQUEST` | Malformed form or query value |
| 422 | `SPEECH_NOT_UNDERSTOOD` | Audio was the only input and no speech was recognised |
| 413 | `TOO_LARGE` | Request body over `MAX_UPLOAD_MB` (default 10) |
| 415 | `UNSUPPORTED_IMAGE`, `UNSUPPORTED_AUDIO` | File type not accepted |
| 502 | `VOICE_UNAVAILABLE` | Speech-to-text failed and audio was the only input |
| 502 | `EXTRACT_FAILED`, `KNOWLEDGE_FAILED` | A core step raised an error. No verdict is returned. |
| 503 | `MODULE_NOT_READY` | A module still has its `NotImplementedError` placeholder |

What does **not** cause an error:

- Voice synthesis fails → 200 with `audio_base64: null`.
- Speech-to-text fails but an image or text was also sent → the check continues without the transcript.

If extract or knowledge fails, the API returns an error rather than guessing a verdict. It never turns a failure into green or amber.

## Stubs and dependency injection

The pipeline receives a `Modules` object (`backend/deps.py`) holding the four functions. `USE_STUBS` chooses where they come from:

| `USE_STUBS` | Effect |
| --- | --- |
| unset or `false` | Real `probashi.*` modules |
| `true` | All three stubbed (`backend/stubs/`) |
| `voice` or `voice,knowledge` | Only the named modules stubbed, the rest real |

Stub answers are synthetic and always amber, with reason codes starting `STUB_`, no sources and no helplines. Responses built with any stub carry the header `X-Probashi-Stubs: extract,knowledge,voice` so they cannot be mistaken for real checks.

In tests, pass your own functions: `create_app(settings, modules)` or `app.dependency_overrides[get_modules]`.

## Privacy

- Uploads are read into memory only. Starlette normally spools uploads over 1 MB to a temp file; the app raises that threshold above the request limit, and a test checks nothing reaches disk.
- Logs are one JSON object per line. The API logs metadata only (which inputs were present, verdict level, reason codes, missing field names, timing), never document text, transcripts or extracted values.
- As a second defence, every logged string, including tracebacks from other modules, is masked for: numbers following "passport"/"visa" (English or Bangla), passport-shaped tokens (1–2 letters + 7–8 digits), and any run of 8 or more digits (ASCII or Bangla).

## Settings

`USE_STUBS`, `CORS_ORIGINS` (comma-separated, default `http://localhost:5173`), `MAX_UPLOAD_MB` (default 10), `LOG_LEVEL` (default `INFO`). See `.env.example`.

## Open questions for other agents

- **Agent 3:** PDFs are passed to `extract_offer` as raw bytes in `image_bytes`, like images. Is that what you expect?
- **Agent 4:** `transcribe_bn` gets the bare mime type (`audio/webm`, codec parameters removed). iPhone Safari may record `audio/mp4`, which is not accepted yet; say if you can handle it.
- **Agent 5:** read errors from `detail.message_bn`. With both `text` and `audio`, both are used.
- **Agent 2:** the backend does not second-guess your verdict. The "unknown is never green" rule is enforced only in `evaluate`.

## Added features

### `POST /api/check` additions

| Field | Type | Meaning |
| --- | --- | --- |
| `more_images` | file, repeatable | Other papers for the same job (visa, contract). At most 3 documents in total, each JPG, PNG or PDF. |
| `?voice=` | query, bool | default `true`. `false` skips speech synthesis, for slow connections. |

The response is `CheckResult` (`backend/models.py`): `CheckResponse` plus an optional `guidance` object. `probashi/schemas.py` is unchanged; clients that only know `CheckResponse` can ignore the extra field.

- **Several documents:** each is extracted on its own, then merged (`probashi/knowledge/consistency.py`). If two papers disagree on a fact, a `DOCUMENT_MISMATCH` reason is added and a green verdict becomes amber. Red stays red.
- **Guidance** (`probashi/knowledge/guidance.py`): follow-up questions for missing facts, questions to ask the agent, the rule behind each reason with its source and last-checked date, a complaint draft for red verdicts, and the extractor's confidence. It is optional: if it fails, the verdict is still returned with `guidance: null`. It can never change the level.

### Other endpoints

| Endpoint | What it does |
| --- | --- |
| `GET /api/guide/{country}` | Rights, pre-departure checklist, payment advice and helplines for a two-letter country code. |
| `GET /api/stats` | Counts since the process started: checks, by level, by channel, by destination, top reason codes, reports. Counts only. In memory, per worker, reset on restart. |
| `POST /api/report` | JSON scam report the user agreed to send (`ReportIn`). Stored as one JSON line in `REPORTS_PATH`. |
| `GET /api/eval` | The engine's score on `data/test_cases/`: cases, correct answers, and `fraud_green` (fraud cases called safe, target 0), with the ids of the misses. Run once per process. 503 `EVAL_UNAVAILABLE` when the engine is a stub. |
| `GET /api/admin/reports` | For review staff: the newest 200 reports and the agencies named more than once (grouped by licence number, else by name). Needs `Authorization: Bearer <ADMIN_TOKEN>`. |
| `POST /api/bots/telegram` | Telegram webhook. Text, photo, document or voice message → verdict as text plus an mp3. Private chats only. |
| `GET`, `POST /api/bots/whatsapp` | WhatsApp Cloud API webhook: verification handshake, then text, image, document or audio → verdict. |

New error codes: `RATE_LIMITED` (429, with `Retry-After`), `TOO_MANY_IMAGES` (422), `CONSENT_REQUIRED` (422), `REPORTING_OFF` (503), `GUIDE_UNAVAILABLE` (503).

### Abuse protection

`/api/check` and `/api/report` allow `RATE_LIMIT_PER_MINUTE` requests per client address (default 20, `0` = off). The limiter is in memory and per process, so with several workers or instances the real limit is higher; put a shared limit at the load balancer for production. `X-Forwarded-For` is believed only when `TRUST_PROXY=true`, and then only its last entry. Bots have the same limit per chat.

### Reports

A report holds: the day, the level, reason codes, destination country, agency name and licence number. It holds no document text, no transcript, no IP address and no time of day. Digit runs in the agency fields are masked like in the logs. A report without `consent: true` is refused, and so is any unknown field. Reporting is off (503) until `REPORTS_PATH` is set. The file is the inbox for a human reviewer, who reads it through `GET /api/admin/reports` (below).

### Review queue

`GET /api/admin/reports` answers 404 until both `ADMIN_TOKEN` and `REPORTS_PATH` are set, 401 `UNAUTHORIZED` without the right token, and is rate limited per client like `/api/check` to slow down guessing. The server refuses to start with a token shorter than 24 characters. There is one shared token and no reviewer accounts, and a reviewer cannot yet mark a report as handled. Several reports about one agency are still claims, not proof.

### Chat channels

A channel answers 404 until all of its variables are set.

- **Telegram:** `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`. Register with `setWebhook`, passing the same secret as `secret_token`; requests without that header are refused.
- **WhatsApp:** `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID`, `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET`. Every POST must carry a valid `X-Hub-Signature-256`. Media is downloaded only from Meta hosts.

Files from chats are fetched into memory, checked and dropped. Tokens never appear in logs. The webhook answers 200 at once and does the work in the background, so the services do not retry.

**Not tested against the live services.** The tests replace all outgoing HTTP with a fake. Before a demo, send one text, one photo and one voice note to each bot.

### New settings

`RATE_LIMIT_PER_MINUTE`, `TRUST_PROXY`, `REPORTS_PATH`, `ADMIN_TOKEN`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID`, `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET`, `WHATSAPP_GRAPH_VERSION`. See `.env.example`.
