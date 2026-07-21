> Status: Partially out of date. See README.md for current test count, auth status, and release gate status.

# notary-platform — AI Decision Assurance Backend + Platform SPA

**GitHub:** `notarydev/notary-platform`

## What this is

The central Notary Platform repo. Contains the FastAPI backend (ingestion, replay, mutation, certification, topology, verification records), the Notary Platform customer-facing SPA at `/app`, and the embedded Command Center SPA at `/cc`.

## Architecture

```
Capture Source (SDK/API/Manual/Webhook)
→ Verification Record (canonical intake)
→ Replayability Assessment (8 states)
→ Replay Run
→ Mutation Test (fix verification)
→ Proof of Mitigation (signed certificate)
→ Scenario / Scenario Run
→ Readiness Policy / Readiness Check
→ Release Gate
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
| Service layer | `src/notary_platform/services/services.py` |
| Notary Platform SPA | `static/app/index.html` (single-file SPA) |
| Command Center (embedded) | `static/cc/` (built from notary-viz) |
| Terraform/AWS | `infra/terraform/*.tf` |
| Docker | `Dockerfile` |

## Build/Run

```bash
# Install
make install

# Test (see README for current count)
make test
make lint
```

## Current state

- Proof loop works (capture→ingest→replay→fix→certify→verify)
- Release Gate path works (scenario → readiness policy → readiness check → gate)
- Full golden path works for both demo and non-demo SDK/API records
- ReplayRunner abstraction separates demo runner from customer contract
- Auth is enforced when NOTARY_API_AUTH_TOKEN is set
