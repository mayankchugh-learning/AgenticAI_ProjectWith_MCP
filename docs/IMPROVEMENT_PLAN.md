# IMPROVEMENT PLAN — Meridian AI

Built from `docs/AUDIT.md` (finding ids `A-0xx`). **Nothing here is implemented.** Every table has a Decision column set to **PENDING**; no item starts without your approval (CLAUDE.md rule 6 also requires a stop before upgrades, paid cloud use, credentials or architectural change).

**Priority mapping:** P0 = CRITICAL, P1 = HIGH, P2 = MEDIUM, P3 = LOW. The audit has no CRITICAL findings, so **P0 is empty**. **Timing groups:** quick wins (under 1 hour), next sprint, longer-term. Effort is from the audit; "under 1 hour" assumes the backend environment already works.

## Step 0: prerequisite for most items
| Step | What | Why | Needs approval | Decision |
|---|---|---|---|---|
| 0 | Install Python 3.12 (or use Docker), create a venv, run `pytest backend/tests` and record the baseline in `docs/setup-log.md` | Rule 5 requires tests before and after every change; the backend has never been run here (A-035) | Yes: system install, `pip install` | PENDING |

Every backend item below assumes Step 0 is done. Frontend items can start now (`npm ci/test/build` already work).

## Overview tables

### Quick wins (under 1 hour)
| ID | Pri | Title | Audit ids | Depends on | Risky? | Decision |
|---|---|---|---|---|---|---|
| Q1 | P1 | Stop auto-deploy on push to `main` | A-047 | none | No | APPROVED |
| Q2 | P2 | Git-ignore key and generated files | A-013, A-046 (part) | none | No | APPROVED |
| Q3 | P2 | Stop returning raw exception text; log tracebacks | A-008, A-052 (part) | Step 0 | No | PENDING |
| Q4 | P2 | Fix FX source label and zero-division | A-018 | Step 0 | No | PENDING |
| Q5 | P2 | Fix misleading UI labels | A-025 | none | No | APPROVED |
| Q6 | P2 | Input limits and upload hardening | A-002 (part), A-009, A-024, A-030, A-044 (part) | Step 0 | Low | PENDING |
| Q7 | P2 | Stop logging user content | A-010 (part) | Step 0 | No | PENDING |
| Q8 | P2 | Confirm the default Gemini model name | A-061 | your API key, approval to call Gemini | No | PENDING |
| Q9 | P3 | Remove dead settings and unused client functions | A-040 | Step 0 | No | PENDING |
| Q10 | P3 | Pin runtime versions | A-050 | none | No | PENDING |
| Q11 | P3 | CORS allowlist from an env var | A-007 | Step 0 | Low | PENDING |
| Q12 | P3 | Pin GitHub Actions by SHA | A-015 | none | No | PENDING |

### Next sprint
| ID | Pri | Title | Audit ids | Depends on | Risky? | Decision |
|---|---|---|---|---|---|---|
| N1 | P1 | Authentication and rate limiting | A-001, A-002 | Q1, Q6, owner decision on access model | **Yes** | PENDING |
| N2 | P1 | Least-privilege deploy and runtime identities | A-003, A-004 | Q1 | **Yes** | PENDING |
| N3 | P1 | Dependency vulnerability triage and upgrades | A-005, A-006 | scan approval, N5, N4 | **Yes** | PENDING |
| N4 | P2 | CI: test, lint, type-check; Dependabot | A-047 (rest), A-048, A-049 | Step 0, N5 | Low | PENDING |
| N5 | P2 | Test coverage: tools, supervisor, error paths | A-035, A-036, A-037 | Step 0 | No | PENDING |
| N6 | P2 | Timeouts and bounded retries | A-028, A-033 | N5 | **Yes** | PENDING |
| N7 | P2 | Upload and ingest atomicity and dedupe | A-020, A-021, A-022 | N5, Q6 | **Yes** | PENDING |
| N8 | P2 | Observability basics | A-051, A-052, A-054 | Q3, Q7 | Low | PENDING |
| N9 | P2 | Make degraded tool results explicit | A-019 | N5 | Medium | PENDING |
| N11 | P2 | Verdict logic in code; structured outputs; prompt hardening | A-011, A-056, A-057 | N5, N9 | **Yes** | PENDING |

