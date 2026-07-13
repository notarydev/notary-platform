# Notary Cloud Platform

Private repository containing the API Server, Replay Engine, and infrastructure-as-code for the Notary forensics platform.

## Architecture

- **API Server**: FastAPI service for ingesting and replaying forensic snapshots
- **Replay Engine**: Asynchronous worker for processing and analyzing captured events
- **Infrastructure**: Terraform/CDK definitions for AWS ECR, ECS, RDS, S3, KMS, and Secrets Manager

## Repository Structure

- `src/notary_platform/` — Platform application code
  - `api_server/` — FastAPI application and API routes
  - `replay_engine/` — Event replay and processing worker
- `infra/` — Infrastructure-as-code (Terraform or CDK)
- `docker/` — Dockerfiles for API Server and Replay Engine
- `tests/` — Test suite
- `.github/workflows/` — CI/CD pipelines

## Development

See [SETUP.md](./SETUP.md) for setup instructions.

## License

Proprietary. All rights reserved.
