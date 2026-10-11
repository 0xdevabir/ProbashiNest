# ProbashiNest — Probashi Shield

Probashi Shield checks a Bangladeshi migrant worker's job offer before they pay a recruiting agent. The worker speaks in Bangla or photographs the offer letter, visa or contract, and gets a red / amber / green verdict with reasons and next steps, spoken back in Bangla.

Built for the International AI Builders Congress 2026 (Idea to Unicorn, JusticeSphere AI).

## How it works

```
Worker (voice or photo)
  → probashi.voice.transcribe_bn      Bangla speech to text
  → probashi.extract.extract_offer    OCR + key facts (employer, salary, agency, fees, country)
  → probashi.knowledge.evaluate       rules first, then RAG with cited sources → verdict
  → probashi.voice.synthesize_bn      spoken Bangla answer
  → frontend                          traffic-light result, reasons, next steps, helplines
```

## Repository layout

| Folder | Owner | What it holds |
| --- | --- | --- |
| `probashi/schemas.py` | Shared | Data contract used by every module (do not edit) |
| `probashi/llm.py` | Shared | Swappable LLM wrapper |
| `probashi/extract/` | Agent 3 | Document reading and fact extraction |
| `probashi/knowledge/`, `data/` | Agent 2 | Knowledge base, verdict engine, test cases |
| `probashi/voice/` | Agent 4 | Bangla speech-to-text and text-to-speech |
| `backend/`, `infra/` | Agent 1 | FastAPI API, integration, AWS deployment |
| `frontend/` | Agent 5 | Mobile-first web app |

Rules for contributors (human or AI) are in [CLAUDE.md](CLAUDE.md).

## Run locally with stubs

No API keys are needed. Stubs stand in for the extract, knowledge and voice modules and return synthetic, always-amber answers.

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env          # USE_STUBS=true is already set there
pytest
uvicorn backend.main:app --reload
```

Then try it:

```bash
curl localhost:8000/health
curl -X POST localhost:8000/api/check -F 'text=সৌদি আরবে ক্লিনারের চাকরি'
```

Interactive API docs are at http://localhost:8000/docs. Or run the backend and the frontend together with Docker:

```bash
docker compose up --build     # backend on :8000, frontend on :5173
```

## Switch to the real modules

Each module folder starts with a placeholder that raises `NotImplementedError`; the owning agent replaces it.

1. In `.env`, set `USE_STUBS=false` and fill in `ANTHROPIC_API_KEY` and the voice provider settings.
2. Restart the backend. `GET /health` should show `"stubs": []`.

While only some modules are ready, stub the rest by name, for example `USE_STUBS=voice` or `USE_STUBS=voice,knowledge`. A module that is neither implemented nor stubbed makes `/api/check` return `503 MODULE_NOT_READY`.

Any response built with a stub carries the header `X-Probashi-Stubs`. If `USE_STUBS` is not set at all, the backend uses the real modules, so a deployment cannot serve fake verdicts by accident.

## More

- API reference, error codes and privacy notes: [backend/README.md](backend/README.md)
- AWS deployment, env vars and cost estimate: [infra/README.md](infra/README.md)
