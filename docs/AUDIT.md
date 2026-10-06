# AUDIT — Meridian AI

Read-only audit. No code was changed and nothing was run except read-only `git`/`grep` and the earlier frontend `npm ci/test/lint/build` (see `docs/setup-log.md`). Every finding points to code (`file:line`), or is marked **INFERRED** (reasoned, not observed) or **NOT VERIFIED** (could not confirm).

**Severity scale:** CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL. **Effort:** S (under a day), M (days), L (weeks). **Risk of changing:** how likely the fix is to break something.
**Result:** 63 findings: 0 CRITICAL, 4 HIGH, 31 MEDIUM, 24 LOW, 4 INFORMATIONAL. Nothing is CRITICAL because no secret was found and the service is a disclosed demo (`README.md`), but the public, unauthenticated, billed deployment path (A-001, A-003, A-047) is the top concern.

## Method and limits
- Read in full: all of `backend/`, `requirements*.txt`, `Dockerfile`, `.dockerignore`, `.gitignore`, `deploy.yml`, `generate_json.py`, `frontend/src/lib/api.ts`, `RagQATab.tsx`, `AuditTab.tsx`, `frontend/package.json`, `vite.config.ts`.
- Grepped only: `DEPLOY.md`, `.env.example` (variable **names only**), frontend `src/` for storage/HTML-injection patterns.
- **Not read:** `.env` (never opened), `sample_docs/*.pdf`, `Project-runbook/`, `DocumentUploadTab.tsx`, `SystemStatusTab.tsx`, `pages/Index.tsx`, `components/ui/*`, `tsconfig*.json`, Playwright files. Frontend findings are therefore limited.
- Not run: the backend (Python 3.12 not installed), pytest, any scanner, any Google call. Library behaviour (LangChain, FastAPI, Vertex, Gemini clients) is NOT VERIFIED.
- Secret scan: ran `git grep` for Google API key, private key block, `private_key` JSON field, AWS key id, GitHub token, `sk-` key and "literal assignment" patterns over tracked files (excluding docs, lockfiles, `Project-runbook/`), printing file and line only. Details in A-016.

## Dependency scan commands (not run; waiting for your approval)
| Stack | Command | Notes |
|---|---|---|
| Frontend (npm) | `cd frontend; npm audit` and `npm audit --omit=dev` | Read-only; contacts the npm registry. `npm ci` already printed "33 vulnerabilities (1 low, 11 moderate, 18 high, 3 critical)" (setup-log), but that is a count only, not an audit I ran. `--omit=dev` shows what ships in the bundle. Do **not** run `npm audit fix`. |
| Backend (pip) | `pip install pip-audit` then `pip-audit -r requirements.txt` | Needs Python 3.12 (not installed), a venv, and network. Installing `pip-audit` is a new tool, so it needs approval. Alternative with no install into the project: `osv-scanner` against `requirements.txt` and `package-lock.json`. |
| Container | `docker scout cves meridian-ai` or `trivy image meridian-ai` | Only after an image is built (not done). |

