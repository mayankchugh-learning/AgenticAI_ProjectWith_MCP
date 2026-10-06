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