### Longer-term
| ID | Pri | Title | Audit ids | Depends on | Risky? | Decision |
|---|---|---|---|---|---|---|
| L1 | P2 | Retrieval quality, returned sources, evaluation harness | A-058, A-059, A-062 | N5, N8 | **Yes** (re-index possible) | PENDING |
| L2 | P2 | Concurrent audit and background ingest | A-029, A-031 | N5, N6 | **Yes** (architectural) | PENDING |
| L3 | P2 | Separate log storage from document bucket | A-010 (rest) | N2, Q7 | Medium | PENDING |
| L4 | P3 | Boundaries, typing, duplication | A-041, A-042, A-044 (rest) | N5, N4 | Medium | PENDING |
| L5 | P3 | Caching and model tiering | A-055 | N8, N11 | Medium | PENDING |
| L6 | P3 | Frontend cleanup and lint | A-046 (rest), A-048 | none | Low | PENDING |
| L7 | P3 | Logger import-time side effects and bounded logs | A-032, A-045 (logger part) | N5 | Medium | PENDING |

### Deployment readiness
| ID | Pri | Requirement | Status today | Plan item | Decision |
|---|---|---|---|---|---|
| DR-1 | P2 | Configuration from environment variables | **Present**: `settings.py:6-35`. Gaps: no startup validation (`:14-18`), empty `GCS_PREFIX` default (`:18`), missing credentials path ignored (`:42-52`), hard-coded CORS (`main.py:44`), model name duplicated in `deploy.yml:235` | DR-1 | PENDING |
| DR-2 | P2 | Health endpoint | **Present but shallow**: `endpoints.py:50-52` always returns ok; no readiness check or probe config (`deploy.yml:226-236`) | DR-2 | PENDING |
| DR-3 | P2 | Graceful shutdown | **Partial**: lifespan flush and `atexit` (`main.py:28-32`, `custom_logger.py:36`). Shell-form `CMD` (`Dockerfile:42`) may not forward SIGTERM (NOT VERIFIED); in-flight audits have no cancellation | DR-3 | PENDING |
| DR-4 | P2 | Non-root container user | **Missing**: no `USER`, compiler in final image, no `HEALTHCHECK` (`Dockerfile:12-22,42`) | DR-4 | PENDING |
| DR-5 | P2 | Pinned dependencies and lockfile | **Partial**: backend pins direct deps only, no lock (`requirements.txt`); frontend has `package-lock.json` plus a second `bun.lock`; base images use floating tags (`Dockerfile:1,12`) | DR-5 | PENDING |
| DR-6 | P3 | Structured logs to stdout | **Present**: JSON to console (`custom_logger.py:46-54`, `severity` at `:9-19`). Gaps: also writes files, logs content (see Q7), no request id (N8) | covered by Q7, N8, L7 | PENDING |
| DR-7 | P3 | Tests needing no live external service | **Present**: `conftest.py:1-14`, fakes in `test_api.py`. Gap: coverage (N5) | covered by N5 | PENDING |

## Recommended order
Step 0 → Q1 → Q2, Q3, Q4, Q5, Q6, Q7, Q10, Q12 (independent, each its own commit) → N5 → N4 → N1/N2 (after your access-model decision) → N8, N9 → N6, N7 → N3 (only after the scan is approved and run) → N11, DR-1 to DR-5 → longer-term items. Q8 can happen any time you approve one Gemini call.

**Dependency chain in short:** tests (N5) gate every risky change; CI (N4) gates upgrades (N3); N1 needs your decision on who may use the app; L2 needs N6 timeouts first; L3 needs N2 so a new bucket has the right permissions.

**Risky changes (need explicit approval before work starts):** N1, N2, N3, N6, N7, N11, L1, L2, DR-3, DR-4, and anything touching `deploy.yml` behaviour.

---

## Item details (quick wins)

