"""Incidents router — list and retrieve incidents."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from notary_platform.api_server.routers.ingestion import storage

router = APIRouter(tags=["incidents"])


@router.get("/incidents")
def list_incidents() -> list[dict[str, Any]]:
    return [inc.to_dict() for inc in storage.list_incidents()]


@router.get("/incidents/{incident_id}")
def get_incident(incident_id: str) -> dict[str, Any]:
    inc = storage.get_incident(incident_id)
    if inc is None:
        raise HTTPException(status_code=404, detail="incident not found")
    return inc.to_dict()
