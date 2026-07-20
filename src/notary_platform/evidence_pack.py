"""Build a local final rehearsal evidence pack for the Harborline pilot demo."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from fastapi.testclient import TestClient

from notary_platform.api_server.main import app
from notary_platform.demo_preflight import run_harborline_preflight
from notary_platform.security_readiness import build_security_readiness


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _get(client: TestClient, path: str) -> dict[str, Any]:
    response = client.get(path)
    if response.status_code != 200:
        raise RuntimeError(f"GET {path} returned {response.status_code}: {response.text}")
    loaded = response.json()
    if not isinstance(loaded, dict):
        raise RuntimeError(f"GET {path} did not return a JSON object")
    return loaded


def build_evidence_pack(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).isoformat()

    preflight = run_harborline_preflight()
    security = build_security_readiness()
    summary = preflight["summary"]
    client = TestClient(app)

    blocked_gate = _get(client, f"/v1/release-gate/checks/{summary['blocked_gate_id']}")
    passing_gate = _get(client, f"/v1/release-gate/checks/{summary['passing_gate_id']}")
    readiness_certificate = _get(client, f"/v1/certificates/{summary['readiness_certificate_id']}")
    certificate_verification = _get(client, f"/v1/certificates/{summary['readiness_certificate_id']}/verify")

    architecture = {
        "generated_at": generated_at,
        "loop": [
            "SDK capture/seal",
            "Platform ingest/verify",
            "Cassette replay",
            "Mutation/fix verification",
            "Scoped proof",
            "Scenario promotion",
            "Release Gate",
        ],
        "surfaces": {
            "platform": "Customer-facing Harborline demo and proof workflow",
            "website": "Public Harborline positioning and design-partner pilot offer",
            "command_center": "Internal program control and live status",
        },
    }
    limitations = {
        "generated_at": generated_at,
        "limitations": [
            "Harborline evidence is a demo scenario, not real customer data.",
            "Local evidence pack uses dev/local settings unless shared/pilot readiness passes.",
            "Security readiness blocks shared/pilot claims until auth, CORS, remote storage, and KMS are configured.",
            "Proof is scoped to the tested scenario and does not certify general AI safety, fairness, or compliance.",
            "No production deployment is performed by the evidence-pack command.",
        ],
    }
    rehearsal = {
        "generated_at": generated_at,
        "status": "pass" if preflight["status"] == "pass" else "blocked",
        "demo": "Harborline Credit Union personal-loan adverse-action workflow",
        "required_recordings": [
            "Open platform app home Harborline path",
            "Open Verification Record",
            "Open blocked Release Gate",
            "Open passing Release Gate",
            "Open readiness certificate verification",
        ],
        "artifacts": {
            "preflight": "harborline-preflight.json",
            "security_readiness": "security-readiness.json",
            "blocked_gate": "blocked-gate.json",
            "passing_gate": "passing-gate.json",
            "readiness_certificate": "readiness-certificate.json",
            "certificate_verification": "readiness-certificate-verification.json",
            "architecture": "architecture-summary.json",
            "limitations": "limitations.json",
        },
    }

    _write_json(output_dir / "harborline-preflight.json", preflight)
    _write_json(output_dir / "security-readiness.json", security)
    _write_json(output_dir / "blocked-gate.json", blocked_gate)
    _write_json(output_dir / "passing-gate.json", passing_gate)
    _write_json(output_dir / "readiness-certificate.json", readiness_certificate)
    _write_json(output_dir / "readiness-certificate-verification.json", certificate_verification)
    _write_json(output_dir / "architecture-summary.json", architecture)
    _write_json(output_dir / "limitations.json", limitations)
    _write_json(output_dir / "rehearsal-manifest.json", rehearsal)
    return rehearsal


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the local Harborline final rehearsal evidence pack.")
    parser.add_argument("--output-dir", default="artifacts/final-evidence-pack", help="Directory to write JSON evidence artifacts.")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    manifest = build_evidence_pack(Path(args.output_dir))
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0 if manifest["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