## 1. Security
| ID | Finding | Evidence | Sev | Effort | Change risk | Proposed fix |
|---|---|---|---|---|---|---|
| A-001 | **No authentication or authorization on any route; the deploy makes the service public.** Anyone can run audits (paid Gemini calls), upload PDFs, trigger bulk ingest, read `/api/status`. | `backend/api/endpoints.py:50-193` (no auth dependency); `deploy.yml:232` `--allow-unauthenticated`; `deploy.yml:250-254` `allUsers` invoker; `DEPLOY.md:172` admits it | HIGH | M | Medium: changes how the SPA and any caller reach the API | Remove `allUsers`/unauthenticated flag and use Cloud Run IAM/IAP, or add an API-key or OAuth dependency to all `/api/*` routes except health |
| A-002 | **No rate limit or input size limit on paid endpoints.** Empty or huge text is accepted; each audit makes about 11+ Gemini calls (INFERRED). | `backend/api/schemas.py:10-11,25-27` (plain `str`); `endpoints.py:97-105`; `agents.py:56-77` | MEDIUM | M | Low | `max_length` on fields, per-IP/key rate limit, max concurrency |
| A-003 | **Over-broad deploy identity with a long-lived key.** Docs grant `roles/editor` and `roles/resourcemanager.projectIamAdmin` to the deployer; the workflow also grants it `roles/run.admin`; auth uses a JSON key stored as a GitHub secret. | `DEPLOY.md:95-102`; `deploy.yml:30,245` | HIGH | M | High: deploy can break | Workload Identity Federation instead of a key; least-privilege roles; drop `projectIamAdmin` |
| A-004 | **Runtime identity unclear.** The deploy command sets no `--service-account`, and the secret grant targets the default compute account; what Vertex/GCS rights that account has at runtime is **NOT VERIFIED**. | `deploy.yml:218,226-236` | MEDIUM | S | Medium | Create a dedicated runtime service account with only `aiplatform.user`, bucket object access and secret accessor |
| A-005 | **Frontend dependency vulnerabilities.** `npm ci` reported 33 findings (1 low, 11 moderate, 18 high, 3 critical). Reachability and dev-only vs shipped split are **NOT VERIFIED**. | setup-log (`npm ci` output); `frontend/package.json` (all `^` ranges) | HIGH | M | Medium: upgrades can break the UI | Run `npm audit --omit=dev` (needs approval), then upgrade only shipped, reachable packages with tests |
| A-006 | **Backend supply chain.** Direct deps pinned with `==`, but transitive deps float: no lockfile or hashes, no scanner. Whether the pinned set installs together is **NOT VERIFIED**. | `requirements.txt:1-28`; no `pip-audit`/Dependabot config found | MEDIUM | M | Medium | Generate a lock (`pip-compile` or `uv lock`) once the environment works; add `pip-audit` and Dependabot |
| A-007 | **CORS allows every origin with credentials.** | `main.py:42-48` | MEDIUM | S | Low (prod is same-origin: `api.ts:5`) | Allowlist origins from an env var |
| A-008 | **Raw exception text returned to clients.** | `endpoints.py:105,119,171,193` (`detail=str(e)`) | MEDIUM | S | Low | Return a generic message plus an error id; keep detail in logs |
| A-009 | **Upload handling is weak.** Extension-only check, no size cap, whole file read into memory, client filename used verbatim (may contain `/`) in the GCS object name, same name overwrites. | `endpoints.py:133,144,149` (local path uses `basename`, `:142`) | MEDIUM | S | Low | Cap size, check `%PDF` header, use a generated object name, keep original name as metadata |
| A-010 | **Logs hold user content and go to the document bucket.** Full queries, answers, audit reports and memos are logged and uploaded to the same bucket as uploads. | `retrieval.py:53,66`; `agents.py:59,63,67,77`; `custom_logger.py:96` | MEDIUM | M | Low | Log sizes/ids only; use a separate log bucket or Cloud Logging only |
| A-011 | **Prompt-injection surface.** Model-chosen tool arguments and user text are f-string interpolated into prompts without delimiting or validation. Impact is INFERRED. | `tools.py:42,67,121-125,203,231`; `retrieval.py:16-23` | MEDIUM | M | Medium | Delimit and validate inputs; do decision logic in code (see A-056) |
| A-012 | **Container runs as root**, keeps the compiler toolchain in the final image, has no `HEALTHCHECK`. | `Dockerfile:12-22,42` (no `USER`) | MEDIUM | S | Medium: log/dir permissions | Non-root user, multi-stage build without `build-essential`, add healthcheck |
| A-013 | **Service-account key file name is not git-ignored.** `DEPLOY.md` tells the user to create `github-deployer-key.json` in the working directory; `.gitignore` covers only `.env`, `.envrc`, `credentials/`. | `DEPLOY.md:103-105`; `.gitignore:142-143,227-228` | MEDIUM | S | Low | Add `*-key.json`, `service-account*.json`, `*.pem`, `*.p12`, `*.pfx` |
| A-014 | `/api/status` exposes project, region, bucket, index and endpoint IDs without auth. | `endpoints.py:62-90` | LOW | S | Low | Covered by A-001, or trim fields |
| A-015 | GitHub Actions pinned by tag, not commit SHA; the workflow prints the secret's length. | `deploy.yml:25,28,33,207` | LOW | S | Low | Pin SHAs; drop the length echo |
| A-016 | **Secret scan: no hardcoded secrets found** in tracked files for the patterns above. The only hit (`deploy.yml:236`, "literal assignment") is a Secret Manager reference, not a value. History contains only `.env.example` among env/key-like paths. Limits: pattern-based, excludes docs and `Project-runbook/`; `.env.example` values were **NOT VERIFIED** (names only inspected). | scan output | INFORMATIONAL | – | – | Re-scan with a dedicated tool (gitleaks) later |
| A-017 | **No unsafe deserialization or code execution found** in `backend/`: no `eval`, `exec`, `pickle`, `yaml.load`, `subprocess`, `os.system`. The only HTML injection API is `dangerouslySetInnerHTML` in the shadcn chart component (use and input source **NOT VERIFIED**). | grep; `frontend/src/components/ui/chart.tsx:70` | INFORMATIONAL | – | – | None |

