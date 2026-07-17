# Notary Platform — Terraform Infrastructure (AWS)

This directory manages the infrastructure for the Notary Platform in a single
AWS account using Terraform. Local development uses `compose.yaml` at the repo
root instead.

- **AWS account:** `447633181871`
- **Region:** `us-east-2`
- **Application tag (`awsApplication`):**
  `arn:aws:resource-groups:us-east-2:447633181871:group/Notary/072xw6nolrnxzw18spteuir5vt`
  is applied to all resources via provider `default_tags`.

State is kept **local** for now — no S3 backend is configured yet.

## What it provisions

- **VPC** (`10.0.0.0/16`) with public + private subnets across 2 AZs, IGW, NAT GW.
- **ECR** repos: `notary-api` (used now) and `notary-replay-worker` (future).
- **ECS** Fargate cluster + API service (port 8000, cpu 512 / mem 1024).
- **RDS** PostgreSQL 16 in private subnets (encrypted, password from variable).
- **S3** evidence bucket with **immutability**: versioning + Object Lock
  (COMPLIANCE, 365 days) + a bucket policy that **denies all delete operations**.
- **KMS** signing/custody key (rotation on, alias `notary/signing`).
- **Secrets Manager** secrets for DB creds, sealing keys, KMS config, and
  OpenAI / Anthropic test API keys (empty placeholders by default).
- **IAM** roles for ECS execution and the API task (scoped to created resources).
- **CloudWatch** log group `/aws/ecs/notary-dev` (30-day retention).

### Phase 1 notes

- **Replay is synchronous** — there is no SQS worker or replay-worker deployment
  yet. An optional commented SQS block exists in `ecs.tf` for Phase 2.
- The S3 Object Lock configuration + deny-delete bucket policy **enforce WORM
  immutability** of evidence, satisfying the custody guarantee.

## Required tools

- `terraform` >= 1.5
- AWS CLI configured with credentials for the target account
- An ECR image pushed for `notary-api` (the `api_image` variable)

## AWS credentials

Never commit credentials. Configure the local shell with **one** of:

```bash
export AWS_PROFILE=notary-dev
# or
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_REGION=us-east-2
```

Verify you are in the right account before applying:

```bash
aws sts get-caller-identity   # Account should be 447633181871
```

## Required variables

| Variable | Default | Notes |
| --- | --- | --- |
| `aws_region` | `us-east-2` | |
| `aws_application_arn` | Notary RG ARN | `awsApplication` default tag |
| `project_name` | `notary` | |
| `environment` | `dev` | |
| `db_username` | — | **required**, no default |
| `db_password` | — | **required**, `sensitive` — never commit |
| `db_instance_class` | `db.t3.micro` | |
| `kms_key_alias` | `notary/signing` | |
| `sealing_key_secret` | `""` | `sensitive`, empty allowed |
| `openai_api_key` | `""` | `sensitive`, placeholder secret |
| `anthropic_api_key` | `""` | `sensitive`, placeholder secret |
| `api_image` | `notary-api:latest` | |
| `api_ingress_cidr` | `0.0.0.0/0` | **restrict in production** |
| `api_dns` | `""` | used for `dashboard_url` output |

## Deploy

```bash
cp terraform.tfvars.example terraform.tfvars   # then edit, DO NOT commit
terraform fmt -recursive
terraform init
terraform validate
terraform plan -out=tfplan
# review the plan, then:
terraform apply tfplan
```

### Expected outputs

`vpc_id`, `public_subnet_ids`, `private_subnet_ids`, `ecr_api_url`,
`ecr_worker_url`, `ecs_cluster_name`, `rds_endpoint`, `evidence_bucket_name`,
`evidence_bucket_arn`, `kms_key_id`, `kms_key_arn`, `secrets_arns`
(database / sealing_keys / signing / openai / anthropic), `dashboard_url`.

### Known temporary shortcuts

- **Local state** — no S3/DynamoDB backend yet.
- **Sync replay** — no SQS queues or replay-worker service; `ecs.tf` has a
  commented Phase 2 SQS block. ECR repo `notary-replay-worker` exists for later.
- **`api_ingress_cidr` defaults to `0.0.0.0/0`** — restrict before real use.
- OpenAI / Anthropic secrets are empty placeholders pending real keys.

### Work order mapping

- **WO-23** — VPC/networking, ECR, ECS foundation
- **WO-21** — RDS PostgreSQL + database secret
- **WO-24** — S3 evidence bucket (WORM), KMS signing key, custody secrets
- **WO-28** — IAM task roles, CloudWatch logs, external API key secrets

`db_password` and `sealing_key_secret` must come from your environment or a
secrets manager (e.g. `TF_VAR_db_password=... terraform apply`), **never
committed** to version control.
