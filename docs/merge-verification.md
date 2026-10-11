# Merge verification (M1: mentor v1.1 on branch `merge/mentor-v1.1`)

Compared with `docs/merge-baseline.md` (backend 9 passed, frontend 16 passed, build exit 0, lint 16 problems). No `.env` access and no Gemini, Google Cloud or deploy-workflow call was made for anything below.

## Verified (commands were run)

| Check | Result |
|---|---|
| `pytest backend/tests -q` | **20 passed** (baseline 9; mentor's merged suite 17; plus 3 added here, see below) |
| `cd frontend; npm test` | 16 passed (no test edits were needed) |
| `npx tsc --noEmit -p tsconfig.app.json` | exit 0 |
| `npm run build` | exit 0 |
| `npm run lint` | 16 problems (9 errors, 7 warnings), same as the baseline |
| `pip install -r requirements.txt -r requirements-dev.txt` | all pins resolved; `pip check` clean |
| Offline smoke (FastAPI `TestClient`, tests) | `/api/health` returns `mode=local`; `/api/status` reports Chroma and the local embedding model; with `APP_MODE=cloud` and empty cloud settings a RAG call returns 503 naming `GCP_PROJECT_ID`, `GCS_BUCKET_NAME`, `VECTOR_SEARCH_INDEX_ID`, `VECTOR_SEARCH_INDEX_ENDPOINT_ID`, and the response contains no key value |
| Secret scan of the staged diff | No key, token, private-key or assigned-secret patterns; no `.env` or key file staged (`.env.example` adds variable names with placeholders only) |
| Line endings | HEAD and index are CRLF throughout the changed files; the staged diff is the same size with and without `--ignore-cr-at-eol` |

## Fix made during verification: one PDF indexed twice

- **Bug (reproduced first):** upload indexed a PDF under `upload://<file>`, "Index stored documents" indexed the stored copy under `local://<file>` (or `gs://<bucket>/<blob>`). The chunk ID is built from the source, so the same PDF got two sets of chunks. The new test showed 1 chunk after upload and 2 after ingest.
- **Fix:** `rag/document_store.source_key(filename)` returns `doc://<file name>`; the upload route and `document_store.pdfs()` (local and cloud) both use it.
- **Regression test:** `test_upload_then_index_stored_documents_does_not_duplicate` uploads through `/api/rag/upload`, runs `ingest_stored_pdfs()`, and asserts the chunk count is unchanged and there is one source.
- **Side effect:** an index built before this change holds chunks under `upload://`, `local://` or `gs://` sources. Re-indexing after the change adds `doc://` chunks next to them. Clear the old index (local: delete `.meridian/chroma`) before re-indexing. Cloud indexes were not touched and not checked.

## NOT VERIFIED

| Item | Why |
|---|---|
| **Live Gemini smoke test: upload, the three retrievers (`similarity`, `multiquery`, `contextual`), and one audit** | The owner's key has no credit (the reference run got `402 RESOURCE_EXHAUSTED` on embedding). To be run by the owner later with a funded key. Until then the real embedding and chat calls, retrieval quality and the audit output after the merge are unproven. |
| Docker build and run with `APP_MODE=local` (health check as the non-root user, no key) | The Docker engine was not running (`dockerDesktopLinuxEngine` pipe missing). The Dockerfile change (a `/app/.meridian` folder owned by `app`) has not been built. |
| Cloud mode (`APP_MODE=cloud`) with real Google Cloud | Out of scope; no cloud call allowed. |
| The default model name `gemini-3.8-flash` | Unchanged and not verified to exist (plan item Q8). |
| Mentor learner docs `docs/01` to `docs/20` | Copied as is. Only the links to the deleted `05-backend-files.md` were repointed; the text was not checked against the code. |
| `docs/REFERENCE.md`, `ARCHITECTURE.md`, `UNDERSTANDING.md` | Not updated for local/cloud mode (not touched in this step). |
