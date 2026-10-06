# ONBOARDING — first day

For a new developer. Commands marked **verified** were run on Windows PowerShell (see `docs/setup-log.md`). Everything else is **NOT VERIFIED** on this machine, because Python is not installed here. Production deployment is out of scope; see `docs/DEPLOYMENT.md` (to be written).

## 1. Set up

1. **Check tools (read-only):** `python --version`, `node --version`, `npm --version`, `git --version`. Wanted: Python 3.12 (not enforced by the repo), Node 20+ (verified on v25.5.0).
2. **Work on a branch, not `main`:** `git switch -c <your-branch>`. A push to `main` triggers the deploy workflow (`.github/workflows/deploy.yml:3-7`).
3. **Frontend (verified):**
   ```powershell
   cd frontend
   npm ci
   npm test
   npm run build
   ```
   `npm run lint` currently fails (16 existing problems); that is not caused by your change.
4. **Backend (NOT VERIFIED):** from the repo root:
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements-dev.txt
   pytest backend/tests
   ```
   Tests fake all external calls (`backend/tests/conftest.py`). Run them in a shell without `GCP_PROJECT_ID` set.
5. **Config:** copy `.env.example` to `.env` yourself and set only what you need (`GOOGLE_API_KEY` for audit). Do not paste `.env` contents anywhere. The backend starts and serves `/api/health` without it (lazy clients, INFERRED).
6. **Run (NOT VERIFIED):** `uvicorn api.main:app --app-dir backend --reload --port 8080`, then `cd frontend; npm run dev` (port 3000).
7. **Avoid paid calls** while learning: the audit endpoint makes about 11+ Gemini calls (INFERRED), and Q&A needs billed Google Cloud resources.

## 2. Guided tour (read in this order)

1. `README.md` and `docs/UNDERSTANDING.md` — what and why.
2. `backend/api/schemas.py` (30 lines) — the request and response shapes.
3. `backend/api/endpoints.py` — every route; note the 500 pattern and `_upload_history`.
4. `backend/config/settings.py` — env var names versus attribute names.
5. `backend/rag/retrieval.py`, then `vector_store.py`, `embeddings.py`, `llm.py` — the Q&A path.
6. `backend/rag/data_ingestion.py` — upload and chunking.
7. `backend/agent/agents.py`, `tools.py`, `prompts.py` — the audit path.
8. `backend/tests/test_api.py` and `conftest.py` — how things are faked.
9. `frontend/src/lib/api.ts`, then `components/RagQATab.tsx` and `AuditTab.tsx`.
10. `docs/ARCHITECTURE.md` for the diagrams.

## 3. Make and test a small change (example)

Goal: add a unit test for `extract_text` (`backend/rag/llm.py:25-32`), which has no test today.

1. Branch: `git switch -c add-extract-text-test`.
2. Run the baseline: `pytest backend/tests` (record the result in `docs/setup-log.md`).
3. Create `backend/tests/test_llm.py`:
   ```python
   from rag.llm import extract_text

   def test_extract_text_joins_text_blocks():
       blocks = [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]
       assert extract_text(blocks) == "a\nb"

   def test_extract_text_returns_plain_string_unchanged():
       assert extract_text("hello") == "hello"
   ```
   (`conftest.py` makes `rag` importable; the join rule is `llm.py:28-31`.)
4. Run `pytest backend/tests/test_llm.py`, then the full suite again. Both must pass before you commit.

Style to follow: thin routes, `from logger import GLOBAL_LOGGER as log`, settings only via `config.settings`, fakes via `monkeypatch`, frontend calls only through `src/lib/api.ts`.

## 4. Submit it

1. One logical change per commit: `git add backend/tests/test_llm.py`, `git commit -m "Add tests for extract_text"`.
2. Push your branch only: `git push -u origin <your-branch>`.
3. Open a pull request on GitHub against `main`.
4. **Warning:** merging into `main` triggers `deploy.yml`, which can create billed Google Cloud resources and a public service if the repo's secrets are set. Do not merge without the owner's approval.
5. Never commit `.env`, keys or credentials, and do not upgrade dependencies without approval.
