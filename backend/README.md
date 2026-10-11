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
