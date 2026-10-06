# OPERATIONS — running and troubleshooting locally

Scope: running the app yourself. Production deployment is described later in `docs/DEPLOYMENT.md` (not yet written). Nothing here was run; the backend has never been started on this machine (Python not installed). NOT VERIFIED unless a `file:line` is given.

## 1. Configuration

- Variables, defaults and purpose: `README.md` (Configuration) and `backend/config/settings.py:6-35`. Values come from process env vars, then `.env` in the **current directory**, then defaults (precedence INFERRED).
- Start the backend from the repo root so `.env` and `./logs` resolve there.
- Never print or share `.env`. Check which variables are set without values: `/api/status` shows project, region, bucket and index IDs (`endpoints.py:62-90`) — it is unauthenticated, so do not expose it publicly.
- Missing values do not fail at startup; they fail on first use (`settings.py:14-18`, lazy clients `llm.py:12`).

## 2. Logs

| Where | What | Source |
|---|---|---|
| Console (stderr/stdout) | JSON lines, level INFO and above | `custom_logger.py:46-54` |
| `logs/<MM_DD_YYYY_HH_MM_SS>.log` in the working directory | same JSON lines, one file per process start; git-ignored | `custom_logger.py:25-31,42-44`; `.gitignore:63` |
| `gs://<GCS_BUCKET_NAME>/logs/<timestamp>.log` | uploaded once at shutdown/exit if a bucket is configured | `custom_logger.py:71-105` |

Fields: `timestamp`, `level`, `severity`, `event`, plus key/value pairs (`custom_logger.py:57-65`). **Logs contain full user queries, answers, audit requests and memos** (`retrieval.py:53,66`; `agents.py:59-77`): treat them as sensitive and do not attach them to tickets unredacted. Setting `GCS_BUCKET_NAME` empty disables the upload and prints a skip notice (`custom_logger.py:85-87`). Log level and folder are not configurable (no setting exists).

Search tip (PowerShell): `Select-String -Path logs\*.log -Pattern '"severity": "ERROR"'` — exact spacing of the JSON is NOT VERIFIED.

## 3. Health checks

| Check | Expect | Notes |
|---|---|---|
| `GET /api/health` | `{"status": "ok"}` | no external calls (`endpoints.py:50-52`) |
| `GET /api/status` | JSON with `backend`, `gcp`, `storage`, `vector_search`, `models`, `ingestion` | no GCP calls; blank/`NA` values show unset config (`endpoints.py:62-90`) |
| `/docs` | interactive API page | FastAPI default, INFERRED |
| `cd frontend; npm test` | 1 test passes | verified |
| `pytest backend/tests` | 9 tests | NOT VERIFIED |

A healthy `/api/health` does **not** prove Gemini or Google Cloud work: nothing connects until first use.

## 4. Common failures and fixes

| Symptom | Likely cause | Fix |
|---|---|---|
| `python`/`py` not found | Python 3.12 not installed | install it (needs owner approval to change the system) |
| `ModuleNotFoundError: api` | wrong directory or missing `--app-dir backend` | run from repo root with `--app-dir backend` |
| Settings empty | `.env` not in the working directory | run from the repo root |
| Audit returns "SYSTEM WARNING … Manual review required" | a tool's Gemini call failed (`tools.py:56-57`) | check `GOOGLE_API_KEY` and `VERTEX_LLM_MODEL_NAME` (default existence NOT VERIFIED); read the log |
| Audit or ask returns HTTP 500 with an error string | uncaught exception (`endpoints.py:103-105,117-119`) | read the `log.error` line; fix key, model, IDs or credentials |
| Q&A 500 / Vector Search errors | index or endpoint IDs, project, region unset or wrong; missing ADC login | verify the names in `/api/status`; needs Google Cloud access |
| Upload says "skipped" | non-PDF extension or no extractable text (`endpoints.py:133-165`) | use a text-based PDF |
| Upload returns 500 mid-batch | one unreadable PDF aborts the batch (`endpoints.py:156,169-171`) | remove the bad file and retry; earlier files may already be indexed |
| Page shows "Failed to fetch" | backend down or wrong `VITE_API_URL` | start the backend; set `VITE_API_URL` if the port is not 8080 |
| Port in use | another process | use `--port 8081` and set `VITE_API_URL` |
| `NativeCommandError` from npm in PowerShell | npm warnings on stderr | check `$LASTEXITCODE` (observed with exit 0) |
| `npm run lint` fails | existing code issues (16) | not caused by your change |

## 5. State, backup and recovery

Persistent state exists only in Google Cloud; nothing is stored locally except log files.

| State | Where | Backup in repo? | Recovery |
|---|---|---|---|
| Vector index (chunks, embeddings) | Vertex AI Vector Search | none | rebuild by re-ingesting PDFs (below) |
| Original PDFs | bucket prefix `GCS_PREFIX` (default empty; `uploads/` in deploy config) | none; bucket versioning NOT VERIFIED | restore from your own copies or `sample_docs/` |
| Logs | `logs/` and bucket `logs/` | none | not recoverable once lost |
| Upload history | process memory (`endpoints.py:36`) | n/a | lost on restart by design |
| Secrets | your `.env`, GitHub secrets, Secret Manager | none | re-create from the provider |

Rebuild an index from stored PDFs: `POST /api/rag/ingest-gcs` (`endpoints.py:185-193`). It re-indexes **every** PDF under the prefix and has no deduplication, so running it against an index that already holds those chunks duplicates them (INFERRED). A failed bulk run is partial and not resumable. If the embedding model changes, the index must be recreated (768-d coupling: `embeddings.py:3-6`).

## 6. Cost and safety reminders
- Audit and Q&A call paid or rate-limited Google services; document Q&A needs an index billed by the hour (`DEPLOY.md`).
- Deployment only happens when `deploy.yml` is started manually (`deploy.yml:3-5`); pushing to `main` no longer deploys.
