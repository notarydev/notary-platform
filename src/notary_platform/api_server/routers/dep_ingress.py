"""DEP ingress endpoints — accept evidence envelopes and batch/cloudevent payloads.

Spec (WP-030):
  POST /v1/dep/resources      — ingest a single resource envelope
  POST /v1/dep/batches        — ingest multiple envelopes atomically
  POST /v1/dep/cloudevents    — ingest a CloudEvent wrapper
  GET  /v1/dep/resources/{resource_id}  — retrieve resource metadata
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from notary_platform.api_server.auth import require_auth
from notary_platform.discovery.ingress import IngressService
from notary_platform.discovery.models import IngestionResultStatus
from notary_platform.storage import get_storage

router = APIRouter(tags=["dep-ingress"])
storage = get_storage()
_ingress_service: IngressService | None = None


def get_ingress_service() -> IngressService:
    global _ingress_service  # noqa: PLW0603
    if _ingress_service is None:
        from notary_platform.dep.registry import SchemaRegistry
        _ingress_service = IngressService(storage, SchemaRegistry())
    return _ingress_service


@router.post("/dep/resources")
def ingest_resource(
    body: dict[str, Any],
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    svc = get_ingress_service()
    receipt = svc.ingest(body, org_id)
    result = receipt.to_dict()

    status_code = _http_status(receipt.status)
    if status_code >= 400:
        raise HTTPException(status_code=status_code, detail=result)
    return result


@router.post("/dep/batches")
def ingest_batch(
    body: dict[str, Any],
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    envelopes = body.get("envelopes", []) if isinstance(body, dict) else []
    if not envelopes:
        raise HTTPException(status_code=422, detail="batch must contain at least one envelope")

    svc = get_ingress_service()
    receipts = [svc.ingest(env, org_id) for env in envelopes]
    accepted = sum(1 for r in receipts if r.status == IngestionResultStatus.ACCEPTED)
    rejected = sum(1 for r in receipts if r.status == IngestionResultStatus.REJECTED)
    quarantined = sum(1 for r in receipts if r.status == IngestionResultStatus.QUARANTINED)
    duplicates = sum(1 for r in receipts if r.status == IngestionResultStatus.DUPLICATE)

    return {
        "total": len(receipts),
        "accepted": accepted,
        "rejected": rejected,
        "quarantined": quarantined,
        "duplicates": duplicates,
        "receipts": [r.to_dict() for r in receipts],
    }


@router.post("/dep/cloudevents")
def ingest_cloudevent(
    body: dict[str, Any],
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    data = body.get("data", body.get("data_base64"))
    if data is None:
        raise HTTPException(status_code=422, detail="CloudEvent missing 'data' or 'data_base64'")

    if isinstance(data, str):
        import base64
        import json
        try:
            data = json.loads(base64.b64decode(data).decode("utf-8"))
        except Exception:
            raise HTTPException(status_code=422, detail="CloudEvent data_base64 is not valid base64-encoded JSON")

    svc = get_ingress_service()
    receipt = svc.ingest(data, org_id)
    result = {"cloudevent_id": body.get("id", ""), **receipt.to_dict()}

    status_code = _http_status(receipt.status)
    if status_code >= 400:
        raise HTTPException(status_code=status_code, detail=result)
    return result


@router.get("/dep/resources/{resource_id}")
def get_resource(
    resource_id: str,
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    resource = storage.get_resource(resource_id, org_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="resource not found")
    return resource.to_dict()


def _http_status(status: str) -> int:
    return {
        IngestionResultStatus.ACCEPTED: 200,
        IngestionResultStatus.DUPLICATE: 200,
        IngestionResultStatus.QUARANTINED: 409,
        IngestionResultStatus.REJECTED: 422,
    }.get(status, 422)
