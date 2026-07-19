# Notary Platform — Architecture, Systems, and Progress

Last updated: 2026-07-19 | Commit: `notary-platform@fb052c4` | Task def: `:30`

---

## Architecture

### North-star flow

```
Capture Source (SDK / API / Manual / Webhook / Batch / Trace)
→ Verification Record
→ AI Execution Events + Evidence Artifacts
→ Replayability Assessment
→ Human Label / Expected Outcome
→ Incident / Investigation
→ Replay Run
→ Fix Verification
→ Proof Bundle / Certificate
→ Scenario Candidate
→ Scenario Library
→ Scenario Run
→ Release Gate review
```

### Current state

| Stage | Status |
|---|---|
| Capture Source (Python SDK) | ✅ Built |
| Capture Source (API/Manual/Webhook) | ✅ Built |
| Capture Source (Batch/Trace) | 🟡 Planned |
| Verification Record | ✅ Built (in-memory) |
| AI Execution Events | ✅ 13 event kinds |
| Replayability Assessment | ✅ 8 states, real logic |
| Human Label | ✅ Model built (in-memory) |
| Incident/Investigation | ✅ Built (Postgres) |
| Replay Run | ✅ Cassette-backed |
| Fix Verification | ✅ Config fixes |
| Proof/Certificate | ✅ KMS-signed, JSON |
| Scenario/Release Gate | 🟡 Scaffold |

---

## Systems

### AWS Infrastructure

| System | Details | Status |
|---|---|---|
| VPC | `vpc-0569cfdf08af9a46b`, 2 public + 2 private subnets | ✅ Running |
| ECS/Fargate | Cluster `notary-dev`, service `notary-dev-api`, task def `:30` | ✅ Running |
| ALB | `notary-dev-alb`, HTTP 80 + HTTPS 443 listeners | ✅ Running |
| ACM Certificate | `api.getnotary.ai`, issued and validated | ✅ Active |
| Cloudflare DNS | CNAME `api.getnotary.ai` → ALB | ✅ Active |
| RDS (Postgres) | `notary-dev-db`, Postgres 16, db.t3.micro | ✅ Running |
| S3 Evidence Bucket | `notary-evidence-447633181871-dev`, Object Lock COMPLIANCE 365d | ✅ Running |
| KMS | Signing key `arn:aws:kms:...key/2cd36ab8...`, ENCRYPT_DECRYPT | ✅ Running |
| Secrets Manager | 5 secrets (database, signing, sealing-keys, openai, anthropic) | ✅ Running |
| ECR | `447633181871.dkr.ecr.us-east-2.amazonaws.com/notary-api` | ✅ Active |
| CloudWatch | `/aws/ecs/notary-dev`, 30d retention | ✅ Active |

### Repositories

| Repo | GitHub | Latest Commit |
|---|---|---|
| notary-platform | `notarydev/notary-platform` | `fb052c4` |
| notary-sdk | `notarydev/notary-sdk` | `56b0a78` |
| notary-viz | `notarydev/notary-viz` | `090e0a1` |
| GetNotary.ai | `notarydev/GetNotary.ai` | `ad9b232` |

### Deployed services

| Service | URL | Status |
|---|---|---|
| Notary Platform | `https://api.getnotary.ai/app` | ✅ Live |
| Command Center | `https://api.getnotary.ai/cc` | ✅ Live |
| API (HTTP) | `http://api.getnotary.ai` | ✅ Live |
| API (HTTPS) | `https://api.getnotary.ai` | ✅ Live |

### CI/CD

| Repo | CI |
|---|---|
| notary-platform | GitHub Actions: pytest (86), ruff, mypy — green |
| notary-viz | GitHub Actions: typecheck, build, vitest (5) — green |
| notary-sdk | GitHub Actions: pytest (54) — green |
| GetNotary.ai | No CI |

---

## Progress

### What works

- **Proof loop:** SDK capture → ingest → cassette replay → fix verification → KMS certificate → signature verify. 86 tests pass.
- **Postgres persistence:** Incidents stored in RDS. Survives restarts.
- **Stable ingress:** ALB with HTTP 80 + HTTPS 443. Domain `api.getnotary.ai`.
- **Verification Records:** Canonical intake with 13 event kinds, 8 replayability states, manual/webhook intake, label creation, promote-to-incident.
- **Notary Platform SPA:** Compliance-first nav (Home, Setup, V.R.s, Incidents, Proofs), live incident actions (Replay, Verify Fix, Issue Proof).
- **Command Center:** System atlas with 6 lenses, draggable nodes, section headers, platform guide overlay.
- **Demo org:** Acme Assurance Demo, 4 agents, 7 systems, 2 policies, seeded at startup.
- **Demo incidents:** 3 seeded via POST /v1/platform/seed-demo (1 certified + 2 ingested).

### What is blocked / broken

| Issue | Impact | Fix |
|---|---|---|
| PDF export 500 | reportlab not in deployed image | Verify `INSTALL_CLOUD=1` includes reportlab |
| Non-lending seed replay broken | Only lending-denial seed creates snapshots | Fix seed-demo to persist snapshots for all scenarios |
| V.R. store in-memory | Resets on deploy | Migrate `_vr_store` to Postgres |
| `/v1` public | No auth on API endpoints | Set `NOTARY_API_AUTH_TOKEN` in task def or build WO-66 |
| Symmetric KMS | Certs not independently verifiable | Switch to RSA SIGN_VERIFY key (Terraform code in `infra/terraform/kms.tf`) |

### What should be built next

1. **WO-66** — stored API/SDK keys + org scoping + audit events
2. **WO-64 completion** — migrate V.R. + HumanLabel stores to Postgres
3. **WO-52/53** — product-grade investigation with visual proof-loop flow
4. **PDF fix** — verify reportlab in Docker image
5. **Auth** — enable `NOTARY_API_AUTH_TOKEN` for design partner deployments

---

## Notary AI

Parked in backlog. Will be built after durable state exists for Verification Records, incidents, labels, proofs, scenarios, users, API keys, and audit. When built, it will guide users through onboarding, explain replay/proof/status, and suggest next actions — but will not give legal advice, decide outcomes, or mutate product state.

---

## Deploy instructions

```bash
# Build (from notary-platform root)
TAG="build-$(date +%Y%m%d-%H%M%S)-amd64"
REPO="447633181871.dkr.ecr.us-east-2.amazonaws.com/notary-api"
docker buildx build --platform linux/amd64 --build-arg INSTALL_CLOUD=1 -t "$REPO:$TAG" --push .

# Register task def and update service
aws ecs register-task-definition --cli-input-json file://taskdef.json
aws ecs update-service --cluster notary-dev --service notary-dev-api \
  --task-definition "notary-dev-api:$REV" \
  --load-balancers "targetGroupArn=$TG,containerName=api,containerPort=8000" \
  --force-new-deployment
```

## Test commands

```bash
pytest -q          # 86 passed
ruff check .       # All clean
mypy src           # Success (26 files)
```

## Smoke test URLs

```
http://api.getnotary.ai/health
http://api.getnotary.ai/app/
http://api.getnotary.ai/cc/
http://api.getnotary.ai/v1/verification-records
http://api.getnotary.ai/v1/incidents
http://api.getnotary.ai/v1/topology
http://api.getnotary.ai/v1/live-status
```
