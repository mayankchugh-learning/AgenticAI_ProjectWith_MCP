# REFERENCE — Meridian AI

Public modules, functions, classes, API endpoints, CLI commands and config options, most-used first. Examples come from the code or `backend/tests/test_api.py`. Nothing here was run. Library behaviour is NOT VERIFIED.

## 1. Backend modules (by number of importers)

### `config.settings` — 7 importers
- **Purpose:** single `settings` object (class `Settings`, pydantic-settings) read from env vars, then `.env` in the working directory (`settings.py:6-37`).
- **Inputs:** env vars listed in §4. **Outputs:** attributes such as `settings.GOOGLE_API_KEY`, `settings.GCP_PROJECT`, `settings.llm_model_name`.
- **Errors:** none raised for missing values; defaults are empty strings (`settings.py:14-18`). Side effect: sets `GOOGLE_APPLICATION_CREDENTIALS` if `GCP_SERVICE_ACCOUNT_PATH` points to an existing file (`:42-47`).
- **Example:** `settings.llm_model_name` defaults to `gemini-3.8-flash` (`settings.py:22`; existence NOT VERIFIED).

### `logger` — 6 importers
- **Purpose:** `GLOBAL_LOGGER` (structlog) and `_LOGGER_INSTANCE` (`logger/__init__.py:5-6`). Class `CustomLogger` (`custom_logger.py:22`); `add_severity(logger, method_name, event_dict)` copies `level` to `severity` (`:9-19`); `flush_to_gcs()` uploads the log file (`:71-105`).
- **Errors:** upload failures only `print` (`:102-105`). Import creates `./logs`.
- **Example (test):** `add_severity(None, "info", {"event": "x", "level": "info"})["severity"] == "INFO"` (`test_api.py:77`).

### `rag.llm` — 3 importers
- `get_llm() -> ChatGoogleGenerativeAI` (cached; model, key, temperature from settings) (`llm.py:11-21`).
- `extract_text(content)` joins `{"type": "text"}` blocks with newlines, otherwise returns `content` unchanged (`llm.py:25-32`).
- **Errors:** none caught here; failures surface at `invoke`.
- **Example:** `extract_text(response.content)` (`tools.py:17`).

### `rag.vector_store`, `rag.embeddings` — 2 and 1 importers
- `get_vector_store() -> VectorSearchVectorStore` (cached) calls `aiplatform.init` then `from_components(project_id, region, embedding, index_id, endpoint_id, gcs_bucket_name, stream_update=True)` (`vector_store.py:11-24`).
- `get_embeddings() -> VertexAIEmbeddings(model_name=settings.embedding_model_name)` (`embeddings.py:15-17`); must output 768 dimensions (`:3-6`).
- **Errors:** raised from the Google libraries on bad IDs/credentials; not cached (INFERRED from `lru_cache`).

### `rag.retrieval`
- `build_retriever(retriever_type="similarity")`: `similarity` k=3, `multiquery` k=3 plus LLM rewrites, `contextual` k=10 plus LLM extractor; unknown values warn and use similarity (`retrieval.py:26-48`).
- `ask_question(query, retriever_type="similarity") -> str`: runs the retrieval chain and returns `response["answer"]` (`:51-67`). Logs the full query and answer (`:53,66`).
- **Errors:** propagate to the route (500).
- **Example (test, faked):** `monkeypatch.setattr(endpoints, "ask_question", lambda query, retriever_type: f"answer to: {query}")` (`test_api.py:26`).

### `rag.data_ingestion`
- `split_into_chunks(pages) -> list[Document]` with `CHUNK_SIZE=1000`, `CHUNK_OVERLAP=100` (`data_ingestion.py:22-28`).
- `ingest_pdf(local_path, source) -> {"pages": n, "chunks": n}`; sets `source` metadata, calls `add_documents` (`:31-44`).
- `ingest_data_from_gcs() -> {"files", "pages", "chunks"}` (`:47-73`).
- **Errors:** unreadable PDF or index errors propagate. Zero chunks means nothing is indexed.
- **Example (test):** `split_into_chunks([Document(page_content="word " * 1000, metadata={"source": "test.pdf"})])` gives more than one chunk, each at most 1000 chars (`test_api.py:48-55`).