### Q1 · P1 · Stop auto-deploy on push to `main`
- **Current state:** `deploy.yml:3-7` runs on every push to `main` and on manual dispatch; it provisions billed resources and a public service; no test job.
- **Problem:** merging any change can create paid resources and expose an unauthenticated API (A-047, A-001).
- **Proposed state:** trigger only on `workflow_dispatch` (later: gate on a passing test job from N4).
- **Why better:** deploys become a deliberate action.
- **Files:** `.github/workflows/deploy.yml`.
- **Dependencies affected:** none.
- **Risks:** anyone relying on auto-deploy must run it by hand.
- **Testing:** read the workflow diff; confirm in GitHub that a push to a branch and to `main` no longer starts the workflow (needs a harmless branch push).
- **Rollback:** revert the commit.

### Q2 · P2 · Git-ignore key and generated files
- **Current state:** `.gitignore` covers `.env`, `.envrc`, `credentials/` only; `DEPLOY.md:103-105` creates `github-deployer-key.json`; `init_embeddings.json` is untracked-but-not-ignored (A-013).
- **Problem:** a key file or generated file can be committed by accident.
- **Proposed state:** add `*-key.json`, `service-account*.json`, `*.pem`, `*.p12`, `*.pfx`, `init_embeddings.json`.
- **Why better:** blocks the likeliest accidental commit.
- **Files:** `.gitignore`.
- **Dependencies affected:** none.
- **Risks:** could hide a legitimately tracked `*-key.json` (none exist; check with `git ls-files`).
- **Testing:** `git check-ignore -v` on sample names; `git status` clean.
- **Rollback:** revert.

### Q3 · P2 · Stop returning raw exception text
- **Current state:** four handlers return `detail=str(e)` (`endpoints.py:105,119,171,193`); audit/ask log only the message (`:104,118`).
- **Problem:** leaks internals; weak debugging (A-008, A-052).
- **Proposed state:** return `"Internal error (id <uuid>)"`; log the id with `exc_info`.
- **Why better:** safer for users, better for operators.
- **Files:** `backend/api/endpoints.py`, `frontend/src/lib/api.ts` (message display), tests.
- **Dependencies affected:** the UI shows `body.detail` (`api.ts:11`); messages change.
- **Risks:** users lose the (sometimes useful) raw error; mitigate with the id.
- **Testing:** monkeypatch a failing `ask_question`, assert 500 and no raw text; assert the log line.
- **Rollback:** revert.

### Q4 · P2 · Fix FX source label and zero-division
- **Current state:** label depends only on parsing (`tools.py:213`); no zero guard (`:212`).
- **Problem:** estimated rate reported as live; possible crash (A-018).
- **Proposed state:** track `source` as `live` or `llm_estimate`; return an FX WARNING if the rate is not positive.
- **Why better:** accurate audit text.
- **Files:** `backend/agent/tools.py`, new tests.
- **Dependencies affected:** the Tax prompt keys on `FX SUCCESS/ALERT/WARNING` (`prompts.py:73-75`); keep those prefixes.
- **Risks:** wording change inside the message.
- **Testing:** mock `requests.get` and `_ask_llm` for live, fallback and zero cases.
- **Rollback:** revert.

### Q5 · P2 · Fix misleading UI labels
- **Current state:** "Verified Answer" (`RagQATab.tsx:163`), fake timers (`AuditTab.tsx:62-70`), "All Passed" (`:293`).
- **Problem:** overstates trust (A-025).
- **Proposed state:** label "Answer (AI-generated)"; indeterminate spinner instead of timed steps; footer shows "Complete" only.
- **Why better:** honest UI.
- **Files:** `RagQATab.tsx`, `AuditTab.tsx`.
- **Dependencies affected:** none.
- **Risks:** cosmetic only.
- **Testing:** `npm run build`, manual view.
- **Rollback:** revert.

### Q6 · P2 · Input limits and upload hardening
- **Current state:** unbounded `str` fields (`schemas.py:10-11,25-27`); extension-only check, full read into memory, per-file client, raw filename in object name (`endpoints.py:133,144,148-149`).
- **Problem:** cost abuse and risky uploads (A-002, A-009, A-024, A-030).
- **Proposed state:** `max_length`, `Literal` retriever type, size cap, `%PDF` header check, generated object name, filename `None` guard, one reused storage client.
- **Why better:** bounded cost and safer storage.
- **Files:** `schemas.py`, `endpoints.py`, tests, frontend error text.
- **Dependencies affected:** clients sending long text get 422.
- **Risks:** limits too tight for real PDFs; choose limits with you.
- **Testing:** oversize, non-PDF named `.pdf`, odd filenames, normal sample PDFs.
- **Rollback:** revert.

