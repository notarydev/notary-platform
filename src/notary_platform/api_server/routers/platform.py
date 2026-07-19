"""Notary Platform customer-facing API (WO-47 through WO-54, WO-80).

Provides read-only endpoints for the Notary Platform SPA. The data is seeded
from platform_data for the demo organization. Production-ready persistence
is added when the backend supports multi-org storage.
"""

from __future__ import annotations

import hashlib
import secrets
import time as _time_module
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from notary_platform.api_server.auth import require_auth
from notary_platform.api_server.routers.ingestion import storage
from notary_platform.models import HomeStats, IncidentStatus, ScenarioCandidate
from notary_platform.platform_data import seed

router = APIRouter(tags=["platform"])

# Seeded demo data. In production these would come from a database.
_SEED: dict[str, Any] = seed()
_DEMO_ORG = _SEED["organization"]
_ENVS_BY_ID = {e.id: e for e in _SEED["environments"]}
_AGENTS_BY_ID = {a.id: a for a in _SEED["agents"]}
_SYSTEMS_BY_ID = {s.id: s for s in _SEED["systems"]}
_POLICIES_BY_ID = {p.id: p for p in _SEED["policies"]}

# Product surface stores (WO-80)
_scenario_store: dict[str, ScenarioCandidate] = {}


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


@router.get("/platform/org/systems/{system_id}")
def get_system(system_id: str, _org: str = Depends(require_auth)) -> dict:
    sys = _SYSTEMS_BY_ID.get(system_id)
    if sys is None or sys.org_id != _org:
        raise HTTPException(status_code=404, detail="system not found")
    return sys.to_dict()


