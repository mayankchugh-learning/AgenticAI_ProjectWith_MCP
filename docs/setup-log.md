# Setup Log

Rules: no changes outside `docs/` until a plan is approved; no secret values recorded.

## 2026-10-06 — Tooling check (read-only)

| Command | Result |
|---|---|
| `claude --version` | 2.1.291 (Claude Code) |
| `git --version` | git version 2.52.0.windows.1 |
| `claude doctor` | Native install, `C:\Users\madfa\.local\bin\claude.exe`, win32-x64; auto-updates enabled (channel: latest); search OK; "No installation issues found." |

Notes:
- `claude doctor` was run non-interactively (stdin from /dev/null) with a 60s timeout; it completed normally.
- Assumption: the repo's `CLAUDE.md` (created earlier, before the session rules) is partly README-derived and will be re-verified against code in Phase 1.

## 2026-10-06 — .claude/settings.json

- Created `.claude/settings.json` at the user's explicit request (an exception to the "docs/ only" rule). It contains only `permissions.deny` entries blocking reads of `.env*`, `secrets/**`, `*.pem`, and `cat/type/Get-Content .env*`. No secrets.
- CORRECTION: the first validation attempt (`python -c ...`) failed because `python` is not on PATH in Git Bash; the commit proceeded anyway. JSON was then validated with PowerShell `ConvertFrom-Json` (valid, 8 deny entries). Committed as 2b26e14 (only `.claude/settings.json`).
- Note: deny rules are pattern-based; other read paths (e.g. `Bash(grep ... .env)`) are NOT VERIFIED as blocked. `.env.example` is intentionally not denied.

## 2026-10-06 — Phase 1 read-only discovery

