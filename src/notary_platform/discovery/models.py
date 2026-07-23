"""Domain models for DEP discovery — providers, resources, conflicts, and ingestion receipts."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ProviderRegistration:
    provider_id: str

    @property
    def id(self) -> str:
        return self.provider_id

    @id.setter
    def id(self, value: str) -> None:
        self.provider_id = value
    org_id: str
    name: str
    provider_type: str  # sdk, platform, trace_system, connector, manual
    contact: str = ""
    public_key: str = ""
    asserted_capabilities: list[str] = field(default_factory=list)
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "org_id": self.org_id,
            "name": self.name,
            "provider_type": self.provider_type,
            "contact": self.contact,
            "public_key": self.public_key,
            "asserted_capabilities": self.asserted_capabilities.copy(),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ProviderRegistration:
        return cls(
            provider_id=d.get("provider_id", ""),
            org_id=d.get("org_id", "demo-org"),
            name=d.get("name", ""),
            provider_type=d.get("provider_type", ""),
            contact=d.get("contact", ""),
            public_key=d.get("public_key", ""),
            asserted_capabilities=list(d.get("asserted_capabilities", [])),
            created_at=d.get("created_at", ""),
        )


@dataclass
class DecisionEvidenceResource:
    resource_id: str

    @property
    def id(self) -> str:
        return self.resource_id

    @id.setter
    def id(self, value: str) -> None:
        self.resource_id = value
    org_id: str
    envelope_id: str
    resource_type: str
    provider_id: str
    digest_algorithm: str
    digest_value: str
    payload_ref: str
    provenance_collected_at: str = ""
    provenance_source_ref: str = ""
    version: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "org_id": self.org_id,
            "envelope_id": self.envelope_id,
            "resource_type": self.resource_type,
            "provider_id": self.provider_id,
            "digest_algorithm": self.digest_algorithm,
            "digest_value": self.digest_value,
            "payload_ref": self.payload_ref,
            "provenance_collected_at": self.provenance_collected_at,
            "provenance_source_ref": self.provenance_source_ref,
            "version": self.version,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DecisionEvidenceResource:
        return cls(
            resource_id=d.get("resource_id", ""),
            org_id=d.get("org_id", "demo-org"),
            envelope_id=d.get("envelope_id", ""),
            resource_type=d.get("resource_type", ""),
            provider_id=d.get("provider_id", ""),
            digest_algorithm=d.get("digest_algorithm", ""),
            digest_value=d.get("digest_value", ""),
            payload_ref=d.get("payload_ref", ""),
            provenance_collected_at=d.get("provenance_collected_at", ""),
            provenance_source_ref=d.get("provenance_source_ref", ""),
            version=d.get("version", ""),
            created_at=d.get("created_at", ""),
        )


@dataclass
class IntegrityConflict:
    conflict_id: str

    @property
    def id(self) -> str:
        return self.conflict_id

    @id.setter
    def id(self, value: str) -> None:
        self.conflict_id = value
    org_id: str
    resource_id: str
    provider_id: str
    existing_digest: str
    conflicting_digest: str
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.conflict_id:
            self.conflict_id = f"con-{uuid.uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "org_id": self.org_id,
            "resource_id": self.resource_id,
            "provider_id": self.provider_id,
            "existing_digest": self.existing_digest,
            "conflicting_digest": self.conflicting_digest,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> IntegrityConflict:
        return cls(
            conflict_id=d.get("conflict_id", ""),
            org_id=d.get("org_id", "demo-org"),
            resource_id=d.get("resource_id", ""),
            provider_id=d.get("provider_id", ""),
            existing_digest=d.get("existing_digest", ""),
            conflicting_digest=d.get("conflicting_digest", ""),
            created_at=d.get("created_at", ""),
        )


class IngestionResultStatus:
    ACCEPTED = "accepted"
    DUPLICATE = "duplicate"
    REJECTED = "rejected"
    QUARANTINED = "quarantined"


@dataclass
class IngestionReceipt:
    resource_id: str
    status: str  # accepted | duplicate | rejected | quarantined
    envelope_id: str = ""
    digest_value: str = ""
    conflict_id: str = ""
    errors: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "status": self.status,
            "envelope_id": self.envelope_id,
            "digest_value": self.digest_value,
            "conflict_id": self.conflict_id,
            "errors": self.errors.copy(),
        }