## 2. Correctness
| ID | Finding | Evidence | Sev | Effort | Change risk | Proposed fix |
|---|---|---|---|---|---|---|
| A-018 | **FX check mislabels LLM-estimated rates as "live market" and can divide by zero.** | `tools.py:213` (label depends only on parsing the pair); `:212` no zero guard | MEDIUM | S | Low | Track the real source; guard `market_rate <= 0` |
| A-019 | **Silent degraded results look like success.** A parse failure returns a hard-coded 15% tax; LLM errors return normal-looking strings; the CFO then reasons on them. | `tools.py:164-175,56-57,94-95,152-153,262-268` | MEDIUM | S | Medium | Mark degraded outputs explicitly (e.g. `DEGRADED:` prefix) and have synthesis fail or hold |
| A-020 | **Multi-file upload can leave partial state.** If a later file fails, earlier files stay indexed and copied to GCS but their results are never added to history. | `endpoints.py:169-176` | MEDIUM | M | Medium | Record per-file results immediately; return partial results with per-file errors |
| A-021 | GCS copy failure only logs a warning, so a file can be indexed without its original stored. | `endpoints.py:152-153` | LOW | S | Low | Surface the failure in the per-file result |
| A-022 | **No dedupe:** re-ingesting adds chunks again; same-name uploads overwrite the original. | `data_ingestion.py:43`; `endpoints.py:149`; no dedupe code found | MEDIUM | M | Medium | Stable chunk ids (hash of source+page+chunk) or delete-then-add per source |
| A-023 | `GCS_PREFIX` defaults to empty and is concatenated without a separator. | `settings.py:18`; `endpoints.py:149` | LOW | S | Low | Normalize with a trailing `/` at load |
| A-024 | `upload.filename` is used with `.lower()` and `basename` without a `None` check. Whether it can be `None` here is **NOT VERIFIED**. | `endpoints.py:133,142` | LOW | S | Low | Guard and reject |
| A-025 | **Misleading UI.** Answers are labelled "Verified Answer"; progress steps are fake timers; footer says "All Passed" even if the memo says rejected. | `RagQATab.tsx:163`; `AuditTab.tsx:62-70,293` | MEDIUM | S | Low | Rename the label; show real status or a spinner; derive footer from the memo decision |
| A-026 | **Concurrency is unverified.** `lru_cache` can build the supervisor twice under concurrent first calls (INFERRED); agents are shared across requests (thread-safety **NOT VERIFIED**); `_gcs_flushed` is checked without a lock between shutdown and `atexit`. | `endpoints.py:40-43`; `agents.py:38-48`; `custom_logger.py:33,73-74` | LOW | S | Low | Test under concurrency before fixing |
| A-027 | A configured credentials path that does not exist is silently ignored; a relative path resolves against the working directory. | `settings.py:42-52` | LOW | S | Low | Warn or fail at startup |