@router.post("/platform/org/systems/{system_id}/test")
def test_system_connection(system_id: str, _org: str = Depends(require_auth)) -> dict:
    sys = _SYSTEMS_BY_ID.get(system_id)
    if sys is None or sys.org_id != _org:
        raise HTTPException(status_code=404, detail="system not found")
    # Simulated safe demo check — never exposes real secrets.
    simulated = sys.status == "connected"
    sys.last_checked = _time_module.strftime("%Y-%m-%dT%H:%M:%SZ", _time_module.gmtime())
    return {
        "system_id": system_id,
        "tested_at": sys.last_checked,
        "status": "healthy" if simulated else "unreachable",
        "auth_status": sys.auth_status,
        "sandbox_supported": sys.sandbox_supported,
        "message": "Simulated connection check succeeded" if simulated else "Simulated connection check failed — configure credentials",
    }


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
    from notary_platform.api_server.routers.verification import _vr_store

    agents = [a for a in _SEED["agents"] if a.environment_id == environment_id]
    systems = [s for s in _SEED["systems"] if s.environment_id == environment_id]
    incidents = storage.list_incidents(org_id=_org)
    incident_count = len(incidents)
    fixes_verified = sum(1 for i in incidents if i.status.value == "mitigated")
    proofs_issued = sum(1 for i in incidents if i.status.value == "certified")
    pending_replay = sum(1 for i in incidents if i.status.value == "ingested" and not i.replay_result)
    pending_verification = sum(1 for i in incidents if i.status.value == "replayed" and i.status.value != "mitigated")

    vrs = [vr for vr in _vr_store.values() if vr.org_id == _org and vr.environment_id == environment_id]
    vrs_replayable = sum(1 for v in vrs if v.replayability.value == "replayable")
    vrs_requires_label = sum(1 for v in vrs if v.replayability.value == "requires_human_label")
    vrs_requires_sandbox = sum(1 for v in vrs if v.replayability.value == "requires_sandbox")
    vrs_evidence_only = sum(1 for v in vrs if v.replayability.value == "evidence_only")
    labels_needing_review = sum(1 for v in vrs if v.suggested_labels or (v.replayability.value == "requires_human_label" and not v.current_label_id))

    # Setup health
    connected_agents = sum(1 for a in agents if a.sdk_status == "connected")
    connected_systems = sum(1 for s in systems if s.status == "connected")
    setup_health = {
        "sdk_installed": connected_agents > 0,
        "agents_instrumented": len(agents),
        "systems_connected": connected_systems,
        "systems_total": len(systems),
        "systems_sandbox_ready": sum(1 for s in systems if s.sandbox_supported),
        "capture_policies": len(_SEED["policies"]),
        "incidents_collected": incident_count,
        "proofs_issued": proofs_issued,
    }

    # Active queues
    queues = {
        "needs_replay": pending_replay,
        "needs_verification": pending_verification,
        "proofs_ready": max(0, fixes_verified - proofs_issued),
        "needs_label": vrs_requires_label,
        "needs_sandbox": vrs_requires_sandbox,
        "evidence_only": vrs_evidence_only,
        "scenario_candidates": len(_scenario_store),
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

    # Blockers
    blockers = []
    if vrs_requires_label:
        blockers.append({"type": "missing_label", "count": vrs_requires_label, "next_action": "Review Verification Records needing labels"})
    if vrs_requires_sandbox:
        blockers.append({"type": "missing_sandbox", "count": vrs_requires_sandbox, "next_action": "Configure required sandboxes"})
    if any(s.status == "disconnected" for s in systems):
        dc = sum(1 for s in systems if s.status == "disconnected")
        blockers.append({"type": "disconnected_system", "count": dc, "next_action": "Reconnect systems in Systems"})

    # Next action (priority: label > sandbox > replay > verify > proof > scenario candidate)
    next_action = None
    if vrs_requires_label:
        v = next((v for v in vrs if v.replayability.value == "requires_human_label"), None)
        if v:
            next_action = {"action": "label", "vr_id": v.id, "label": f"Add label to {v.id}", "view": "verification-records"}
    if not next_action and vrs_requires_sandbox:
        v = next((v for v in vrs if v.replayability.value == "requires_sandbox"), None)
        if v:
            next_action = {"action": "sandbox", "vr_id": v.id, "label": f"Configure sandbox for {v.id}", "view": "systems"}
    if not next_action:
        for inc in incidents:
            if not inc.replay_result:
                next_action = {"action": "replay", "incident_id": inc.incident_id, "label": f"Replay {inc.incident_id}", "view": "incidents"}
                break
    if not next_action:
        for inc in incidents:
            if inc.status.value == "replayed" and not inc.mutation_result:
                next_action = {"action": "verify", "incident_id": inc.incident_id, "label": f"Verify fix for {inc.incident_id}", "view": "incidents"}
                break
    if not next_action:
        for inc in incidents:
            if inc.status.value == "mitigated" and not inc.certificate:
                next_action = {"action": "proof", "incident_id": inc.incident_id, "label": f"Issue proof for {inc.incident_id}", "view": "incidents"}
                break
    if not next_action and _scenario_store:
        sc = next((s for s in _scenario_store.values() if s.state == "candidate"), None)
        if sc:
            next_action = {"action": "scenario", "scenario_id": sc.id, "label": f"Promote {sc.business_title} to scenario", "view": "scenarios"}

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
        vrs_total=len(vrs),
        vrs_replayable=vrs_replayable,
        vrs_requires_label=vrs_requires_label,
        vrs_requires_sandbox=vrs_requires_sandbox,
        vrs_evidence_only=vrs_evidence_only,
        labels_needing_review=labels_needing_review,
        systems_disconnected=sum(1 for s in systems if s.status == "disconnected"),
        systems_sandbox_ready=sum(1 for s in systems if s.sandbox_supported),
        scenario_candidates=len(_scenario_store),
        blocked_items=len(blockers),
    )
    result = stats.to_dict()
    result["setup_health"] = setup_health
    result["queues"] = queues
    result["recent_proofs"] = recent_proofs
    result["blockers"] = blockers
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
def seed_demo(
    depth: str = Query("full"),
    _org: str = Depends(require_auth),
) -> dict:
    """Create the scenario-backed demo catalog.

    depth=full: 20 Verification Records, incidents, proofs, labels, scenario candidates.
    depth=quick: legacy 3-incident seed (kept for backward compatibility).
    """
    from notary_platform.api_server.routers.incidents import _demo_agent_fn
    from notary_platform.api_server.routers.verification import _label_store, _vr_store
    from notary_platform.demo_catalog import build_catalog

    if depth == "quick":
        from notary_platform.certificates import generate_certificate
        from notary_platform.demo_scenarios import SCENARIOS, build_snapshot
        from notary_platform.replay_engine.mutation import run_mutation
        from notary_platform.replay_engine.worker import run_replay

        agent_fn = _demo_agent_fn
        if not agent_fn:
            return {"created": 0, "error": "no agent function registered"}
        created = []
        scenarios = {
            "inc-001-lending": ("lending-denial", True),
            "inc-002-support": (None, False),
            "inc-003-prior-auth": (None, False),
        }
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
                    run_replay(inc, snap, agent_fn)
                    result = run_mutation(snap, agent_fn, {"threshold": 620}, expected_correct_behavior="APPROVE")
                    inc.mutation_result = result
                    if result.get("mitigated"):
                        inc.status = IncidentStatus("mitigated")
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
                inc = storage.create_incident({}, org_id=_org)
                inc._record_custody("ingested", actor=f"demo seed: {iid}", detail="Incidents page")
                storage.update_incident(inc)
            created.append(inc.incident_id)
        return {"created": len(created), "incident_ids": created}

    result = build_catalog(storage, _vr_store, _label_store, _scenario_store, org_id=_org)
    return result


