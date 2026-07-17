"""Mutation-testing and certificate router (WO-5).

Spec endpoints:
  POST /v1/incidents/{incident_id}/mutation-tests
  GET  /v1/incidents/{incident_id}/mutation-tests
  POST /v1/incidents/{incident_id}/certificates
  GET  /v1/incidents/{incident_id}/certificates/{certificate_id}
  GET  /v1/incidents/{incident_id}/certificates/{certificate_id}/download
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import notary_platform.api_server.routers.incidents as incidents_mod
from notary_platform.api_server.auth import require_auth
from notary_platform.certificates import (
    CERTIFICATE_ID,
    generate_certificate,
    verify_certificate_signature,
)
from notary_platform.models import IncidentStatus
from notary_platform.replay_engine.mutation import run_mutation

router = APIRouter(tags=["mutation", "certificates"])


class MutationRequest(BaseModel):
    fix_config: dict[str, Any]
    expected_correct_behavior: str = "APPROVE"


@router.post("/incidents/{incident_id}/mutation-tests")
def apply_mutation(incident_id: str, body: MutationRequest, org_id: str = Depends(require_auth)) -> dict[str, Any]:
    inc = incidents_mod._get_incident(incident_id, org_id)

    # Mutation requires a reproducible incident.
    if not inc.replay_result or inc.replay_result.get("replay_status") != "replayed":
        raise HTTPException(
            status_code=409,
            detail="mutation requires a reproducible replay; run replay first",
        )

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
    inc._record_custody(
        "mutation_tested",
        actor=org_id,
        detail=f"mitigated={result.get('mitigated')} decision={result.get('mutated_decision')}",
    )
    incidents_mod.storage.update_incident(inc)
    incidents_mod.storage.persist_evidence(incident_id, "mutation", result)

    return {"incident_id": incident_id, "org_id": org_id, **result}


@router.get("/incidents/{incident_id}/mutation-tests")
def get_mutation(incident_id: str, org_id: str = Depends(require_auth)) -> dict[str, Any]:
    inc = incidents_mod._get_incident(incident_id, org_id)
    if not inc.mutation_result:
        raise HTTPException(status_code=404, detail="mutation test not run")
    return {"incident_id": incident_id, "org_id": org_id, **inc.mutation_result}


@router.post("/incidents/{incident_id}/certificates")
def issue_certificate(incident_id: str, org_id: str = Depends(require_auth)) -> dict[str, Any]:
    inc = incidents_mod._get_incident(incident_id, org_id)

    if inc.status != IncidentStatus.mitigated:
        raise HTTPException(
            status_code=409,
            detail=f"incident status is '{inc.status.value}', must be 'mitigated'",
        )

    mutation = inc.mutation_result
    cert = generate_certificate(
        incident_id=incident_id,
        root_hash=inc.snapshot_summary.get("root_hash", ""),
        integrity_status="verified" if inc.snapshot_summary.get("integrity") == "verified" else "unverified",
        replay_result=inc.replay_result,
        original_decision=mutation.get("original_decision"),
        mutated_decision=mutation.get("mutated_decision"),
        fix_config=mutation.get("fix_config", {}),
        expected_correct_behavior=mutation.get("expected_correct_behavior", ""),
        timestamp=inc.snapshot_summary.get("timestamp", ""),
    )

    inc.certificate = cert
    inc.status = IncidentStatus.certified
    inc._record_custody("certified", actor=org_id, detail=f"certificate {CERTIFICATE_ID}")
    incidents_mod.storage.store_certificate(incident_id, cert)
    incidents_mod.storage.update_incident(inc)

    return cert


@router.get("/incidents/{incident_id}/certificates/{certificate_id}")
def get_certificate(incident_id: str, certificate_id: str, org_id: str = Depends(require_auth)) -> dict[str, Any]:
    inc = incidents_mod._get_incident(incident_id, org_id)
    cert = inc.certificate
    if cert is None:
        raise HTTPException(status_code=404, detail="certificate not found")
    if cert.get("certificate_id") != certificate_id:
        raise HTTPException(status_code=404, detail="certificate not found")
    return cert


@router.get("/incidents/{incident_id}/certificates/{certificate_id}/download")
def download_certificate(incident_id: str, certificate_id: str, org_id: str = Depends(require_auth)) -> JSONResponse:
    inc = incidents_mod._get_incident(incident_id, org_id)
    cert = inc.certificate
    if cert is None or cert.get("certificate_id") != certificate_id:
        raise HTTPException(status_code=404, detail="certificate not found")
    resp = JSONResponse(content=cert)
    resp.headers["Content-Disposition"] = f'attachment; filename="proof_of_mitigation_{incident_id}.json"'
    return resp


@router.get("/incidents/{incident_id}/certificates/{certificate_id}/verify")
def verify_certificate(incident_id: str, certificate_id: str, org_id: str = Depends(require_auth)) -> dict[str, Any]:
    inc = incidents_mod._get_incident(incident_id, org_id)
    cert = inc.certificate
    if cert is None or cert.get("certificate_id") != certificate_id:
        raise HTTPException(status_code=404, detail="certificate not found")
    valid = verify_certificate_signature(cert)
    return {"incident_id": incident_id, "certificate_id": certificate_id, "signature_valid": valid}
