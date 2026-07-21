# Migration Guide — Moving Notary to a New Machine / Editor

This document explains how to move the Notary project (the `notary-platform`
repo, and the companion `notary-sdk` repo) from one development machine or
editor to another. It covers what lives **in git**, what lives **in AWS**, and
what is **machine-local** and must be recreated.

> Audience: a developer who has been working on this project on one Mac and
> needs to continue on another (or in a fresh VS Code / editor install).

---

## 1. What is where

This is **not** a VS Code workspace — there is no `.code-workspace` file. VS
Code simply opens the repository folder. Two separate git repos are involved:

| Repo | Default local path | Purpose |
|------|-------------------|---------|
| `notary-platform` | `~/notary-platform` (or wherever cloned) | API server, replay engine, certificate signing, Terraform, Docker |
| `notary-sdk` | `~/notary-sdk` | Offline capture/seal SDK (separate repo, separate upstream) |

### Platform repo layout

- `src/notary_platform/` — all Python code (`api_server/`, `replay_engine/`,
  `certificates.py`, `storage.py`, `models.py`, `config.py`)
- `tests/` — pytest suite (60 tests)
- `infra/terraform/` — AWS infrastructure as code (vpc, ecr, ecs, rds, s3,
  kms, secrets, iam, cloudwatch)
- `Dockerfile`, `compose.yaml`, `Makefile`, `scripts/demo.sh` — build / run
- `packages/notary-sdk-ts/` — the TypeScript SDK package
- `.venv/` — local Python virtualenv (**gitignored**, machine-local)
- `.env` — **gitignored** local AWS wiring (do **not** copy between machines as-is)

### Machine-local tooling (NOT in the repo)

These were installed outside the project and must be reinstalled on the new
machine:

- `terraform` (v1.9.8 used during Phase 1)
- AWS CLI v2 (`aws`)
- Docker (Docker Desktop on macOS is a GUI install)
- Python 3.9+ (CI pins 3.9; AWS KMS/boto3 note: boto3 warns on 3.9 past
  April 2026 — 3.10+ recommended going forward)

### Cloud state (NOT on any machine)

All provisioned in AWS account **`447633181871`**, region **`us-east-2`**:

- S3 `notary-evidence-447633181871-dev` — versioned + Object Lock (COMPLIANCE)
- RDS `notary-dev-db` — PostgreSQL, **private subnet** (reachable only from ECS)
- KMS `alias/notary/signing` — symmetric `ENCRYPT_DECRYPT` key
- Secrets Manager: `notary-dev/database`, `notary-dev/sealing-keys`,
  `notary-dev/signing` (+ openai/anthropic)
- ECR `notary-api` (image pushed), `notary-replay-worker` (placeholder, Phase 2)
- ECS cluster `notary-dev`

None of this needs to be migrated — it is already in AWS. You only need
credentials and a correctly wired `.env` on the new machine.

---

## 2. What does NOT travel with the repo

| Artifact | Why | How to recreate |
|----------|-----|-----------------|
| `.venv/` | gitignored, machine-local | `python3 -m venv .venv && pip install -e ".[dev,cloud]"` |
| `.env` | gitignored, contains live wiring | derive from `.env.example` + Secrets Manager (see §4) |
| `terraform` / `aws` / `docker` | installed outside repo | package manager or manual download |
| AWS credentials | live IAM session / `~/.aws` | `aws configure` for `Opencode_Notary` user, region `us-east-2` |
| `.mypy_cache/`, `.ruff_cache/`, `.pytest_cache/` | gitignored build artifacts | regenerated automatically |

---

## 3. Step-by-step migration

### On the new machine

```bash
# 1. Clone both repos
git clone https://github.com/notarydev/notary-platform.git
git clone https://github.com/notarydev/notary-sdk.git
cd notary-platform

# 2. Python environment (3.9+; 3.10+ recommended)
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,cloud]"   # cloud extra = boto3 / sqlalchemy / psycopg2 for ECS

# 3. Tooling (not in the repo)
#    macOS (Homebrew):  brew install awscli terraform
#    or download manually, e.g. terraform + aws CLI as was done originally.
#    Docker: install Docker Desktop (GUI) — the headless install used during
#    Phase 1 was a one-off and does not survive reboots.

# 4. AWS credentials (Opencode_Notary IAM user, region us-east-2)
aws configure
#    AWS Access Key ID / Secret: from the IAM user
#    Default region: us-east-2
#    Ensure `aws sts get-caller-identity` returns account 447633181871

# 5. Runtime .env (gitignored) — pull real values from Secrets Manager:
aws secretsmanager get-secret-value --secret-id notary-dev/database --region us-east-2
aws secretsmanager get-secret-value --secret-id notary-dev/signing  --region us-east-2

#    .env should contain:
#    NOTARY_USE_REMOTE_STORAGE=1
#    NOTARY_DATABASE_URL=postgresql+psycopg2://<user>:<pass>@<host>:5432/notary_dev
#    NOTARY_EVIDENCE_BUCKET=notary-evidence-447633181871-dev
#    NOTARY_KMS_KEY_ARN=arn:aws:kms:us-east-2:447633181871:key/2cd36ab8-979c-409b-ab97-70a0a6b7073a
#    NOTARY_SIGNING_KEY_ID=platform-workability
#    NOTARY_API_AUTH_TOKEN=      # empty = auth disabled locally

# 6. Verify
pytest tests/                              # expect 60 passing
ruff check . && mypy src                  # clean
terraform -chdir=infra/terraform init
terraform -chdir=infra/terraform plan     # expect "No changes"
```

