"""Ingestion router — accepts SDK snapshots and creates incidents."""

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from notary_platform.snapshot import ForensicSnapshot, verify_snapshot
from notary_platform.storage import Storage

router = APIRouter(tags=["ingestion"])
storage = Storage()


class SnapshotIngestRequest(BaseModel):
    snapshot: dict[str, Any]
    secret_key_b64: Optional[str] = None


@router.post("/ingestion/snapshots")
def ingest_snapshot(body: SnapshotIngestRequest) -> dict[str, Any]:
    snapshot_dict = body.snapshot

    for field in ("schema_version", "timestamp", "elements", "merkle_chain", "root_hash"):
        if field not in snapshot_dict:
            raise HTTPException(status_code=422, detail=f"missing required field: {field}")

    snapshot = ForensicSnapshot.from_dict(snapshot_dict)

    integrity_status = "verified"
    if body.secret_key_b64 is not None:
        import base64

        try:
            key = base64.b64decode(body.secret_key_b64)
        except Exception:
            raise HTTPException(status_code=400, detail="secret_key_b64 cannot decode")

        if not verify_snapshot(snapshot, key):
            raise HTTPException(status_code=400, detail="snapshot integrity validation failed")
    else:
        integrity_status = "not_verified_missing_key"

    incident = storage.create_incident(snapshot_dict)

    return {
        "incident_id": incident.incident_id,
        "status": incident.status.value,
        "integrity": integrity_status,
    }


@router.get("/ingestion/snapshots/{incident_id}")
def get_snapshot(incident_id: str) -> dict[str, Any]:
    snap = storage.get_snapshot(incident_id)
    if snap is None:
        raise HTTPException(status_code=404, detail="incident not found")
    return snap
