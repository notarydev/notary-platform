# Notary Cloud Platform

Private repository containing the API Server, Replay Engine, and infrastructure-as-code for the Notary forensics platform.

## Architecture

- **API Server**: FastAPI service for ingesting forensic snapshots, managing incidents, and issuing evidence certificates.
- **Replay Engine**: Asynchronous worker scaffold for replaying captured events and generating derived analysis.
- **Infrastructure**: Terraform stubs for AWS ECR, ECS, RDS, S3 evidence storage, and Secrets Manager.

## Repository Structure

- `src/notary_platform/` — Platform application code.
  - `api_server/` — FastAPI application and API routes.
  - `replay_engine/` — Event replay and processing worker.
- `infra/` — Infrastructure-as-code documentation and Terraform stubs.
- `docker/` — Dockerfiles for API Server and Replay Engine images.
- `tests/` — Test suite.
- `.github/workflows/` — CI pipeline.

## Development

```bash
python -m pip install -e ".[dev]"
ruff check .
mypy src
pytest -q
```

## Docker

```bash
docker build -f docker/api_server.Dockerfile -t notary-api .
docker build -f docker/replay_engine.Dockerfile -t notary-replay .
```

## License

Proprietary. All rights reserved.
