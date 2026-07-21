from __future__ import annotations

import json

from notary_platform.evidence_pack import build_evidence_pack


def test_evidence_pack_writes_rehearsal_artifacts(tmp_path) -> None:
    manifest = build_evidence_pack(tmp_path)

    assert manifest["status"] == "pass"
    for filename in manifest["artifacts"].values():
        path = tmp_path / filename
        assert path.exists(), filename
        assert json.loads(path.read_text(encoding="utf-8"))

    preflight = json.loads((tmp_path / "northstar-preflight.json").read_text(encoding="utf-8"))
    security = json.loads((tmp_path / "security-readiness.json").read_text(encoding="utf-8"))
    passing_gate = json.loads((tmp_path / "passing-gate.json").read_text(encoding="utf-8"))
    verify = json.loads((tmp_path / "readiness-certificate-verification.json").read_text(encoding="utf-8"))

    assert preflight["status"] == "pass"
    assert security["status"] == "blocked"
    assert passing_gate["status"] == "pass"
    assert verify["signature_valid"] is True