## 3. Reliability and performance
| ID | Finding | Evidence | Sev | Effort | Change risk | Proposed fix |
|---|---|---|---|---|---|---|
| A-028 | **No timeouts or retries in repo code** for Gemini, Vertex, Vector Search or GCS (only the FX call has `timeout=10`). Library defaults are **NOT VERIFIED**. | `llm.py:16-20`; `vector_store.py:14-24`; `endpoints.py:148-150`; `data_ingestion.py:51-61`; `tools.py:194` | MEDIUM | M | Medium | Set explicit timeouts and bounded retries with backoff |
| A-029 | **Audit is sequential and blocking.** Three independent agents run one after another, then synthesis; one worker thread is held for minutes. | `agents.py:56-77` | MEDIUM | M | Medium: shared agent thread-safety | Run the agents concurrently, or move to a job with polling |
| A-030 | Whole upload read into memory; a new `storage.Client` is created per file. | `endpoints.py:144,148` | MEDIUM | S | Low | Stream to disk with a size cap; reuse one client |
| A-031 | **Bulk ingest blocks the request** and sends all chunks in one `add_documents` call; library batch limits **NOT VERIFIED**. | `data_ingestion.py:43,47-73`; `endpoints.py:185-193` | MEDIUM | M | Medium | Batch the chunks; run as a background job |
| A-032 | Importing `logger` creates `./logs` (fails on a read-only filesystem), and the log file is unbounded. On Cloud Run local disk is memory-backed (INFERRED). | `custom_logger.py:25-26,42`; `logger/__init__.py:5` | LOW | S | Low | Stdout-only in containers; make the file handler optional |
| A-033 | Browser fetch has no timeout or abort; a long audit can leave the UI waiting indefinitely. | `api.ts:7-8` | LOW | S | Low | Add `AbortController` with a long timeout |
| A-034 | Upload history is per process (up to 3 instances) and lost on restart. | `endpoints.py:36`; `deploy.yml:234` | LOW | M | Low | Accept, or persist |

## 4. Tests
| ID | Finding | Evidence | Sev | Effort | Change risk | Proposed fix |
|---|---|---|---|---|---|---|
| A-035 | **Coverage gaps.** 9 tests cover route shapes and chunking. Untested: all five tools, the supervisor, `retrieval`, `ingest_pdf`, GCS paths, settings, logger flush, and the SPA path-traversal guard. The "9 passed" claim is **NOT VERIFIED** (not run). | `backend/tests/test_api.py:11-79`; `main.py:66-73` | MEDIUM | M | Low | Add fake-LLM tests for tools/supervisor; test the SPA guard |
| A-036 | **No error-path tests.** The 500 handlers, 422 validation, corrupt PDF and partial-upload cases are untested. | `endpoints.py:103-105,117-119,169-171,192-193` vs `test_api.py` | MEDIUM | M | Low | Monkeypatch failures and assert status codes and bodies |
| A-037 | **Brittle tests.** `test_status…` expects `test-project`, but `conftest` uses `setdefault`, so a pre-set `GCP_PROJECT_ID` breaks it; sample-PDF test asserts exactly 4 files. | `test_api.py:17,69`; `conftest.py:11` | LOW | S | Low | Force values with `monkeypatch.setenv`/assignment; assert at least the expected files |
| A-038 | Frontend has one placeholder test (`expect(true).toBe(true)`); Playwright is configured but no specs were seen. | `frontend/src/test/example.test.ts:4-6`; `frontend/playwright.config.ts` | LOW | S | Low | Add real component tests when UI logic changes |
| A-039 | **Tests need no live external service** (env and calls are faked). Positive finding. | `conftest.py:1-14`; `test_api.py:26,37` | INFORMATIONAL | – | – | Keep it that way |