### `agent.agents`
- `create_specialized_agent(tools, system_prompt)` wraps `langchain.agents.create_agent` (`agents.py:32-34`).
- `ProcurementSupervisor().run_audit(request: str) -> {"risk_result", "tax_result", "control_result", "cfo_memo"}` (`:37-84`); agents run sequentially, then one plain LLM call.
- **Errors:** uncaught (route returns 500). **Example (test, faked):** `FakeSupervisor.run_audit` returns the four keys (`test_api.py:32-40`).

### `agent.tools` (decorated with `@tool`)
| Tool | Inputs | Output | Fallback on LLM error |
|---|---|---|---|
| `check_sanctions_list` | `vendor_name: str` | text starting `RED ALERT:` or `CLEARED:` (requested, not enforced) | "SYSTEM WARNING … Manual review required" (`tools.py:29-58`) |
| `get_vendor_credit_score` | `vendor_name: str` | `CREDIT SCORE: n/100 \| RISK: … \| …` or raw text | warning string (`:62-112`) |
| `calculate_cross_border_tax` | `amount: float, origin: str, destination: str` | dict (`tax_rate`, `tax_amount`, `route`, …) | `{"error"}`; 15% fallback dict if JSON parse fails (`:118-175`) |
| `validate_fx_hedge` | `currency_pair: str, rate_used: float` | `FX SUCCESS…` / `FX ALERT…` / `FX WARNING…` string | LLM estimate, else warning (`:179-223`) |
| `categorize_expense` | `amount: float, item_description: str` | `CLASSIFICATION/REASONING/DEPRECIATION/FLAGS` text | keyword heuristic (`:229-269`) |

Internal helper: `_ask_llm(prompt)` returns text or `"LLM_ERROR: …"` (`:13-19`).

### `agent.prompts`
String constants `RISK_AGENT_PROMPT`, `TAX_AGENT_PROMPT`, `CONTROL_AGENT_PROMPT`, `SYNTHESIS_PROMPT_TEMPLATE` (placeholders `{risk_result}`, `{tax_result}`, `{control_result}`) (`prompts.py:18,53,92,140`). The CFO template keys on the literal strings `RED ALERT`, `FX ALERT`, `HOLD FOR TREASURY AUDIT` (`:165-172`).

### `api.schemas` and `api.main`
- Models: `AuditRequest(request_text: str)`, `AuditResponse(risk_result, tax_result, control_result, cfo_memo)`, `QueryRequest(query: str, retriever_type: str = "similarity")`, `QueryResponse(answer: str)` (`schemas.py:10-30`).
- `api.main.app`: FastAPI app, CORS `*`, routers, optional SPA serving (`main.py:35-75`). Shutdown calls `flush_to_gcs` (`:29-32`).

## 2. API endpoints (`backend/api/endpoints.py`)

| Method and path | Purpose | Input | Output | Errors | Example |
|---|---|---|---|---|---|
| `GET /api/health` | liveness | none | `{"status": "ok"}` | none | `client.get("/api/health").json() == {"status": "ok"}` (`test_api.py:12`) |
| `GET /api/status` | config summary, no GCP calls | none | nested dict: backend, gcp, storage, vector_search, models, ingestion (`:62-90`) | none | test asserts `body["gcp"]["project_id"] == "test-project"` (`test_api.py:17`) |
| `POST /api/agent/audit` | run audit | `{"request_text": str}` | 4 text fields | 422 invalid body (framework); 500 `detail=str(e)` (`:103-105`) | `client.post("/api/agent/audit", json={"request_text": "buy 200 PLCs"})` (`test_api.py:38`) |
| `POST /api/rag/ask` | RAG question | `{"query": str, "retriever_type": str}` | `{"answer": str}` | 500 `detail=str(e)` (`:117-119`) | `client.post("/api/rag/ask", json={"query": "hello", "retriever_type": "similarity"})` (`test_api.py:27`) |
| `POST /api/rag/upload` | upload and index PDFs | multipart field `files` (one or more) | `{"results": [{filename, status, reason?, pages?, chunks?}]}` | non-`.pdf` skipped; scanned PDF skipped; other failures 500 (`:122-176`) | `client.post("/api/rag/upload", files={"files": ("notes.txt", b"hi", "text/plain")})` returns status `skipped` (`test_api.py:44`) |
| `GET /api/rag/uploads` | uploads this process | none | `{"uploads": [...]}` (in memory) | none | untested |
| `POST /api/rag/ingest-gcs` | index every PDF under the prefix | none | `{"status": "GCS ingestion complete", "files", "pages", "chunks"}` | 500 (`:185-193`) | untested |
| any other `/api/*` | | | 404 | `main.py:68-69` | `test_api.py:21-23` |

