from __future__ import annotations

from notary_platform.config import Settings
from notary_platform.security_readiness import build_security_readiness, format_security_readiness


def test_default_local_settings_are_blocked_for_shared_deploy() -> None:
    result = build_security_readiness(Settings())

    assert result["status"] == "blocked"
    assert result["environment"] == "local_or_incomplete"
    blocked = {check["id"] for check in result["checks"] if not check["passed"]}
    assert {"api_auth", "command_center_auth", "cors", "remote_storage", "kms_signing"}.issubset(blocked)


def test_shared_demo_storage_is_not_immutable_evidence() -> None:
    result = build_security_readiness(Settings(storage_profile="shared_demo"))
    check = next(check for check in result["checks"] if check["id"] == "shared_demo_boundary")

    assert check["passed"] is False
    assert "not immutable" in check["detail"]


def test_pilot_ready_settings_pass() -> None:
    settings = Settings(
        api_auth_token="api-token",
        command_center_token="cc-token",
        viz_origin="https://command.getnotary.ai,https://getnotary.ai",
        use_remote_storage=True,
        database_url="postgresql://example",
        evidence_bucket="notary-evidence-pilot",
        kms_key_arn="arn:aws:kms:us-east-2:123456789012:key/example",
        storage_profile="memory",
    )

    result = build_security_readiness(settings)

    assert result["status"] == "pass"
    assert result["stop_boundaries"] == []
    assert all(check["passed"] is True for check in result["checks"])


def test_report_lists_stop_boundaries() -> None:
    report = format_security_readiness(build_security_readiness(Settings()))

    assert "Security/deployment readiness: BLOCKED" in report
    assert "Stop boundaries:" in report
    assert "NOTARY_API_AUTH_TOKEN" in report
