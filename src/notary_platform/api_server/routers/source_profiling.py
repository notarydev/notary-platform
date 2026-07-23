"""Source profiling and mapping router (WP-040).

Spec:
  POST /v1/discovery/sources                       — create source connection
  POST /v1/discovery/sources/{source_id}/profile    — queue/execute profile
  GET  /v1/discovery/sources/{source_id}/profiles/{profile_id} — profile results
  POST /v1/discovery/sources/{source_id}/mappings/propose — propose mappings
  POST /v1/discovery/sources/{source_id}/mappings    — confirm mapping
  GET  /v1/discovery/sources/{source_id}/coverage    — coverage report
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from notary_platform.api_server.auth import require_auth
from notary_platform.discovery.profiling import SourceProfileService
from notary_platform.discovery.sources import SourceConnection
from notary_platform.storage import get_storage

router = APIRouter(tags=["discovery"])
storage = get_storage()

_services: dict[str, SourceProfileService] = {}


def _get_svc() -> SourceProfileService:
    key = str(id(storage))
    if key not in _services:
        _services[key] = SourceProfileService(storage)
    return _services[key]


@router.post("/discovery/sources")
def create_source(
    body: dict[str, Any],
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    conn = SourceConnection.from_dict(body)
    conn.org_id = org_id
    created = storage.create_source_connection(conn)
    return created.to_dict()


@router.get("/discovery/source-connections")
def list_source_connections(org_id: str = Depends(require_auth)) -> list[dict[str, Any]]:
    results = storage.list_source_connections(org_id)
    return [s.to_dict() for s in results]


@router.get("/discovery/source-connections/{source_id}")
def get_source(
    source_id: str,
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    conn = storage.get_source_connection(source_id, org_id)
    if conn is None:
        raise HTTPException(status_code=404, detail="source not found")
    return conn.to_dict()


@router.post("/discovery/source-connections/{source_id}/profile")
def profile_source(
    source_id: str,
    body: dict[str, Any],
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    conn = storage.get_source_connection(source_id, org_id)
    if conn is None:
        raise HTTPException(status_code=404, detail="source not found")

    records = body.get("records", [])
    if not records:
        raise HTTPException(status_code=422, detail="records required for profiling")

    svc = _get_svc()
    profile = svc.profile_records(source_id, org_id, records)
    return profile.to_dict()


@router.get("/discovery/source-connections/{source_id}/profiles/{profile_id}")
def get_profile(
    source_id: str,
    profile_id: str,
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    profile = storage.get_source_profile(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="profile not found")
    if profile.org_id != org_id:
        raise HTTPException(status_code=404, detail="profile not found")
    return profile.to_dict()


@router.post("/discovery/source-connections/{source_id}/mappings/propose")
def propose_mappings(
    source_id: str,
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    conn = storage.get_source_connection(source_id, org_id)
    if conn is None:
        raise HTTPException(status_code=404, detail="source not found")

    svc = _get_svc()
    mapping = svc.propose_mappings(source_id, org_id)
    return mapping.to_dict()


@router.post("/discovery/source-connections/{source_id}/mappings")
def confirm_mapping(
    source_id: str,
    body: dict[str, Any],
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    conn = storage.get_source_connection(source_id, org_id)
    if conn is None:
        raise HTTPException(status_code=404, detail="source not found")

    mapping_id = body.get("mapping_id", "")
    if not mapping_id:
        raise HTTPException(status_code=422, detail="mapping_id required")

    edits = body.get("mappings")
    svc = _get_svc()
    result = svc.confirm_mapping(mapping_id, org_id, edits)
    if result is None:
        raise HTTPException(status_code=404, detail="mapping not found")
    return result.to_dict()


@router.get("/discovery/source-connections/{source_id}/coverage")
def get_coverage(
    source_id: str,
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    conn = storage.get_source_connection(source_id, org_id)
    if conn is None:
        raise HTTPException(status_code=404, detail="source not found")

    svc = _get_svc()
    return svc.get_coverage(source_id, org_id)