## 5. Maintainability
| ID | Finding | Evidence | Sev | Effort | Change risk | Proposed fix |
|---|---|---|---|---|---|---|
| A-040 | **Dead code.** `settings.debug`/`app_env` have no readers; three `api.ts` functions have no callers; duplicate toast hooks; `jspdf` has no import; many unused shadcn components (INFERRED). | `settings.py:9,11`; `api.ts:24,32,65`; `hooks/use-toast.ts` vs `components/ui/use-toast.ts`; `package.json` | LOW | S | Low | Remove after confirming with a dependency tool (needs approval) |
| A-041 | **Duplication.** Code-fence stripping and JSON parsing repeated; five tools share the same prompt-call-parse shape. | `tools.py:98-105,155-161` | LOW | S | Low | Extract one helper |
| A-042 | **Boundary leaks.** `agent` imports `rag.llm`; `api` imports `google.cloud.storage` directly. | `agents.py:29`; `tools.py:5`; `endpoints.py:21,148` | LOW | M | Medium | Move the LLM factory to a shared module; wrap GCS in a small service |
| A-043 | **Large functions.** `upload_documents` is 55 lines doing validation, IO, GCS, ingest, history; `validate_fx_hedge` mixes parsing, HTTP, LLM, math; deploy is one huge step. | `endpoints.py:122-176`; `tools.py:179-223`; `deploy.yml:76-191` | LOW | M | Medium | Split only when touching them |
| A-044 | **Weak typing.** No Python type checking; `retriever_type: str` should be a `Literal`; frontend uses `any`. | `schemas.py:27`; `retrieval.py:46-47`; `RagQATab.tsx:36,67`; `AuditTab.tsx:82` | LOW | S | Low | Literal type; enable mypy/pyright gradually |
| A-045 | **Import-time side effects and global singletons** make testing and reuse harder. | `logger/__init__.py:5`; `custom_logger.py:25-36`; `settings.py:37` | LOW | M | Medium | Lazy logger setup |
| A-046 | **Template leftovers.** Package name `vite_react_shadcn_ts`, `TODO` placeholders in `index.html`, two lockfiles, `lovable-tagger`, and `init_embeddings.json` is not git-ignored. | `frontend/package.json`; `frontend/index.html:6,11`; `bun.lock`; `generate_json.py:4`; `.gitignore` | LOW | S | Low | Rename, pick one lockfile, ignore the generated file |

## 6. Developer experience
| ID | Finding | Evidence | Sev | Effort | Change risk | Proposed fix |
|---|---|---|---|---|---|---|
| A-047 | **CI only deploys.** Every push to `main` provisions paid resources and deploys publicly; no test, lint or type-check job. | `deploy.yml:3-7,24-258` | HIGH | S | Low | Make deploy manual (`workflow_dispatch`) and add a separate test job |
| A-048 | `npm run lint` fails: 16 problems (9 errors, 7 warnings), e.g. `tailwind.config.ts:91`, `ui/textarea.tsx:5`. | setup-log; lint output | LOW | S | Low | Fix or relax rules in generated UI files |
| A-049 | No Python lint, format or type-check config; no pre-commit; no Dependabot. | repo root listing (no `pyproject.toml`, `ruff.toml`, `mypy.ini`, `.pre-commit-config.yaml`, `.github/dependabot.yml`) | MEDIUM | S | Low | Add `ruff`, `mypy`/`pyright`, pre-commit, Dependabot |
| A-050 | No runtime version pinning: no `.python-version`, `.nvmrc` or `engines`; verification ran on Node 25.5.0 while the Dockerfile uses Node 20. | `Dockerfile:1,12`; setup-log | LOW | S | Low | Add version files and `engines` |

