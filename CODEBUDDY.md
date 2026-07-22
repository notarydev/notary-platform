# Notary Platform — Agent Onboarding

## What this is

Forensic proof-of-mitigation platform. Root cause analysis for AI decision failures, sealed as tamper-evident evidence, replayed deterministically, fixed via mutation testing, certified with signed Proof of Mitigation, and promoted to release-gate readiness checks.

## Repo

- **GitHub**: `github.com/notarydev/notary-platform`
- **Branch**: `main` — commits go straight to main (no PR flow)
- **Deploy**: `./infra/deploy-api.sh` — builds Docker, pushes to ECR `notary-api` (us-east-2), deploys to ECS `notary-dev-api` on cluster `notary-dev`
- **Live**: https://api.getnotary.ai (backend), https://api.getnotary.ai/app/ (frontend SPA)

## Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.12, FastAPI, uvicorn |
| Storage | In-memory (default), Postgres + S3 optional |
| Frontend SPA | Vanilla JS/HTML/CSS at `static/app/` (no build step) |
| Command Center | Separate SPA at `static/cc/` (served at `/cc`) |
| SDK | `packages/notary-sdk-py/` (local install) |
| Infra | Docker, ECR, ECS/Fargate, Terraform |

## Routes (FastAPI app)

| Route | Serves |
|-------|--------|
| `/` | Redirects to `/app/` |
| `/app/` | Platform SPA (main product UI) |
| `/cc/` | Command Center SPA (analytics overlay) |
| `/v1/*` | API routers |
| `/health` | Health check |

## API auth

- `NOTARY_API_AUTH_TOKEN` unset = auth disabled (local dev)
- When set, every `/v1/*` call needs `Authorization: Bearer <token>` or `x-api-key`

## Frontend architecture (`static/app/`)

- `index.html` — SPA shell, loads all scripts
- `app.js` — ~3500 lines, vanilla JS (no frameworks), SPA routing + all views
- `components.js` — shared UI components (cards, tables, drawers, code blocks)
- `styles.css` — full visual system (Chivo/IBM Plex Sans/JetBrains Mono fonts, dark theme)
- The SPA reads/writes `window.S` for state, calls `apiGet`/`apiPost` etc. for backend

## Key product objects

| Object | Description |
|--------|-------------|
| VerificationRecord | Sealed forensic evidence of an AI decision |
| ReplayRun | Deterministic cassette replay result |
| MutationTest | Fix verification — does the fix produce expected outcome? |
| Certificate (Proof of Mitigation) | Signed tamper-evident proof |
| Scenario | Reusable test case promoted from a verified incident |
| ReadinessPolicy | Set of scenarios that must pass before release |
| ReleaseGateResult | CI/CD gate decision (pass/fail) |

## Demo data

- `POST /v1/demo/catalog/seed` — seeds 21 VRs across lending, hiring, support scenarios
- `POST /v1/demo/harborline-release-gate/seed` — seeds the Harborline/Meridian golden path
- The golden path demo is Harborline Credit Union / Meridian Credit Union (lending scenario)
- Org ID `org:harborline-demo` is mapped to display name "Northstar Air" via `friendlyOrg()` in app.js

## Common tasks

```bash
make install    # set up venv + dependencies
make run        # start dev server on :8000
make test       # run pytest suite (153+ tests)
make lint       # ruff + mypy
make dev        # continuous test mode
./infra/deploy-api.sh   # build + push + deploy
```

## Agent expectations

1. **Never change the demo scenario from Harborline/Meridian** — that's what Emergent built and the user wants. The frontend calls `/v1/demo/harborline-release-gate/seed`.
2. **Frontend changes go in `static/app/`** — no build step, no framework, no npm. Pure HTML/CSS/JS.
3. **Two SPAs exist**: `/app` (main) and `/cc` (command center). The `/cc` is a separate React-ish build from `notary-viz` repo — don't touch it unless asked.
4. **Backend changes go in `src/notary_platform/`** — all routers under `api_server/routers/`.
5. **Commit directly to `main`** — the user doesn't use PRs. Always `git add -A && git commit -m "..." && git push`.
6. **Deploy via `./infra/deploy-api.sh`** — always run after committing.
7. **Test before commit** — `make test` must pass (known exception: `test_ui_vertical.py::test_release_gate_end_to_end` is pre-existing and broken).
8. **Don't touch Emergent config** — `.emergent/` directory is managed by Emergent platform, not by us.
9. **The root `/` redirects to `/app/`** — never change this. The old dashboard (Forensic Control Center) at `/` was removed.
10. **All 23 API endpoints the frontend calls have matching backend routes** — if you add a new frontend feature, add the backend route too.
11. **Keep `friendlyOrg()` logic** — it maps `harborline-demo` → "Northstar Air" for display. The backend still uses `org:harborline-demo` internally.
12. **The code snippet in app.js uses `pip install notary-sdk`** (PyPI) not `pip install -e packages/notary-sdk-py` — the Emergent preview has the PyPI version.
