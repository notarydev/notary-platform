"""Golden path test for a non-demo SDK/API-created Verification Record.

Proves that a real customer-created record can travel through the full
product spine: capture → record → replay → mutation → proof → scenario →
scenario run (fail + pass) → readiness → release gate.

This test does NOT seed demo_catalog.py.
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from notary_platform.api_server.main import app
from notary_platform.api_server.routers.ingestion import set_replay_runner, storage
from notary_platform.services import DemoReplayRunner

client = TestClient(app)


def _clear_storage() -> None:
    storage._vrs.clear()
    storage._labels.clear()
    storage._incidents.clear()
    storage._snapshots.clear()
    storage._evidence.clear()
    storage._certificates.clear()
    storage._evidence_artifacts.clear()
    storage._replay_runs.clear()
    storage._mutation_tests.clear()
    storage._proof_certs.clear()
    storage._scenarios.clear()
    storage._scenario_candidates.clear()
    storage._scenario_runs.clear()
    storage._readiness_policies.clear()
    storage._readiness_checks.clear()
    storage._release_gate_results.clear()
    storage._counter = 0


class TestCustomerRecordGoldenPath:
    def setup_method(self) -> None:
        _clear_storage()
        set_replay_runner(DemoReplayRunner(scenario_id="lending-denial"))

    def _create_record_with_sdk_snapshot(self) -> dict[str, Any]:
        """Simulate an SDK-created snapshot being submitted."""
        snapshot = {
            "schema_version": 1,
            "timestamp": "2025-01-01T00:00:00Z",
            "elements": [
                {
                    "kind": "human",
                    "payload": {"source_record_ref": "APP-1234", "domain": "Lending"},
                    "element_hash": "a1" * 16,
                },
                {
                    "kind": "llm",
                    "payload": {"prompt": "Loan application APP-1234", "response": "Need credit score", "model": "demo-model", "temperature": 0.0, "seed": 12345},  # noqa: E501
                    "element_hash": "a2" * 16,
                },
                {
                    "kind": "http",
                    "payload": {"request": {"method": "POST", "url": "https://demo.notary.local/credit-bureau", "body": ""}, "response": {"score": 650}, "status": 200},  # noqa: E501
                    "element_hash": "a3" * 16,
                },
                {
                    "kind": "decision",
                    "payload": {"decision": "DENY", "expected_correct_behavior": "APPROVE"},
                    "element_hash": "a4" * 16,
                },
            ],
            "merkle_chain": ["a1" * 16, "a2" * 16, "a3" * 16, "a4" * 16],
            "root_hash": "demo-root-hash",
            "agent_version": "loan-agent@candidate",
            "policy_version": "credit-policy-v1",
            "source_system_id": "sys:lending",
            "source_record_ref": "APP-1234",
            "agent_id": "agent:lending",
            "business_function": "Personal loan underwriting",
            "model_provider": "Demo Provider",
            "model_name": "demo-model",
        }
        resp = client.post("/v1/verification-records/from-snapshot", json=snapshot)
        assert resp.status_code == 200
        return resp.json()

    def test_record_is_not_demo(self) -> None:
        vr = self._create_record_with_sdk_snapshot()
        assert vr["is_demo"] is False

    def test_events_include_all_kinds(self) -> None:
        vr = self._create_record_with_sdk_snapshot()
        kinds = [e["kind"] for e in vr["events"]]
        assert "human_action" in kinds
        assert "model_call" in kinds
        assert "tool_call" in kinds or "api_response" in kinds
        assert "decision" in kinds

    def test_replayability_is_computed_not_forced(self) -> None:
        vr = self._create_record_with_sdk_snapshot()
        assert vr["replayability_source"] == "computed"

    def test_full_golden_path(self) -> None:
        vr = self._create_record_with_sdk_snapshot()
        vr_id = vr["id"]

        # Add label
        label_resp = client.post(
            f"/v1/verification-records/{vr_id}/label",
            params={"expected_outcome": "APPROVE", "reviewer": "Test", "role": "QA", "reason": "Golden path test"},
        )
        assert label_resp.status_code == 200

        # Replay
        replay = client.post(f"/v1/verification-records/{vr_id}/replay-runs").json()
        assert replay["status"] == "replayed", f"Expected replayed, got {replay['status']}"

        # Mutation (customer fix config)
        mutation = client.post(
            f"/v1/verification-records/{vr_id}/mutation-tests",
            json={"fix_config": {"threshold": 620}, "expected_correct_behavior": "APPROVE"},
        ).json()
        assert mutation["verdict"] == "verified", f"Expected verified, got {mutation['verdict']}"

        # Proof of Mitigation
        proof = client.post(f"/v1/verification-records/{vr_id}/proof-of-mitigation").json()
        assert proof["certificate_type"] == "proof_of_mitigation"
        assert proof["claim"]["expected_outcome"] == "APPROVE"

        # Verify proof signature
        verify = client.get(f"/v1/certificates/{proof['id']}/verify").json()
        assert verify["signature_valid"] is True

        # Promote to Scenario
        scenario = client.post("/v1/scenarios", params={"vr_id": vr_id}).json()
        assert scenario["source_vr_id"] == vr_id
        expected_outcome = scenario["expected_outcome"]
        assert expected_outcome == "APPROVE"

        # Scenario run WITHOUT fix config — should fail
        run_no_fix = client.post(
            "/v1/scenario-runs",
            json={"scenario_ids": [scenario["id"]], "agent_version": "1.2.0"},
        ).json()
        assert run_no_fix["status"] == "completed"
        no_fix_result = next(r for r in run_no_fix["results"] if r["scenario_id"] == scenario["id"])
        assert no_fix_result["status"] == "failed", f"Expected failed without fix, got {no_fix_result['status']}"

        # Scenario run WITH fix config — should pass
        run_with_fix = client.post(
            "/v1/scenario-runs",
            json={"scenario_ids": [scenario["id"]], "agent_version": "1.2.0", "fix_config": {"threshold": 620}},
        ).json()
        assert run_with_fix["status"] == "completed"
        with_fix_result = next(r for r in run_with_fix["results"] if r["scenario_id"] == scenario["id"])
        assert with_fix_result["status"] == "passed", f"Expected passed with fix, got {with_fix_result['status']}"

        # Readiness Policy
        policy = client.post(
            "/v1/readiness-policies",
            json={"name": "Customer Golden Path Gate", "required_scenario_ids": [scenario["id"]]},
        ).json()
        assert policy["name"] == "Customer Golden Path Gate"

        # Readiness Check (with fix)
        check = client.post(
            "/v1/readiness-checks",
            json={"policy_id": policy["id"], "agent_version": "1.2.0", "fix_config": {"threshold": 620}},
        ).json()
        assert check["verdict"] == "passed", f"Expected passed, got {check['verdict']}"

        # Release Gate
        gate = client.post(
            "/v1/release-gate/checks",
            json={"policy_id": policy["id"], "agent_version": "1.2.0", "fix_config": {"threshold": 620}},
        ).json()
        assert gate["status"] == "pass", f"Expected pass, got {gate['status']}"

        # Readiness certificate verifies
        if check.get("certificate_id"):
            cert_verify = client.get(f"/v1/certificates/{check['certificate_id']}/verify").json()
            assert cert_verify["signature_valid"] is True
