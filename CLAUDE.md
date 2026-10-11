# Probashi Shield — instructions for every agent

This repo (ProbashiNest) is built by 5 parallel Claude Code agents. Read this whole file before starting.

## The product

Probashi Shield is a Bangla voice-first AI tool for the International AI Builders Congress 2026 (Idea to Unicorn, JusticeSphere AI). It checks a Bangladeshi migrant worker's job offer before they pay a recruiting agent. The worker speaks in Bangla or photographs an offer letter, visa or contract. The system extracts key facts, checks them against labour rules, licensed agency data and known fraud patterns, and returns a traffic-light verdict (red / amber / green) with reasons and next steps, spoken back in Bangla.

Users: first-time migrant workers going to the Gulf states and Malaysia, and their families. Many have low literacy, cheap Android phones and slow internet.

## Folder ownership

| Folder | Owner | Responsibility |
| --- | --- | --- |
| `probashi/schemas.py` | Shared | Data contract. **Never modify.** Import from it. |
| `probashi/llm.py` | Shared | LLM wrapper. Use it; ask before changing its signatures. |
| `probashi/extract/` | Agent 3 | OCR and fact extraction |
| `probashi/knowledge/`, `data/` | Agent 2 | Rules, RAG, verdict engine, test cases |
| `probashi/voice/` | Agent 4 | Bangla speech-to-text and text-to-speech |
| `backend/`, `infra/`, root config files | Agent 1 | FastAPI API, integration, deployment |
| `frontend/` | Agent 5 | Mobile-first web app |

Only create or edit files inside your own folders. Each module folder currently contains a placeholder `__init__.py` that raises `NotImplementedError`; the owner replaces it but keeps the function signatures. If you need another agent's module before it exists, write a clearly marked stub inside your own folder or tests, never in theirs. Put your tests in a `tests/` folder inside your own folder; the root `tests/` folder is for shared-contract tests only.

## Module interfaces

```python
probashi.extract.extract_offer(image_bytes: bytes | None, text: str | None) -> ExtractedOffer
probashi.knowledge.evaluate(offer: ExtractedOffer) -> Verdict
probashi.voice.transcribe_bn(audio_bytes: bytes, mime_type: str) -> str
probashi.voice.synthesize_bn(text: str) -> bytes  # mp3
```

HTTP API (Agent 1):
- `POST /api/check` — multipart with optional `image`, optional `audio`, optional `text` (at least one) → `CheckResponse` JSON
- `GET /health`

## Global rules

- Python 3.11+, Pydantic v2, pytest. Frontend: React + Vite + TypeScript + Tailwind.
- Secrets only from environment variables. Add any new variable to `.env.example`. Never commit keys.
- LLM calls go through `probashi/llm.py` (`complete_text`, `complete_json`). Provider and model come from `LLM_PROVIDER` and `LLM_MODEL`.
- **Safety rule:** missing or unverifiable evidence must NEVER produce `green`. Unknown means `amber`.
- **Never invent** laws, agency names, licence numbers, phone numbers or statistics. Every fact needs a source URL, or must be marked TODO / unverified. Made-up test data must be labelled synthetic.
- Privacy: do not store uploaded documents or audio on disk; mask passport and visa numbers in logs.
- Bangla text shown to users must be simple, short-sentence, spoken-style Bangla suitable for low-literacy readers.
- Work on your own git branch (`agent-1-backend`, `agent-2-knowledge`, `agent-3-extract`, `agent-4-voice`, `agent-5-frontend`). Commit often with clear messages.
- Finish with: passing tests, a README section for your part (in your folder's `README.md`), and a short summary of what is done, what is stubbed, and any open questions.

## Running the shared tests

```bash
pip install -e ".[dev]"
pytest
```
