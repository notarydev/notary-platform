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
