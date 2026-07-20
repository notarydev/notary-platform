"""Security and deployment readiness checks for shared/pilot environments."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any, Sequence

from notary_platform.config import SETTINGS, Settings


@dataclass(frozen=True)
class ReadinessCheck:
    id: str
    title: str
    passed: bool
    detail: str
    stop_boundary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "passed": self.passed,
            "detail": self.detail,
            "stop_boundary": self.stop_boundary,
        }


def _origins(viz_origin: str) -> list[str]:
    return [origin.strip() for origin in viz_origin.split(",") if origin.strip()]


def build_security_readiness(settings: Settings = SETTINGS) -> dict[str, Any]:
    origins = _origins(settings.viz_origin)
    auth_enabled = bool(settings.api_auth_token)
    command_center_auth = bool(settings.command_center_token)
    cors_locked = bool(origins) and "*" not in origins and all("localhost" not in origin for origin in origins)
    remote_storage_ready = bool(settings.use_remote_storage and settings.database_url and settings.evidence_bucket)
    signing_ready = bool(settings.kms_key_arn)
    shared_demo_only = settings.storage_profile == "shared_demo" and not settings.use_remote_storage

    checks = [
        ReadinessCheck(
            "api_auth",
            "API auth token",
            auth_enabled,
            "NOTARY_API_AUTH_TOKEN is set." if auth_enabled else "NOTARY_API_AUTH_TOKEN is empty; local/demo only.",
            "Set shared/pilot API auth through Secrets Manager before shared access.",
        ),
        ReadinessCheck(
            "command_center_auth",
            "Command Center auth token",
            command_center_auth,
            "NOTARY_COMMAND_CENTER_TOKEN is set." if command_center_auth else "Command Center status endpoints are auth-optional; local/demo only.",
            "Set a Command Center token before exposing status endpoints.",
        ),
        ReadinessCheck(
            "cors",
            "CORS allowed origins",
            cors_locked,
            f"Allowed origins: {', '.join(origins) or 'none'}",
            "Replace localhost/wildcard origins with exact shared deployment origins before pilot use.",
        ),
        ReadinessCheck(
            "remote_storage",
            "Remote evidence and metadata storage",
            remote_storage_ready,
            (
                "Postgres and S3 evidence bucket are configured."
                if remote_storage_ready
                else "Remote storage is not fully configured; memory/shared-demo is not immutable production evidence."
            ),
            "Enable NOTARY_USE_REMOTE_STORAGE with database URL and S3 Object Lock bucket for pilot evidence claims.",
        ),
        ReadinessCheck(
            "kms_signing",
            "KMS-backed certificate sealing",
            signing_ready,
            "NOTARY_KMS_KEY_ARN is set." if signing_ready else "Certificates use local/dev signing fallback.",
            "Set NOTARY_KMS_KEY_ARN before claiming production-grade certificate sealing.",
        ),
        ReadinessCheck(
            "shared_demo_boundary",
            "Shared demo storage boundary",
            not shared_demo_only,
            "Storage profile is not shared_demo." if not shared_demo_only else "shared_demo persists demos but is not immutable custody storage.",
            "Do not describe shared_demo JSON persistence as WORM/immutable evidence.",
        ),
    ]

    passed = all(check.passed for check in checks)
    return {
        "status": "pass" if passed else "blocked",
        "environment": "shared_or_pilot" if passed else "local_or_incomplete",
        "checks": [check.to_dict() for check in checks],
        "stop_boundaries": [check.stop_boundary for check in checks if not check.passed],
    }


def format_security_readiness(result: dict[str, Any]) -> str:
    lines = [f"Security/deployment readiness: {result['status'].upper()}", ""]
    for check in result["checks"]:
        marker = "PASS" if check["passed"] else "BLOCKED"
        lines.append(f"- {marker} {check['id']}: {check['detail']}")
    if result["stop_boundaries"]:
        lines.extend(["", "Stop boundaries:"])
        lines.extend(f"- {boundary}" for boundary in result["stop_boundaries"])
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    json_mode = "--json" in args
    result = build_security_readiness()
    if json_mode:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(format_security_readiness(result))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
