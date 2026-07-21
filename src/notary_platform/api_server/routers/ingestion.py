"""Ingestion router — accepts SDK snapshots and creates incidents (WO-3).

Spec endpoints:
  POST /v1/incidents/ingest
  GET  /v1/incidents
  GET  /v1/incidents/{incident_id}
"""

from __future__ import annotations

import base64
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from notary_platform.api_server.auth import require_auth
from notary_platform.services import ServiceRegistry
from notary_platform.snapshot import ForensicSnapshot, verify_snapshot
from notary_platform.storage import get_storage

router = APIRouter(tags=["incidents"])
storage = get_storage()
_registry = ServiceRegistry(storage)


class SnapshotIngestRequest(BaseModel):
    snapshot: dict[str, Any]
    secret_key_b64: Optional[str] = None
    # Deprecated compatibility field. The authenticated/header org is authoritative.
    org_id: Optional[str] = None


@router.post("/incidents/ingest")
def ingest_snapshot(body: SnapshotIngestRequest, org_id: str = Depends(require_auth)) -> dict[str, Any]:
    snapshot_dict = body.snapshot

    for field in ("schema_version", "timestamp", "elements", "merkle_chain", "root_hash"):
        if field not in snapshot_dict:
            raise HTTPException(status_code=422, detail=f"missing required field: {field}")

    snapshot = ForensicSnapshot.from_dict(snapshot_dict)

    integrity_status = "verified"
    if body.secret_key_b64 is not None:
        try:
            key = base64.b64decode(body.secret_key_b64)
        except Exception:
            raise HTTPException(status_code=400, detail="secret_key_b64 cannot decode")

        if not verify_snapshot(snapshot, key):
            raise HTTPException(status_code=400, detail="snapshot integrity validation failed")
    else:
        integrity_status = "not_verified_missing_key"

    acting_org = org_id
    incident = storage.create_incident(snapshot_dict, org_id=acting_org)
    incident._record_custody(
        "ingested",
        actor=acting_org,
        detail=f"snapshot ingested; integrity={integrity_status}",
    )
    incident.snapshot_summary = {
        **incident.snapshot_summary,
        "integrity": integrity_status,
    }
    storage.update_incident(incident)

    # Persist the raw snapshot as immutable evidence.
    evidence_ref = storage.persist_evidence(incident.incident_id, "snapshot", snapshot_dict)
    incident._record_custody("evidence_stored", actor="system", detail=evidence_ref)
    storage.update_incident(incident)

    # Phase 2: also create a Verification Record from the SDK snapshot
    try:
        from notary_platform.services import IngestionService

        ingestion_service = IngestionService(_registry)
        ingestion_service.create_from_sdk_snapshot(
            snapshot_dict,
            org_id=acting_org,
            promoted_to_incident=incident.incident_id,
        )
    except Exception:
        pass  # V.R. creation is best-effort; don't break existing ingestion

    return {
        "incident_id": incident.incident_id,
        "org_id": acting_org,
        "status": incident.status.value,
        "integrity": integrity_status,
        "evidence_ref": evidence_ref,
    }


@router.get("/incidents")
def list_incidents(org_id: str = Depends(require_auth)) -> list[dict[str, Any]]:
    result = []
    for inc in storage.list_incidents(org_id=org_id):
        d = inc.to_dict()
        has_fix = inc.mutation_result is not None and inc.mutation_result.get("mitigated")
        has_cert = inc.certificate is not None and inc.certificate.get("certificate_id") is not None
        d["can_issue_proof"] = bool(has_fix) and not has_cert
        d["issue_proof_reason"] = (
            "Fix verification must produce the expected outcome before issuing proof."
            if not has_fix
            else ("Proof already issued" if has_cert else "")
        )
        result.append(d)
    return result


@router.get("/incidents/{incident_id}")
def get_incident(incident_id: str, org_id: str = Depends(require_auth)) -> dict[str, Any]:
    inc = storage.get_incident(incident_id)
    if inc is None:
        raise HTTPException(status_code=404, detail="incident not found")
    if inc.org_id != org_id:
        raise HTTPException(status_code=404, detail="incident not found")
    return inc.to_dict()


@router.get("/incidents/{incident_id}/snapshot")
def get_incident_snapshot(incident_id: str, org_id: str = Depends(require_auth)) -> dict[str, Any]:
    snap = storage.get_snapshot(incident_id)
    if snap is None:
        raise HTTPException(status_code=404, detail="snapshot not found")
    inc = storage.get_incident(incident_id)
    if inc is not None and inc.org_id != org_id:
        raise HTTPException(status_code=404, detail="snapshot not found")
    return snap