### Q7 · P2 · Stop logging user content
- **Current state:** full query, answer, reports and memo logged (`retrieval.py:53,66`; `agents.py:59,63,67,77`).
- **Problem:** sensitive text in log files and the document bucket (A-010).
- **Proposed state:** log lengths, retriever type and elapsed time.
- **Why better:** privacy; smaller logs.
- **Files:** `retrieval.py`, `agents.py`.
- **Dependencies affected:** debugging loses content; N8 adds structured metrics.
- **Risks:** harder to diagnose bad answers; keep an opt-in debug flag if you want one.
- **Testing:** run a faked flow and grep the log for the test string.
- **Rollback:** revert.

### Q8 · P2 · Confirm the default Gemini model
- **Current state:** default `gemini-3.8-flash` (`settings.py:22`; also `deploy.yml:235`), existence NOT VERIFIED (A-061).
- **Problem:** if invalid, every AI feature fails.
- **Proposed state:** confirm against the Google model list or one test call, then set one source of truth.
- **Why better:** removes the biggest unknown for running the audit.
- **Files:** `settings.py`, `deploy.yml`, `.env.example`, docs.
- **Dependencies affected:** needs your `GOOGLE_API_KEY` in `.env` (I will not read it).
- **Risks:** one billed API call.
- **Testing:** the single test call; check response status only.
- **Rollback:** revert the name change.

### Q9 · P3 · Remove dead settings and unused client functions
- **Current state:** `settings.debug`/`app_env` unused (`settings.py:9,11`); `uploadDocuments`, `listUploads`, `healthCheck` uncalled (`api.ts:24,32,65`) (A-040).
- **Problem:** noise.
- **Proposed state:** remove them (keep `ENVIRONMENT` in deploy only if wanted).
- **Why better:** less to read and maintain.
- **Files:** `settings.py`, `api.ts`.
- **Dependencies affected:** `GET /api/rag/uploads` would have no UI caller (backend route stays).
- **Risks:** low; confirm with a repo-wide search first.
- **Testing:** pytest, `npm run build`.
- **Rollback:** revert.

### Q10 · P3 · Pin runtime versions
- **Current state:** no `.python-version`, `.nvmrc` or `engines` (A-050).
- **Problem:** works on one Node (25.5.0) but ships on Node 20 (`Dockerfile:1`).
- **Proposed state:** add `.python-version` (3.12), `.nvmrc` (20), `engines` in `package.json`.
- **Why better:** same runtime everywhere.
- **Files:** new files; `frontend/package.json`.
- **Dependencies affected:** `npm ci` may warn on Node 25 if `engines` is strict.
- **Risks:** low.
- **Testing:** rerun `npm ci/test/build` on Node 20.
- **Rollback:** delete the files.

### Q11 · P3 · CORS allowlist from an env var
- **Current state:** `allow_origins=["*"]` with credentials (`main.py:42-48`).
- **Problem:** A-007.
- **Proposed state:** `CORS_ALLOW_ORIGINS` env var, default same-origin only.
- **Why better:** closes cross-site calls.
- **Files:** `main.py`, `settings.py`, `.env.example`, README.
- **Dependencies affected:** `npm run dev` on port 3000 needs `http://localhost:3000` allowed.
- **Risks:** blocks the dev server if misconfigured.
- **Testing:** TestClient with an `Origin` header.
- **Rollback:** revert.

### Q12 · P3 · Pin GitHub Actions by SHA
- **Current state:** `checkout@v4`, `auth@v2`, `setup-gcloud@v2` (`deploy.yml:25,28,33`); length of the key echoed (`:207`).
- **Problem:** A-015.
- **Proposed state:** pin full commit SHAs; drop the echo.
- **Why better:** supply-chain hygiene.
- **Files:** `deploy.yml`.
- **Dependencies affected:** needs correct SHAs looked up from GitHub.
- **Risks:** a wrong SHA breaks the workflow.
- **Testing:** manual dispatch on a test project (paid; only with approval).
- **Rollback:** revert.

