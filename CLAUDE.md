# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Meridian AI: a FastAPI backend plus a React/Vite frontend with two features: (1) RAG Q&A over uploaded PDFs (Vertex AI Vector Search + Gemini), and (2) a multi-agent procurement audit (risk, tax and control agents, then a CFO memo). It is a learning project. "Aldermoor Industries" and all sample data in `sample_docs/` are fictional.

## Commands

Run everything from the repo root, because `.env` is resolved relative to the working directory.

```bash
# Backend setup (Python 3.12)
python3.12 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
cp .env.example .env                                     # set GOOGLE_API_KEY at minimum

# Run backend (Swagger UI at http://localhost:8080/docs)
uvicorn api.main:app --app-dir backend --reload --port 8080

# Tests (no network or credentials needed; conftest.py fakes the env)
pytest backend/tests
pytest backend/tests/test_api.py::test_name              # single test

# Smoke-test the audit pipeline directly (from backend/)
cd backend && python -m agent.agents

# Frontend (separate terminal, serves on :3000)
cd frontend && npm install && npm run dev
npm run lint        # eslint
npm test            # vitest run (single file: npx vitest run src/test/example.test.ts)
npm run build       # output to frontend/dist

# Docker (multi-stage: builds frontend, then Python image serving both on :8080)
docker build -t meridian-ai . && docker run -p 8080:8080 --env-file .env meridian-ai
```

## Architecture

The backend packages live in `backend/` and import each other as top-level modules (`from rag.llm import ...`), so `backend/` must be on `sys.path`. That is why uvicorn takes `--app-dir backend` and `tests/conftest.py` inserts it into `sys.path`. Dependency direction is `api -> rag, agent -> config, logger`.

- `api/`: `main.py` builds the app, adds CORS (wide open) and includes the routers. `endpoints.py` defines four routers (`health`, `status`, `agent`, `rag`). `schemas.py` holds the Pydantic models. When `frontend/dist` exists, `main.py` also serves the built SPA through a catch-all route. The route rejects `api/*` paths and guards against path traversal.
- `rag/`: `llm.py` has `get_llm()`, a cached Gemini chat model that authenticates with `GOOGLE_API_KEY`, and `extract_text()`, which flattens Gemini's content-block lists. `embeddings.py` uses Vertex AI and needs GCP credentials. The embedding output must stay at 768 dimensions to match the Vector Search index. `vector_store.py`, `data_ingestion.py` (PDF to chunks to store) and `retrieval.py` (top-3 chunks, then an answer grounded in them) complete the pipeline. This is a deliberate split: the LLM uses an API key, while embeddings and Vector Search use GCP auth.
- `agent/`: `ProcurementSupervisor` in `agents.py` runs three `langchain.agents.create_agent` agents sequentially (risk, tax, control), each with its own prompt (`prompts.py`) and tools (`tools.py`, five mock/LLM-knowledge tools; only the FX check uses live data). It then makes one plain LLM call with `SYNTHESIS_PROMPT_TEMPLATE` for the CFO memo. No LangGraph code is written directly.
- `config/settings.py`: a pydantic-settings `Settings` singleton reading `.env`. Env var names differ from attribute names (e.g. `GCP_PROJECT_ID` is `settings.GCP_PROJECT`, `VERTEX_LLM_MODEL_NAME` is `settings.llm_model_name`). Check the `validation_alias` before adding or using a setting. It also exports `GOOGLE_APPLICATION_CREDENTIALS` from `GCP_SERVICE_ACCOUNT_PATH`.
- `logger/`: structlog JSON logging (`GLOBAL_LOGGER`). It writes files under `./logs` and flushes them to GCS on shutdown/exit when `GCS_BUCKET_NAME` is set. Tests blank that variable to disable the upload.
- `frontend/`: Vite + React + TypeScript + shadcn/ui + Tailwind. Tabs are in `src/components/` (`RagQATab`, `DocumentUploadTab`, `AuditTab`, `SystemStatusTab`). `src/lib/api.ts` is the only code that calls the backend.

## Gotchas

- The audit needs only `GOOGLE_API_KEY`. RAG upload and Q&A also need the GCP and Vector Search settings, plus a deployed index and endpoint. See `DEPLOY.md`, which also covers hourly costs.
- The default model name `gemini-3.8-flash` may be retired. If you see "model not found", set `VERTEX_LLM_MODEL_NAME`.
- Deployment is through `.github/workflows/deploy.yml` to Cloud Run (the Dockerfile honors `$PORT`).
