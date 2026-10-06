# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Only facts verified by reading code or running a command are stated. Anything else is marked NOT VERIFIED. Evidence lives in `docs/setup-log.md`, `docs/PROJECT_DISCOVERY.md` and `docs/UNDERSTANDING.md`.

## Project summary

Meridian AI is a learning/demo app: a FastAPI backend plus a React/Vite SPA with two features. (1) Document Q&A (RAG): upload PDFs, chunk and embed them into Vertex AI Vector Search, answer questions with Gemini from retrieved chunks. (2) Purchase audit: three LangChain tool-using agents (risk, tax, control) run in sequence, then one plain LLM call writes a CFO memo. The company "Aldermoor Industries" and `sample_docs/` are fictional. Most audit "checks" are LLM recall, not real data; only the FX rate uses a live API.

## Commands (run from the repo root unless noted)

Worked in this repo on Windows PowerShell (Node v25.5.0, npm 11.10.0):
- Install frontend: `cd frontend; npm ci`
- Test frontend: `cd frontend; npm test` (1 test passed, vitest)
- Build frontend: `cd frontend; npm run build` (writes `frontend/dist`)

Ran but failed:
- Lint frontend: `cd frontend; npm run lint` exits 1 (16 problems: 9 errors, 7 warnings). Do not "fix" unless asked.

Not verified (Python 3.12 is not installed on this machine, so none have run):
- Backend install, run, tests. The Quick start and Testing sections of `README.md` list them, marked not yet verified.
- Type-check: no command has been run. `frontend/tsconfig*.json` exist.
- `npm run dev`, Docker build, any call to Gemini or Google Cloud.

## Directory map and key files

- `backend/api/` — `main.py` (app, CORS, SPA serving, shutdown log flush), `endpoints.py` (all routes), `schemas.py` (Pydantic models).
- `backend/rag/` — `llm.py` (Gemini by API key), `embeddings.py` and `vector_store.py` (Vertex), `data_ingestion.py` (PDF to chunks to index), `retrieval.py` (RAG chain, 3 retriever types).
- `backend/agent/` — `agents.py` (supervisor), `tools.py` (5 tools), `prompts.py` (agent and CFO prompts).
- `backend/config/settings.py` — the `settings` singleton; env var names differ from attribute names.
- `backend/logger/custom_logger.py` — structlog JSON logging, GCS flush on exit.
- `backend/tests/` — `conftest.py` (fake env), `test_api.py`.
- `frontend/src/lib/api.ts` — the only backend client. Tabs in `frontend/src/components/`. `components/ui/` is shadcn (`frontend/components.json` exists).
- `.github/workflows/deploy.yml` — provisions paid GCP resources and deploys; `Dockerfile` — builds the SPA, then serves both on one port.
- `docs/` — discovery notes and `setup-log.md`; `Project-runbook/` is git-ignored.

## Code conventions observed

- Layering: `api -> agent, rag -> config, logger`. Routes stay thin and call `rag/` or `agent/` code.
- Logging: `from logger import GLOBAL_LOGGER as log`, then structured calls such as `log.info("event", key=value)`. Log sizes and ids, not user content.
- Route errors: `try/except Exception`, `log.error(...)`, then `HTTPException(500, detail=str(e))` (`backend/api/endpoints.py`).
- Tools do not raise on LLM failure: they return a warning string or a fallback (`backend/agent/tools.py`).
- External clients are created lazily with `@lru_cache` factories (`get_llm`, `get_vector_store`, `get_embeddings`, `get_supervisor`).
- Settings come from `config.settings.settings`, never from `os.environ` directly. Env aliases are set with `validation_alias`.
- Tests: pytest with FastAPI `TestClient`. Fake external calls with `monkeypatch.setattr(endpoints, ...)`. `conftest.py` sets fake env values, so tests need no network or accounts.
- Frontend: call the backend only through `src/lib/api.ts`. Use the `@/` import alias.

## Operating rules (from the session rules)

1. Until the owner approves a plan, do not modify, delete, rename or upgrade anything. Create files only under `docs/`, unless the owner explicitly asks otherwise.
2. Never print, copy, log or commit secrets. Treat `.env` files, keys, certificates, tokens and connection strings as sensitive. Name variables only, never values. Never invent secret values.
3. Verify claims against the code, not the README or folder names. Trace real execution paths.
4. Cite `file:line` for findings. Mark inferences INFERRED and unconfirmed items NOT VERIFIED. Never say something works unless you ran it.
5. Prefer small, reversible changes. One logical change per commit. Run tests before and after every change.
6. Stop and ask before: needing credentials, touching production or paid cloud resources, deleting data, upgrading dependencies, architectural changes, or unclear security behavior.
7. Log every significant command, result and assumption in `docs/setup-log.md`.

## Windows notes and gotchas

- Primary shell is PowerShell 5.1. It has no `&&`; chain with `;`. Git Bash is also available.
- `py` and `python` are not on PATH (Python 3.12 not installed). Do not assume Python tooling works.
- Node here is v25.5.0, but `Dockerfile` builds with Node 20. Results on Node 20 are NOT VERIFIED.
- Native-command stderr shows as `NativeCommandError` in PowerShell even when the exit code is 0 (seen with npm warnings). Check `$LASTEXITCODE`.
- Git prints `LF will be replaced by CRLF` warnings. They are harmless.
- Run backend commands from the repo root. `.env` is resolved relative to the working directory, and the logger creates `./logs` in the working directory.
- Importing `logger` has side effects: it creates `./logs`, registers an `atexit` hook and configures logging.
- A push to `main` triggers `deploy.yml` (billed GCP provisioning, public Cloud Run). Push branches other than `main`.
- Frontend has two lockfiles (`package-lock.json`, `bun.lock`). Use `npm ci`; `Dockerfile` does.
- `npm ci` reports 33 audit findings. Leave them unless asked.
- The audit tab's progress steps are fake timers (`frontend/src/components/AuditTab.tsx`), not real server progress.
- `.claude/settings.json` denies reads of `.env`, `.env.local`, `.env.production`, `secrets/**` and `*.pem`.

## Do not

- Do not read, print or commit `.env` files, keys or credentials.
- Do not upgrade, loosen or add dependencies without approval.
- Do not run `npm audit fix` or `npm audit fix --force`.
- Do not hand-edit `package-lock.json`, `frontend/dist` or `node_modules`.
- Do not push to `main`, trigger `deploy.yml`, or create or delete cloud resources without explicit approval.
- Do not call Gemini, Vertex AI, GCS or the audit endpoint without approval. They can cost money and send data to Google.
- Do not run `git restore`, `git reset --hard`, `git branch -D` or any delete without approval.
- Do not rewrite or delete `docs/setup-log.md` entries; correct them with a new entry.
