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

    if has_llm and not has_cassette:
        return ReplayabilityStatus.evidence_only, "LLM outputs are non-deterministic. Replay can verify conditions but not exact outputs.", []
    if not has_cassette and not has_llm and not has_decision:
        return ReplayabilityStatus.missing_context, "No recorded responses, model calls, or decisions found in this record.", ["cassette_data"]
    if has_cassette and not has_label:
        missing.append("human_label")
        return ReplayabilityStatus.requires_human_label, "Cassette data is present but no expected outcome label has been added.", missing
    if has_cassette and has_label and has_decision:
        return ReplayabilityStatus.replayable, "All prerequisites met: cassette data, human label, and decision present.", []
    if has_llm and has_cassette:
        return ReplayabilityStatus.partially_replayable, "LLM call present; replay can verify recorded system responses but LLM outputs may differ.", []
    return ReplayabilityStatus.unknown, "Replayability could not be determined.", []


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
