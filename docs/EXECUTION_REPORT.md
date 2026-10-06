# EXECUTION REPORT

Covers the approved items of `docs/IMPROVEMENT_PLAN.md` (as on disk on 2026-10-07). Nothing here is committed by Claude.

## 1. Approved items
The plan has 49 Decision cells: **3 APPROVED**, 46 PENDING, 0 DEFER, 0 REJECT.

| ID | Pri | Title | Status |
|---|---|---|---|
| Q1 | P1 | Stop auto-deploy on push to `main` | Implemented, verified |
| Q2 | P2 | Git-ignore key and generated files | Implemented, verified |
| Q5 | P2 | Fix misleading UI labels | Implemented, verified |

All other items are PENDING and untouched.

## 2. Characterization tests
| Item | Code affected | Characterization approach |
|---|---|---|
| Q5 | `frontend/src/components/RagQATab.tsx` (9 tests), `frontend/src/components/AuditTab.tsx` (6 tests) | vitest + Testing Library, API client replaced with `vi.mock`, so no network, backend or API key. Covers success, error, empty input, Enter/Shift+Enter, retriever choice, example queries, pending state, clear history, reset, and the old fake 3s/6s/9s timers |
| Q1 | `.github/workflows/deploy.yml` (config, no module) | PyYAML parse before and after: triggers `{push: main, workflow_dispatch}` then `{workflow_dispatch}`; job list unchanged |
| Q2 | `.gitignore` (config, no module) | `git check-ignore` on sample names before (none ignored) and after (all ignored); controls such as `.env.example` still not ignored; `git ls-files -ci --exclude-standard` empty |

- No test framework was missing: pytest 8.4.2, httpx, vitest and Testing Library were already installed. Nothing new was installed and no `pytest.ini` was added.
- No test needs a live service, so no skip marker is needed. A search of `backend/tests` and `frontend/src/test` found no live HTTP calls and no skipped tests.
- The tests were written and run green against the unchanged code first. After the Q5 change 3 of them failed as intended and those 3 assertions (written in this task, not baseline tests) were updated to the new behaviour. Details are in the Resolution Log in `docs/AUDIT.md`.

## 3. Baseline versus result
| Check | Baseline (before any change) | Result (final run) |
|---|---|---|
| Frontend tests (`npm test`) | 1 passed | **16 passed** (3 files) |
| Frontend lint (`npm run lint`) | 16 problems (9 errors, 7 warnings) | 16 problems (9 errors, 7 warnings), unchanged |
| Frontend type check (`npx tsc --noEmit -p tsconfig.app.json`) | exit 0 | exit 0 |
| Frontend build (`npm run build`) | OK | OK (13.45 s) |
| Backend tests (`pytest backend/tests -q`) | 9 passed | **9 passed** (16.09 s) |
| Formatter | none configured | none configured |

No test that passed in the baseline fails now. Lint failures are the pre-existing 16.

## 4. State of the working tree
17 files are staged and not committed: 15 modified and 2 new test files. This report is a new file and is untracked until you add it. No push has been made.

## 5. Limits
- The components were tested in jsdom, not a real browser.
- The deploy workflow was never run; its behaviour is NOT VERIFIED beyond the YAML trigger change.
- Backend code was not modified by Q1, Q2 or Q5, so backend tests only confirm nothing regressed.
