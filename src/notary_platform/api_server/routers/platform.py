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
from notary_platform.models import HomeStats, IncidentStatus
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
    incidents = storage.list_incidents(org_id=_org)
    incident_count = len(incidents)
    fixes_verified = sum(1 for i in incidents if i.status.value == "mitigated")
    proofs_issued = sum(1 for i in incidents if i.status.value == "certified")
    pending_replay = sum(1 for i in incidents if i.status.value == "ingested" and not i.replay_result)
    pending_verification = sum(1 for i in incidents if i.status.value == "replayed" and i.status.value != "mitigated")

    # Setup health
    connected_agents = sum(1 for a in agents if a.sdk_status == "connected")
    connected_systems = sum(1 for s in systems if s.status == "connected")
    setup_health = {
        "sdk_installed": connected_agents > 0,
        "agents_instrumented": len(agents),
        "systems_connected": connected_systems,
        "systems_total": len(systems),
        "capture_policies": len(_SEED["policies"]),
        "incidents_collected": incident_count,
        "proofs_issued": proofs_issued,
    }

    # Active queues
    queues = {
        "needs_replay": pending_replay,
        "needs_verification": pending_verification,
        "proofs_ready": max(0, fixes_verified - proofs_issued),
    }

    # Recent proofs
    recent_proofs = []
    for inc in incidents:
        if inc.certificate and inc.status.value == "certified":
            recent_proofs.append({
                "incident_id": inc.incident_id,
                "agent": "Lending Decision Agent" if "lending" in str(inc.incident_id).lower() else "Support Handoff Agent",
                "status": "certified",
                "date": inc.certificate.get("timestamp", ""),
            })
    recent_proofs = recent_proofs[:5]

    # Next action (priority: need replay > need verify > need proof)
    next_action = None
    for inc in incidents:
        if not inc.replay_result:
            next_action = {"action": "replay", "incident_id": inc.incident_id, "label": f"Replay {inc.incident_id}"}
            break
    if not next_action:
        for inc in incidents:
            if inc.status.value == "replayed" and not inc.mutation_result:
                next_action = {"action": "verify", "incident_id": inc.incident_id, "label": f"Verify fix for {inc.incident_id}"}
                break
    if not next_action:
        for inc in incidents:
            if inc.status.value == "mitigated" and not inc.certificate:
                next_action = {"action": "proof", "incident_id": inc.incident_id, "label": f"Issue proof for {inc.incident_id}"}
                break

    # is_demo flag for frontend
    is_demo = environment_id == "env:demo"

    stats = HomeStats(
        org_id=_DEMO_ORG.id,
        environment_id=environment_id,
        agent_count=len(agents),
        system_count=len(systems),
        incident_count=incident_count,
        replay_ready=sum(1 for i in incidents if i.replay_result),
        fixes_verified=fixes_verified,
        proofs_issued=proofs_issued,
        scenario_count=sum(a.scenario_count for a in agents),
        pending_replay=pending_replay,
        pending_verification=pending_verification,
        pending_proof=fixes_verified - proofs_issued,
    )
    result = stats.to_dict()
    result["setup_health"] = setup_health
    result["queues"] = queues
    result["recent_proofs"] = recent_proofs
    result["next_action"] = next_action
    result["is_demo"] = is_demo
    return result


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


@router.post("/platform/seed-demo")
def seed_demo(_org: str = Depends(require_auth)) -> dict:
    """Create 5 demo incidents through the full proof-loop."""
    from notary_platform.api_server.routers.incidents import _demo_agent_fn
    from notary_platform.certificates import generate_certificate
    from notary_platform.demo_scenarios import SCENARIOS, build_snapshot
    from notary_platform.replay_engine.mutation import run_mutation
    from notary_platform.replay_engine.worker import run_replay

    agent_fn = _demo_agent_fn
    if not agent_fn:
        return {"created": 0, "error": "no agent function registered"}

    created = []
    # Only lending-denial uses the full proof-loop. Others are ingested-only.
    scenarios = {
        "inc-001-lending": ("lending-denial", True),
        "inc-002-support": (None, False),
        "inc-003-prior-auth": (None, False),
    }

    fn = agent_fn
    for iid, (scenario_id, do_full) in scenarios.items():
        if scenario_id:
            scenario = SCENARIOS.get(scenario_id)
            if not scenario:
                continue
            snap = build_snapshot(scenario)
            inc = storage.create_incident(snap, org_id=_org)
            inc._record_custody("ingested", actor=f"demo seed: {scenario_id}", detail="Incidents page")
            storage.update_incident(inc)
            storage.persist_evidence(inc.incident_id, "snapshot", snap)

            if do_full:
                run_replay(inc, snap, fn)
                storage.update_incident(inc)
                result = run_mutation(snap, fn, {"threshold": 620}, expected_correct_behavior="APPROVE")
                inc.mutation_result = result
                if result.get("mitigated"):
                    inc.status = IncidentStatus("mitigated")
                storage.update_incident(inc)
                cert = generate_certificate(
                    incident_id=inc.incident_id,
                    root_hash=inc.snapshot_summary.get("root_hash", ""),
                    integrity_status="verified",
                    replay_result=inc.replay_result,
                    original_decision=result.get("original_decision"),
                    mutated_decision=result.get("mutated_decision"),
                    fix_config=result.get("fix_config", {}),
                    expected_correct_behavior="APPROVE",
                    timestamp=inc.snapshot_summary.get("timestamp", ""),
                )
                inc.certificate = cert
                inc.status = IncidentStatus("certified")
                storage.store_certificate(inc.incident_id, cert)
                storage.update_incident(inc)
        else:
            # Create a lightweight incident with no snapshot/replay for demo
            inc = storage.create_incident({}, org_id=_org)
            inc._record_custody("ingested", actor=f"demo seed: {iid}", detail="Incidents page")
            storage.update_incident(inc)

        created.append(inc.incident_id)

    return {"created": len(created), "incident_ids": created}