FastAPI's interactive docs at `/docs` are not disabled in `main.py`; that they are served is INFERRED (framework default).

## 3. CLI commands

| Command | Purpose | Status |
|---|---|---|
| `uvicorn api.main:app --app-dir backend --reload --port 8080` (repo root) | run the API (`README.md`, `Dockerfile:42`) | NOT VERIFIED (Python not installed) |
| `python -m agent.agents` (from `backend/`) | run a built-in sample audit and print the memo (`agents.py:88-99`) | NOT VERIFIED; calls Gemini |
| `pytest backend/tests` | backend tests | NOT VERIFIED |
| `npm ci`, `npm test`, `npm run build` (in `frontend/`) | install, test, build | verified (`docs/setup-log.md`) |
| `npm run lint` | lint | runs, exits 1 (16 problems) |
| `npm run dev`, `build:dev`, `preview`, `test:watch` | other scripts (`frontend/package.json`) | NOT VERIFIED |
| `docker build -t meridian-ai .` | build image (`Dockerfile`) | NOT VERIFIED |

## 4. Configuration options

Names, defaults and use are in `backend/config/settings.py` and tabulated in `README.md` (Configuration): `GOOGLE_API_KEY`, `GCP_PROJECT_ID`, `GCP_REGION`, `GCS_BUCKET_NAME`, `GCS_PREFIX`, `GCP_SERVICE_ACCOUNT_PATH`, `VERTEX_LLM_MODEL_NAME`, `LLM_TEMPERATURE`, `VERTEX_EMBEDDING_MODEL_NAME`, `VECTOR_SEARCH_INDEX_ID`, `VECTOR_SEARCH_INDEX_ENDPOINT_ID`, `ENVIRONMENT` (unused). Also `PORT` (Docker CMD, `Dockerfile:42`) and `VITE_API_URL` (frontend, `api.ts:5`).

## 5. Frontend client (`frontend/src/lib/api.ts`)
`uploadDocument(file)`, `uploadDocuments(files)`, `listUploads()`, `askQuestion(query, retrieverType)`, `triggerGcsIngestion()`, `runAudit(requestText)`, `healthCheck()`, `getSystemStatus()` (`api.ts:18-80`). Each throws `Error(body.detail || "HTTP <status>")` on a non-OK response (`:7-13`). `uploadDocuments`, `listUploads` and `healthCheck` have no callers outside `api.ts` (grep).

## 6. Still undocumented
- Full text and behaviour of the prompts beyond headers and placeholders (`agent/prompts.py` was read, but outputs depend on the model).
- Frontend: `DocumentUploadTab.tsx`, `SystemStatusTab.tsx`, `pages/Index.tsx`, `App.tsx` routing and tab wiring, `hooks/*`, all `components/ui/*`, Tailwind/PostCSS/ESLint/Playwright/Vitest configs, `frontend/src/test/*`.
- `DEPLOY.md` beyond the cost warning and teardown headings; `Project-runbook/*`; contents of `sample_docs/*.pdf` (not opened).
- Real behaviour of LangChain, LangGraph, FastAPI, Vertex AI and Gemini clients (timeouts, retries, thread-safety, where chunk text is stored).
- Runtime behaviour of every endpoint except what the 9 tests assert (and those were not run).
- Cloud Run runtime IAM, logging output format in Cloud Logging, index behaviour under load.
