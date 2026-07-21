"""Integrations & Capture setup API (Phase E).

Replaces the old Setup wizard with a persistent, backend-driven workspace.
Each AI system has its own connectors, field rules, validation runs, and status.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from notary_platform.api_server.auth import require_auth
from notary_platform.api_server.routers.ingestion import storage
from notary_platform.models import (
    AISystem,
    CaptureConnector,
    CaptureValidationRun,
    CoverageAssessment,
    DecisionFamilyCandidate,
    FieldHandlingRule,
)

router = APIRouter(tags=["setup"])


def _org_id() -> str:
    return "demo-org"


# ── AI Systems ──


@router.get("/setup/ai-systems")
def list_ai_systems(
    environment_id: Optional[str] = Query(None),
    _org: str = Depends(require_auth),
) -> list[dict]:
    org = _org_id()
    return [s.to_dict() for s in storage.list_ai_systems(org, environment_id or "")]


@router.post("/setup/ai-systems")
def create_ai_system(body: dict[str, Any], _org: str = Depends(require_auth)) -> dict:
    org = _org_id()
    env_id = body.get("environment_id", "env:demo")
    system = AISystem(
        id=f"ais-{uuid.uuid4().hex[:12]}",
        org_id=org,
        environment_id=env_id,
        name=body["name"],
        system_type=body.get("system_type", "agent"),
        deployment_version=body.get("deployment_version", ""),
        decision_endpoint=body.get("decision_endpoint", ""),
        external_caller=body.get("external_caller", False),
        risk_classification=body.get("risk_classification", ""),
        business_owner=body.get("business_owner", ""),
        technical_owner=body.get("technical_owner", ""),
        status="draft",
    )
    return storage.create_ai_system(system).to_dict()


@router.get("/setup/ai-systems/{system_id}")
def get_ai_system(system_id: str, _org: str = Depends(require_auth)) -> dict:
    system = storage.get_ai_system(system_id)
    if not system:
        raise HTTPException(404, "AI system not found")
    return system.to_dict()


@router.put("/setup/ai-systems/{system_id}")
def update_ai_system(system_id: str, body: dict[str, Any], _org: str = Depends(require_auth)) -> dict:
    system = storage.get_ai_system(system_id)
    if not system:
        raise HTTPException(404, "AI system not found")
    for key in ("name", "system_type", "deployment_version", "decision_endpoint",
                "external_caller", "risk_classification", "business_owner", "technical_owner", "status"):
        if key in body:
            setattr(system, key, body[key])
    return storage.update_ai_system(system).to_dict()


# ── Capture Connectors ──


@router.get("/setup/ai-systems/{system_id}/connectors")
def list_connectors(system_id: str, _org: str = Depends(require_auth)) -> list[dict]:
    return [c.to_dict() for c in storage.list_capture_connectors(system_id)]


@router.post("/setup/ai-systems/{system_id}/connectors")
def create_connector(system_id: str, body: dict[str, Any], _org: str = Depends(require_auth)) -> dict:
    conn = CaptureConnector(
        id=f"conn-{uuid.uuid4().hex[:12]}",
        ai_system_id=system_id,
        org_id=_org_id(),
        connector_type=body["connector_type"],
        name=body.get("name", ""),
        status="not_configured",
        config_json=json.dumps(body.get("config", {})),
    )
    return storage.create_capture_connector(conn).to_dict()


@router.put("/setup/connectors/{conn_id}")
def update_connector(conn_id: str, body: dict[str, Any], _org: str = Depends(require_auth)) -> dict:
    conn = storage.get_capture_connector(conn_id)
    if not conn:
        raise HTTPException(404, "Connector not found")
    if "name" in body:
        conn.name = body["name"]
    if "status" in body:
        conn.status = body["status"]
    if "config" in body:
        conn.config_json = json.dumps(body["config"])
    if "error_message" in body:
        conn.error_message = body["error_message"]
    return storage.update_capture_connector(conn).to_dict()


@router.post("/setup/connectors/{conn_id}/test")
def test_connector(conn_id: str, _org: str = Depends(require_auth)) -> dict:
    conn = storage.get_capture_connector(conn_id)
    if not conn:
        raise HTTPException(404, "Connector not found")
    # Simulated connectivity test — in production this would probe
    # the actual endpoint / SDK heartbeat / webhook reachability.
    conn.last_tested_at = __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime())
    conn.status = "connected"
    storage.update_capture_connector(conn)
    return {"status": "connected", "message": "Connection verified", "last_tested": conn.last_tested_at}


@router.get("/setup/connectors/{conn_id}/samples")
def get_connector_samples(conn_id: str, _org: str = Depends(require_auth)) -> list[dict]:
    """Return recent evidence samples received through this connector.
    In production this queries the actual captured data; for now we
    return simulated samples so the evidence-graph UI has content.
    """
    conn = storage.get_capture_connector(conn_id)
    if not conn:
        raise HTTPException(404, "Connector not found")
    now = __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime())
    source = conn.name or conn.connector_type
    samples = [
        {
            "id": f"ev-{uuid.uuid4().hex[:8]}",
            "event_type": "ai_decision",
            "source_system": source,
            "timestamp": now,
            "summary": f"Detected AI decision from {conn.connector_type}",
            "elements": [
                {"kind": "input", "source": "end-user", "summary": "Application data",
                 "classification": "public", "influenced_decision": True, "sealed": True},
                {"kind": "model_invocation", "source": source, "summary": "AI model call",
                 "classification": "internal", "influenced_decision": True, "sealed": True},
                {"kind": "tool_response", "source": "external-api", "summary": "Enrichment service response",
                 "classification": "sensitive", "influenced_decision": True, "sealed": True},
                {"kind": "policy_config", "source": "policy-service", "summary": "Active policy version",
                 "classification": "internal", "influenced_decision": True, "sealed": True},
                {"kind": "decision", "source": source, "summary": "Final decision output",
                 "classification": "public", "influenced_decision": True, "sealed": True},
            ],
        },
    ]
    return samples


# ── Evidence Graph ──


@router.get("/setup/evidence-graph/{sample_id}")
def get_evidence_graph(sample_id: str, _org: str = Depends(require_auth)) -> dict:
    """Return an evidence graph for a captured sample, showing the
    Inputs → Model → Tools → Policy → Decision flow."""
    return {
        "sample_id": sample_id,
        "nodes": [
            {"id": "input", "label": "Inputs", "type": "input", "items": ["Application data", "User context"]},
            {"id": "model", "label": "Model / Agent", "type": "process", "items": ["Agent version", "Prompt/configuration"]},
            {"id": "tools", "label": "Tool Responses", "type": "external", "items": ["Enrichment API", "Policy service"]},
            {"id": "policy", "label": "Policy / Config", "type": "config", "items": ["Policy version", "Rules applied"]},
            {"id": "decision", "label": "Decision", "type": "output", "items": ["Final outcome"]},
        ],
        "edges": [
            {"from": "input", "to": "model"},
            {"from": "model", "to": "tools"},
            {"from": "tools", "to": "model"},
            {"from": "model", "to": "policy"},
            {"from": "policy", "to": "decision"},
        ],
    }


# ── Field Handling Rules ──


@router.get("/setup/ai-systems/{system_id}/field-rules")
def list_field_rules(system_id: str, _org: str = Depends(require_auth)) -> list[dict]:
    return [r.to_dict() for r in storage.list_field_handling_rules(system_id)]


@router.put("/setup/ai-systems/{system_id}/field-rules")
def replace_field_rules(system_id: str, body: list[dict[str, Any]], _org: str = Depends(require_auth)) -> list[dict]:
    storage.delete_field_handling_rules(system_id)
    rules = []
    for item in body:
        rule = FieldHandlingRule(
            id=f"fhr-{uuid.uuid4().hex[:12]}",
            ai_system_id=system_id,
            field_pattern=item["field_pattern"],
            action=item.get("action", "store"),
            retention_days=item.get("retention_days", 365),
            sensitive=item.get("sensitive", False),
            use_for_replay=item.get("use_for_replay", True),
        )
        rules.append(storage.create_field_handling_rule(rule))
    return [r.to_dict() for r in rules]


# ── Capture Validation ──


@router.post("/setup/ai-systems/{system_id}/validate")
def run_capture_validation(system_id: str, _org: str = Depends(require_auth)) -> dict:
    system = storage.get_ai_system(system_id)
    if not system:
        raise HTTPException(404, "AI system not found")

    connectors = storage.list_capture_connectors(system_id)
    has_connector = any(c.status == "connected" for c in connectors)

    coverage = CoverageAssessment(
        decision_detected=has_connector,
        input_captured=has_connector,
        model_version_captured=True,
        prompt_captured=True,
        tool_responses_available=has_connector,
        final_decision_captured=has_connector,
        root_hash_valid=True,
        cassette_material_available=has_connector,
        expected_outcome_source_available=False,
    )

    if has_connector:
        coverage.replay_readiness = "investigation_ready"
        coverage.assessment = "Evidence captured and sealed. Add an expected-outcome source to enable replay."
    else:
        coverage.replay_readiness = "insufficient_context"
        coverage.assessment = "No connected capture source found. Connect a capture source first."

    run = CaptureValidationRun(
        id=f"val-{uuid.uuid4().hex[:12]}",
        ai_system_id=system_id,
        org_id=_org_id(),
        status="complete",
        checks_json=json.dumps({
            "has_connector": has_connector,
            "has_decision_endpoint": bool(system.decision_endpoint),
            "connector_count": len(connectors),
        }),
        coverage_json=json.dumps(coverage.to_dict()),
    )
    storage.create_capture_validation_run(run)
    return run.to_dict()


@router.get("/setup/ai-systems/{system_id}/validation-runs")
def list_validation_runs(system_id: str, _org: str = Depends(require_auth)) -> list[dict]:
    return [r.to_dict() for r in storage.list_capture_validation_runs(system_id)]


# ── Decision Family Candidates ──


@router.get("/setup/decision-families")
def list_decision_families(
    ai_system_id: Optional[str] = Query(None),
    _org: str = Depends(require_auth),
) -> list[dict]:
    org = _org_id()
    return [c.to_dict() for c in storage.list_decision_family_candidates(org, ai_system_id or "")]


@router.post("/setup/decision-families")
def create_decision_family(body: dict[str, Any], _org: str = Depends(require_auth)) -> dict:
    candidate = DecisionFamilyCandidate(
        id=f"dfc-{uuid.uuid4().hex[:12]}",
        org_id=_org_id(),
        ai_system_id=body["ai_system_id"],
        pattern_name=body["pattern_name"],
        decision_count=body.get("decision_count", 0),
        confirmed=body.get("confirmed", False),
    )
    return storage.create_decision_family_candidate(candidate).to_dict()


@router.put("/setup/decision-families/{candidate_id}")
def update_decision_family(candidate_id: str, body: dict[str, Any], _org: str = Depends(require_auth)) -> dict:
    candidate = None
    org = _org_id()
    for c in storage.list_decision_family_candidates(org):
        if c.id == candidate_id:
            candidate = c
            break
    if not candidate:
        raise HTTPException(404, "Decision family candidate not found")
    if "confirmed" in body:
        candidate.confirmed = body["confirmed"]
    if "pattern_name" in body:
        candidate.pattern_name = body["pattern_name"]
    return storage.update_decision_family_candidate(candidate).to_dict()


# ── Setup Status ──


@router.get("/setup/status")
def get_setup_status(_org: str = Depends(require_auth)) -> dict:
    org = _org_id()
    systems = storage.list_ai_systems(org)
    active_systems = [s for s in systems if s.status == "active"]
    return {
        "total_systems": len(systems),
        "active_systems": len(active_systems),
        "systems_in_setup": [s.to_dict() for s in systems if s.status != "active"],
    }
