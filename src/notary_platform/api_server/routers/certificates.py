"""Certificates and mutation router."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import notary_platform.api_server.routers.incidents as incidents_mod
from notary_platform.certificates import generate_certificate, verify_certificate_signature
from notary_platform.models import IncidentStatus
from notary_platform.replay_engine.mutation import run_mutation

router = APIRouter(tags=["certificates"])


class MutationRequest(BaseModel):
    fix_config: dict[str, Any]
    expected_correct_behavior: str = "APPROVE"


@router.post("/incidents/{incident_id}/mutation")
def apply_mutation(incident_id: str, body: MutationRequest) -> dict[str, Any]:
    inc = incidents_mod.storage.get_incident(incident_id)
    if inc is None:
        raise HTTPException(status_code=404, detail="incident not found")

    snapshot_dict = incidents_mod.storage.get_snapshot(incident_id)
    if snapshot_dict is None:
        raise HTTPException(status_code=404, detail="snapshot not found")

    agent_fn = incidents_mod._demo_agent_fn
    if agent_fn is None:
        raise HTTPException(status_code=400, detail="no agent function registered")

    result = run_mutation(
        snapshot_dict,
        agent_fn,
        body.fix_config,
        expected_correct_behavior=body.expected_correct_behavior,
    )

    inc.mutation_result = result
    if result.get("mitigated"):
        inc.status = IncidentStatus.mitigated
    incidents_mod.storage.update_incident(inc)

    return {"incident_id": incident_id, **result}


@router.post("/certificates/{incident_id}")
def issue_certificate(incident_id: str) -> dict[str, Any]:
    inc = incidents_mod.storage.get_incident(incident_id)
    if inc is None:
        raise HTTPException(status_code=404, detail="incident not found")

    if inc.status != IncidentStatus.mitigated:
        raise HTTPException(
            status_code=409,
            detail=f"incident status is '{inc.status.value}', must be 'mitigated'",
        )

    mutation = inc.mutation_result
    cert = generate_certificate(
        incident_id=incident_id,
        original_decision=mutation.get("original_decision"),
        mutated_decision=mutation.get("mutated_decision"),
        fix_config=mutation.get("fix_config", {}),
        timestamp=inc.snapshot_summary.get("timestamp", ""),
    )

    incidents_mod.storage.store_certificate(incident_id, cert)
    inc.status = IncidentStatus.certified
    inc.certificate = cert
    incidents_mod.storage.update_incident(inc)

    return cert


@router.get("/certificates/{incident_id}")
def get_certificate(incident_id: str) -> dict[str, Any]:
    cert = incidents_mod.storage.get_certificate(incident_id)
    if cert is None:
        raise HTTPException(status_code=404, detail="certificate not found")
    return cert


@router.get("/certificates/{incident_id}/verify")
def verify_certificate(incident_id: str) -> dict[str, Any]:
    cert = incidents_mod.storage.get_certificate(incident_id)
    if cert is None:
        raise HTTPException(status_code=404, detail="certificate not found")
    valid = verify_certificate_signature(cert)
    return {"incident_id": incident_id, "signature_valid": valid}
