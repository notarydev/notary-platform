#!/usr/bin/env bash
#
# Deploy current notary-platform main to the live api.getnotary.ai service.
#
# PREREQUISITES (supplied by the AWS account owner for us-east-2):
#   - AWS credentials with ECR push + ECS update-service + (optional) kms/secrets read
#     for the account that owns the notary-dev ALB/ECS (NOT the Opencode_Notary
#     us-east-1 account — that one has no ECR/ECS).
#   - Docker daemon running locally.
#   - `aws` CLI and `docker` on PATH.
#
# WHAT THIS DOES (no Terraform apply — only rebuild + push + force redeploy):
#   1. Build the platform image from current main.
#   2. Push to ECR repo notary-dev-api (us-east-2).
#   3. Force a new ECS deployment of service notary-dev-api on cluster notary-dev.
#   4. Print verification commands.
#
# It does NOT touch DNS, secrets, KMS, CORS, or Terraform state.
#
# SAFETY: deploys MUST originate from a fresh origin/main — never a feature or PR
# branch (it will be stale relative to main and can ship the wrong code). The
# pre-flight below enforces this and refuses to run otherwise.
set -euo pipefail

# --- pre-flight: only deploy from a fresh, clean origin/main ---
CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [ "$CURRENT_BRANCH" != "main" ]; then
  echo "REFUSING TO DEPLOY: current branch is '$CURRENT_BRANCH', not 'main'." >&2
  echo "Run: git fetch origin --prune && git checkout main && git reset --hard origin/main" >&2
  exit 1
fi
if [ -n "$(git status --porcelain)" ]; then
  echo "REFUSING TO DEPLOY: working tree is dirty. Commit or stash changes first." >&2
  exit 1
fi
git fetch origin --prune >/dev/null 2>&1
LOCAL="$(git rev-parse HEAD)"
REMOTE="$(git rev-parse origin/main)"
if [ "$LOCAL" != "$REMOTE" ]; then
  echo "REFUSING TO DEPLOY: local main ($LOCAL) != origin/main ($REMOTE)." >&2
  echo "Run: git fetch origin --prune && git reset --hard origin/main" >&2
  exit 1
fi

REGION="${AWS_REGION:-us-east-2}"
PROJECT_NAME="${PROJECT_NAME:-notary}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
NAME_PREFIX="${PROJECT_NAME}-${ENVIRONMENT}"          # -> notary-dev
# NOTE: the ECR repo is named "${project_name}-api" in infra/terraform/ecr.tf
# (NO environment prefix), i.e. "notary-api" — not "notary-dev-api". The ECS
# service/cluster DO carry the environment prefix (notary-dev-api / notary-dev).
ECR_REPO="${PROJECT_NAME}-api"                         # -> notary-api
ECS_CLUSTER="${NAME_PREFIX}"                           # -> notary-dev
ECS_SERVICE="${NAME_PREFIX}-api"                       # -> notary-dev-api
IMAGE_TAG="${IMAGE_TAG:-main-$(git rev-parse --short HEAD)-$(date +%Y%m%d-%H%M%S)}"
# ECR tags are immutable, so always use a unique tag (don't reuse SHAs).
# ECS Fargate runs linux/amd64 — build for that arch even on Apple-Silicon hosts,
# otherwise tasks fail with: CannotPullContainerError: ... does not contain
# descriptor matching platform 'linux/amd64'.
BUILD_PLATFORM="${BUILD_PLATFORM:-linux/amd64}"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO}:${IMAGE_TAG}"

echo "==> Deploying notary-platform"
echo "    region:       ${REGION}"
echo "    ecr repo:     ${ECR_REPO}"
echo "    ecs:          ${ECS_SERVICE} @ ${ECS_CLUSTER}"
echo "    image tag:    ${IMAGE_TAG}"
echo "    build plat:   ${BUILD_PLATFORM}"

# 1. Authenticate Docker to ECR
aws ecr get-login-password --region "${REGION}" \
  | docker login --username AWS --password-stdin \
    "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

# 2. Build + push for the target platform (no :latest — tags are immutable)
docker buildx build --platform "${BUILD_PLATFORM}" -t "${ECR_URI}" --push .

# 3. Register a new task-definition revision that points at the new image, then
#    force a redeploy. (A bare --force-new-deployment does NOT change the image;
#    the task def pins a specific tag, so we must register a new revision.)
TD_JSON="$(aws ecs describe-task-definition --task-definition "${ECS_SERVICE}" --region "${REGION}" --query 'taskDefinition')"
echo "${TD_JSON}" | python3 -c '
import json, sys
td = json.load(sys.stdin)
for k in ["taskDefinitionArn","status","requiresAttributes","compatibilities","registeredAt","registeredBy","revision"]:
    td.pop(k, None)
td["containerDefinitions"][0]["image"] = "'"${ECR_URI}"'"
print(json.dumps(td))' > /tmp/td-new.json
NEW_TD="$(aws ecs register-task-definition --region "${REGION}" --cli-input-json file:///tmp/td-new.json --query 'taskDefinition.taskDefinitionArn' --output text)"
echo "    new task def: ${NEW_TD}"

# 4. Update service to the new task def and force a new deployment
aws ecs update-service \
  --region "${REGION}" \
  --cluster "${ECS_CLUSTER}" \
  --service "${ECS_SERVICE}" \
  --task-definition "${NEW_TD}" \
  --force-new-deployment \
  --query 'service.serviceName' \
  --output text

echo "==> Redeploy triggered. Wait for the new task to become healthy, then verify:"
echo
echo "curl -s https://api.getnotary.ai/health"
echo "curl -s https://api.getnotary.ai/app/app.js | grep Harborline"
echo "curl -s https://api.getnotary.ai/app/app.js | grep 'Blocked Gate'"
echo "curl -s https://api.getnotary.ai/app/app.js | grep 'Passing Gate'"
echo
echo "Expected: /health -> {\"status\":\"ok\"} and all three greps return >=1 match."
