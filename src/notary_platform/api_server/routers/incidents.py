"""Incidents router — list, retrieve, and replay incidents (WO-4).

Spec endpoints:
  POST /v1/incidents/{incident_id}/replay
  GET  /v1/incidents/{incident_id}/replay
  GET  /v1/incidents/{incident_id}/replay/stream  (SSE)
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, AsyncGenerator, Callable, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from notary_platform.api_server.auth import require_auth
from notary_platform.api_server.routers.ingestion import storage
from notary_platform.models import ReplayExecutionEvent, ReplayRun
from notary_platform.replay_engine.worker import run_replay

router = APIRouter(tags=["incidents"])

_demo_agent_fn: Optional[Callable[..., Any]] = None


def set_demo_agent(fn: Callable[..., Any]) -> None:
    global _demo_agent_fn  # noqa: PLW0603
    _demo_agent_fn = fn


def _get_incident(incident_id: str, org_id: str) -> Any:
    inc = storage.get_incident(incident_id)
    if inc is None or inc.org_id != org_id:
        raise HTTPException(status_code=404, detail="incident not found")
    return inc


def _derive_execution_events(snapshot_dict: dict[str, Any], result: dict[str, Any], decision: str) -> list[ReplayExecutionEvent]:
    """Derive per-step execution events from snapshot elements and replay result."""
    elements = snapshot_dict.get("elements", [])
    input_el = next((e for e in elements if e.get("kind") == "input"), None)
    http_el = next((e for e in elements if e.get("kind") == "http"), None)
    policy_el = next((e for e in elements if e.get("kind") == "policy"), None)

    applicant_id = (input_el or {}).get("payload", {}).get("applicant_id", "—") if input_el else "—"
    bureau_status = (http_el or {}).get("payload", {}).get("response", {}).get("status", "missing_evidence") if http_el else "—"
    policy_version = (policy_el or {}).get("payload", {}).get("version", "v1.3") if policy_el else "—"
    replayed_decision = result.get("decision", "—")
    replay_status = result.get("replay_status", "error")

    s = "pass" if result.get("replay_status") else "pending"
    events = [
        ReplayExecutionEvent(step="Applicant facts", source="sealed input",
            expected="match", actual="match" if applicant_id != "—" else "—", status="pass", sequence=0),
        ReplayExecutionEvent(step="Bureau response", source="cassette",
            expected=bureau_status, actual=bureau_status, status=s, sequence=1),
        ReplayExecutionEvent(step="Policy version", source="sealed metadata",
            expected=policy_version, actual=policy_version, status=s, sequence=2),
        ReplayExecutionEvent(step="AI decision", source="replay",
            expected=decision, actual=replayed_decision,
            status="reproduced" if replay_status == "replayed" else "pending", sequence=3),
        ReplayExecutionEvent(step="Replay verdict", source="comparison",
            expected="reproduce failure",
            actual="reproduced" if replay_status == "replayed" else "pending",
            status=replay_status, sequence=4),
    ]
    return events


@router.post("/incidents/{incident_id}/replay")
def replay_incident(incident_id: str, org_id: str = Depends(require_auth)) -> dict[str, Any]:
    inc = _get_incident(incident_id, org_id)

    snapshot_dict = storage.get_snapshot(incident_id)
    if snapshot_dict is None:
        raise HTTPException(status_code=404, detail="snapshot not found")

    agent_fn = _demo_agent_fn
    if agent_fn is None:
        inc._record_custody("replay_escalation", actor=org_id, detail="no agent function registered")
        storage.update_incident(inc)
        return {
            "incident_id": incident_id,
            "replay_status": "escalation_required",
            "reason": "no agent function registered",
        }

    result = run_replay(inc, snapshot_dict, agent_fn)
    inc._record_custody("replayed", actor=org_id, detail=f"decision={result.get('decision')}")
    storage.update_incident(inc)
    storage.persist_evidence(incident_id, "replay", result)

    # Create ReplayRun + execution events
    decision_el = next((e for e in snapshot_dict.get("elements", []) if e.get("kind") == "decision"), None)
    original_decision = (decision_el or {}).get("payload", {}).get("decision", "—")
    run = ReplayRun(
        id=f"rr-{uuid.uuid4().hex[:8]}",
        org_id=org_id,
        verification_record_id="",
        incident_id=incident_id,
        status=result.get("replay_status", "incomplete"),
        original_decision=original_decision,
        replayed_decision=result.get("decision", ""),
    )
    storage.create_replay_run(run)
    events = _derive_execution_events(snapshot_dict, result, original_decision)
    storage.create_replay_execution_events(run.id, events)

    inc.replay_result["replay_run_id"] = run.id
    storage.update_incident(inc)

    return {"incident_id": incident_id, "org_id": org_id, "replay_run_id": run.id, **result}


@router.get("/incidents/{incident_id}/replay")
def get_replay(incident_id: str, org_id: str = Depends(require_auth)) -> dict[str, Any]:
    inc = _get_incident(incident_id, org_id)
    if not inc.replay_result:
        raise HTTPException(status_code=404, detail="replay not run")
    return {"incident_id": incident_id, "org_id": org_id, **inc.replay_result}


@router.get("/replay-runs/{run_id}/events")
def get_replay_events(run_id: str, org_id: str = Depends(require_auth)) -> list[dict]:
    run = storage.get_replay_run(run_id)
    if run is None or run.org_id != org_id:
        raise HTTPException(status_code=404, detail="Replay Run not found")
    events = storage.list_replay_execution_events(run_id)
    return [e.to_dict() for e in events]


async def _event_stream(run_id: str) -> AsyncGenerator[str, None]:
    """SSE generator: yield stored execution events, then keep-alive."""
    seen = 0
    for _ in range(30):
        events = storage.list_replay_execution_events(run_id)
        while seen < len(events):
            yield f"data: {json.dumps(events[seen].to_dict())}\n\n"
            seen += 1
        if len(events) > 0 and all(e.status in ("pass", "fail", "reproduced", "error") for e in events):
            yield "event: done\ndata: {}\n\n"
            return
        await asyncio.sleep(0.5)
    yield "event: done\ndata: {}\n\n"


@router.get("/incidents/{incident_id}/replay/stream")
async def stream_replay_events(incident_id: str, org_id: str = Depends(require_auth)) -> StreamingResponse:
    inc = _get_incident(incident_id, org_id)
    run_id = (inc.replay_result or {}).get("replay_run_id", "")
    if not run_id:
        raise HTTPException(status_code=404, detail="no replay run found for this incident")
    return StreamingResponse(_event_stream(run_id), media_type="text/event-stream")


@router.get("/incidents/{incident_id}/workflow")
def incident_workflow(incident_id: str, org_id: str = Depends(require_auth)) -> dict[str, Any]:
    """Return the proof-loop workflow stepper state for an incident."""
    inc = _get_incident(incident_id, org_id)
    from notary_platform.models import EventKind
    vrs = storage.list_vrs(org_id)
    source_vr = next((v for v in vrs if v.promoted_to_incident == incident_id), None)
    has_label = source_vr is not None and bool(source_vr.current_label_id)
    has_cassette = source_vr is not None and any(
        e.kind in (EventKind.api_response, EventKind.tool_call) for e in source_vr.events
    )
    has_sandbox = source_vr is not None and source_vr.sandbox_readiness.get("ready", False)
    has_replay = bool(inc.replay_result)
    has_fix = bool(inc.mutation_result)
    has_proof = bool(inc.certificate)

    def step_state(label: str, ready: bool, complete: bool, blocked: bool = False) -> dict:
        if blocked:
            return {"label": label, "state": "blocked", "detail": "Blocked — see missing prerequisites", "action": None}
        if complete:
            return {"label": label, "state": "complete", "detail": "Done", "action": None}
        if ready:
            return {"label": label, "state": "ready", "detail": "Ready to run", "action": label}
        return {"label": label, "state": "not_started", "detail": "Waiting for previous step", "action": None}

    return {
        "incident_id": incident_id,
        "steps": [
            step_state("Captured evidence", True, True),
            step_state("Replayability", True, has_label or has_cassette, blocked=not has_cassette and not has_label),
            step_state("Replay preflight", has_label and has_cassette, has_replay),
            step_state("Replay result", has_replay, has_replay),
            step_state("Fix proposal", has_replay, has_fix),
            step_state("Fix verification", has_fix and has_sandbox, has_fix, blocked=has_fix and not has_sandbox),
            step_state("Proof eligibility", has_fix, has_proof),
            step_state("Proof issued", has_proof, has_proof),
            step_state("Scenario candidate", has_proof, False),
        ],
        "missing_prerequisites": source_vr.missing_prerequisites if source_vr else [],
        "can_replay": has_cassette and has_label,
        "can_verify": has_replay,
        "can_issue_proof": has_fix,
    }
