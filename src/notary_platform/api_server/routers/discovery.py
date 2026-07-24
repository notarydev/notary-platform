"""Discovery router — source inventory and provider registration.

Spec (WP-030):
  GET  /v1/discovery/sources              — list all indexed resources for the org
  POST /v1/discovery/providers             — register a provider
  GET  /v1/discovery/providers/{provider_id}  — get provider details
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from notary_platform.api_server.auth import require_auth
from notary_platform.discovery.models import ProviderRegistration
from notary_platform.storage import get_storage

router = APIRouter(tags=["discovery"])
storage = get_storage()


@router.get("/discovery/sources")
def list_sources(org_id: str = Depends(require_auth)) -> list[dict[str, Any]]:
    return [r.to_dict() for r in storage.list_resources(org_id)]


@router.post("/discovery/providers")
def register_provider(
    body: dict[str, Any],
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    provider = ProviderRegistration.from_dict(body)
    provider.org_id = org_id

    existing = storage.get_provider(provider.provider_id, org_id)
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"provider '{provider.provider_id}' already exists in this org")

    created = storage.create_provider(provider)
    return created.to_dict()


@router.get("/discovery/providers/{provider_id}")
def get_provider(
    provider_id: str,
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    provider = storage.get_provider(provider_id, org_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="provider not found")
    return provider.to_dict()
