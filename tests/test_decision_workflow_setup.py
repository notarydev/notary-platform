"""Tests for the Decision Workflow setup API.

Proves:
- Create decision workflow
- List decision workflows
- Evidence source defaults per workflow type
- Save evidence boundary selections
- Setup status reflects workflow progress
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from notary_platform.api_server.main import app

client = TestClient(app)


class TestDecisionWorkflowSetup:
    def test_create_workflow(self) -> None:
        """POST /setup/decision-workflows creates a workflow."""
        resp = client.post(
            "/v1/setup/decision-workflows",
            json={
                "name": "Bereavement refund policy answer",
                "workflow_type": "refund_or_policy_answer",
                "description": "Bot decides refund or escalation",
                "common_failure": "Bot gives refund policy that does not exist",
                "expected_safe_outcome": "ESCALATE_TO_HUMAN",
                "risk_level": "high",
            },
        )
        assert resp.status_code == 200, resp.text
        wf = resp.json()
        assert wf["name"] == "Bereavement refund policy answer"
        assert wf["workflow_type"] == "refund_or_policy_answer"
        assert wf["expected_safe_outcome"] == "ESCALATE_TO_HUMAN"
        assert wf["risk_level"] == "high"
        assert wf["status"] == "draft"
        assert wf["id"].startswith("wf-")
        TestDecisionWorkflowSetup._wf_id = wf["id"]

    def test_list_workflows(self) -> None:
        """GET /setup/decision-workflows returns created workflows."""
        resp = client.get("/v1/setup/decision-workflows")
        assert resp.status_code == 200
        ids = [w["id"] for w in resp.json()]
        assert TestDecisionWorkflowSetup._wf_id in ids

    def test_get_workflow(self) -> None:
        """GET /setup/decision-workflows/{id} returns the workflow."""
        resp = client.get(f"/v1/setup/decision-workflows/{TestDecisionWorkflowSetup._wf_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Bereavement refund policy answer"

    def test_update_workflow(self) -> None:
        """PATCH /setup/decision-workflows/{id} updates fields."""
        resp = client.patch(
            f"/v1/setup/decision-workflows/{TestDecisionWorkflowSetup._wf_id}",
            json={"risk_level": "critical", "status": "configuring"},
        )
        assert resp.status_code == 200
        assert resp.json()["risk_level"] == "critical"
        assert resp.json()["status"] == "configuring"

    def test_evidence_sources_auto_seeded(self) -> None:
        """GET evidence-sources returns defaults for workflow type."""
        wid = TestDecisionWorkflowSetup._wf_id
        resp = client.get(f"/v1/setup/decision-workflows/{wid}/evidence-sources")
        assert resp.status_code == 200
        sources = resp.json()
        assert len(sources) >= 4
        required = [s for s in sources if s["required"]]
        assert len(required) >= 3
        assert any(s["source_type"] == "customer_support_record" for s in sources)
        assert any(s["source_type"] == "policy_knowledge_source" for s in sources)
        assert any(s["source_type"] == "ai_system_output" for s in sources)

    def test_save_evidence_sources(self) -> None:
        """PUT evidence-sources persists selections."""
        wid = TestDecisionWorkflowSetup._wf_id
        resp = client.get(f"/v1/setup/decision-workflows/{wid}/evidence-sources")
        sources = resp.json()
        for s in sources:
            s["selected"] = True
        resp = client.put(f"/v1/setup/decision-workflows/{wid}/evidence-sources", json=sources)
        assert resp.status_code == 200
        saved = resp.json()
        assert all(s["selected"] for s in saved)

    def test_setup_status_reflects_workflow(self) -> None:
        """GET /setup/status shows workflow_created true."""
        resp = client.get("/v1/setup/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("workflow_created") is True
        assert data.get("has_active_workflow") is True
        assert len(data.get("workflows", [])) >= 1
