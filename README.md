# Notary Platform

Backend for the Notary forensic proof loop: **SDK capture/seal → platform ingest/verify →
immutable evidence storage → cassette replay → mutation/fix verification → signed Proof of
Mitigation certificate → Scenario Library → Readiness Policy → Release Gate →
dashboard demo.**

This repository implements the **WO-28 vertical slice** in addition to the original Phase 1
proof loop. The new product objects are durable, service-backed, and exposed through the
API/UI:

- `EvidenceArtifact` — signed files, SDK snapshots, and chain-of-custody evidence
- `ReplayRun` — deterministic cassette replay
- `MutationTest` — fix verification and boundary analysis
- `KnownLimitation` — scoped limitations with signatures
- `ProofClaim` / `ProofCertificate` (Proof of Mitigation)
- `Scenario` / `ScenarioRun` — reusable, versioned test cases
- `ReadinessPolicy` / `ReadinessCheck` — scenario-based release criteria
- `ReleaseGateResult` — machine-readable CI/CD gate decision
- `ActionEligibility` — server-side reasons for why actions are enabled/disabled

## Repository layout

```
notary-platform/
  src/notary_platform/
    api_server/        FastAPI app + routers
                       (ingestion, incidents, verification records, certificates,
                        release gate / scenarios / readiness)
    replay_engine/     cassette replay + mutation verification
    services/          service layer for the product domain (storage-agnostic)
    storage.py         storage backend (in-memory default; Postgres + S3 when configured)
    certificates.py    Proof of Mitigation signing (KMS in prod, dev key locally)
    snapshot.py        SDK-compatible snapshot + verification
    models.py          all product objects (Phase 1 + WO-28)
    config.py          environment-based configuration (no hardcoded secrets)
    demo_catalog.py    21 synthetic demo cases spanning lending, hiring, support, prior-auth
  tests/               pytest suite (99 tests passing)
  static/app/          Forensic Control Center SPA (HTML/JS/CSS)
  packages/            local client packages (notary-sdk-py)
  infra/terraform/     AWS baseline (VPC, ECR, ECS, RDS, S3 Object Lock, KMS, Secrets)
  Dockerfile           container image for ECS/Fargate
  compose.yaml         local dev (api + postgres + optional localstack)
  Makefile             install / test / lint / run / docker-build / demo
  scripts/             demo scripts
```

## Quick start (local, zero cloud)

```bash
make install          # create .venv and install -e ".[dev]"
make test             # run the test suite
make run              # start the API at http://localhost:8000
# open the dashboard:
# http://localhost:8000/app/
```

From the dashboard you can walk through the full product loop:
**Ingest evidence → Replay → Mutation/fix → Issue proof → Promote to Scenario →
Run scenario → Create readiness policy → Run readiness check → Release gate.**

### One-command golden path

```bash
make run
# in another terminal:
python - <<'PY'
import subprocess, json, time
server = subprocess.Popen(["make", "run"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
time.sleep(3)
base = "http://localhost:8000/v1"

# seed the catalog
subprocess.run(["curl", "-s", "-X", "POST", f"{base}/demo/catalog/seed"])

# 1. find a replayable verification record
vrs = json.loads(subprocess.run(["curl", "-s", f"{base}/verification-records?replayability=replayable"], capture_output=True, text=True).stdout)
vr = vrs[0]

# 2. replay it
subprocess.run(["curl", "-s", "-X", "POST", f"{base}/verification-records/{vr['id']}/replay-runs"])

# 3. mutation test with a fix
subprocess.run(["curl", "-s", "-X", "POST", f"{base}/verification-records/{vr['id']}/mutation-tests",
  "-H", "Content-Type: application/json",
  "-d", json.dumps({"fix_config": {"threshold": 620}, "expected_correct_behavior": "APPROVE"})])

# 4. issue proof of mitigation
subprocess.run(["curl", "-s", "-X", "POST", f"{base}/verification-records/{vr['id']}/proof-of-mitigation"])

# 5. promote to a reusable scenario
subprocess.run(["curl", "-s", "-X", "POST", f"{base}/scenarios?vr_id={vr['id']}"])

# 6. run the scenario
subprocess.run(["curl", "-s", "-X", "POST", f"{base}/scenario-runs",
  "-H", "Content-Type: application/json",
  "-d", json.dumps({"scenario_ids": [f"sc-from-{vr['id']}"], "agent_version": "1.2.0"})])

server.terminate()
PY
```

## End-to-end API flow

```bash
# 0. seed the catalog
 curl -X POST "http://localhost:8000/v1/demo/catalog/seed"

# 1. list verification records (the durable forensic object)
curl "http://localhost:8000/v1/verification-records"

# 2. replay from cassette
curl -X POST "http://localhost:8000/v1/verification-records/<id>/replay-runs"

# 3. run the scenario fix as a mutation test
curl -X POST "http://localhost:8000/v1/verification-records/<id>/mutation-tests" \
  -H 'Content-Type: application/json' \
  -d '{"fix_config":{"threshold":620},"expected_correct_behavior":"APPROVE"}'

# 4. issue a signed Proof of Mitigation certificate
curl -X POST "http://localhost:8000/v1/verification-records/<id>/proof-of-mitigation"

# 5. verify the certificate signature
curl "http://localhost:8000/v1/certificates/<cert-id>/verify"

# 6. promote the verified record to a reusable scenario
curl -X POST "http://localhost:8000/v1/scenarios?vr_id=<id>"

# 7. run the scenario against an agent version
curl -X POST "http://localhost:8000/v1/scenario-runs" \
  -H 'Content-Type: application/json' \
  -d '{"scenario_ids":["<sc-id>"],"agent_version":"1.2.0"}'

# 8. create a readiness policy
curl -X POST "http://localhost:8000/v1/readiness-policies" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Lending Gate","required_scenario_ids":["<sc-id>"]}'

# 9. run a readiness check
curl -X POST "http://localhost:8000/v1/readiness-checks" \
  -H 'Content-Type: application/json' \
  -d '{"policy_id":"<policy-id>","agent_version":"1.2.0"}'

# 10. release gate
curl -X POST "http://localhost:8000/v1/release-gate/checks" \
  -H 'Content-Type: application/json' \
  -d '{"policy_id":"<policy-id>","agent_version":"1.2.0"}'
```