---

## Item details (next sprint)

### N1 · P1 · Authentication and rate limiting
- **Current state:** no auth (`endpoints.py:50-193`); public service (`deploy.yml:232,250-254`).
- **Problem:** A-001, A-002.
- **Proposed state:** Cloud Run IAM or IAP, or a shared API key / token dependency on `/api/*` (except health), plus rate limits.
- **Why better:** protects quota and data.
- **Files:** `endpoints.py`/`main.py`, `deploy.yml`, `frontend/src/lib/api.ts`, docs.
- **Dependencies affected:** SPA must send credentials; any other caller breaks.
- **Risks:** architectural; locks out users if wrong.
- **Testing:** unauthenticated gets 401/403; authorized passes; health open.
- **Rollback:** revert and redeploy; keep the old revision in Cloud Run.

### N2 · P1 · Least-privilege deploy and runtime identities
- **Current state:** `roles/editor` + `projectIamAdmin` for the deployer (`DEPLOY.md:95-102`), `run.admin` (`deploy.yml:245`), JSON key (`:30`), default compute account at runtime (`:218`).
- **Problem:** A-003, A-004.
- **Proposed state:** Workload Identity Federation; deployer with only needed roles; a dedicated runtime service account.
- **Why better:** a leak or bug cannot take over the project.
- **Files:** `deploy.yml`, `DEPLOY.md`.
- **Dependencies affected:** GitHub secrets (`GCP_CREDENTIALS_JSON` removed), IAM in your project.
- **Risks:** deploys fail until IAM is right; touches real cloud IAM (approval required).
- **Testing:** dry-run in a throwaway project.
- **Rollback:** keep the old key and roles until the new path succeeds, then remove.

### N3 · P1 · Dependency vulnerability triage and upgrades
- **Current state:** `npm ci` reported 33 findings; backend transitive deps floating (A-005, A-006).
- **Problem:** unknown exposure.
- **Proposed state:** (1) run `npm audit --omit=dev` and `pip-audit -r requirements.txt` (approval needed), (2) classify, (3) upgrade only reachable, shipped packages one at a time.
- **Why better:** fixes real risk without churn.
- **Files:** `frontend/package.json`, `package-lock.json`, `requirements.txt`, a new lock.
- **Dependencies affected:** the whole build; LangChain family versions are tightly coupled.
- **Risks:** breaking changes; needs approval for every upgrade.
- **Testing:** N5 tests + N4 CI + `npm run build` before and after.
- **Rollback:** revert the lockfile commit.

### N4 · P2 · CI for test, lint and type-check; Dependabot
- **Current state:** only `deploy.yml`; lint fails (A-047, A-048, A-049).
- **Problem:** nothing checks changes.
- **Proposed state:** `ci.yml` running pytest, `npm test`, `npm run build`, lint (non-blocking until L6), and `ruff`; add Dependabot.
- **Why better:** catches breakage before merge.
- **Files:** `.github/workflows/ci.yml`, `.github/dependabot.yml`, tool configs.
- **Dependencies affected:** needs Step 0 and N5.
- **Risks:** low; CI minutes.
- **Testing:** open a PR from a branch.
- **Rollback:** delete the workflow.

### N5 · P2 · Test coverage: tools, supervisor, error paths
- **Current state:** 9 route-shape tests (`test_api.py:11-79`) (A-035, A-036, A-037).
- **Problem:** the logic that matters is untested.
- **Proposed state:** fake-LLM tests for each tool's success, parse-failure and error branches; supervisor test with fake agents; 422/500/corrupt-PDF tests; SPA path-traversal test; robust env handling.
- **Why better:** safe base for risky changes.
- **Files:** `backend/tests/*`.
- **Dependencies affected:** none (tests only).
- **Risks:** none to runtime.
- **Testing:** run the suite; mutate code briefly to see tests fail.
- **Rollback:** delete test files.

