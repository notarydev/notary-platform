# notary-platform — AI Decision Assurance Backend + Platform SPA

**GitHub:** `notarydev/notary-platform` | **Latest:** `9ba9196` | **Branch:** `main`

## What this is

The central Notary Platform repo. Contains the FastAPI backend (ingestion, replay, mutation, certification, topology, verification records), the Notary Platform customer-facing SPA at `/app`, and the embedded Command Center SPA at `/cc`.

## Architecture

```
Capture Source (SDK/API/Manual/Webhook)
→ Verification Record (canonical intake)
→ Replayability Assessment (8 states)
→ Incident / Investigation (Postgres-backed)
→ Replay / Fix Verification (cassette-backed)
→ Proof / Certificate (KMS-signed)
→ Scenario / Release Gate (planned)
```

## Key files

| Area | Files |
|---|---|
| API server | `src/notary_platform/api_server/main.py`, `routers/*.py` |
| Models | `src/notary_platform/models.py` |
| Storage (in-memory + Postgres/S3) | `src/notary_platform/storage.py` |
| Verification Records | `src/notary_platform/api_server/routers/verification.py` |
| Platform data/seed | `src/notary_platform/platform_data.py` |
| Certificates | `src/notary_platform/certificates.py` |
| SDK snapshot/verify | `src/notary_platform/snapshot.py` |
| Demo scenarios | `src/notary_platform/demo_scenarios.py` |
| Notary Platform SPA | `static/app/index.html` (single-file SPA) |
| Command Center (embedded) | `static/cc/` (built from notary-viz) |
| Terraform/AWS | `infra/terraform/*.tf` |
| Docker | `Dockerfile` |
| Docs | `docs/notary-platform-architecture-systems-progress.md` |

## Build/Run

```bash
# Install
pip install -e ".[dev]"
pip install -e ".[cloud]"  # for Postgres/S3/KMS

# Test
pytest -q                    # 86 tests
ruff check .                 # lint
mypy src                     # typecheck

# Run locally
uvicorn notary_platform.api_server.main:app --host 0.0.0.0 --port 8001

# Docker build
docker buildx build --platform linux/amd64 --build-arg INSTALL_CLOUD=1 -t REPO:TAG .
```

## Deploy

- AWS ECS/Fargate: `notary-dev-api` service, cluster `notary-dev`
- Postgres: `notary-dev-db.cnoy4iaqgnpz.us-east-2.rds.amazonaws.com`
- ALB: `notary-dev-alb-216871116.us-east-2.elb.amazonaws.com`
- Domain: `api.getnotary.ai` (HTTP + HTTPS)

## Current state

- 86 tests passing, CI green
- Proof loop works (capture→ingest→replay→fix→certify→verify)
- Postgres persistence for incidents, in-memory for V.R.s and labels
- ALB/HTTPS deployed, Stable domain
- `/app` and `/cc` served from same origin
- Auth still public on `/v1`