## 7. Observability
| ID | Finding | Evidence | Sev | Effort | Change risk | Proposed fix |
|---|---|---|---|---|---|---|
| A-051 | **No request ids, access or latency logs, metrics, tracing or error reporting** found in `backend/`. | all backend files read | MEDIUM | M | Low | Middleware for request id and timing; optional OpenTelemetry/Error Reporting |
| A-052 | **Swallowed errors are not logged.** Tool LLM failures and FX API failures are silent; log-flush failure only `print`s; `ask`/`audit` log `str(e)` without traceback while upload/ingest log tracebacks. | `tools.py:18-19,198-199`; `custom_logger.py:102-105`; `endpoints.py:104,118` vs `:170,192` | MEDIUM | S | Low | Log all failures with `exc_info`; consistent pattern |
| A-053 | Health is shallow (always "ok"); no readiness check; no probe configuration. | `endpoints.py:50-52`; `deploy.yml:226-236`; `Dockerfile` | LOW | S | Low | Add `/api/ready` checking config, and set a startup/liveness probe |
| A-054 | **No LLM usage, latency or cost logging.** | none found in `rag/` or `agent/` | MEDIUM | S | Low | Log model, token counts (if returned), elapsed time per call |

## 8. AI components (cost and quality)
| ID | Finding | Evidence | Sev | Effort | Change risk | Proposed fix |
|---|---|---|---|---|---|---|
| A-055 | **Call fan-out and no caching.** An audit makes about 11+ Gemini calls (INFERRED); each tool is itself an extra model call; one model for every task; identical inputs are recomputed even though temperature is 0 by default. | `agents.py:56-77`; `tools.py:13-19`; `settings.py:24` | MEDIUM | M | Medium | Cache by input hash; cheaper model for simple tools; cap calls |
| A-056 | **Decisions are delegated to the LLM.** The "RED ALERT means immediate rejection" rule is in a prompt, but code runs all three agents regardless and the CFO model matches strings. | `prompts.py:32-33,165-172`; `agents.py:56-67` | MEDIUM | M | High: behaviour change | Compute the verdict in code from structured tool outputs |
| A-057 | **Prompt and output handling.** No structured output (JSON recovered by stripping fences); no date supplied for the memo ("Date: [today]"); silent fallbacks (A-019). | `tools.py:98-105,155-166`; `prompts.py:183` | MEDIUM | M | Medium | Use structured/JSON-schema outputs; pass the date |
| A-058 | **Retrieval quality is unmeasured and sources are dropped.** Chunking (1000/100) and k (3/10) are fixed; no score threshold or metadata filter; `source` metadata is stored but only the answer is returned. | `data_ingestion.py:22-23,37-38`; `retrieval.py:36-48,67`; `schemas.py:29-30` | MEDIUM | M | Medium | Return sources/pages; tune with an eval set |
| A-059 | **No evaluation harness.** No golden questions or regression tests for prompts or retrieval; README examples are manual. | none found | MEDIUM | M | Low | Build a small question/expected-answer set run against faked or real models |
| A-060 | `contextual` runs one LLM call per retrieved chunk (k=10) and `multiquery` adds a call; both opt-in. | `retrieval.py:36-45` | LOW | S | Low | Document cost; leave |
| A-061 | **Default model `gemini-3.8-flash` may not exist or be available to your key** (**NOT VERIFIED**); the README warns names are retired. | `settings.py:22`; `deploy.yml:235` | MEDIUM | S | Low | Confirm against the model list; keep one source of truth for the name |
| A-062 | **Embedding/index fit unverified:** index uses `DOT_PRODUCT` with a 768-d model (normalization **NOT VERIFIED**); query vs document embedding task types **NOT VERIFIED**. | `deploy.yml:84-95`; `embeddings.py:17` | LOW | M | High: re-index | Verify in Vertex docs before any change |
| A-063 | Sanctions, credit, tax and expense "tools" are LLM recall, not data sources; disclosed in the README. | `tools.py:29-175,229-269` | INFORMATIONAL | – | – | None unless real integrations are wanted |

## Resolution Log

Findings above describe the repository as audited on 2026-10-06 and are not rewritten. Resolutions are appended here. Not committed by Claude; the owner commits.

Common baseline (before any change, 2026-10-07): frontend `npm test` 1 passed; `npm run lint` 16 problems (9 errors, 7 warnings); `npx tsc --noEmit -p tsconfig.app.json` exit 0; `npm run build` OK; backend `pytest backend/tests -q` 9 passed.