## API surface

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/v1/incidents/ingest` | accept a sealed SDK snapshot, verify, persist, record custody |
| GET | `/v1/incidents` | list incidents (org-scoped) |
| GET | `/v1/incidents/{id}` | incident detail + custody chain |
| GET | `/v1/incidents/{id}/snapshot` | raw ingested snapshot |
| POST | `/v1/incidents/{id}/replay` | cassette replay (legacy path) |
| POST | `/v1/incidents/{id}/mutation-tests` | legacy mutation test path |
| POST | `/v1/incidents/{id}/certificates` | legacy certificate path |
| GET | `/v1/verification-records` | list verification records (with filters) |
| GET | `/v1/verification-records/{id}` | verification record detail |
| POST | `/v1/verification-records/{id}/replay-runs` | run a deterministic replay |
| POST | `/v1/verification-records/{id}/mutation-tests` | apply fix, compare to expected behavior |
| POST | `/v1/verification-records/{id}/proof-of-mitigation` | issue signed PoM certificate |
| GET | `/v1/certificates/{id}` | certificate JSON |
| GET | `/v1/certificates/{id}/verify` | signature verification |
| POST | `/v1/scenarios` | promote a VR to a reusable scenario |
| GET | `/v1/scenarios` | list scenarios |
| GET | `/v1/scenarios/{id}` | scenario detail |
| PATCH | `/v1/scenarios/{id}` | activate/retire a scenario |
| POST | `/v1/scenario-runs` | run scenarios against an agent version |
| GET | `/v1/scenario-runs/{id}` | run result |
| POST | `/v1/readiness-policies` | create readiness policy |
| GET | `/v1/readiness-policies` | list policies |
| PATCH | `/v1/readiness-policies/{id}` | enable/disable policy |
| POST | `/v1/readiness-checks` | run readiness check |
| GET | `/v1/readiness-checks/{id}` | check result |
| POST | `/v1/release-gate/checks` | run release gate |
| GET | `/v1/release-gate/checks/{id}` | gate result |
| GET | `/v1/eligibility` | server-side action eligibility + reasons |
| POST | `/v1/demo/catalog/seed` | seed 21 demo verification records |

## UI

The dashboard is a single-page application served at `/app/`:

- **Verification Records** — browse, replay, label, verify fix, issue proof
- **Scenarios** — scenario library, candidates, runs
- **Readiness** — policies, checks, release gate results
- **Governance** — label queue, audit, chain of custody
- **SDK** — install instructions for the local Python SDK package

The UI only shows actions the server reports as eligible, and disabled actions display the
server-provided reason.

## Authentication & org scoping

Phase 1 uses a **static bearer-token / API-key** model (set `NOTARY_API_AUTH_TOKEN`).
When unset, auth is disabled so local demos and tests run with no credentials. When set,
every `/v1/*` endpoint requires the token (`Authorization: Bearer …`, `x-api-key`, or
`?api_key=`) and an `X-Notary-Org` header scopes reads/writes to the acting org (cross-org
access returns 404). Production deployments **must** set the token via AWS Secrets Manager
— never commit it.

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

## SDK package

A minimal Python SDK client lives in `packages/notary-sdk-py/` and is installed locally via:

```bash
pip install -e ./packages/notary-sdk-py
```

The UI shows this install command because the package is not published to PyPI yet.

## AWS deployment

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
IAM roles, CloudWatch log group. Replay is **synchronous** for now (no SQS worker); the
code documents the seam for an async worker.

## Testing

```bash
make test     # pytest suite: ingestion, replay, certificates, golden path, replay runner contract, auth, release gate
make lint     # ruff + mypy
```

## Known limitations

- **Signing**: local/dev uses HMAC-SHA256 (`NOTARY_DEV_SIGNING_KEY`); production uses KMS
  ENCRYPT_DECRYPT (symmetric, server-verifiable only). Neither mode is a public-key
  independent signature. Certificates are tamper-evident but not independently verifiable
  by third parties without access to the same KMS key or dev key.
- **Replay**: cassette-first; demo records replay via the built-in `DemoReplayRunner`.
  Non-demo customer records require a configured `ReplayRunner` — without one, replay
  returns `unsupported_runner`. The ServiceRegistry accepts a custom ReplayRunner
  implementation.
- **Persistence**: in-memory by default (great for demos/tests); set
  `NOTARY_USE_REMOTE_STORAGE` for Postgres + S3.
- **Dashboard**: a forensic proof UI, not observability/APM (no latency graphs, alerts, traces).
- **Demo data**: demo records from `demo_catalog.py` are marked `is_demo=True` and their
  replayability may be demo-forced for storytelling. Computed replayability is always
  stored separately in `computed_replayability`. Proof and release gate decisions use
  actual ReplayRun/MutationTest/ScenarioRun results, not demo-forced state.
- **Release Gate**: covers only scenarios in the readiness policy. Does not certify
  general AI safety or behavior outside tested conditions.
- **Postgres/S3 stores**: the service layer is storage-agnostic, but the Postgres/S3 storage
  methods for product objects are intentionally minimal; the in-memory store is the
  fully exercised path for demos and tests.