### N6 · P2 · Timeouts and bounded retries
- **Current state:** none in repo code except `tools.py:194` (A-028, A-033).
- **Problem:** hangs and transient failures.
- **Proposed state:** explicit client timeouts and 2-3 retries with backoff on Gemini/Vertex/GCS; frontend `AbortController`.
- **Why better:** predictable failure.
- **Files:** `llm.py`, `vector_store.py`, `endpoints.py`, `data_ingestion.py`, `api.ts`.
- **Dependencies affected:** parameter names depend on library versions (NOT VERIFIED).
- **Risks:** retries multiply cost; timeouts cut long audits.
- **Testing:** fake slow/failing clients.
- **Rollback:** revert.

### N7 · P2 · Upload and ingest atomicity and dedupe
- **Current state:** partial state on failure; silent GCS copy failure; duplicates on re-ingest (`endpoints.py:152-153,169-176`; `data_ingestion.py:43`) (A-020, A-021, A-022).
- **Problem:** inconsistent index and bucket.
- **Proposed state:** per-file result recorded immediately; copy failure reported; stable chunk ids or delete-then-add per source.
- **Why better:** repeatable, recoverable ingestion.
- **Files:** `endpoints.py`, `data_ingestion.py`, tests.
- **Dependencies affected:** Vector Search id semantics (NOT VERIFIED).
- **Risks:** data changes in a billed index; test only with a throwaway index.
- **Testing:** fake store asserting ids; multi-file failure case.
- **Rollback:** revert code; re-ingest from `uploads/`.

### N8 · P2 · Observability basics
- **Current state:** no request ids, timings, LLM usage; swallowed errors (A-051, A-052, A-054).
- **Problem:** hard to see what happened or what it cost.
- **Proposed state:** middleware adding request id and duration; log every tool failure with `exc_info`; log per-call model, elapsed time and token counts if available.
- **Why better:** diagnosable and cost-aware.
- **Files:** `main.py`, `tools.py`, `llm.py`, `custom_logger.py`.
- **Dependencies affected:** log format gains fields.
- **Risks:** log volume.
- **Testing:** assert log fields in tests.
- **Rollback:** revert.

### N9 · P2 · Make degraded tool results explicit
- **Current state:** fallbacks look like normal output (`tools.py:164-175,56-57,262-268`) (A-019).
- **Problem:** CFO reasons over weak data.
- **Proposed state:** `DEGRADED:` marker and a `degraded` flag aggregated into the response; synthesis holds when any check degraded.
- **Why better:** fewer silently wrong decisions.
- **Files:** `tools.py`, `agents.py`, `prompts.py`, `schemas.py`, UI.
- **Dependencies affected:** response schema (additive).
- **Risks:** behaviour change in memos.
- **Testing:** fake LLM failures.
- **Rollback:** revert.

### N11 · P2 · Verdict logic in code, structured outputs, prompt hardening
- **Current state:** decisions via prompt string matching (`prompts.py:165-172`); RED ALERT not enforced (`agents.py:56-67`); fence-stripped JSON (`tools.py:98-105`); injectable f-strings (A-011, A-056, A-057).
- **Problem:** unreliable and manipulable decisions.
- **Proposed state:** tools return structured data; code computes REJECTED/CONDITIONAL HOLD/APPROVED; stop early on a sanctions hit; delimit untrusted text; pass today's date.
- **Why better:** deterministic, testable decisions.
- **Files:** `agents.py`, `tools.py`, `prompts.py`, `schemas.py`.
- **Dependencies affected:** UI and any API consumer of the four text fields.
- **Risks:** high; changes core behaviour (architectural; needs approval).
- **Testing:** golden cases per decision branch with fake tools.
- **Rollback:** revert; keep the old path behind a flag during rollout.

---

## Item details (longer-term)

### L1 · P2 · Retrieval quality, sources, evaluation
- **Current state:** fixed chunking/k; sources dropped (`retrieval.py:36-48,67`); no eval (A-058, A-059, A-062).
- **Problem:** quality unknown.
- **Proposed state:** return source and page with answers; a golden question set; tune chunking/k/threshold; verify embedding/metric fit in Vertex docs.
- **Why better:** measurable, checkable answers.
- **Files:** `retrieval.py`, `schemas.py`, `RagQATab.tsx`, new `evals/`.
- **Dependencies affected:** response schema (additive); index only if parameters change.
- **Risks:** re-indexing in a billed index.
- **Testing:** eval run before and after each change.
- **Rollback:** revert; restore the previous index from source PDFs.