### Q1 — Stop auto-deploy on push to `main` (resolves A-047 in part)
- **Change:** `deploy.yml` trigger reduced from `push` to `main` + `workflow_dispatch` to `workflow_dispatch` only, with a comment.
- **Reason:** a push to `main` could create billed Google Cloud resources and a public, unauthenticated service with no test gate.
- **Files modified:** `.github/workflows/deploy.yml`; docs that described the old trigger: `README.md`, `CLAUDE.md`, `DEPLOY.md`, `docs/ARCHITECTURE.md`, `docs/ONBOARDING.md`, `docs/OPERATIONS.md` (plus a snapshot note in `docs/PROJECT_DISCOVERY.md` and `docs/UNDERSTANDING.md`).
- **Tests executed:** YAML parsed with PyYAML before and after: triggers were `{push: {branches: [main]}, workflow_dispatch}`, now `{workflow_dispatch}`; jobs unchanged (`['deploy']`). Full suites as below.
- **Result:** pass.
- **Known limitations:** the workflow itself was never run, so end-to-end deploy behaviour is still NOT VERIFIED. There is still no test or lint gate (plan item N4), and a manual run still creates paid resources and a public service (plan items N1, N2). Whether the GitHub UI shows the "Run workflow" button on a non-default branch was not checked.

### Q2 — Git-ignore key and generated files (resolves A-013; part of A-046)
- **Change:** `.gitignore` gains `*-key.json`, `*service-account*.json`, `*.pem`, `*.p12`, `*.pfx` and `init_embeddings.json`.
- **Reason:** `DEPLOY.md` step 6 creates `github-deployer-key.json` in the working directory, which no rule ignored.
- **Files modified:** `.gitignore`.
- **Tests executed:** `git check-ignore` on sample names before (all not ignored) and after (all ignored, including `my-service-account-prod.json` after widening one pattern); `git ls-files -ci --exclude-standard` shows no tracked file became ignored; `.env.example`, `requirements.txt`, `frontend/package.json`, `backend/api/main.py`, `.claude/settings.json` and the sample PDFs are still not ignored.
- **Result:** pass.
- **Known limitations:** patterns are name-based; a key saved as e.g. `creds.json` is still not ignored. `*.pem` also ignores any future legitimately tracked `.pem` file (none exist now). Secret scanning of history was not re-run.

### Q5 — Fix misleading UI labels (resolves A-025)
- **Change:** `RagQATab.tsx`: label "Verified Answer" became "AI-generated answer". `AuditTab.tsx`: removed the three client timers that moved phases to running/done at 3s, 6s and 9s, so phases stay `pending` until the response arrives; the footer text "All Passed" became "Complete".
- **Reason:** the UI overstated trust in model output, invented progress the server does not report, and said "All Passed" even for a REJECTED memo.
- **Files modified:** `frontend/src/components/RagQATab.tsx`, `frontend/src/components/AuditTab.tsx`; new `frontend/src/test/RagQATab.characterization.test.tsx` and `frontend/src/test/AuditTab.characterization.test.tsx`.
- **Tests executed:** 15 characterization tests written first against the unchanged code (all passed: 16 total with the existing test). After the change, exactly 3 of them failed as intended (the old label, the old footer text, the timer behaviour); those 3 assertions, which I wrote in this task and which were not part of the baseline, were updated to the new behaviour. Baseline tests (`example.test.ts`, 9 pytest) were not modified. Final: frontend 16 passed, lint 16 problems (unchanged), tsc exit 0, build OK, pytest 9 passed.
- **Result:** pass.
- **Known limitations:** the audit pipeline panel now shows four numbered pending steps for the whole run (the right-hand panel shows the spinner), which is honest but less lively. `AuditTab.tsx` still maps `running` phases to `error` on failure, which is now a no-op. The footer still reads "4 Agents · Sequential" (three agents plus synthesis). No formatter is configured. The components were tested in jsdom, not in a browser (visual check NOT VERIFIED).