- Read (no execution): backend/api/{main,endpoints,schemas}.py, backend/agent/{agents,tools}.py, backend/rag/*.py, backend/config/settings.py, backend/logger/*.py, backend/tests/*, requirements*.txt, Dockerfile, .dockerignore, .gitignore, deploy.yml, generate_json.py, frontend/package.json, vite config, frontend/src/lib/api.ts, RagQATab.tsx, README.md. Grepped (not fully read): backend/agent/prompts.py, DEPLOY.md.
- `.env` was never opened. `.env.example` was grepped for variable NAMES only (12 names).
- Grep results: no TODO/FIXME/XXX/HACK in backend, frontend/src, root *.py, yml, Dockerfile; `settings.debug`/`app_env` have no readers in backend/.
- Nothing installed, built, run or modified. Output: docs/PROJECT_DISCOVERY.md (plan/proposal; awaiting owner decisions in its section 12).
- Assumptions: pydantic-settings precedence (env > .env > defaults) taken from library defaults, not observed. README "9 passed" matches the 9 test functions counted but is NOT VERIFIED.

## 2026-10-06 — docs/UNDERSTANDING.md

- Created docs/UNDERSTANDING.md (9 sections) from files read in earlier discovery steps; no new commands beyond read-only git and grep. Not committed.
- Read-only git results used: 3 commits, 1 author (Mayank Chugh), all on 2026-10-06; every file changed once; only TODOs are frontend/index.html:6 and :11.
- Assumption: library behaviour (LangChain, LangGraph, FastAPI, Vertex/Gemini clients) not read; marked NOT VERIFIED in the doc.
- A comprehension quiz (15 questions) was started in chat; the doc contains answers, so it was written before the quiz began.

- 2026-10-06 user-requested: git add . + git commit on branch main (4 files: CLAUDE.md, docs/*). Push NOT performed: pushes to main trigger deploy.yml:3-7 (paid GCP provisioning); awaiting confirmation.

- Created branch scratch/explore from main at b1c7b54 (user-provided workflow, step 1 only). Branch claude/analysis does not exist locally or on origin. No logging added, nothing run, nothing pushed.

- User asked for git push (after earlier "do not push"). Pushed ONLY branch scratch/explore (commit b1c7b54) to origin with upstream tracking. main was NOT pushed, so deploy.yml (triggers on main) was not started. The uncommitted setup-log line was not included.

## 2026-10-06 — Local setup: steps 0 and 4 (user approved steps 0, 2-4)

- Step 0 (read-only): `py` launcher and `python` NOT FOUND in PowerShell; node v25.5.0, npm 11.10.0, Docker 29.2.0; PowerShell Process execution policy already Bypass.
- Step 2 (Python venv/pip) NOT STARTED: Python 3.12 is not installed; installing it (winget, system-wide) is step 1 and needs explicit approval.
- Step 4 in `frontend/`: `npm ci` OK (498 packages, exit 0; npm audit reports 33 vulnerabilities: 1 low, 11 moderate, 18 high, 3 critical — NOT fixed, no upgrades); `npm run lint` FAILED exit 1 (16 problems: 9 errors, 7 warnings; errors seen: no-empty-object-type, no-require-imports in tailwind.config.ts:91); `npm test` OK (1 test passed, vitest 3.2.4); `npm run build` OK (vite 5.4.21, 1681 modules, dist/ created, git-ignored).
- Caveat: ran on Node 25.5.0, whereas the Dockerfile builds with Node 20 (Dockerfile:1); results on Node 20 NOT VERIFIED. Deprecation warning for `punycode` seen (harmless).
- `git status` after step 4: only docs/setup-log.md modified; node_modules and dist are ignored.

## 2026-10-06 — CLAUDE.md rewritten

- Rewrote CLAUDE.md at the owner's request (explicit exception to the docs/-only rule), on branch scratch/explore. Commands section lists only what ran: npm ci, npm test, npm run build; npm run lint is listed as failed; backend and type-check commands are listed as NOT VERIFIED. Not committed, not pushed.

## 2026-10-06 — README.md rewritten

- Rewrote README.md at the owner's request (explicit exception to the docs/-only rule) on scratch/explore. Frontend commands marked verified (npm ci/test/build); backend, dev server, Docker, and all API usage examples marked NOT YET VERIFIED (Python not installed). Not committed, not pushed.

## 2026-10-06 — New docs and re-verification pass

- Created docs/ARCHITECTURE.md, docs/REFERENCE.md, docs/ONBOARDING.md, docs/OPERATIONS.md (not committed). DEPLOYMENT.md intentionally not written yet.
- Re-verified CLAUDE.md, README.md and docs/*.md: (1) every backticked file name resolves to a tracked/untracked file except docs/DEPLOYMENT.md (planned), backend/tests/test_llm.py (proposed example), init_embeddings.json (CI-generated, not in repo); (2) every UPPER_CASE env-like token is a settings alias, a known extra (PORT, VITE_API_URL, GOOGLE_APPLICATION_CREDENTIALS, GCP_CREDENTIALS_JSON) or a code constant; (3) ports: 8080 (Dockerfile:38,42; main.py:5; deploy.yml:233) and 3000 (frontend/vite.config.ts:10) confirmed; 8081 is only a suggested alternative.
- Claims fixed: README health-without-.env now marked INFERRED; README tab wording narrowed (Index.tsx not read); curl.exe, API-key URL and 403 explanation marked NOT VERIFIED/sourced; CLAUDE.md stale README line pointer replaced; PROJECT_DISCOVERY.md and UNDERSTANDING.md got a note that their README.md:<line> citations refer to the original README at c2bbced (rewritten since).
- Still NOT VERIFIED by design: all backend commands (no Python), the 9 pytest tests, npm run dev, Docker build, every API example, all library behaviour.

## 2026-10-07 — Audit and improvement plan

- Created docs/AUDIT.md (63 findings: 0 critical, 4 high, 31 medium, 24 low, 4 informational) and docs/IMPROVEMENT_PLAN.md. Nothing implemented. Not committed.
- Secret scan: git grep for key/token patterns over tracked files printing file:line only; no hardcoded secrets found (one false positive, a Secret Manager reference at deploy.yml:236). The first private-key pattern attempt failed because git grep parsed it as an option; re-run with -e found none. .env was never opened; .env.example values were not viewed.
- No scanners run. Proposed (awaiting approval): npm audit [--omit=dev] in frontend/; pip-audit -r requirements.txt (needs Python + install of pip-audit).
- Limits: backend never run (no Python); frontend components DocumentUploadTab, SystemStatusTab, Index.tsx, ui/*, tsconfig and Playwright files not read.
