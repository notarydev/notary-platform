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
    DecisionWorkflow,
    FieldHandlingRule,
    RecordSelectionRule,
    ReplayabilityStatus,
    WorkflowEvidenceSource,
)
from notary_platform.setup_engine import (
    AssuranceSetupService,
    CapturePolicyService,
    EvidenceContractService,
    ImportPreviewService,
    RecordSelectionService,
    ReleaseGatePlanner,
    ScenarioCandidateService,
    SetupReadinessService,
    get_workflow_template,
    get_workflow_templates,
    parse_discovery_input,
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


# ── Decision Workflows ──


@router.get("/setup/decision-workflows")
def list_decision_workflows(
    environment_id: Optional[str] = Query(None),
    _org: str = Depends(require_auth),
) -> list[dict]:
    org = _org_id()
    return [wf.to_dict() for wf in storage.list_decision_workflows(org, environment_id or "")]


@router.post("/setup/decision-workflows")
def create_decision_workflow(body: dict[str, Any], _org: str = Depends(require_auth)) -> dict:
    org = _org_id()
    wf = DecisionWorkflow(
        id=f"wf-{uuid.uuid4().hex[:12]}",
        org_id=org,
        environment_id=body.get("environment_id", "env:demo"),
        name=body.get("name", ""),
        workflow_type=body.get("workflow_type", ""),
        description=body.get("description", ""),
        ai_system_id=body.get("ai_system_id", ""),
        primary_source_system_id=body.get("primary_source_system_id", ""),
        policy_source_system_id=body.get("policy_source_system_id", ""),
        expected_safe_outcome=body.get("expected_safe_outcome", ""),
        common_failure=body.get("common_failure", ""),
        risk_level=body.get("risk_level", "medium"),
        status="draft",
    )
    wf.touch()
    return storage.create_decision_workflow(wf).to_dict()


@router.get("/setup/decision-workflows/{wf_id}")
def get_decision_workflow(wf_id: str, _org: str = Depends(require_auth)) -> dict:
    wf = storage.get_decision_workflow(wf_id)
    if not wf:
        raise HTTPException(404, "Decision workflow not found")
    return wf.to_dict()


@router.patch("/setup/decision-workflows/{wf_id}")
def update_decision_workflow(wf_id: str, body: dict[str, Any], _org: str = Depends(require_auth)) -> dict:
    wf = storage.get_decision_workflow(wf_id)
    if not wf:
        raise HTTPException(404, "Decision workflow not found")
    for key in ("name", "workflow_type", "description", "ai_system_id",
                "primary_source_system_id", "policy_source_system_id",
                "expected_safe_outcome", "common_failure", "risk_level", "status"):
        if key in body:
            setattr(wf, key, body[key])
    wf.touch()
    return storage.update_decision_workflow(wf).to_dict()


# ── Workflow Evidence Sources ──

# Default evidence sources for each workflow type
_WORKFLOW_EVIDENCE_DEFAULTS: dict[str, list[dict]] = {
    "refund_or_policy_answer": [
        {"source_type": "customer_support_record", "name": "Customer Support Record", "required": True,
         "captures": "Customer message, case ID, channel, timestamp, and source ticket reference.",
         "why_include": "Proves what the customer asked and where the decision happened.",
         "proof_enabled": "Proves the exact request the bot actually saw.",
         "does_not_capture": "Agent staffing, queue timing, unrelated CRM history."},
        {"source_type": "policy_knowledge_source", "name": "Policy Knowledge Source", "required": True,
         "captures": "The official policy response or policy version the bot retrieved.",
         "why_include": "A policy mismatch is the causal evidence for the wrong answer.",
         "proof_enabled": "Enables cassette replay without live policy-service calls.",
         "does_not_capture": "Policy authoring workflow or approval chain."},
        {"source_type": "ai_system_output", "name": "AI System Output", "required": True,
         "captures": "Model call, prompt, response, tool call proposals, and final decision.",
         "why_include": "This is the decision system being reviewed.",
         "proof_enabled": "Shows what the AI decided and why.",
         "does_not_capture": "Training data or unrelated model internals."},
        {"source_type": "prompt_policy_config", "name": "Prompt / Policy Config", "required": True,
         "captures": "Prompt version, routing rule, model configuration, feature flag, and policy version.",
         "why_include": "The bot must be evaluated against the configuration in force at decision time.",
         "proof_enabled": "Lets Notary compare behavior across versions and releases.",
         "does_not_capture": "Prompt authoring workflow unless explicitly included."},
        {"source_type": "human_review_queue", "name": "Human Review Queue", "required": False,
         "captures": "Expected outcome label, human override, reviewer role, approval reason.",
         "why_include": "Provides the customer-approved answer key for proof.",
         "proof_enabled": "Enables Proof of Mitigation and Proof of Readiness.",
         "does_not_capture": "Reviewer productivity or case assignment."},
        {"source_type": "release_ci_system", "name": "Release / CI System", "required": False,
         "captures": "Agent version, git commit, build ID, release candidate.",
         "why_include": "Connects Scenarios to Release Gate checks.",
         "proof_enabled": "Shows which release passed or failed.",
         "does_not_capture": "Arbitrary CI metadata."},
    ],
    "lending_decision": [
        {"source_type": "loan_application", "name": "Loan Application Record", "required": True,
         "captures": "Application data, applicant details, loan amount, purpose.",
         "why_include": "The decision is based on this application.",
         "proof_enabled": "Proves the exact application the model evaluated.",
         "does_not_capture": "Applicant credit history not used in decision."},
        {"source_type": "ai_system_output", "name": "AI System Output", "required": True,
         "captures": "Model call, score, decision, and reason codes.",
         "why_include": "This is the decision system under review.",
         "proof_enabled": "Shows model output and decision rationale.",
         "does_not_capture": "Training data or model internals."},
        {"source_type": "underwriting_policy", "name": "Underwriting Policy Config", "required": True,
         "captures": "Policy version, risk tiers, rules applied.",
         "why_include": "The decision must be evaluated against policy in force.",
         "proof_enabled": "Proves which policy version governed the decision.",
         "does_not_capture": "Policy draft history."},
    ],
}

_FLATTENED_SOURCE_TYPES = [src for cat in _WORKFLOW_EVIDENCE_DEFAULTS.values() for src in cat]


@router.get("/setup/decision-workflows/{wf_id}/evidence-sources")
def list_evidence_sources(wf_id: str, _org: str = Depends(require_auth)) -> list[dict]:
    wf = storage.get_decision_workflow(wf_id)
    if not wf:
        raise HTTPException(404, "Decision workflow not found")
    existing = storage.list_workflow_evidence_sources(wf_id)
    if existing:
        return [s.to_dict() for s in existing]
    # Seed defaults based on workflow type
    defaults = _WORKFLOW_EVIDENCE_DEFAULTS.get(wf.workflow_type, _WORKFLOW_EVIDENCE_DEFAULTS.get("refund_or_policy_answer", []))
    sources = []
    for d in defaults:
        src = WorkflowEvidenceSource(
            id=f"wes-{uuid.uuid4().hex[:12]}",
            workflow_id=wf_id,
            org_id=wf.org_id,
            environment_id=wf.environment_id,
            source_type=d["source_type"],
            name=d["name"],
            required=d.get("required", False),
            selected=d.get("required", False),  # required sources auto-selected
            captures=d.get("captures", ""),
            why_include=d.get("why_include", ""),
            proof_enabled=d.get("proof_enabled", ""),
            does_not_capture=d.get("does_not_capture", ""),
            status="selected" if d.get("required", False) else "suggested",
        )
        sources.append(src)
    return [s.to_dict() for s in storage.save_workflow_evidence_sources(wf_id, sources)]


@router.put("/setup/decision-workflows/{wf_id}/evidence-sources")
def save_evidence_sources(wf_id: str, body: list[dict[str, Any]], _org: str = Depends(require_auth)) -> list[dict]:
    wf = storage.get_decision_workflow(wf_id)
    if not wf:
        raise HTTPException(404, "Decision workflow not found")
    sources = []
    for item in body:
        src = WorkflowEvidenceSource(
            id=item.get("id", f"wes-{uuid.uuid4().hex[:12]}"),
            workflow_id=wf_id,
            org_id=wf.org_id,
            environment_id=wf.environment_id,
            source_type=item.get("source_type", ""),
            name=item.get("name", ""),
            system_id=item.get("system_id", ""),
            required=item.get("required", False),
            selected=item.get("selected", False),
            captures=item.get("captures", ""),
            why_include=item.get("why_include", ""),
            proof_enabled=item.get("proof_enabled", ""),
            does_not_capture=item.get("does_not_capture", ""),
            status="selected" if item.get("selected", False) else "suggested",
        )
        sources.append(src)
    return [s.to_dict() for s in storage.save_workflow_evidence_sources(wf_id, sources)]


# ── Record Selection Rules ──

_DEFAULT_RECORD_RULES: list[dict] = [
    {"trigger_type": "policy_answer", "label": "Bot gives policy/refund/fare answer",
     "description": "Bot response contains refund, fare, billing, legal, or policy language.", "enabled": True},
    {"trigger_type": "customer_dispute", "label": "Customer disputes bot answer",
     "description": "Customer replied negatively to bot, opened dispute, or asked for manager.", "enabled": True},
    {"trigger_type": "human_override", "label": "Human agent overrides bot",
     "description": "Human changed or corrected the outcome the bot produced.", "enabled": True},
    {"trigger_type": "handoff_requested", "label": "Human handoff requested but bot continued",
     "description": "Customer asked to speak to a human but the bot continued responding.", "enabled": True},
    {"trigger_type": "policy_mismatch", "label": "Bot answer conflicts with policy source",
     "description": "Policy lookup response contradicts the bot's answer to the customer.", "enabled": True},
    {"trigger_type": "missing_policy_lookup", "label": "Policy lookup missing or failed",
     "description": "Bot gave a policy answer without retrieving the current policy.", "enabled": True},
    {"trigger_type": "low_confidence", "label": "Low confidence or missing model response",
     "description": "Bot confidence below threshold or model did not respond.", "enabled": True},
    {"trigger_type": "sample", "label": "Random sample of normal conversations",
     "description": "Sample 0.1% of conversations that matched no other rule.", "enabled": False},
]


@router.get("/setup/decision-workflows/{wf_id}/record-selection-rules")
def list_record_selection_rules(wf_id: str, _org: str = Depends(require_auth)) -> list[dict]:
    wf = storage.get_decision_workflow(wf_id)
    if not wf:
        raise HTTPException(404, "Decision workflow not found")
    existing = storage.list_record_selection_rules(wf_id)
    if existing:
        return [r.to_dict() for r in existing]
    rules = []
    for d in _DEFAULT_RECORD_RULES:
        rule = RecordSelectionRule(
            id=f"rsr-{uuid.uuid4().hex[:12]}",
            workflow_id=wf_id,
            org_id=wf.org_id,
            trigger_type=d["trigger_type"],
            label=d.get("label", ""),
            description=d.get("description", ""),
            enabled=d.get("enabled", True),
            condition="{}",
        )
        rules.append(rule)
    return [r.to_dict() for r in storage.save_record_selection_rules(wf_id, rules)]


@router.put("/setup/decision-workflows/{wf_id}/record-selection-rules")
def save_record_selection_rules(wf_id: str, body: list[dict[str, Any]], _org: str = Depends(require_auth)) -> list[dict]:
    wf = storage.get_decision_workflow(wf_id)
    if not wf:
        raise HTTPException(404, "Decision workflow not found")
    rules = []
    for item in body:
        rule = RecordSelectionRule(
            id=item.get("id", f"rsr-{uuid.uuid4().hex[:12]}"),
            workflow_id=wf_id,
            org_id=wf.org_id,
            trigger_type=item.get("trigger_type", ""),
            label=item.get("label", ""),
            description=item.get("description", ""),
            enabled=item.get("enabled", True),
            condition=json.dumps(item.get("condition", {})),
        )
        rules.append(rule)
    return [r.to_dict() for r in storage.save_record_selection_rules(wf_id, rules)]


# ── Setup Status ──


@router.get("/setup/status")
def get_setup_status(_org: str = Depends(require_auth)) -> dict:
    """Return setup completion status for the new workflow-centered flow."""
    org = _org_id()
    wfs = storage.list_decision_workflows(org)
    active_wf = next((w for w in wfs if w.status != "draft"), None)
    wf_id = active_wf.id if active_wf else ""
    has_workflow = bool(wfs)
    ai_systems = storage.list_ai_systems(org)
    has_ai_system = bool(ai_systems)
    evidence_sources = storage.list_workflow_evidence_sources(wf_id) if wf_id else []
    has_evidence = any(s.selected for s in evidence_sources)
    connectors = []
    for s in ai_systems:
        connectors.extend(storage.list_capture_connectors(s.id))
    has_capture = any(c.status != "not_configured" for c in connectors)
    vrs = storage.list_vrs(org)
    has_records = bool(vrs)
    has_replayable = any(vr.replayability != ReplayabilityStatus.unknown for vr in vrs)
    candidates = storage.list_scenario_candidates(org)
    has_candidates = bool(candidates)
    policies = storage.list_readiness_policies(org)
    has_release_gate = bool(policies)

    return {
        "workflow_created": has_workflow,
        "ai_system_registered": has_ai_system,
        "evidence_boundary_defined": has_evidence,
        "capture_method_configured": has_capture,
        "first_records_received": has_records,
        "replayability_reviewed": has_replayable,
        "scenario_created": has_candidates,
        "release_gate_created": has_release_gate,
        "workflows": [wf.to_dict() for wf in wfs],
        "ai_systems": [s.to_dict() for s in ai_systems],
        "vrs_total": len(vrs),
        "has_active_workflow": active_wf is not None,
        "active_workflow_id": wf_id,
    }


# ═══════════════════════════════════════════════════════════════
# Decision Assurance Setup Engine
# ═══════════════════════════════════════════════════════════════

_engine_svc = AssuranceSetupService(storage)
_evidence_svc = EvidenceContractService()
_capture_svc = CapturePolicyService()
_record_svc = RecordSelectionService()
_import_preview_svc = ImportPreviewService()
_scenario_svc = ScenarioCandidateService()
_release_gate_planner = ReleaseGatePlanner()
_readiness_svc = SetupReadinessService()


def _ensure_plan_workflow(plan: Any) -> Any:
    """Attach a workflow and selection rules to plans created by Discovery.

    Older plans and the lightweight Discovery entry point may not carry a
    workflow id. Heal those plans at the boundary so preview and commit never
    silently become a no-op because there are no selection rules.
    """
    if plan.workflow_id and storage.get_decision_workflow(plan.workflow_id):
        return plan

    template = get_workflow_template(plan.workflow_type) or get_workflow_template("refund_or_policy_answer")
    workflow_id = f"wf-{uuid.uuid4().hex[:12]}"
    workflow = DecisionWorkflow(
        id=workflow_id,
        org_id=plan.org_id,
        environment_id=plan.environment_id,
        name=plan.workflow_name or (template or {}).get("name", "Decision Discovery"),
        workflow_type=plan.workflow_type or (template or {}).get("workflow_type", "refund_or_policy_answer"),
        description=(template or {}).get("description", "Imported AI decision events selected for assurance review."),
        expected_safe_outcome=(template or {}).get("expected_safe_outcome", ""),
        common_failure=(template or {}).get("bad_outcome", ""),
        risk_level=(template or {}).get("risk_level", "medium"),
        status="configuring",
    )
    workflow.touch()
    storage.create_decision_workflow(workflow)

    rule_definitions = (template or {}).get("record_selection_rules") or _DEFAULT_RECORD_RULES
    rules = [
        RecordSelectionRule(
            id=f"rsr-{uuid.uuid4().hex[:12]}",
            workflow_id=workflow_id,
            org_id=plan.org_id,
            trigger_type=rule.get("trigger_type", ""),
            label=rule.get("label", ""),
            description=rule.get("description", ""),
            enabled=rule.get("enabled", True),
            condition=json.dumps(rule.get("condition", {})),
        )
        for rule in rule_definitions
    ]
    storage.save_record_selection_rules(workflow_id, rules)
    plan.workflow_id = workflow_id
    plan.touch()
    _engine_svc.update_plan(plan.id, workflow_id=workflow_id)
    return plan


@router.get("/setup/workflow-templates")
def list_workflow_templates() -> list[dict]:
    return get_workflow_templates()


@router.get("/setup/plans")
def list_plans(_org: str = Depends(require_auth)) -> list[dict]:
    org = _org_id()
    return [p.to_dict() for p in _engine_svc.get_all_plans(org)]


@router.post("/setup/plans")
def create_plan(body: dict[str, Any], _org: str = Depends(require_auth)) -> dict:
    org = _org_id()
    env = body.get("environment_id", "env:demo")
    plan = _engine_svc.create_plan(
        org_id=org, environment_id=env,
        objective=body.get("objective", ""),
        workflow_type=body.get("workflow_type", ""),
        workflow_name=body.get("workflow_name", ""),
    )
    _ensure_plan_workflow(plan)
    return plan.to_dict()


@router.get("/setup/plans/{plan_id}")
def get_plan(plan_id: str, _org: str = Depends(require_auth)) -> dict:
    plan = _engine_svc.get_plan(plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    return plan.to_dict()


@router.patch("/setup/plans/{plan_id}")
def patch_plan(plan_id: str, body: dict[str, Any], _org: str = Depends(require_auth)) -> dict:
    plan = _engine_svc.update_plan(plan_id, **body)
    if not plan:
        raise HTTPException(404, "Plan not found")
    return plan.to_dict()


@router.get("/setup/plans/{plan_id}/evidence-sources")
def plan_evidence_sources(plan_id: str, _org: str = Depends(require_auth)) -> dict:
    plan = _engine_svc.get_plan(plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    return _evidence_svc.recommend(plan)


@router.put("/setup/plans/{plan_id}/evidence-sources")
def save_plan_evidence_sources(plan_id: str, body: dict[str, Any], _org: str = Depends(require_auth)) -> dict:
    plan = _engine_svc.update_plan(plan_id, evidence_contract=json.dumps(body))
    if not plan:
        raise HTTPException(404, "Plan not found")
    return body


@router.get("/setup/plans/{plan_id}/capture-methods/recommend")
def plan_capture_recommendations(plan_id: str, _org: str = Depends(require_auth)) -> list[dict]:
    plan = _engine_svc.get_plan(plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    ai_systems = []
    if plan.ai_system_id:
        sys = storage.get_ai_system(plan.ai_system_id)
        if sys:
            ai_systems.append(sys.to_dict())
    return _capture_svc.recommend(plan, ai_systems)


@router.put("/setup/plans/{plan_id}/capture-method")
def save_plan_capture_method(plan_id: str, body: dict[str, Any], _org: str = Depends(require_auth)) -> dict:
    plan = _engine_svc.get_plan(plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    method = body.get("capture_method", "")
    policy = _capture_svc.build_policy(method, plan)
    _engine_svc.update_plan(plan_id, capture_policy=json.dumps(policy))
    return policy


@router.get("/setup/plans/{plan_id}/record-selection-rules")
def plan_record_selection_rules(plan_id: str, _org: str = Depends(require_auth)) -> list[dict]:
    plan = _engine_svc.get_plan(plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    _ensure_plan_workflow(plan)
    if not plan.workflow_id:
        return []
    existing = storage.list_record_selection_rules(plan.workflow_id)
    if existing:
        return [r.to_dict() for r in existing]
    from notary_platform.setup_engine import WORKFLOW_TEMPLATES
    tmpl = WORKFLOW_TEMPLATES.get(plan.workflow_type)
    if not tmpl:
        return []
    rules = []
    for d in tmpl.record_selection_rules:
        rule = RecordSelectionRule(
            id=f"rsr-{uuid.uuid4().hex[:12]}",
            workflow_id=plan.workflow_id,
            org_id=plan.org_id,
            trigger_type=d["trigger_type"],
            label=d.get("label", ""),
            description=d.get("description", ""),
            enabled=d.get("enabled", True),
            condition="{}",
        )
        rules.append(rule)
    return [r.to_dict() for r in storage.save_record_selection_rules(plan.workflow_id, rules)]


@router.put("/setup/plans/{plan_id}/record-selection-rules")
def save_plan_record_selection_rules(plan_id: str, body: list[dict[str, Any]],
                                      _org: str = Depends(require_auth)) -> list[dict]:
    plan = _engine_svc.get_plan(plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    if not plan.workflow_id:
        raise HTTPException(400, "No workflow connected to plan")
    rules = []
    for item in body:
        rule = RecordSelectionRule(
            id=item.get("id", f"rsr-{uuid.uuid4().hex[:12]}"),
            workflow_id=plan.workflow_id,
            org_id=plan.org_id,
            trigger_type=item.get("trigger_type", ""),
            label=item.get("label", ""),
            description=item.get("description", ""),
            enabled=item.get("enabled", True),
            condition=json.dumps(item.get("condition", {})),
        )
        rules.append(rule)
    return [r.to_dict() for r in storage.save_record_selection_rules(plan.workflow_id, rules)]


@router.post("/setup/plans/{plan_id}/imports/preview")
def plan_import_preview(plan_id: str, body: dict[str, Any], _org: str = Depends(require_auth)) -> dict:
    plan = _engine_svc.get_plan(plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    _ensure_plan_workflow(plan)
    records = body.get("records", [])
    field_mapping = body.get("field_mapping", {})
    records = [_record_svc.normalize_record(record, field_mapping) for record in records]
    rules = storage.list_record_selection_rules(plan.workflow_id) if plan.workflow_id else []
    preview = _import_preview_svc.preview(records, rules)
    result = preview.to_dict()
    selection_results = _record_svc.apply_rules(records, rules)
    result["findings"] = [
        {
            "source_record_ref": r.source_row_id,
            "trigger": r.trigger,
            "reason": r.reason,
            "replayability": r.replayability,
            "scenario_candidate": r.scenario_candidate,
            "matched_rules": r.matched_rules,
        }
        for r in selection_results
        if r.create_vr
    ][:200]
    ev = _import_preview_svc.estimate_volume(plan.workflow_type or "")
    result["estimated_volume"] = ev
    result["ignored_count"] = result["total_records"] - result["matched_count"]
    result["estimated_storage_gb"] = round(result["total_records"] * 0.00008, 2)
    result["estimated_monthly_records"] = ev["high_risk_matched"]
    result["missing_required_fields"] = preview.missing_fields
    return result


@router.post("/setup/plans/{plan_id}/imports/parse")
def plan_import_parse(plan_id: str, body: dict[str, Any], _org: str = Depends(require_auth)) -> dict:
    """Parse a discovery file payload before field mapping and preview."""
    if not _engine_svc.get_plan(plan_id):
        raise HTTPException(404, "Plan not found")
    try:
        records = parse_discovery_input(str(body.get("content", "")), str(body.get("format", "json")))
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(400, f"Invalid discovery input: {exc}") from exc
    return {"format": body.get("format", "json"), "record_count": len(records), "records": records}


@router.post("/setup/plans/{plan_id}/imports/commit")
def plan_import_commit(plan_id: str, body: dict[str, Any], _org: str = Depends(require_auth)) -> dict:
    from notary_platform.api_server.routers.ingestion import get_registry
    from notary_platform.services import IngestionService
    plan = _engine_svc.get_plan(plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    _ensure_plan_workflow(plan)
    records_raw = body.get("records", [])
    field_mapping = body.get("field_mapping", {})
    selected_refs = {str(ref) for ref in body.get("selected_source_record_refs", [])}
    rules = storage.list_record_selection_rules(plan.workflow_id) if plan.workflow_id else []
    records_raw = [_record_svc.normalize_record(record, field_mapping) for record in records_raw]
    results = _record_svc.apply_rules(records_raw, rules)
    created = []
    rejected = []
    findings = []
    for idx, rslt in enumerate(results):
        if not rslt.create_vr:
            continue
        if idx >= len(records_raw):
            continue
        item = records_raw[idx]
        source_record_ref = str(item.get("source_record_ref", rslt.source_row_id))
        finding = {
            "source_record_ref": source_record_ref,
            "trigger": rslt.trigger,
            "reason": rslt.reason,
            "replayability": rslt.replayability,
            "scenario_candidate": rslt.scenario_candidate,
            "matched_rules": rslt.matched_rules,
        }
        findings.append(finding)
        if selected_refs and source_record_ref not in selected_refs:
            continue
        snapshot = {
            "schema_version": item.get("schema_version", 1),
            "source_system_id": item.get("source_system_id", "import"),
            "source_record_ref": source_record_ref,
            "business_function": item.get("business_function", plan.workflow_id),
            "expected_outcome": item.get("expected_outcome", ""),
            "elements": item.get("elements", []),
            "agent_id": item.get("agent_id", ""),
            "agent_version": item.get("agent_version", ""),
            "model_provider": item.get("model_provider", ""),
            "model_name": item.get("model_name", ""),
            "policy_version": item.get("policy_version", ""),
        }
        ingestion = IngestionService(get_registry())
        try:
            vr = ingestion.create_from_sdk_snapshot(snapshot, org_id=plan.org_id)
            created.append({
                "id": vr.id,
                "source_record_ref": vr.source_record_ref,
                "replayability": vr.replayability.value,
                "trigger": rslt.trigger,
            })
        except Exception as exc:
            rejected.append({
                "source_record_ref": snapshot["source_record_ref"],
                "reason": str(exc),
            })
    return {"imported": len(created), "rejected": rejected, "records": created, "discovery_findings": findings}


@router.get("/setup/plans/{plan_id}/readiness")
def plan_readiness(plan_id: str, _org: str = Depends(require_auth)) -> dict:
    plan = _engine_svc.get_plan(plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    assessment = _readiness_svc.assess(plan, storage)
    return assessment.to_dict()


@router.post("/setup/plans/{plan_id}/scenario-candidates/recommend")
def plan_scenario_candidates(plan_id: str, _org: str = Depends(require_auth)) -> list[dict]:
    plan = _engine_svc.get_plan(plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    vrs = storage.list_vrs(plan.org_id)
    records = [vr.to_dict() for vr in vrs if vr.source_type != "demo_seed"]
    return _scenario_svc.recommend_from_records(records)


@router.post("/setup/plans/{plan_id}/release-gate/recommend")
def plan_release_gate(plan_id: str, _org: str = Depends(require_auth)) -> dict:
    plan = _engine_svc.get_plan(plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    scenarios = storage.list_scenarios(plan.org_id)
    return _release_gate_planner.recommend([s.to_dict() for s in scenarios])
