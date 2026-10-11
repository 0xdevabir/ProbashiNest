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

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # then fill in your keys
pytest
```

Each module currently has a placeholder that raises `NotImplementedError`; the owning agent replaces it.
