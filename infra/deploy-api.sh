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
set -euo pipefail

REGION="${AWS_REGION:-us-east-2}"
PROJECT_NAME="${PROJECT_NAME:-notary}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
NAME_PREFIX="${PROJECT_NAME}-${ENVIRONMENT}"          # -> notary-dev
ECR_REPO="${NAME_PREFIX}-api"                          # -> notary-dev-api
ECS_CLUSTER="${NAME_PREFIX}"                           # -> notary-dev
ECS_SERVICE="${NAME_PREFIX}-api"                       # -> notary-dev-api
IMAGE_TAG="${IMAGE_TAG:-main-$(git rev-parse --short HEAD)}"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO}:${IMAGE_TAG}"

echo "==> Deploying notary-platform"
echo "    region:     ${REGION}"
echo "    ecr repo:   ${ECR_REPO}"
echo "    ecs:        ${ECS_SERVICE} @ ${ECS_CLUSTER}"
echo "    image tag:  ${IMAGE_TAG}"

# 1. Authenticate Docker to ECR
aws ecr get-login-password --region "${REGION}" \
  | docker login --username AWS --password-stdin \
    "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

# 2. Build (production image, no [dev] extra)
docker build -t "${ECR_REPO}:${IMAGE_TAG}" -t "${ECR_REPO}:latest" .

# 3. Push
docker tag "${ECR_REPO}:${IMAGE_TAG}" "${ECR_URI}"
docker push "${ECR_URI}"
docker push "${ECR_REPO}:latest"

# 4. Force ECS redeploy (picks up the new :latest image)
aws ecs update-service \
  --region "${REGION}" \
  --cluster "${ECS_CLUSTER}" \
  --service "${ECS_SERVICE}" \
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