@router.get("/platform/demo-catalog")
def demo_catalog(_org: str = Depends(require_auth)) -> dict:
    """Return the demo catalog definitions for the UI."""
    from notary_platform.demo_catalog import DEMO_CASES
    return {
        "cases": [
            {
                "scenario_id": c.scenario_id,
                "business_title": c.business_title,
                "domain": c.domain,
                "source_system_id": c.source_system_id,
                "capture_source": c.capture_source,
                "replayability": c.replayability.value,
                "incident_state": c.incident_state,
                "proof_state": c.proof_state,
                "scenario_state": c.scenario_state,
                "next_action": c.next_action,
            }
            for c in DEMO_CASES
        ]
    }


@router.get("/platform/product-status")
def product_status(_org: str = Depends(require_auth)) -> dict:
    """Return product-surface readiness summary for the internal Command Center."""
    from notary_platform.api_server.routers.verification import _vr_store
    return {
        "environment": "env:demo",
        "product_surface": {
            "home": "ready",
            "setup": "ready",
            "verification_records": "ready",
            "incidents": "ready",
            "proofs": "ready",
            "systems": "ready",
            "scenarios": "ready_scaffold",
            "governance": "ready_scaffold",
            "settings": "ready",
        },
        "demo_data_seeded": len(_vr_store) > 0,
    }


@router.get("/scenario-candidates")
def list_scenario_candidates(
    state: Optional[str] = Query(None),
    _org: str = Depends(require_auth),
) -> list[dict]:
    """List scenario candidates, optionally filtered by state."""
    candidates = [s for s in _scenario_store.values() if s.org_id == _org]
    if state:
        candidates = [s for s in candidates if s.state == state]
    return [s.to_dict() for s in candidates]


# ── API Key management (WO-66) ──
_key_store: dict[str, dict] = {}


@router.post("/platform/keys")
def create_api_key(label: str = Query(""), key_type: str = Query("api"), org_id: str = Depends(require_auth)) -> dict:
    raw = "sk-" + secrets.token_urlsafe(32)
    key_id = "key-" + secrets.token_hex(6)
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    _key_store[key_id] = {
        "id": key_id, "org_id": org_id, "key_type": key_type, "label": label,
        "key_hash": hashed, "scopes": ["read", "write"],
        "created_at": _time_module.strftime("%Y-%m-%dT%H:%M:%SZ", _time_module.gmtime()),
        "last_used": "", "revoked": False,
    }
    return {"id": key_id, "key": raw, "label": label, "key_type": key_type, "message": "Store this key — it will only be shown once"}


@router.get("/platform/keys")
def list_api_keys(org_id: str = Depends(require_auth)) -> list[dict]:
    return [{k: v for k, v in d.items() if k != "key_hash"} for d in _key_store.values() if d["org_id"] == org_id]


@router.post("/platform/keys/{key_id}/revoke")
def revoke_api_key(key_id: str, org_id: str = Depends(require_auth)) -> dict:
    key = _key_store.get(key_id)
    if not key or key["org_id"] != org_id:
        raise HTTPException(status_code=404, detail="Key not found")
    key["revoked"] = True
    return {"id": key_id, "revoked": True}
