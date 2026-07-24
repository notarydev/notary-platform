from __future__ import annotations

import uuid
from typing import Any

from notary_platform.dep.registry import SchemaRegistry
from notary_platform.dep.validation import validate_envelope
from notary_platform.discovery.models import (
    DecisionEvidenceResource,
    IngestionReceipt,
    IngestionResultStatus,
    IntegrityConflict,
)
from notary_platform.storage import StorageBackend


def _extract_resource_id(envelope: dict[str, Any]) -> str:
    return envelope.get("resource", {}).get("id", "")


def _extract_provider_id(envelope: dict[str, Any]) -> str:
    return envelope.get("resource", {}).get("provider_id", "")


def _extract_digest_value(envelope: dict[str, Any]) -> str:
    return envelope.get("digest", {}).get("value", "")


def _make_resource(envelope: dict[str, Any], org_id: str) -> DecisionEvidenceResource:
    resource = envelope.get("resource", {})
    digest = envelope.get("digest", {})
    provenance = envelope.get("provenance", {})
    rid = resource.get("id", f"res-{uuid.uuid4().hex[:12]}")
    pid = resource.get("provider_id", _extract_provider_id(envelope))
    return DecisionEvidenceResource(
        resource_id=rid,
        org_id=org_id,
        envelope_id=envelope.get("id", ""),
        resource_type=resource.get("type", "unknown"),
        provider_id=pid,
        digest_algorithm=digest.get("algorithm", "sha256"),
        digest_value=digest.get("value", ""),
        payload_ref=f"dep://payload/{rid}",
        provenance_collected_at=provenance.get("collected_at", resource.get("collected_at", "")),
        provenance_source_ref=provenance.get("source_ref", resource.get("source_ref", "")),
        version=resource.get("version", ""),
    )


class IngressService:
    """Ingest decision evidence payloads (DEP envelopes).

    Flow:
        1. Validate envelope structure against JSON Schema.
        2. Deduplicate by digest: same digest → ``duplicate``,
           different digest → ``quarantined`` + IntegrityConflict,
           not exists → ``accepted``.
        3. Persist immutable payload to storage.
        4. Index the resource in storage.
    """

    def __init__(self, storage: StorageBackend, registry: SchemaRegistry | None = None):
        self._storage = storage
        self._registry = registry or SchemaRegistry()

    def ingest(self, envelope: dict[str, Any], org_id: str) -> IngestionReceipt:
        validation = validate_envelope(envelope, self._registry)
        if not validation.valid:
            return IngestionReceipt(
                resource_id=_extract_resource_id(envelope),
                status=IngestionResultStatus.REJECTED,
                errors=validation.to_dicts(),
            )

        resource_id = _extract_resource_id(envelope)
        if not resource_id:
            return IngestionReceipt(
                resource_id="",
                status=IngestionResultStatus.REJECTED,
                errors=[{"code": "missing_resource_id", "message": "Envelope missing resource.id"}],
            )

        digest_value = _extract_digest_value(envelope)

        existing = self._storage.get_resource_by_id_and_org(resource_id, org_id)
        if existing is not None:
            if existing.digest_value == digest_value:
                return IngestionReceipt(
                    resource_id=resource_id,
                    status=IngestionResultStatus.DUPLICATE,
                    envelope_id=envelope.get("id", ""),
                    digest_value=digest_value,
                )

            conflict = IntegrityConflict(
                conflict_id=f"con-{uuid.uuid4().hex[:12]}",
                org_id=org_id,
                resource_id=resource_id,
                provider_id=_extract_provider_id(envelope),
                existing_digest=existing.digest_value,
                conflicting_digest=digest_value,
            )
            self._storage.create_integrity_conflict(conflict)
            return IngestionReceipt(
                resource_id=resource_id,
                status=IngestionResultStatus.QUARANTINED,
                envelope_id=envelope.get("id", ""),
                digest_value=digest_value,
                conflict_id=conflict.conflict_id,
                errors=[{
                    "code": "resource_identity_conflict",
                    "message": f"Resource '{resource_id}' already exists with a different digest",
                    "resource_id": resource_id,
                    "existing_digest": existing.digest_value,
                    "conflicting_digest": digest_value,
                }],
            )

        resource = _make_resource(envelope, org_id)
        self._storage.persist_payload(resource.payload_ref, envelope)
        self._storage.create_resource(resource)
        return IngestionReceipt(
            resource_id=resource_id,
            status=IngestionResultStatus.ACCEPTED,
            envelope_id=envelope.get("id", ""),
            digest_value=digest_value,
        )