### L2 · P2 · Concurrent audit and background ingest
- **Current state:** sequential audit (`agents.py:56-77`); blocking bulk ingest (`endpoints.py:185-193`) (A-029, A-031).
- **Problem:** long blocked requests.
- **Proposed state:** run the three agents concurrently; job-and-poll for ingestion.
- **Why better:** faster, resilient.
- **Files:** `agents.py`, `endpoints.py`, new job store.
- **Dependencies affected:** needs N6; may need Cloud Tasks/Pub/Sub (architectural).
- **Risks:** thread-safety of shared agents (NOT VERIFIED), state storage.
- **Testing:** concurrency tests with fakes.
- **Rollback:** feature flag back to sequential.

### L3 · P2 · Separate log storage from the document bucket
- **Current state:** logs upload to the document bucket (`custom_logger.py:96`).
- **Problem:** A-010 residual.
- **Proposed state:** stdout-only logging to Cloud Logging; drop the GCS uploader.
- **Why better:** access control and retention are separate.
- **Files:** `custom_logger.py`, `main.py`, `deploy.yml`.
- **Dependencies affected:** shutdown flush removed.
- **Risks:** losing the bucket log copy.
- **Testing:** local run, check console output.
- **Rollback:** revert.

### L4 · P3 · Boundaries, typing, duplication
- **Current state:** A-041, A-042, A-044.
- **Proposed state:** shared LLM module, a GCS helper, one JSON-fence helper, mypy/pyright gradually.
- **Why better:** clearer layers.
- **Files:** `agents.py`, `tools.py`, `endpoints.py`, `rag/llm.py`.
- **Dependencies affected:** imports across modules.
- **Risks:** moderate churn.
- **Testing:** N5 suite.
- **Rollback:** revert per commit.

### L5 · P3 · Caching and model tiering
- **Current state:** A-055; every call hits Gemini.
- **Proposed state:** cache by input hash; cheaper model for simple tools.
- **Why better:** cost and latency.
- **Files:** `llm.py`, `tools.py`, `agents.py`.
- **Dependencies affected:** model names, cache store.
- **Risks:** stale or cross-user cached data; pick TTL and key carefully.
- **Testing:** hit/miss tests.
- **Rollback:** flag off.

### L6 · P3 · Frontend cleanup and lint
- **Current state:** 16 lint problems; template leftovers; two lockfiles (A-046, A-048).
- **Proposed state:** fix or relax rules in generated UI files, rename package, remove `bun.lock`, fill `index.html` TODOs, remove unused deps.
- **Why better:** clean, single toolchain.
- **Files:** `frontend/*`.
- **Dependencies affected:** `package-lock.json` changes if deps are removed.
- **Risks:** low.
- **Testing:** `npm ci/lint/test/build`.
- **Rollback:** revert.

### L7 · P3 · Logger side effects and bounded logs
- **Current state:** `./logs` created at import (`custom_logger.py:25-26`; `logger/__init__.py:5`) (A-032, A-045).
- **Proposed state:** lazy init; file handler optional; stdout default in containers.
- **Why better:** works on read-only filesystems; testable.
- **Files:** `logger/*`, `main.py`.
- **Dependencies affected:** every `from logger import GLOBAL_LOGGER`.
- **Risks:** moderate.
- **Testing:** import in a read-only temp dir.
- **Rollback:** revert.

---

## Item details (deployment readiness)

### DR-1 · P2 · Config validation at startup
- **Current state:** empty-string defaults; no validation (`settings.py:14-18,42-52`) (A-023, A-027).
- **Problem:** failures appear on first request.
- **Proposed state:** fail or warn at startup for features that are enabled; normalize `GCS_PREFIX`; warn when the credentials path is missing; one source of truth for the model name.
- **Why better:** early, clear failures.
- **Files:** `settings.py`, `main.py`, `.env.example`.
- **Dependencies affected:** tests rely on fake env (`conftest.py`).
- **Risks:** a strict failure blocks `/api/health`-only runs; make it a warning for optional features.
- **Testing:** settings unit tests.
- **Rollback:** revert.

