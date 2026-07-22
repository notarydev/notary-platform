"""Verification Record intake and assessment router (WO-69/70/71).

Phase 2 canonical intake for all AI decision evidence, regardless
of capture source. Handles SDK snapshots, API submissions, manual
entries, and webhook intake.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from notary_platform.api_server.auth import require_auth
from notary_platform.api_server.routers.ingestion import get_registry as _get_ingestion_registry
from notary_platform.api_server.routers.ingestion import storage
from notary_platform.models import (
    DataSourceType,
    EventKind,
    ReplayabilityStatus,
    VerificationRecord,
)
from notary_platform.services import (
    IngestionService,
    LabelProvenanceService,
)

router = APIRouter(tags=["verification"])

# Backward-compatible module-level registry. New code uses the storage backend.
_registry = _get_ingestion_registry()


def _next_vr_id() -> str:
    return f"vr-{uuid.uuid4().hex[:8]}"


def _assess_replayability(vr: VerificationRecord) -> tuple[ReplayabilityStatus, str, list[str]]:
    """Assess replayability using the service-layer logic."""
    from notary_platform.services import ReplayabilityService
    return ReplayabilityService(_registry).assess(vr)


# ── CRUD ──


@router.post("/verification-records")
def create_vr(
    source_type: str = Query("api_submission"),
    external_ref: str = Query(""),
    agent_id: str = Query(""),
    business_function: str = Query(""),
    org_id: str = Depends(require_auth),
) -> dict:
    try:
        DataSourceType(source_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown source_type: {source_type}")
    ingestion = IngestionService(_registry)
    vr = ingestion.create_from_api_submission(
        org_id=org_id,
        external_ref=external_ref,
        agent_id=agent_id,
    )
    vr.source_type = DataSourceType(source_type)
    vr.business_function = business_function
    storage.update_vr(vr)
    return vr.to_dict()


@router.post("/verification-records/from-snapshot")
def create_vr_from_snapshot(
    snapshot: dict,
    source_type: str = Query("sdk_snapshot"),
    agent_id: str = Query(""),
    org_id: str = Depends(require_auth),
) -> dict:
    try:
        DataSourceType(source_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown source_type: {source_type}")
    ingestion = IngestionService(_registry)
    vr = ingestion.create_from_sdk_snapshot(snapshot, org_id=org_id, agent_id=agent_id)
    return vr.to_dict()


@router.get("/verification-records")
def list_vrs(
    source_type: Optional[str] = Query(None),
    replayability: Optional[str] = Query(None),
    agent_id: Optional[str] = Query(None),
    org_id: str = Depends(require_auth),
) -> list[dict]:
    results = storage.list_vrs(org_id=org_id)
    if source_type:
        results = [r for r in results if r.source_type.value == source_type]
    if replayability:
        results = [r for r in results if r.replayability.value == replayability]
    if agent_id:
        results = [r for r in results if r.agent_id == agent_id]
    return [r.to_dict() for r in results]


@router.get("/verification-records/{vr_id}")
def get_vr(vr_id: str, org_id: str = Depends(require_auth)) -> dict:
    vr = storage.get_vr(vr_id)
    if vr is None or vr.org_id != org_id:
        raise HTTPException(status_code=404, detail="Verification Record not found")
    return vr.to_dict()


@router.get("/verification-records/{vr_id}/evidence")
def get_vr_evidence(vr_id: str, org_id: str = Depends(require_auth)) -> list[dict]:
    vr = storage.get_vr(vr_id)
    if vr is None or vr.org_id != org_id:
        raise HTTPException(status_code=404, detail="Verification Record not found")
    artifacts = storage.list_evidence_artifacts_for_vr(vr_id, org_id)
    return [a.to_dict() for a in artifacts]


@router.get("/verification-records/{vr_id}/replayability")
def get_replayability(vr_id: str, org_id: str = Depends(require_auth)) -> dict:
    vr = storage.get_vr(vr_id)
    if vr is None or vr.org_id != org_id:
        raise HTTPException(status_code=404, detail="Verification Record not found")
    return {"id": vr_id, "replayability": vr.replayability.value, "reason": vr.replayability_reason, "missing_prerequisites": vr.missing_prerequisites}


@router.post("/verification-records/{vr_id}/promote-to-incident")
def promote_to_incident(vr_id: str, org_id: str = Depends(require_auth)) -> dict:
    vr = storage.get_vr(vr_id)
    if vr is None or vr.org_id != org_id:
        raise HTTPException(status_code=404, detail="Verification Record not found")
    ingestion = IngestionService(_registry)
    incident = ingestion.create_incident_from_vr(vr)
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
    labels = LabelProvenanceService(_registry)
    try:
        label = labels.create_label(vr_id, org_id, expected_outcome, reviewer=reviewer, role=role, reason=reason)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return label.to_dict()


@router.get("/verification-records/{vr_id}/label")
def get_label(vr_id: str, org_id: str = Depends(require_auth)) -> dict:
    vr = storage.get_vr(vr_id)
    if vr is None or vr.org_id != org_id:
        raise HTTPException(status_code=404, detail="Verification Record not found")
    if not vr.current_label_id:
        raise HTTPException(status_code=404, detail="No label found")
    label = storage.get_label(vr.current_label_id)
    if label is None:
        raise HTTPException(status_code=404, detail="Label not found")
    return label.to_dict()


# ── Intake paths ──


@router.post("/verification-records/manual")
def manual_intake(payload: dict, org_id: str = Depends(require_auth)) -> dict:
    ingestion = IngestionService(_registry)
    vr = ingestion.create_manual(org_id, payload)
    return vr.to_dict()


@router.post("/verification-records/webhook")
def webhook_intake(payload: dict, org_id: str = Depends(require_auth)) -> dict:
    ingestion = IngestionService(_registry)
    vr = ingestion.create_webhook(org_id, payload)
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
    vr = storage.get_vr(vr_id)
    if vr is None or vr.org_id != org_id:
        raise HTTPException(status_code=404, detail="Verification Record not found")
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
    vr = storage.get_vr(vr_id)
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
    vr.suggested_labels = suggestions
    storage.update_vr(vr)
    return {"vr_id": vr_id, "suggested_labels": suggestions}


@router.post("/verification-records/{vr_id}/label-reject")
def reject_suggested_label(vr_id: str, body: dict, org_id: str = Depends(require_auth)) -> dict:
    vr = storage.get_vr(vr_id)
    if vr is None or vr.org_id != org_id:
        raise HTTPException(status_code=404, detail="Verification Record not found")
    reject_value = body.get("value", "")
    vr.suggested_labels = [s for s in vr.suggested_labels if s.get("value") != reject_value]
    storage.update_vr(vr)
    return {"vr_id": vr_id, "rejected": reject_value, "remaining": len(vr.suggested_labels)}


@router.get("/verification-records/{vr_id}/label-history")
def label_history(vr_id: str, org_id: str = Depends(require_auth)) -> dict:
    vr = storage.get_vr(vr_id)
    if vr is None or vr.org_id != org_id:
        raise HTTPException(status_code=404, detail="Verification Record not found")
    labels = [lbl.to_dict() for lbl in storage.list_labels_for_vr(vr_id)]
    return {"vr_id": vr_id, "labels": labels}


@router.post("/verification-records/bulk-label-approve")
def bulk_approve(body: dict, org_id: str = Depends(require_auth)) -> dict:
    filter_conf = body.get("filter", {})
    min_conf = filter_conf.get("suggested_confidence_min", 0.0)
    max_conf = filter_conf.get("suggested_confidence_max", 1.0)
    approved = []
    for vr in storage.list_vrs(org_id=org_id):
        if vr.current_label_id:
            lbl = storage.get_label(vr.current_label_id)
            if lbl and min_conf <= lbl.suggested_confidence <= max_conf and lbl.status == "active":
                lbl.status = "active"  # already approved
                lbl.approval_reason = body.get("approval_reason", "Bulk approved")
                approved.append(vr.id)
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


@router.post("/verification-records/import-preview")
def import_preview(body: dict[str, Any], _org: str = Depends(require_auth)) -> dict[str, Any]:
    """Preview what would be imported from JSON/JSONL records.
    Returns counts without creating any records.
    """
    records_raw = body.get("records", [])
    matched = 0
    replayable = 0
    needs_label = 0
    missing_cassette = 0
    evidence_only = 0
    samples = []
    for item in records_raw[:20]:  # Preview up to 20
        elements = item.get("elements", [])
        has_decision = any(e.get("kind") == "decision" for e in elements)
        has_cassette = any(e.get("kind") in ("tool", "llm", "http") for e in elements)
        has_expected = bool(item.get("expected_outcome"))
        if has_decision:
            matched += 1
            if has_cassette and has_expected:
                replayable += 1
            elif has_cassette and not has_expected:
                needs_label += 1
            elif not has_cassette and has_expected:
                missing_cassette += 1
            else:
                evidence_only += 1
            if len(samples) < 5:
                samples.append({
                    "source_record_ref": item.get("source_record_ref", ""),
                    "has_decision": has_decision,
                    "has_cassette": has_cassette,
                    "has_expected": has_expected,
                })
    total = len(records_raw)
    candidate_estimate = max(1, matched // 20) if matched > 20 else 0
    return {
        "total_records": total,
        "matched_count": matched,
        "replayable_count": replayable,
        "needs_label_count": needs_label,
        "missing_cassette_count": missing_cassette,
        "evidence_only_count": evidence_only,
        "scenario_candidate_count": candidate_estimate,
        "sample_records": samples,
    }


@router.post("/verification-records/import")
def import_verification_records(
    body: dict[str, Any],
    _org: str = Depends(require_auth),
) -> dict[str, Any]:
    """Import records from JSON/JSONL. Expects {'records': [...], 'workflow_id': '...'}."""
    records_raw = body.get("records", [])
    wf_id = body.get("workflow_id", "")
    results = []
    for item in records_raw:
        snapshot = {
            "schema_version": item.get("schema_version", 1),
            "source_system_id": item.get("source_system_id", "import"),
            "source_record_ref": item.get("source_record_ref", ""),
            "business_function": item.get("business_function", wf_id),
            "expected_outcome": item.get("expected_outcome", ""),
            "elements": item.get("elements", []),
        }
        ingestion = IngestionService(_registry)
        vr = ingestion.create_from_sdk_snapshot(
            snapshot,
            org_id=_org,
            agent_id=item.get("agent_id", ""),
        )
        results.append({
            "id": vr.id,
            "replayability": vr.replayability.value,
            "next_action": vr.next_action,
        })
    return {"imported": len(results), "records": results}
