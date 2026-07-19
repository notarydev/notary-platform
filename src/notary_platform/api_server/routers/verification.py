"""Verification Record intake and assessment router (WO-69/70/71).

Phase 2 canonical intake for all AI decision evidence, regardless
of capture source. Handles SDK snapshots, API submissions, manual
entries, and webhook intake.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from notary_platform.api_server.auth import require_auth
from notary_platform.api_server.routers.ingestion import storage
from notary_platform.models import (
    AIExecutionEvent,
    DataSourceType,
    EventKind,
    HumanLabel,
    ReplayabilityStatus,
    VerificationRecord,
    sdk_element_to_event,
)

router = APIRouter(tags=["verification"])

# In-memory V.R. store. Production replaces with Postgres persistence.
_vr_store: dict[str, VerificationRecord] = {}
_label_store: dict[str, HumanLabel] = {}


def _next_vr_id() -> str:
    return f"vr-{uuid.uuid4().hex[:8]}"


def _assess_replayability(vr: VerificationRecord) -> tuple[ReplayabilityStatus, str, list[str]]:
    has_llm = any(e.kind == EventKind.model_call for e in vr.events)
    has_cassette = any(e.kind in (EventKind.api_response, EventKind.tool_call) for e in vr.events)
    has_decision = any(e.kind == EventKind.decision for e in vr.events)
    has_label = bool(vr.current_label_id and _label_store.get(vr.current_label_id))
    missing = []

    # WO-78: Compute determinism score and flags
    score, flags = _compute_determinism(vr)
    vr.replayability_score = score
    vr.non_deterministic_flags = flags

    if has_llm and not has_cassette:
        state = ReplayabilityStatus.evidence_only
        msg = "LLM outputs are non-deterministic. Replay can verify conditions but not exact outputs."
    elif not has_cassette and not has_llm and not has_decision:
        state = ReplayabilityStatus.missing_context
        msg = "No recorded responses, model calls, or decisions found in this record."
        missing.append("cassette_data")
    elif has_cassette and not has_label:
        state = ReplayabilityStatus.requires_human_label
        msg = "Cassette data is present but no expected outcome label has been added."
        missing.append("human_label")
    elif has_cassette and has_label and has_decision:
        state = ReplayabilityStatus.replayable
        msg = "All prerequisites met: cassette data, human label, and decision present."
    elif has_llm and has_cassette:
        state = ReplayabilityStatus.partially_replayable
        msg = "LLM call present; replay can verify recorded system responses but LLM outputs may differ."
    else:
        state = ReplayabilityStatus.unknown
        msg = "Replayability could not be determined."

    if score >= 0.8 and state == ReplayabilityStatus.replayable:
        vr.defensibility_summary = f"{int(score*100)}% of the decision path is deterministically re-testable. Proof demonstrates fix resolves core logic."
    elif score >= 0.5:
        vr.defensibility_summary = f"{int(score*100)}% deterministically re-testable. Remaining relies on sealed evidence assumptions."
    else:
        vr.defensibility_summary = f"Evidence-only: {int(score*100)}% deterministically testable. Manual verification required."

    return state, msg, missing


def _compute_determinism(vr: VerificationRecord) -> tuple[float, list[dict]]:
    """WO-78: Compute replayability score and flag non-deterministic components."""
    total_weight = 10.0
    penalty = 0.0
    flags = []
    has_llm = any(e.kind == EventKind.model_call for e in vr.events)
    has_http = any(e.kind in (EventKind.tool_call, EventKind.api_response) for e in vr.events)

    if has_llm:
        penalty += 3.0
        flags.append({"component": "llm_call", "severity": "NON_DETERMINISTIC_CORE", "location": "model_interaction",
            "description": "LLM outputs are non-deterministic. May differ on replay.", "remediation": "Use temp=0 or seed."})
    if not has_http:
        penalty += 2.0
        flags.append({"component": "missing_cassette", "severity": "NON_DETERMINISTIC_CORE", "location": "external_calls",
            "description": "No recorded API/tool responses. Cannot replay.", "remediation": "Capture all API calls with responses."})
    is_missing_label = not vr.current_label_id
    if is_missing_label:
        penalty += 1.5
        flags.append({"component": "missing_label", "severity": "NON_DETERMINISTIC_SIDE_EFFECT", "location": "human_review",
            "description": "No expected outcome label.", "remediation": "Add approved expected outcome."})
    if not any(e.kind == EventKind.decision for e in vr.events):
        penalty += 1.0
        flags.append({"component": "missing_decision", "severity": "NON_DETERMINISTIC_CORE", "location": "decision_path",
            "description": "No decision event captured.", "remediation": "Capture final decision in SDK."})

    score = max(0.0, min(1.0, 1.0 - (penalty / total_weight)))
    return score, flags


# ── CRUD ──


@router.post("/verification-records")
def create_vr(
    source_type: str = Query("api_submission"),
    external_ref: str = Query(""),
    agent_id: str = Query(""),
    business_function: str = Query(""),
    org_id: str = Depends(require_auth),
) -> dict:
    vid = _next_vr_id()
    try:
        st = DataSourceType(source_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown source_type: {source_type}")
    vr = VerificationRecord(id=vid, org_id=org_id, source_type=st, external_ref=external_ref, agent_id=agent_id, business_function=business_function)
    vr.replayability, vr.replayability_reason, vr.missing_prerequisites = _assess_replayability(vr)
    _vr_store[vid] = vr
    return vr.to_dict()


@router.post("/verification-records/from-snapshot")
def create_vr_from_snapshot(
    snapshot: dict,
    source_type: str = Query("sdk_snapshot"),
    agent_id: str = Query(""),
    org_id: str = Depends(require_auth),
) -> dict:
    vid = _next_vr_id()
    try:
        st = DataSourceType(source_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown source_type: {source_type}")
    events = [sdk_element_to_event(e, i) for i, e in enumerate(snapshot.get("elements", []))]
    vr = VerificationRecord(
        id=vid,
        org_id=org_id,
        source_type=st,
        agent_id=agent_id,
        events=events,
        root_hash=snapshot.get("root_hash", ""),
    )
    vr.replayability, vr.replayability_reason, vr.missing_prerequisites = _assess_replayability(vr)
    _vr_store[vid] = vr
    return vr.to_dict()


@router.get("/verification-records")
def list_vrs(
    source_type: Optional[str] = Query(None),
    replayability: Optional[str] = Query(None),
    agent_id: Optional[str] = Query(None),
    org_id: str = Depends(require_auth),
) -> list[dict]:
    results = list(_vr_store.values())
    results = [r for r in results if r.org_id == org_id]
    if source_type:
        results = [r for r in results if r.source_type.value == source_type]
    if replayability:
        results = [r for r in results if r.replayability.value == replayability]
    if agent_id:
        results = [r for r in results if r.agent_id == agent_id]
    return [r.to_dict() for r in results]


@router.get("/verification-records/{vr_id}")
def get_vr(vr_id: str, org_id: str = Depends(require_auth)) -> dict:
    vr = _vr_store.get(vr_id)
    if vr is None or vr.org_id != org_id:
        raise HTTPException(status_code=404, detail="Verification Record not found")
    return vr.to_dict()


@router.get("/verification-records/{vr_id}/replayability")
def get_replayability(vr_id: str, org_id: str = Depends(require_auth)) -> dict:
    vr = _vr_store.get(vr_id)
    if vr is None or vr.org_id != org_id:
        raise HTTPException(status_code=404, detail="Verification Record not found")
    return {"id": vr_id, "replayability": vr.replayability.value, "reason": vr.replayability_reason, "missing_prerequisites": vr.missing_prerequisites}


@router.post("/verification-records/{vr_id}/promote-to-incident")
def promote_to_incident(vr_id: str, org_id: str = Depends(require_auth)) -> dict:
    vr = _vr_store.get(vr_id)
    if vr is None or vr.org_id != org_id:
        raise HTTPException(status_code=404, detail="Verification Record not found")
    snap = {"elements": [e.payload for e in vr.events], "root_hash": vr.root_hash, "schema_version": 1, "timestamp": vr.created_at, "merkle_chain": []}
    incident = storage.create_incident(snap, org_id=org_id)
    vr.promoted_to_incident = incident.incident_id
    _vr_store[vr_id] = vr
    return {"verification_record_id": vr_id, "incident_id": incident.incident_id, "status": incident.status.value}


# ── Human Label ──


@router.post("/verification-records/{vr_id}/label")
def add_label(
    vr_id: str,
    expected_outcome: str = Query(""),
    reviewer: str = Query(""),
    role: str = Query(""),
    reason: str = Query(""),
    org_id: str = Depends(require_auth),
) -> dict:
    vr = _vr_store.get(vr_id)
    if vr is None or vr.org_id != org_id:
        raise HTTPException(status_code=404, detail="Verification Record not found")
    label = HumanLabel(id=uuid.uuid4().hex, verification_record_id=vr_id, expected_outcome=expected_outcome, reviewer=reviewer, role=role, reason=reason)
    _label_store[label.id] = label
    vr.current_label_id = label.id
    vr.replayability, vr.replayability_reason, vr.missing_prerequisites = _assess_replayability(vr)
    _vr_store[vr_id] = vr
    return label.to_dict()


@router.get("/verification-records/{vr_id}/label")
def get_label(vr_id: str, org_id: str = Depends(require_auth)) -> dict:
    vr = _vr_store.get(vr_id)
    if vr is None or vr.org_id != org_id:
        raise HTTPException(status_code=404, detail="Verification Record not found")
    if not vr.current_label_id:
        raise HTTPException(status_code=404, detail="No label found")
    label = _label_store.get(vr.current_label_id)
    if label is None:
        raise HTTPException(status_code=404, detail="Label not found")
    return label.to_dict()


# ── Intake paths ──


@router.post("/verification-records/manual")
def manual_intake(payload: dict, org_id: str = Depends(require_auth)) -> dict:
    vid = _next_vr_id()
    events = []
    if payload.get("transcript"):
        events.append(AIExecutionEvent(id=uuid.uuid4().hex, kind=EventKind.human_action, payload={"transcript": payload["transcript"][:500]}, order=0))
    if payload.get("decision"):
        events.append(AIExecutionEvent(id=uuid.uuid4().hex, kind=EventKind.decision, payload={"decision": payload["decision"]}, order=1))
    vr = VerificationRecord(
        id=vid, org_id=org_id, source_type=DataSourceType.manual_submission,
        external_ref=payload.get("ticket_id", ""), agent_id=payload.get("agent_id", ""),
        business_function=payload.get("business_function", ""), events=events,
        is_demo=payload.get("is_demo", False),
    )
    vr.replayability, vr.replayability_reason, vr.missing_prerequisites = _assess_replayability(vr)
    _vr_store[vid] = vr
    return vr.to_dict()


@router.post("/verification-records/webhook")
def webhook_intake(payload: dict, org_id: str = Depends(require_auth)) -> dict:
    vid = _next_vr_id()
    events_data = payload.get("events", [])
    events = []
    for i, e in enumerate(events_data):
        kind_str = e.get("kind", "model_call")
        try:
            kind = EventKind(kind_str)
        except ValueError:
            kind = EventKind.decision
        ev = AIExecutionEvent(id=uuid.uuid4().hex, kind=kind, payload=e.get("payload", {}), order=i)
        events.append(ev)
    if not events:
        events = [AIExecutionEvent(id=uuid.uuid4().hex, kind=EventKind.decision, payload=payload, order=0)]
    vr = VerificationRecord(
        id=vid, org_id=org_id, source_type=DataSourceType.webhook,
        external_ref=payload.get("source_id", ""), events=events,
    )
    vr.replayability, vr.replayability_reason, vr.missing_prerequisites = _assess_replayability(vr)
    _vr_store[vid] = vr
    return vr.to_dict()


# ── Capture Adapter Registry ──


ADAPTERS = {
    "python_sdk": {"label": "Python SDK", "status": "built", "desc": "Explicit capture via RunCapture. Works today."},
    "api_submission": {"label": "API Submission", "status": "built", "desc": "Generic JSON submission endpoint."},
    "manual_submission": {"label": "Manual Submission", "status": "built", "desc": "Submit decisions/overrides manually."},
    "webhook": {"label": "Webhook", "status": "built", "desc": "POST events from any system."},
    "batch_import": {"label": "Batch Import", "status": "planned", "desc": "CSV/JSONL import for historical analysis."},
    "trace_import": {"label": "Trace Import", "status": "planned", "desc": "OpenTelemetry/OpenInference trace ingestion."},
    "openai_adapter": {"label": "OpenAI Adapter", "status": "planned", "desc": "Auto-capture from OpenAI SDK calls."},
    "anthropic_adapter": {"label": "Anthropic Adapter", "status": "planned", "desc": "Auto-capture from Anthropic SDK calls."},
    "langgraph_adapter": {"label": "LangGraph Adapter", "status": "planned", "desc": "Auto-capture from LangGraph agents."},
    "langchain_adapter": {"label": "LangChain Adapter", "status": "planned", "desc": "Auto-capture from LangChain chains."},
    "pydanticai_adapter": {"label": "PydanticAI Adapter", "status": "planned", "desc": "Auto-capture from PydanticAI agents."},
    "mcp_tools": {"label": "MCP Tools", "status": "planned", "desc": "Capture from MCP tool calls."},
    "typescript_sdk": {"label": "TypeScript SDK", "status": "planned", "desc": "JS/TS SDK parity for Node.js agents."},
}


@router.get("/platform/adapters")
def list_adapters() -> list[dict]:
    return [{"id": k, **v} for k, v in ADAPTERS.items()]


# ── WO-78: Replay Preflight ──


@router.get("/verification-records/{vr_id}/replay-preflight")
def replay_preflight(vr_id: str, org_id: str = Depends(require_auth)) -> dict:
    vr = _vr_store.get(vr_id)
    if vr is None or vr.org_id != org_id:
        raise HTTPException(status_code=404, detail="Verification Record not found")
    [f for f in vr.non_deterministic_flags if f.get("component") == "missing_cassette"]
    warnings = [f for f in vr.non_deterministic_flags if f.get("severity") == "NON_DETERMINISTIC_SIDE_EFFECT"]
    blocks = [f for f in vr.non_deterministic_flags if f.get("severity") == "NON_DETERMINISTIC_CORE"]

    if vr.replayability == ReplayabilityStatus.replayable:
        status = "PASS"
    elif vr.replayability == ReplayabilityStatus.evidence_only:
        status = "FAIL"
    elif blocks:
        status = "FAIL"
    else:
        status = "WARN"

    return {
        "incident_id": vr.promoted_to_incident or vr_id,
        "preflight_status": status,
        "replayability_state": vr.replayability.value,
        "replayability_score": vr.replayability_score,
        "can_proceed": status != "FAIL",
        "warnings": warnings,
        "blocking_factors": blocks,
        "missing_prerequisites": vr.missing_prerequisites,
        "next_actions": ["Review evidence manually"] if status == "FAIL" else [],
    }


# ── WO-79: Label Heuristics + Bulk Approve ──


_LABEL_HEURISTICS = {
    "incident_type": [
        ("model_degradation", "Model output or behavior degraded from expected", 0.5),
        ("api_failure", "External API returned error or timeout", 0.7),
        ("policy_violation", "Decision violates known compliance or business rule", 0.6),
        ("external_override", "Human intervention or escalation detected", 0.8),
    ],
    "severity": [
        ("high", "Financial or compliance impact suspected", 0.5),
        ("medium", "Moderate impact or limited scope", 0.5),
        ("low", "Minimal impact", 0.5),
    ],
}


@router.post("/verification-records/{vr_id}/label-suggest")
def suggest_labels(vr_id: str, org_id: str = Depends(require_auth)) -> dict:
    vr = _vr_store.get(vr_id)
    if vr is None or vr.org_id != org_id:
        raise HTTPException(status_code=404, detail="Verification Record not found")
    has_llm = any(e.kind == EventKind.model_call for e in vr.events)
    has_error = any(e.kind in (EventKind.api_response, EventKind.tool_call) for e in vr.events)
    suggestions = []
    for cat, rules in _LABEL_HEURISTICS.items():
        for value, desc, base_conf in rules:
            conf = base_conf
            if cat == "incident_type" and value == "model_degradation" and has_llm:
                conf = 0.65
                suggestions.append({"category": cat, "value": value, "confidence": conf, "heuristic": "llm_detected_v1", "reasoning": desc})
            elif cat == "incident_type" and value == "api_failure" and has_error:
                suggestions.append({"category": cat, "value": value, "confidence": conf, "heuristic": "api_detected_v1", "reasoning": desc})
            elif cat == "incident_type" and value == "policy_violation":
                suggestions.append({"category": cat, "value": value, "confidence": conf, "heuristic": "default_v1", "reasoning": desc})
            elif cat == "severity":
                suggestions.append({"category": cat, "value": value, "confidence": conf, "heuristic": "default_v1", "reasoning": desc})
    return {"vr_id": vr_id, "suggested_labels": suggestions}


@router.post("/verification-records/bulk-label-approve")
def bulk_approve(body: dict, org_id: str = Depends(require_auth)) -> dict:
    filter_conf = body.get("filter", {})
    min_conf = filter_conf.get("suggested_confidence_min", 0.0)
    max_conf = filter_conf.get("suggested_confidence_max", 1.0)
    approved = []
    for vid, vr in list(_vr_store.items()):
        if vr.org_id != org_id:
            continue
        if vr.current_label_id:
            lbl = _label_store.get(vr.current_label_id)
            if lbl and min_conf <= lbl.suggested_confidence <= max_conf and lbl.status == "active":
                lbl.status = "active"  # already approved
                lbl.approval_reason = body.get("approval_reason", "Bulk approved")
                approved.append(vid)
    return {"approved_count": len(approved), "approved_vr_ids": approved}


@router.get("/system/determinism-checklist")
def get_determinism_checklist() -> dict:
    return {
        "checklist": [
            {"item": "sealed_external_responses",
             "description": "All outbound API calls must have recorded responses.",
             "severity": "NON_DETERMINISTIC_CORE", "detection": "Scan for unsealed HTTP events."},
            {"item": "deterministic_llm_params",
             "description": "LLM calls should use temp=0 for reproducible outputs.",
             "severity": "NON_DETERMINISTIC_CORE", "detection": "Check for LLM events."},
            {"item": "decision_captured",
             "description": "The final decision must be captured.",
             "severity": "NON_DETERMINISTIC_CORE", "detection": "Check for decision event."},
            {"item": "human_label_required",
             "description": "A human-approved expected outcome is needed for proof.",
             "severity": "NON_DETERMINISTIC_SIDE_EFFECT", "detection": "Check for approved label."},
        ]
    }


@router.get("/system/label-heuristics")
def get_label_heuristics() -> dict:
    return {
        "heuristics": [
            {"id": "llm_detected_v1", "category": "incident_type",
             "target": "model_degradation", "trigger": "LLM events present", "confidence": "0.65"},
            {"id": "api_detected_v1", "category": "incident_type",
             "target": "api_failure", "trigger": "Tool/API events present", "confidence": "0.7"},
            {"id": "default_v1", "category": "severity",
             "target": "medium", "trigger": "Default assessment", "confidence": "0.5"},
        ]
    }