### DR-2 · P2 · Readiness endpoint and probes
- **Current state:** `/api/health` always ok (`endpoints.py:50-52`).
- **Problem:** A-053.
- **Proposed state:** keep `/api/health` as liveness; add `/api/ready` checking config presence (no paid calls); set Cloud Run startup/liveness probes.
- **Why better:** the platform can route and restart correctly.
- **Files:** `endpoints.py`, `deploy.yml`, `Dockerfile`.
- **Dependencies affected:** deploy flags.
- **Risks:** a wrong probe causes restart loops.
- **Testing:** TestClient for both endpoints.
- **Rollback:** revert; remove probes.

### DR-3 · P2 · Graceful shutdown
- **Current state:** lifespan flush (`main.py:28-32`); shell-form `CMD` (`Dockerfile:42`).
- **Problem:** SIGTERM forwarding and in-flight request behaviour are NOT VERIFIED.
- **Proposed state:** exec-form `CMD` (needs `PORT` handling), documented grace period, test shutdown locally.
- **Why better:** clean stops and complete log flush.
- **Files:** `Dockerfile`.
- **Dependencies affected:** how `${PORT}` is expanded.
- **Risks:** a wrong `CMD` stops the container starting.
- **Testing:** `docker run` then `docker stop` and read the logs.
- **Rollback:** revert.

### DR-4 · P2 · Non-root, smaller container
- **Current state:** root, `build-essential` in the final image, no `HEALTHCHECK` (`Dockerfile:12-22,42`) (A-012).
- **Proposed state:** multi-stage build, non-root `USER`, writable log dir or stdout-only (see L7), `HEALTHCHECK`.
- **Why better:** smaller attack surface.
- **Files:** `Dockerfile`, possibly `custom_logger.py`.
- **Dependencies affected:** write permissions for `./logs`; compiled wheels must be copied correctly.
- **Risks:** runtime permission errors.
- **Testing:** build, run, call `/api/health`, upload a PDF.
- **Rollback:** revert.

### DR-5 · P2 · Pinned dependencies and lockfile
- **Current state:** direct pins only; two frontend lockfiles; floating base images (A-006, A-046).
- **Proposed state:** a Python lock with hashes; keep one frontend lockfile; pin base images by tag plus digest.
- **Why better:** reproducible builds.
- **Files:** `requirements*.txt`/lock, `Dockerfile`.
- **Dependencies affected:** build pipeline.
- **Risks:** lock generation needs a working environment (Step 0); version resolution failures are possible (NOT VERIFIED).
- **Testing:** clean install from the lock; full tests.
- **Rollback:** revert.

---

## Not recommended
| Audit id | Finding | Why not worth fixing now | Decision |
|---|---|---|---|
| A-014 | `/api/status` discloses IDs | Low value alone; N1 (auth) fixes it as a side effect | PENDING |
| A-016 | Secret scan: nothing found | Nothing to fix; re-scan later with gitleaks | PENDING |
| A-017 | No unsafe deserialization found | Nothing to fix | PENDING |
| A-026 | Possible concurrency issues | Unconfirmed (NOT VERIFIED); investigate only if a bug is observed | PENDING |
| A-034 | Upload history per process | Cosmetic list; a shared store costs more than it gives | PENDING |
| A-038 | Frontend placeholder test | Little UI logic to test; add tests when UI logic changes | PENDING |
| A-039 | Tests need no live services | Positive finding | PENDING |
| A-043 | Large functions | Split only while editing them (N7); standalone refactor is churn | PENDING |
| A-045 (rest) | Global singletons and `lru_cache` | Works as intended (lazy clients); only the logger part is in L7 | PENDING |
| A-060 | Contextual/multiquery cost | Opt-in features chosen by the user; document, do not remove | PENDING |
| A-062 | Embedding/metric fit | Cannot change without a billed re-index; verify against docs first (inside L1) | PENDING |
| A-063 | Tools are LLM recall | Disclosed demo limitation; real data integrations are out of scope | PENDING |
