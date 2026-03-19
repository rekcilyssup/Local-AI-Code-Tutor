# LeetCode Mentor (Local RAG)

LeetCode Mentor is a local-first RAG app that helps review coding attempts using your own past submission history.

It uses:
- FastAPI backend for retrieval and model streaming
- ChromaDB for vector storage
- Ollama for local LLM + embeddings
- React + TypeScript frontend for rich chat-style interaction

The key goal is grounded mentoring: responses are generated with retrieved examples from your database, and the UI can show source context used in generation.

## What This Project Does

1. Scrapes your recent LeetCode submissions.
2. Stores code + metadata in ChromaDB.
3. Retrieves similar examples (failed + accepted) for a new code input.
4. Builds a strict mentor prompt with retrieval context.
5. Streams LLM output token-by-token to the UI.
6. Shows citations/sources and telemetry metrics.

## Architecture

- Backend app entry: [backend/app/main.py](backend/app/main.py)
- Versioned API router: [backend/app/api/v1/api.py](backend/app/api/v1/api.py)
- Mentor routes: [backend/app/api/v1/routes/mentor.py](backend/app/api/v1/routes/mentor.py)
- Settings: [backend/app/core/settings.py](backend/app/core/settings.py)
- Chroma client helpers: [backend/app/db/chroma_client.py](backend/app/db/chroma_client.py)
- Ollama embedding function: [backend/app/db/embedding.py](backend/app/db/embedding.py)
- Retrieval + prompt builder: [backend/app/services/mentor_service.py](backend/app/services/mentor_service.py)
- LLM streaming + SSE events: [backend/app/services/llm_stream_service.py](backend/app/services/llm_stream_service.py)
- React frontend: [frontend/src/App.tsx](frontend/src/App.tsx)
- Scraper job: [backend/scripts/scrape_leetcode.py](backend/scripts/scrape_leetcode.py)
- Ingestion job: [backend/scripts/ingest_submissions.py](backend/scripts/ingest_submissions.py)
- API contract doc: [backend/docs/frontend-backend-contract.md](backend/docs/frontend-backend-contract.md)

## API Overview

Base URL: `http://127.0.0.1:8000`

- `GET /api/v1/health`
- `POST /api/v1/mentor`
- `POST /api/v1/mentor/stream` (SSE)

SSE events include:
- `sources`
- `token`
- `metrics`
- `done`
- `error`

## Prerequisites

1. Python 3.11+ (your local setup currently uses 3.14).
2. Ollama running locally.
3. Required models available in Ollama:
- chat model set in `MENTOR_MODEL`
- embedding model set in `EMBED_MODEL` (default `nomic-embed-text`)

Example:

```bash
ollama list
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

## Setup

1. Create and activate virtual environment.

```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies.

```bash
pip install -r requirements.txt
```

3. Create local env file.

```bash
cp .env.example .env
```

4. Adjust config if needed in [backend/app/core/settings.py](backend/app/core/settings.py) and `.env`.

Important defaults:
- `MENTOR_MODEL=llama3.1:8b`
- `EMBED_MODEL=nomic-embed-text`
- `LOCAL_LLM_TIMEOUT_SECONDS=120`
- `LOCAL_LLM_STARTUP_CHECK=true`
- `CHROMA_PATH=./data/chroma_db`
- `CHROMA_COLLECTION=leetcode_submission_code`

When startup check is enabled, the backend logs a warning if Ollama is not reachable or if `MENTOR_MODEL` is not installed locally.

## Data Pipeline (Scrape + Ingest)

1. Scrape submissions:

```bash
cd backend
python -m scripts.scrape_leetcode --limit 100
```

2. Ingest into Chroma:

```bash
cd backend
python -m scripts.ingest_submissions
```

This populates the active Chroma path from `.env` (default `./data/chroma_db`).

## Run Backend + Frontend

Terminal 1 (backend):

```bash
cd backend
uvicorn app.main:app --reload
```

Terminal 2 (frontend):

```bash
cd frontend
npm install
npm run dev
```

## Model Control

Model selection is backend-driven.

Set your active model in `.env` using:
- `MENTOR_MODEL=<your_model_tag>`

Restart backend after changes.

The frontend sidebar shows the currently active backend model for visibility.

## How To Verify RAG Is Actually Working

When `RAG_DEBUG=true`, backend terminal prints retrieval traces:

- request preview
- matched examples
- status/title/lang/distance
- stream timing metrics

Expected healthy trace example:

```text
[RAG] request top_k=2 ...
[RAG] match 1: status=Wrong Answer title=... distance=...
[RAG] match 2: status=Accepted title=... distance=...
[RAG] stream metrics ttft=... gen=... total=...
```

UI verification:
- Use "View Sources & Metrics" in chat to inspect retrieved source docs and telemetry.

## Common Issues

1. `ModuleNotFoundError: fastapi`
- You likely installed into wrong Python environment.
- Activate venv and run `pip install -r requirements.txt`.

2. No retrieval matches (`RAG grounding warning: no retrieval matches returned`)
- Check `CHROMA_PATH` points to populated DB.
- Re-run ingestion.

3. Ollama model not found (404)
- Ensure exact model tag exists in `ollama list`.
- Update `MENTOR_MODEL` accordingly.

## Notes For UI Contributors

Use [docs/frontend-backend-contract.md](docs/frontend-backend-contract.md) as the API compatibility source of truth.

Do not change endpoint paths or SSE event schema unless backend and docs are updated together.

## License

Add your preferred license file for open/public distribution.