### Editor migration (VS Code or other)

This repo has **no** `.vscode/` folder committed (it is gitignored), so there
is nothing project-specific to copy. To replicate the setup in a new VS Code:

1. Install VS Code and open the `notary-platform` folder (`File → Open Folder`).
2. Recommended extensions: Python (`ms-python.python`), Ruff
   (`charliermarsh.ruff`), and (optional) Terraform (`hashicorp.terraform`),
   YAML, Docker.
3. Select the `.venv` interpreter: `Cmd+Shift+P → Python: Select Interpreter →
   ./notary-platform/.venv/bin/python`.
4. Your personal editor config (`settings.json`, keybindings, themes) lives in
   `~/Library/Application Support/Code/User/` on macOS — copy that directory if
   you want your editor preferences to follow you. That is independent of the
   project.

---

## 4. Runtime environment variables (`.env`)

The app reads these from the environment (or a `.env` file). Reference values
below reflect the provisioned `us-east-2` deployment.

| Variable | Purpose | Source |
|----------|---------|--------|
| `NOTARY_USE_REMOTE_STORAGE` | `1` to use Postgres + S3 (else in-memory) | set `1` for AWS |
| `NOTARY_DATABASE_URL` | SQLAlchemy URL for RDS | `notary-dev/database` secret |
| `NOTARY_EVIDENCE_BUCKET` | S3 evidence bucket | `notary-evidence-447633181871-dev` |
| `NOTARY_KMS_KEY_ARN` | KMS key for cert sealing | `notary-dev/signing` secret |
| `NOTARY_SIGNING_KEY_ID` | KMS key id | `notary-dev/signing` secret |
| `NOTARY_API_AUTH_TOKEN` | bearer/API-key; empty = auth off | set in non-prod |
| `NOTARY_DEFAULT_ORG_ID` | org scoping default | `demo-org` |

When `NOTARY_KMS_KEY_ARN` is unset, certificates fall back to an HMAC dev key
(loudly warned). Never hardcode secrets — always source from Secrets Manager or
environment variables.

---

## 5. Building and pushing the image (ECS)

Only `notary-api` is deployed in Phase 1 (replay is synchronous; the
`notary-replay-worker` ECR repo is a placeholder for Phase 2).

```bash
aws ecr get-login-password --region us-east-2 \
  | docker login --username AWS --password-stdin 447633181871.dkr.ecr.us-east-2.amazonaws.com

docker build --build-arg INSTALL_CLOUD=1 -t notary-api:latest -f Dockerfile .
docker tag notary-api:latest 447633181871.dkr.ecr.us-east-2.amazonaws.com/notary-api:latest
docker push 447633181871.dkr.ecr.us-east-2.amazonaws.com/notary-api:latest
```

The `Dockerfile` copies `README.md` (required by hatchling) and installs the
optional `cloud` extra via the `INSTALL_CLOUD` build-arg.

---

## 6. Known gotchas

- **RDS is private.** `notary-dev-db` is not publicly accessible; the app can
  only reach Postgres from inside the VPC (ECS). Local runs against remote
  storage will hang on DB connect — run in-VPC or use the in-memory store
  locally.
- **KMS key is symmetric.** `notary/signing` uses `ENCRYPT_DECRYPT`, so cert
  sealing uses `kms:Encrypt`/`Decrypt`, not asymmetric `Sign`/`Verify`.
- **`sealing-keys` secret is empty** (placeholder). Set a real worker sealing
  key before enabling live replay signing.
- **Region is `us-east-2`**, not `us-east-1` — the Terraform default was aligned
  to match the deployed infrastructure.
- **Do not commit `.env` or `.tfvars`.** Both are gitignored for a reason.
