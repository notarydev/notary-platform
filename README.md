# Notary Platform

Forensic proof-of-mitigation platform: **SDK capture/seal → platform ingest → cassette replay → mutation/fix verification → signed Proof of Mitigation → Scenario Library → Readiness Policy → Release Gate.**

## Quick start

```bash
make install    # create .venv and install -e ".[dev]"
make run        # start API at http://localhost:8000
```

Open http://localhost:8000/app/ to walk the full product loop.

## Walkthrough

1. Seed demo data: `POST /v1/demo/catalog/seed`
2. Browse verification records at `/app/?view=verification-records`
3. Replay a record, run a mutation test (fix), issue a proof
4. Promote to scenario, create a readiness policy, run a release gate

## Repository layout

```
src/notary_platform/
  api_server/      FastAPI app + routers
  replay_engine/   cassette replay + mutation verification
  services/        service layer (storage-agnostic)
  storage.py       storage backend (in-memory default; Postgres + S3)
  certificates.py  Proof of Mitigation signing
  models.py        all product objects
  config.py        environment configuration
  demo_catalog.py  synthetic demo cases
  demo_scenarios.py  scenario definitions
static/
  app/             Platform SPA (HTML/JS/CSS) — served at /app
  cc/              Command Center SPA — served at /cc
packages/
  notary-sdk-py/   Python SDK client
infra/
  terraform/       AWS infrastructure (VPC, ECR, ECS, RDS, S3, KMS)
  deploy-api.sh    Docker build + ECR push + ECS deploy
tests/             pytest suite
```

## UI

| Route | SPA | Purpose |
|-------|-----|---------|
| `/app/` | Platform SPA | Main product UI — VRs, Scenarios, Readiness, Release Gate, SDK setup |
| `/cc/` | Command Center | Viz/analytics overlay |
| `/` | — | Redirects to `/app/` |

## Key API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/v1/incidents/ingest` | Accept sealed SDK snapshot, verify, persist |
| GET | `/v1/incidents` | List incidents |
| POST | `/v1/demo/harborline-release-gate/seed` | Seed Harborline/Meridian demo scenario |
| POST | `/v1/demo/catalog/seed` | Seed 21 demo verification records |
| GET | `/v1/verification-records` | List VRs (with filters) |
| POST | `/v1/verification-records/{id}/replay-runs` | Run replay |
| POST | `/v1/verification-records/{id}/mutation-tests` | Run fix verification |
| POST | `/v1/verification-records/{id}/proof-of-mitigation` | Issue signed PoM |
| POST | `/v1/scenarios` | Promote VR → scenario |
| POST | `/v1/scenario-runs` | Run scenarios against agent version |
| POST | `/v1/readiness-policies` | Create readiness policy |
| POST | `/v1/readiness-checks` | Run readiness check |
| POST | `/v1/release-gate/checks` | Run release gate |
| GET | `/v1/platform/home` | Platform home/org data |
| GET | `/v1/platform/org` | Current organization |
| GET | `/v1/platform/keys` | List API keys |
| GET | `/v1/setup/status` | Setup status |
| GET | `/v1/health` | Health check |

Full API surface is available via the OpenAPI docs at http://localhost:8000/docs.

## Authentication

Set `NOTARY_API_AUTH_TOKEN` for bearer-token auth. Unset = auth disabled (local demos/tests).

## SDK

```bash
pip install -e ./packages/notary-sdk-py
```

The platform SPA shows this install command.

## Deployment

```bash
./infra/deploy-api.sh    # builds Docker image, pushes to ECR, deploys to ECS
```

## Testing

```bash
make test     # pytest suite
make lint     # ruff + mypy
```

## Configuration

See `.env.example`. All secrets come from environment or AWS Secrets Manager.

| Variable | Purpose |
|----------|---------|
| `NOTARY_API_AUTH_TOKEN` | Bearer/API key for auth |
| `NOTARY_USE_REMOTE_STORAGE` | Enable Postgres + S3 persistence |
| `NOTARY_DATABASE_URL` | Postgres connection string |
| `NOTARY_EVIDENCE_BUCKET` | S3 evidence bucket |
| `NOTARY_KMS_KEY_ARN` | KMS key for production certificate signing |
