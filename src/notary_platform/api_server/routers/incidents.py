"""Incidents router — list, retrieve, and replay incidents."""

from __future__ import annotations

from typing import Any, Callable, Optional

from fastapi import APIRouter, HTTPException

from notary_platform.api_server.routers.ingestion import storage
from notary_platform.replay_engine.worker import run_replay

router = APIRouter(tags=["incidents"])

_demo_agent_fn: Optional[Callable[..., Any]] = None


def set_demo_agent(fn: Callable[..., Any]) -> None:
    global _demo_agent_fn  # noqa: PLW0603
    _demo_agent_fn = fn


@router.get("/incidents")
def list_incidents() -> list[dict[str, Any]]:
    return [inc.to_dict() for inc in storage.list_incidents()]


@router.get("/incidents/{incident_id}")
def get_incident(incident_id: str) -> dict[str, Any]:
    inc = storage.get_incident(incident_id)
    if inc is None:
        raise HTTPException(status_code=404, detail="incident not found")
    return inc.to_dict()


@router.post("/incidents/{incident_id}/replay")
def replay_incident(incident_id: str) -> dict[str, Any]:
    inc = storage.get_incident(incident_id)
    if inc is None:
        raise HTTPException(status_code=404, detail="incident not found")

    snapshot_dict = storage.get_snapshot(incident_id)
    if snapshot_dict is None:
        raise HTTPException(status_code=404, detail="snapshot not found")

    agent_fn = _demo_agent_fn
    if agent_fn is None:
        return {
            "incident_id": incident_id,
            "replay_status": "escalation_required",
            "reason": "no agent function registered",
        }

    result = run_replay(inc, snapshot_dict, agent_fn, storage=storage)
    return {"incident_id": incident_id, **result}
