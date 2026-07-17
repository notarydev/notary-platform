"""Configuration for the Notary Platform.

All secrets come from the environment or AWS Secrets Manager. Nothing is
hardcoded. See README for the full list of required variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Settings:
    """Runtime configuration loaded from the environment."""

    # Auth: a static API key / bearer token for the prototype. In production
    # this is delivered via AWS Secrets Manager and injected as an env var.
    api_auth_token: str = ""

    # Org scoping. The prototype uses a single static org/user model.
    default_org_id: str = "demo-org"

    # S3 immutable evidence store.
    evidence_bucket: str = os.getenv("NOTARY_EVIDENCE_BUCKET", "")
    evidence_prefix: str = os.getenv("NOTARY_EVIDENCE_PREFIX", "evidence/")

    # RDS PostgreSQL metadata store.
    database_url: str = os.getenv("NOTARY_DATABASE_URL", "")

    # KMS / signing. When empty, the prototype falls back to a local dev
    # signing key (NOT for production) — see certificates.py.
    signing_key_id: str = os.getenv("NOTARY_SIGNING_KEY_ID", "")
    kms_key_arn: str = os.getenv("NOTARY_KMS_KEY_ARN", "")

    # When true, persistence uses S3 + Postgres. When false (default locally),
    # an in-memory store is used so the demo runs with zero cloud setup.
    use_remote_storage: bool = bool(os.getenv("NOTARY_USE_REMOTE_STORAGE", ""))

    # Viz SPA origin for CORS. May be a comma-separated list of allowed origins
    # (local + deployed) so shared environments can lock CORS to known origins.
    viz_origin: str = os.getenv("NOTARY_VIZ_ORIGIN", "http://localhost:5173")

    # Optional auth token for the Command Center status endpoints. When set, the
    # viz endpoints require this bearer token (or X-Command-Center-Token header).
    # Leave empty for local/demo (auth-optional). Set for any shared deployment.
    command_center_token: str = os.getenv("NOTARY_COMMAND_CENTER_TOKEN", "")

    @property
    def auth_enabled(self) -> bool:
        return bool(self.api_auth_token)


def load_settings() -> Settings:
    return Settings(
        api_auth_token=os.getenv("NOTARY_API_AUTH_TOKEN", ""),
        default_org_id=os.getenv("NOTARY_DEFAULT_ORG_ID", "demo-org"),
        evidence_bucket=os.getenv("NOTARY_EVIDENCE_BUCKET", ""),
        evidence_prefix=os.getenv("NOTARY_EVIDENCE_PREFIX", "evidence/"),
        database_url=os.getenv("NOTARY_DATABASE_URL", ""),
        signing_key_id=os.getenv("NOTARY_SIGNING_KEY_ID", ""),
        kms_key_arn=os.getenv("NOTARY_KMS_KEY_ARN", ""),
        use_remote_storage=bool(os.getenv("NOTARY_USE_REMOTE_STORAGE", "")),
        viz_origin=os.getenv("NOTARY_VIZ_ORIGIN", "http://localhost:5173"),
        command_center_token=os.getenv("NOTARY_COMMAND_CENTER_TOKEN", ""),
    )


# A process-wide settings instance. Tests may override attributes directly.
SETTINGS = load_settings()
