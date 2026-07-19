"""Incidents router — list, retrieve, and replay incidents (WO-4).

Spec endpoints:
  POST /v1/incidents/{incident_id}/replay
  GET  /v1/incidents/{incident_id}/replay
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from fastapi import APIRouter, Depends, HTTPException

from notary_platform.api_server.auth import require_auth
from notary_platform.api_server.routers.ingestion import storage
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
    return {"incident_id": incident_id, "org_id": org_id, **result}


@router.get("/incidents/{incident_id}/replay")
def get_replay(incident_id: str, org_id: str = Depends(require_auth)) -> dict[str, Any]:
    inc = _get_incident(incident_id, org_id)
    if not inc.replay_result:
        raise HTTPException(status_code=404, detail="replay not run")
    return {"incident_id": incident_id, "org_id": org_id, **inc.replay_result}


@router.get("/incidents/{incident_id}/workflow")
def incident_workflow(incident_id: str, org_id: str = Depends(require_auth)) -> dict[str, Any]:
    """Return the proof-loop workflow stepper state for an incident."""
    inc = _get_incident(incident_id, org_id)
    from notary_platform.api_server.routers.verification import _vr_store
    from notary_platform.models import EventKind
    source_vr = next((v for v in _vr_store.values() if v.promoted_to_incident == incident_id), None)
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
