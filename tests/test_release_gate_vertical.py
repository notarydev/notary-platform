"""Vertical slice tests for the WO-28 Release Gate path.

Exercises the spine: catalog seed → VR → replay → mutation → proof →
scenario → scenario run → readiness policy → readiness check → release gate.
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from notary_platform.api_server.main import app
from notary_platform.api_server.routers.ingestion import storage

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


class TestReleaseGateVertical:
    def setup_method(self) -> None:
        _clear_storage()

    def _seed_catalog(self) -> dict[str, Any]:
        resp = client.post("/v1/demo/catalog/seed")
        assert resp.status_code == 200
        return resp.json()

    def _find_replayable_vr(self) -> dict[str, Any]:
        resp = client.get("/v1/verification-records?replayability=replayable")
        assert resp.status_code == 200
        vrs = resp.json()
        assert vrs, "No replayable VRs found"
        return vrs[0]

    def test_catalog_seed_creates_records(self) -> None:
        result = self._seed_catalog()
        assert result["created_verification_records"] == 21
        assert result["created_incidents"] > 0
        assert result["created_proof_certificates"] > 0
        assert result["scenario_candidates"] > 0
        assert result["scenarios"] > 0

    def test_replayable_record_produces_replay_run(self) -> None:
        self._seed_catalog()
        vr = self._find_replayable_vr()
        resp = client.post(f"/v1/verification-records/{vr['id']}/replay-runs")
        assert resp.status_code == 200
        run = resp.json()
        assert run["status"] == "replayed"
        assert run["replayed_decision"]

    def test_missing_cassette_produces_blocker(self) -> None:
        self._seed_catalog()
        resp = client.get("/v1/verification-records?replayability=missing_context")
        assert resp.status_code == 200
        vrs = resp.json()
        assert vrs
        eligibility = client.get(f"/v1/verification-records/{vrs[0]['id']}/eligibility/replay").json()
        assert eligibility["eligible"] is False
        assert "missing" in eligibility["reason"].lower() or "cassette" in eligibility["reason"].lower()

    def test_mutation_pass_and_fail_persist(self) -> None:
        self._seed_catalog()
        vr = self._find_replayable_vr()
        client.post(f"/v1/verification-records/{vr['id']}/replay-runs")
        resp = client.post(
            f"/v1/verification-records/{vr['id']}/mutation-tests",
            json={
                "fix_config": {"require_policy_match_for_refund_claims": True, "escalate_when_policy_requires_human_review": True},
                "expected_correct_behavior": "ESCALATE_TO_HUMAN",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["verdict"] == "verified"
        assert resp.json()["decision_changed"] is True

        # Same record, failing fix config (no fix applied).
        resp = client.post(
            f"/v1/verification-records/{vr['id']}/mutation-tests",
            json={"fix_config": {}, "expected_correct_behavior": "ESCALATE_TO_HUMAN"},
        )
        assert resp.status_code == 200
        assert resp.json()["verdict"] == "not_verified"
        assert resp.json()["decision_changed"] is False

    def test_proof_blocked_before_mitigation(self) -> None:
        self._seed_catalog()
        vrs = client.get("/v1/verification-records").json()
        # Pick a record that has no mutation test.
        vr = next(v for v in vrs if v["replayability"] not in {"replayable", "partially_replayable"})
        resp = client.post(f"/v1/verification-records/{vr['id']}/proof-of-mitigation")
        assert resp.status_code == 400
        assert "mutation" in resp.json()["detail"].lower() or "replay" in resp.json()["detail"].lower()

    def test_signed_proof_verifies_and_tamper_fails(self) -> None:
        self._seed_catalog()
        vr = self._find_replayable_vr()
        client.post(f"/v1/verification-records/{vr['id']}/replay-runs")
        client.post(
            f"/v1/verification-records/{vr['id']}/mutation-tests",
            json={
                "fix_config": {"require_policy_match_for_refund_claims": True, "escalate_when_policy_requires_human_review": True},
                "expected_correct_behavior": "ESCALATE_TO_HUMAN",
            },
        )
        resp = client.post(f"/v1/verification-records/{vr['id']}/proof-of-mitigation")
        assert resp.status_code == 200
        cert = resp.json()
        verify_resp = client.get(f"/v1/certificates/{cert['id']}/verify")
        assert verify_resp.json()["signature_valid"] is True

        # Tamper with signed payload locally.
        from notary_platform.certificates import verify_certificate_signature

        tampered = dict(cert["signed_payload"])
        tampered["mutated_decision"] = "DENY"
        assert verify_certificate_signature(tampered) is False

    def test_scenario_promotion_and_duplicate_handling(self) -> None:
        self._seed_catalog()
        candidates = client.get("/v1/scenario-candidates").json()
        candidate = next(c for c in candidates if c["state"] == "candidate")
        resp = client.post(f"/v1/scenario-candidates/{candidate['id']}/promote")
        assert resp.status_code == 200
        scenario_id = resp.json()["id"]
        # Duplicate promotion returns existing scenario.
        resp = client.post(f"/v1/scenario-candidates/{candidate['id']}/promote")
        assert resp.status_code == 200
        assert resp.json()["id"] == scenario_id

    def test_scenario_run_pass_fail_errored(self) -> None:
        self._seed_catalog()
        scenarios = client.get("/v1/scenarios").json()
        assert scenarios
        resp = client.post(
            "/v1/scenario-runs",
            json={"scenario_ids": [s["id"] for s in scenarios], "agent_version": "1.2.0"},
        )
        assert resp.status_code == 200
        run = resp.json()
        assert run["status"] == "completed"
        assert "passed" in run["summary"]
        assert "failed" in run["summary"]
        assert "errored" in run["summary"]

    def test_readiness_check_pass_and_fail(self) -> None:
        self._seed_catalog()
        scenarios = client.get("/v1/scenarios").json()
        # Policy with all scenarios should pass/fail depending on runs.
        policy_resp = client.post(
            "/v1/readiness-policies",
            json={"name": "Lending Gate", "required_scenario_ids": [s["id"] for s in scenarios]},
        )
        assert policy_resp.status_code == 200
        policy_id = policy_resp.json()["id"]
        check_resp = client.post(
            "/v1/readiness-checks",
            json={"policy_id": policy_id, "agent_version": "1.2.0"},
        )
        assert check_resp.status_code == 200
        check = check_resp.json()
        assert check["verdict"] in {"passed", "failed"}
        assert check["scenario_run_id"]

    def test_release_gate_pass_fail_error(self) -> None:
        self._seed_catalog()
        scenarios = client.get("/v1/scenarios").json()
        policy_resp = client.post(
            "/v1/readiness-policies",
            json={"name": "Release Gate", "required_scenario_ids": [s["id"] for s in scenarios]},
        )
        policy_id = policy_resp.json()["id"]
        resp = client.post(
            "/v1/release-gate/checks",
            json={"policy_id": policy_id, "agent_version": "1.2.0"},
        )
        assert resp.status_code == 200
        result = resp.json()
        assert result["status"] in {"pass", "fail", "error"}
        assert result["ci_cd_command"]

        # Error case: unknown policy.
        resp = client.post(
            "/v1/release-gate/checks",
            json={"policy_id": "rp-unknown", "agent_version": "1.2.0"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "error"

    def test_northstar_release_gate_fails_before_fix_and_passes_after_fix(self) -> None:
        resp = client.post("/v1/demo/northstar/seed")
        assert resp.status_code == 200
        seeded = resp.json()
        assert seeded["demo_org"] == "Northstar Air"
        assert seeded["scenario_contract"]["scenario_id"] == "vr-northstar-001"
        assert seeded["scenario_contract"]["original_captured_decision"] == "OFFER_RETROACTIVE_REFUND"
        assert seeded["scenario_contract"]["expected_correct_behavior"] == "ESCALATE_TO_HUMAN"

        vr = client.get(f"/v1/verification-records/{seeded['verification_record_id']}").json()
        assert vr["source_record_ref"] == "50093821"
        assert vr["agent_id"] == "agent:support-bot-v42"
        assert vr["replayability"] == "replayable"
        assert vr["current_label_id"] == seeded["label_id"]
        assert vr["expected_outcome"] == "ESCALATE_TO_HUMAN"

        replay = client.get(f"/v1/replay-runs/{seeded['replay_run_id']}").json()
        assert replay["status"] == "replayed"
        assert replay["original_decision"] == "OFFER_RETROACTIVE_REFUND"
        assert replay["replayed_decision"] == "OFFER_RETROACTIVE_REFUND"

        mutation = client.get(f"/v1/mutation-tests/{seeded['mutation_test_id']}").json()
        assert mutation["verdict"] == "verified"
        assert mutation["original_decision"] == "OFFER_RETROACTIVE_REFUND"
        assert mutation["mutated_decision"] == "ESCALATE_TO_HUMAN"
        assert mutation["decision_changed"] is True

        scenario = client.get(f"/v1/scenarios/{seeded['scenario_id']}").json()
        assert scenario["source_vr_id"] == seeded["verification_record_id"]
        assert scenario["source_incident_id"] == seeded["incident_id"]
        assert scenario["approved_label_id"] == seeded["label_id"]
        assert scenario["expected_outcome"] == "ESCALATE_TO_HUMAN"
        assert f"vr:{seeded['verification_record_id']}" in scenario["evidence_refs"]
        assert f"incident:{seeded['incident_id']}" in scenario["evidence_refs"]

        before_gate = client.get(f"/v1/release-gate/checks/{seeded['release_gate_before_fix_id']}").json()
        assert before_gate["status"] == "fail"
        assert before_gate["certificate_id"] == ""
        assert seeded["scenario_id"] in before_gate["failing_scenarios"]
        assert before_gate["scenario_run_id"]
        assert f"readiness_check:{before_gate['readiness_check_id']}" in before_gate["evidence_refs"]
        assert f"scenario_run:{before_gate['scenario_run_id']}" in before_gate["evidence_refs"]
        before_result = next(r for r in before_gate["scenario_results"] if r["scenario_id"] == seeded["scenario_id"])
        assert before_result["status"] == "failed"
        assert before_result["expected_decision"] == "ESCALATE_TO_HUMAN"
        assert before_result["actual_decision"] == "OFFER_RETROACTIVE_REFUND"
        assert before_result["reason"] == "Expected ESCALATE_TO_HUMAN, got OFFER_RETROACTIVE_REFUND"

        after_gate = client.get(f"/v1/release-gate/checks/{seeded['release_gate_after_fix_id']}").json()
        assert after_gate["status"] == "pass"
        assert after_gate["failing_scenarios"] == []
        assert after_gate["certificate_id"]
        assert after_gate["certificate_id"] == seeded["release_gate_after_fix_certificate_id"]
        assert f"certificate:{after_gate['certificate_id']}" in after_gate["evidence_refs"]
        after_result = next(r for r in after_gate["scenario_results"] if r["scenario_id"] == seeded["scenario_id"])
        assert after_result["status"] == "passed"
        assert after_result["expected_decision"] == "ESCALATE_TO_HUMAN"
        assert after_result["actual_decision"] == "ESCALATE_TO_HUMAN"
        assert after_result["reason"] == ""

        cert = client.get(f"/v1/certificates/{after_gate['certificate_id']}").json()
        assert cert["certificate_type"] == "proof_of_readiness"
        assert cert["claim"]["scope_disclaimer"].startswith("This proof applies to the tested scenario")
        verify = client.get(f"/v1/certificates/{after_gate['certificate_id']}/verify").json()
        assert verify["signature_valid"] is True

    def test_action_eligibility_returns_reasons(self) -> None:
        self._seed_catalog()
        # Find a replayable record that has not yet been mutated/proven.
        all_vrs = client.get("/v1/verification-records").json()
        replayable_no_mutation = next(
            (v for v in all_vrs
             if v["replayability"] == "replayable"
             and not client.get(f"/v1/verification-records/{v['id']}/mutation-tests").json()),
            None,
        )
        if replayable_no_mutation is None:
            # Create a fresh replayable record for this assertion.
            snap = {
                "elements": [
                    {"kind": "http", "payload": {"request": {"method": "POST", "url": "/score"}, "response": {"score": 650}, "status": 200}},
                    {"kind": "decision", "payload": {"decision": "DENY"}},
                ],
                "root_hash": "demo-root",
            }
            vr = client.post("/v1/verification-records/from-snapshot", json=snap).json()
            client.post(f"/v1/verification-records/{vr['id']}/label?expected_outcome=APPROVE&reviewer=Test&role=QA&reason=demo")
            vr = client.get(f"/v1/verification-records/{vr['id']}").json()
        else:
            vr = replayable_no_mutation
        eligibility = client.get(f"/v1/verification-records/{vr['id']}/eligibility/replay").json()
        assert eligibility["eligible"] is True
        eligibility = client.get(f"/v1/verification-records/{vr['id']}/eligibility/issue_proof").json()
        assert eligibility["eligible"] is False
        assert eligibility["reason"]

    def test_sdk_install_ui_truthful(self) -> None:
        # The static app must not claim PyPI install is the primary path.
        app_js = client.get("/app/app.js").text
        assert "pip install notary-sdk" not in app_js
        assert "Python SDK" in app_js or "pip install" in app_js

    def test_vertical_path_end_to_end(self) -> None:
        """Golden path: seed → replay → mutation → proof → scenario → run → policy → gate."""
        self._seed_catalog()
        vr = self._find_replayable_vr()

        # Replay
        replay = client.post(f"/v1/verification-records/{vr['id']}/replay-runs").json()
        assert replay["status"] == "replayed"

        # Mutation
        mutation = client.post(
            f"/v1/verification-records/{vr['id']}/mutation-tests",
            json={
                "fix_config": {"require_policy_match_for_refund_claims": True, "escalate_when_policy_requires_human_review": True},
                "expected_correct_behavior": "ESCALATE_TO_HUMAN",
            },
        ).json()
        assert mutation["verdict"] == "verified"

        # Proof
        proof = client.post(f"/v1/verification-records/{vr['id']}/proof-of-mitigation").json()
        assert proof["certificate_type"] == "proof_of_mitigation"
        assert client.get(f"/v1/certificates/{proof['id']}/verify").json()["signature_valid"] is True

        # Scenario
        scenario = client.post("/v1/scenarios", params={"vr_id": vr["id"]}).json()
        assert scenario["source_vr_id"] == vr["id"]

        # Scenario Run
        run = client.post(
            "/v1/scenario-runs",
            json={"scenario_ids": [scenario["id"]], "agent_version": "1.2.0"},
        ).json()
        assert run["status"] == "completed"

        # Readiness Policy
        policy = client.post(
            "/v1/readiness-policies",
            json={"name": "Vertical Gate", "required_scenario_ids": [scenario["id"]]},
        ).json()

        # Readiness Check
        check = client.post(
            "/v1/readiness-checks",
            json={"policy_id": policy["id"], "agent_version": "1.2.0"},
        ).json()
        assert check["verdict"] in {"passed", "failed"}

        # Release Gate
        gate = client.post(
            "/v1/release-gate/checks",
            json={"policy_id": policy["id"], "agent_version": "1.2.0"},
        ).json()
        assert gate["status"] in {"pass", "fail", "error"}
        assert gate["ci_cd_command"]
