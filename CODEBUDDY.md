# Notary Platform

Forensic proof-of-mitigation platform. Root cause analysis for AI decision failures, sealed as tamper-evident evidence, replayed deterministically, fixed via mutation testing, certified with signed Proof of Mitigation, and promoted to release-gate readiness checks.

## Repo

- **GitHub**: `github.com/notarydev/notary-platform`
- **Deploy**: `./infra/deploy-api.sh` — builds Docker, pushes to ECR, deploys to ECS
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

## Routes

| Route | Serves |
|-------|--------|
| `/` | Redirects to `/app/` |
| `/app/` | Platform SPA (main product UI) |
| `/cc/` | Command Center SPA (analytics overlay) |
| `/v1/*` | API routers |
| `/health` | Health check |

## API

- `NOTARY_API_AUTH_TOKEN` unset = auth disabled (local dev). When set, every `/v1/*` call needs `Authorization: Bearer <token>` or `x-api-key`.

## Frontend architecture

`static/app/` is a vanilla JS SPA: `index.html` (shell), `app.js` (~3600 lines, all views + routing), `components.js` (shared components), `styles.css` (full visual system). No build step, no frameworks, no npm.

## Key product objects

| Object | Description |
|--------|-------------|
| VerificationRecord | Sealed forensic evidence of an AI decision |
| ReplayRun | Deterministic cassette replay result |
| MutationTest | Fix verification |
| Certificate (Proof of Mitigation) | Signed tamper-evident proof |
| Scenario | Reusable test case promoted from a verified incident |
| ReadinessPolicy | Set of scenarios that must pass before release |
| ReleaseGateResult | CI/CD gate decision |

## Demo data

- `POST /v1/demo/catalog/seed` — seeds 21 VRs across lending, hiring, support scenarios
- `POST /v1/demo/harborline-release-gate/seed` — seeds the golden path demo
- Org ID `org:harborline-demo` is displayed as "Northstar Air" in the UI

## Git workflow (external agents)

All changes must go through branches and pull requests — never commit directly to `main`.

### Branch naming

```
<source>/<description>
```

| Source | Description |
|--------|-------------|
| `emergent/` | Changes from the Emergent platform |
| `opencode/` | Changes from the OpenCode CLI agent |
| `manual/` | Changes made directly by a developer |

Examples: `emergent/fix-env-select`, `opencode/cleanup-docs`, `manual/update-readme`

### Process

1. `git checkout -b <source>/<description> main` — create a branch from main
2. Make changes, test locally (`make test`, `make lint`)
3. `git add -A && git commit -m "scope: message"`
4. `git push -u origin <branch>` — push the branch
5. Create a pull request on GitHub (title matches commit message)
6. Request review from the repo owner
7. Once approved, merge to `main`
8. Deploy: `./infra/deploy-api.sh`

### After deploy

Verify:
```bash
curl -s https://api.getnotary.ai/health
curl -s https://api.getnotary.ai/app/index.html | grep "env-select"
```

## Common tasks

```bash
make install    # set up venv + dependencies
make run        # start dev server on :8000
make test       # run pytest suite
make lint       # ruff + mypy
./infra/deploy-api.sh   # build + push + deploy
```
