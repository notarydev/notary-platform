# Notary Platform

Backend for the Notary forensic proof loop: **SDK capture/seal → platform ingest/verify →
immutable evidence storage → cassette replay → mutation/fix verification → signed Proof of
Mitigation certificate → dashboard demo.**

This is the **Phase 1** prototype: a working AWS-backed end-to-end proof loop in a single
dev/test account. Phase 2 features (Scenario Library, Testing Playground, Proof of Readiness,
Evidence Export) are intentionally out of scope for this milestone.

## Repository layout

```
notary-platform/
  src/notary_platform/
    api_server/        FastAPI app + routers (ingestion, incidents, certificates, dashboard)
    replay_engine/     cassette replay + mutation verification
    storage.py         storage backend (in-memory default; Postgres + S3 when configured)
    certificates.py    Proof of Mitigation signing (KMS in prod, dev key locally)
    snapshot.py        SDK-compatible snapshot + verification
    models.py          Incident / custody-event models
    config.py          environment-based configuration (no hardcoded secrets)
    demo_scenarios.py  synthetic demo scenarios (lending, prior-auth, hiring, support)
  tests/               pytest suite (ingestion, replay, certificates, dashboard, auth)
  infra/terraform/     AWS baseline (VPC, ECR, ECS, RDS, S3 Object Lock, KMS, Secrets)
  Dockerfile           container image for ECS/Fargate
  compose.yaml         local dev (api + postgres + optional localstack)
  Makefile             install / test / lint / run / docker-build / demo
  scripts/demo.sh      seed a demo scenario against a running server
```

## Quick start (local, zero cloud)

```bash
make install          # create .venv and install -e ".[dev]"
make test             # run the test suite
make run              # start the API at http://localhost:8000
# in another terminal:
make demo SCENARIO_ID=lending-denial
# open: http://localhost:8000/dashboard?scenario_id=lending-denial
```

`make demo` starts the server, seeds a sealed demo incident, and prints the dashboard URL.
From the dashboard you can **Replay failure → Apply scenario fix → Issue certificate →
Verify signature**.

### End-to-end API flow (no UI)

```bash
# 1. seed a demo incident (builds a sealed snapshot)
curl -X POST "http://localhost:8000/v1/demo/lending-seed?scenario_id=lending-denial"

# 2. list incidents
curl "http://localhost:8000/v1/incidents"

# 3. replay from sealed cassette
curl -X POST "http://localhost:8000/v1/incidents/<id>/replay"

# 4. run the scenario fix as a mutation test
curl -X POST "http://localhost:8000/v1/incidents/<id>/mutation-tests" \
  -H 'Content-Type: application/json' \
  -d '{"fix_config":{"threshold":620},"expected_correct_behavior":"APPROVE"}'

# 5. issue the signed Proof of Mitigation certificate
curl -X POST "http://localhost:8000/v1/incidents/<id>/certificates"

# 6. verify the signature
curl "http://localhost:8000/v1/incidents/<id>/certificates/pom-cert-v1/verify"
```

## API surface (Phase 1)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/v1/incidents/ingest` | accept a sealed SDK snapshot, verify, persist, record custody |
| GET | `/v1/incidents` | list incidents (org-scoped) |
| GET | `/v1/incidents/{id}` | incident detail + custody chain |
| GET | `/v1/incidents/{id}/snapshot` | raw ingested snapshot |
| POST | `/v1/incidents/{id}/replay` | cassette replay (reproduce the decision) |
| GET | `/v1/incidents/{id}/replay` | replay result |
| POST | `/v1/incidents/{id}/mutation-tests` | apply fix, compare to expected behavior |
| GET | `/v1/incidents/{id}/mutation-tests` | mutation result |
| POST | `/v1/incidents/{id}/certificates` | issue signed PoM certificate (requires `mitigated`) |
| GET | `/v1/incidents/{id}/certificates/{cid}` | certificate JSON |
| GET | `/v1/incidents/{id}/certificates/{cid}/download` | certificate download |
| GET | `/v1/incidents/{id}/certificates/{cid}/verify` | signature verification |
| GET/POST | `/dashboard`, `/v1/demo/lending-seed` | Forensic Control Center UI + seeding |

## Authentication & org scoping

Phase 1 uses a **static bearer-token / API-key** model (set `NOTARY_API_AUTH_TOKEN`).
When unset, auth is disabled so local demos and tests run with no credentials. When set,
every `/v1/incidents*` endpoint requires the token (`Authorization: Bearer …`,
`x-api-key`, or `?api_key=`) and an `X-Notary-Org` header scopes reads/writes to the
acting org (cross-org access returns 404). Production deployments **must** set the token
via AWS Secrets Manager — never commit it.

## Configuration / environment variables

See `.env.example`. All secrets come from the environment or AWS Secrets Manager — none are
hardcoded.

| Variable | Purpose | Default |
|----------|---------|---------|
| `NOTARY_API_AUTH_TOKEN` | bearer/API key; empty = auth disabled | `""` |
| `NOTARY_DEFAULT_ORG_ID` | fallback org id | `demo-org` |
| `NOTARY_USE_REMOTE_STORAGE` | enable Postgres + S3 persistence | `""` (in-memory) |
| `NOTARY_DATABASE_URL` | Postgres connection string (required if remote) | `""` |
| `NOTARY_EVIDENCE_BUCKET` | S3 evidence bucket (required if remote) | `""` |
| `NOTARY_EVIDENCE_PREFIX` | S3 key prefix | `evidence/` |
| `NOTARY_KMS_KEY_ARN` | KMS key for cert signing (prod) | `""` |
| `NOTARY_DEV_SIGNING_KEY` | dev HMAC signing key (local only) | ephemeral default |
| `NOTARY_SIGNING_KEY_ID` | signing key reference | `""` |

## AWS deployment (Phase 1)

Infrastructure-as-code lives in `infra/terraform/` (region `us-east-1`, single account).
See `infra/terraform/README.md` for the full sequence. Summary:

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars   # fill db_password + sealing_key_secret from your env/secret store
terraform init
terraform plan
terraform apply
```

Provisioned: VPC + subnets, ECR repos, ECS/Fargate cluster + API service, RDS PostgreSQL
(encrypted), S3 evidence bucket with **versioning + Object Lock (COMPLIANCE)** and a
**deny-delete** bucket policy, KMS key for signing/custody, Secrets Manager secrets,
IAM roles, CloudWatch log group. Replay is **synchronous** for Phase 1 (no SQS worker);
the code documents the seam for an async worker.

## Known limitations

- **Signing**: local/dev uses an HMAC key (`NOTARY_DEV_SIGNING_KEY`); production must set
  `NOTARY_KMS_KEY_ARN`. The demo certificate is **not** a general AI-safety certificate —
  it proves the fix resolved *this tested scenario*.
- **Persistence**: in-memory by default (great for demos/tests); set
  `NOTARY_USE_REMOTE_STORAGE` for Postgres + S3.
- **Replay**: cassette-first; requires no live Stripe/GitHub/Salesforce. Missing cassette
  entries return `escalation_required` rather than pretending success.
- **Production systems**: capture sources only — the platform never replays or mutates
  against production.
- **Dashboard**: a forensic proof UI, not observability/APM (no latency graphs, alerts, traces).
- **Phase 2** (Scenario Library, Testing Playground, Proof of Readiness, Evidence Export)
  is not implemented in this milestone.

## Testing

```bash
make test     # 60 tests: ingestion integrity, cassette replay, mutation + cert, dashboard, auth/org scoping
make lint     # ruff + mypy
```
