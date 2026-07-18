"""Notary Platform customer-facing API (WO-47 through WO-54).

Provides read-only endpoints for the Notary Platform SPA. The data is seeded
from platform_data for the demo organization. Production-ready persistence
is added when the backend supports multi-org storage.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query

from notary_platform.api_server.auth import require_auth
from notary_platform.api_server.routers.ingestion import storage
from notary_platform.models import HomeStats
from notary_platform.platform_data import seed

router = APIRouter(tags=["platform"])

# Seeded demo data. In production these would come from a database.
_SEED: dict[str, Any] = seed()
_DEMO_ORG = _SEED["organization"]
_ENVS_BY_ID = {e.id: e for e in _SEED["environments"]}
_AGENTS_BY_ID = {a.id: a for a in _SEED["agents"]}
_SYSTEMS_BY_ID = {s.id: s for s in _SEED["systems"]}
_POLICIES_BY_ID = {p.id: p for p in _SEED["policies"]}


@router.get("/platform/org")
def get_org(_org: str = Depends(require_auth)) -> dict:
    """Return the current organization."""
    return _DEMO_ORG.to_dict()


@router.get("/platform/org/environments")
def list_environments(_org: str = Depends(require_auth)) -> list[dict]:
    """List environments in the current organization."""
    return [e.to_dict() for e in _SEED["environments"]]


@router.get("/platform/org/agents")
def list_agents(
    environment_id: Optional[str] = Query(None),
    _org: str = Depends(require_auth),
) -> list[dict]:
    """List agents, optionally filtered by environment."""
    agents = _SEED["agents"]
    if environment_id:
        agents = [a for a in agents if a.environment_id == environment_id]
    return [a.to_dict() for a in agents]


@router.get("/platform/org/systems")
def list_systems(
    environment_id: Optional[str] = Query(None),
    _org: str = Depends(require_auth),
) -> list[dict]:
    """List system connections, optionally filtered by environment."""
    systems = _SEED["systems"]
    if environment_id:
        systems = [s for s in systems if s.environment_id == environment_id]
    return [s.to_dict() for s in systems]


@router.get("/platform/org/policies")
def list_policies(
    environment_id: Optional[str] = Query(None),
    _org: str = Depends(require_auth),
) -> list[dict]:
    """List capture policies, optionally filtered by environment."""
    policies = _SEED["policies"]
    if environment_id:
        policies = [p for p in policies if p.environment_id == environment_id]
    return [p.to_dict() for p in policies]


@router.get("/platform/home")
def get_home(
    environment_id: str = Query("env:demo"),
    _org: str = Depends(require_auth),
) -> dict:
    """Return Home overview stats for the given environment."""
    agents = [a for a in _SEED["agents"] if a.environment_id == environment_id]
    systems = [s for s in _SEED["systems"] if s.environment_id == environment_id]

    # Stats derived from seed data + actual incident storage.
    incidents = storage.list_incidents(org_id=_org)
    incident_count = len(incidents)
    replay_ready = sum(1 for i in incidents if i.replay_result)
    fixes_verified = sum(1 for i in incidents if i.status.value == "mitigated")
    proofs_issued = sum(1 for i in incidents if i.status.value == "certified")
    pending_replay = sum(
        1 for i in incidents if i.status.value == "ingested" and not i.replay_result
    )

    stats = HomeStats(
        org_id=_DEMO_ORG.id,
        environment_id=environment_id,
        agent_count=len(agents),
        system_count=len(systems),
        incident_count=incident_count,
        replay_ready=replay_ready,
        fixes_verified=fixes_verified,
        proofs_issued=proofs_issued,
        scenario_count=sum(a.scenario_count for a in agents),
        pending_replay=pending_replay,
        pending_verification=incident_count - fixes_verified,
        pending_proof=fixes_verified - proofs_issued,
    )
    return stats.to_dict()


@router.get("/platform/home/queue")
def get_home_queue(
    environment_id: str = Query("env:demo"),
    _org: str = Depends(require_auth),
) -> list[dict]:
    """Return pending-action items for the home queue."""
    incidents = storage.list_incidents(org_id=_org)
    queue = []
    for inc in incidents:
        action = None
        if not inc.replay_result:
            action = "needs_replay"
        elif inc.status.value == "mitigated" and not inc.certificate:
            action = "proof_ready"
        elif inc.status.value == "ingested":
            action = "needs_verification"
        if action:
            queue.append({"incident_id": inc.incident_id, "status": inc.status.value, "next_action": action})
    return queue
