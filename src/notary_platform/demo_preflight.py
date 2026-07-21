"""Local Harborline demo preflight checks.

Runs the flagship demo through the real FastAPI app in-process. This avoids
network, cloud, credential, and production dependencies while still exercising
the same API contract a presenter uses in the browser.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any, Sequence, TextIO

from fastapi.testclient import TestClient

from notary_platform.api_server.main import app
from notary_platform.api_server.routers.ingestion import storage
from notary_platform.storage import MemoryStorage

PASS_EXIT_CODE = 0
FAIL_EXIT_CODE = 1


@dataclass(frozen=True)
class PreflightCheck:
    name: str
    passed: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


def _clear_storage() -> None:
    """Reset the local demo backend for repeatable dry runs."""
    if not isinstance(storage, MemoryStorage):
        raise RuntimeError("Harborline preflight reset is only supported for local demo storage")
    storage.reset()


def _check(name: str, condition: bool, detail: str) -> PreflightCheck:
    return PreflightCheck(name=name, passed=condition, detail=detail)


def _get(client: TestClient, path: str) -> dict[str, Any]:
    response = client.get(path)
    if response.status_code != 200:
        raise RuntimeError(f"GET {path} returned {response.status_code}: {response.text}")
    loaded = response.json()
    if not isinstance(loaded, dict):
        raise RuntimeError(f"GET {path} did not return a JSON object")
    return loaded


def run_harborline_preflight(reset: bool = True) -> dict[str, Any]:
    if reset:
        _clear_storage()

    client = TestClient(app)
    checks: list[PreflightCheck] = []

    health = _get(client, "/health")
    checks.append(_check("api_health", health.get("status") == "ok", "FastAPI app health endpoint returned ok"))

    seed_response = client.post("/v1/demo/harborline-release-gate/seed")
    seed_ok = seed_response.status_code == 200
    seeded = seed_response.json() if seed_ok else {"error": seed_response.text}
    checks.append(_check("harborline_seed", seed_ok, "Harborline demo seed endpoint completed"))
    if not seed_ok or not isinstance(seeded, dict):
        return _result(checks, seeded if isinstance(seeded, dict) else {"error": str(seeded)})

    checks.append(
        _check(
            "scenario_contract",
            seeded.get("scenario_contract", {}).get("scenario_id") == "harborline-personal-loan-adverse-action"
            and seeded.get("scenario_contract", {}).get("expected_correct_behavior") == "UNDERWRITING_REVIEW",
            "Scenario contract is the Harborline adverse-action case with underwriting-review expected behavior",
        )
    )

    vr = _get(client, f"/v1/verification-records/{seeded['verification_record_id']}")
    replay = _get(client, f"/v1/replay-runs/{seeded['replay_run_id']}")
    mutation = _get(client, f"/v1/mutation-tests/{seeded['mutation_test_id']}")
    scenario = _get(client, f"/v1/scenarios/{seeded['scenario_id']}")
    before_gate = _get(client, f"/v1/release-gate/checks/{seeded['release_gate_before_fix_id']}")
    after_gate = _get(client, f"/v1/release-gate/checks/{seeded['release_gate_after_fix_id']}")
    cert = _get(client, f"/v1/certificates/{seeded['release_gate_after_fix_certificate_id']}")
    verify = _get(client, f"/v1/certificates/{seeded['release_gate_after_fix_certificate_id']}/verify")
    app_js_response = client.get("/app/app.js")

    checks.extend([
        _check(
            "verification_record",
            vr.get("source_record_ref") == "HLCU-PL-0427" and vr.get("replayability") == "replayable",
            "Seed created a replayable Harborline Verification Record",
        ),
        _check(
            "replay",
            replay.get("original_decision") == "DENY" and replay.get("replayed_decision") == "DENY",
            "Replay reproduces the original denied decision",
        ),
        _check(
            "mutation",
            mutation.get("verdict") == "verified" and mutation.get("mutated_decision") == "UNDERWRITING_REVIEW",
            "Fix changes the decision to underwriting review",
        ),
        _check(
            "scenario",
            scenario.get("source_vr_id") == seeded["verification_record_id"]
            and f"vr:{seeded['verification_record_id']}" in scenario.get("evidence_refs", []),
            "Scenario is promoted from the seeded record and carries evidence refs",
        ),
        _check(
            "blocked_gate",
            before_gate.get("status") == "fail" and seeded["scenario_id"] in before_gate.get("failing_scenarios", []),
            "Release Gate blocks the before-fix agent",
        ),
        _check(
            "passing_gate",
            after_gate.get("status") == "pass" and bool(after_gate.get("certificate_id")),
            "Release Gate passes the fixed agent and emits a readiness certificate",
        ),
        _check(
            "gate_evidence",
            bool(after_gate.get("scenario_run_id")) and bool(after_gate.get("evidence_refs")),
            "Passing gate exposes scenario run and evidence references",
        ),
        _check(
            "certificate_signature",
            cert.get("certificate_type") == "proof_of_readiness" and verify.get("signature_valid") is True,
            "Readiness certificate signature verifies",
        ),
        _check(
            "presenter_ui",
            app_js_response.status_code == 200
            and "Northstar Air" in app_js_response.text
            and "From AI failure to release gate" in app_js_response.text
            and "ESCALATE_TO_HUMAN" in app_js_response.text,
            "Platform app contains the Northstar demo presenter path",
        ),
    ])

    return _result(checks, seeded, before_gate=before_gate, after_gate=after_gate)


def _result(
    checks: list[PreflightCheck],
    seeded: dict[str, Any],
    before_gate: dict[str, Any] | None = None,
    after_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    passed = all(check.passed for check in checks)
    return {
        "status": "pass" if passed else "fail",
        "demo": "harborline-release-gate",
        "checks": [check.to_dict() for check in checks],
        "summary": {
            "verification_record_id": seeded.get("verification_record_id", ""),
            "scenario_id": seeded.get("scenario_id", ""),
            "blocked_gate_id": seeded.get("release_gate_before_fix_id", ""),
            "blocked_gate_status": (before_gate or {}).get("status", seeded.get("release_gate_before_fix_status", "")),
            "passing_gate_id": seeded.get("release_gate_after_fix_id", ""),
            "passing_gate_status": (after_gate or {}).get("status", seeded.get("release_gate_after_fix_status", "")),
            "readiness_certificate_id": seeded.get("release_gate_after_fix_certificate_id", ""),
            "claim_scope": seeded.get("scenario_contract", {}).get("scope", ""),
        },
    }


def format_text_report(result: dict[str, Any]) -> str:
    lines = [
        f"Harborline demo preflight: {result['status'].upper()}",
        "",
        "Checks:",
    ]
    for check in result["checks"]:
        marker = "PASS" if check["passed"] else "FAIL"
        lines.append(f"- {marker} {check['name']}: {check['detail']}")
    summary = result["summary"]
    lines.extend(
        [
            "",
            "Presenter anchors:",
            f"- Verification Record: {summary['verification_record_id']}",
            f"- Blocked Gate: {summary['blocked_gate_id']} ({summary['blocked_gate_status']})",
            f"- Passing Gate: {summary['passing_gate_id']} ({summary['passing_gate_status']})",
            f"- Readiness Certificate: {summary['readiness_certificate_id']}",
            "",
            f"Claim scope: {summary['claim_scope']}",
        ]
    )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None, stdout: TextIO | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local Harborline demo preflight.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON instead of a text report.")
    parser.add_argument("--no-reset", action="store_true", help="Do not clear in-memory demo state before running.")
    args = parser.parse_args(argv)

    output_stream = stdout if stdout is not None else sys.stdout
    result = run_harborline_preflight(reset=not args.no_reset)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True), file=output_stream)
    else:
        print(format_text_report(result), file=output_stream)
    return PASS_EXIT_CODE if result["status"] == "pass" else FAIL_EXIT_CODE


if __name__ == "__main__":
    raise SystemExit(main())
