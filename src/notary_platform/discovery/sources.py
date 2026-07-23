"""Domain models for source connections, cursors, profiling, and field mapping."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class SourceConnection:
    id: str = ""
    org_id: str = ""
    name: str = ""
    source_type: str = ""  # dep, file, api, sdk, oltp
    adapter_type: str = ""  # generic_dep, csv_import, langsmith, salesforce
    status: str = "created"  # created | connecting | connected | error | disconnected
    config_json: str = "{}"
    credentials_ref: str = ""
    description: str = ""
    last_connected_at: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            object.__setattr__(self, "id", f"src-{uuid.uuid4().hex[:12]}")
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "name": self.name,
            "source_type": self.source_type,
            "adapter_type": self.adapter_type,
            "status": self.status,
            "config_json": self.config_json,
            "credentials_ref": self.credentials_ref,
            "description": self.description,
            "last_connected_at": self.last_connected_at,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SourceConnection:
        return cls(
            id=d.get("id", f"src-{uuid.uuid4().hex[:12]}"),
            org_id=d.get("org_id", ""),
            name=d.get("name", ""),
            source_type=d.get("source_type", ""),
            adapter_type=d.get("adapter_type", ""),
            status=d.get("status", "created"),
            config_json=d.get("config_json", "{}"),
            credentials_ref=d.get("credentials_ref", ""),
            description=d.get("description", ""),
            last_connected_at=d.get("last_connected_at", ""),
            created_at=d.get("created_at", ""),
        )


@dataclass
class SourceCursor:
    id: str = ""
    source_id: str = ""
    org_id: str = ""
    cursor_value: str = ""
    record_count: int = 0
    last_updated: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            object.__setattr__(self, "id", f"cur-{uuid.uuid4().hex[:12]}")
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.last_updated:
            self.last_updated = self.created_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "org_id": self.org_id,
            "cursor_value": self.cursor_value,
            "record_count": self.record_count,
            "last_updated": self.last_updated,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SourceCursor:
        return cls(
            id=d.get("id", f"cur-{uuid.uuid4().hex[:12]}"),
            source_id=d.get("source_id", ""),
            org_id=d.get("org_id", ""),
            cursor_value=d.get("cursor_value", ""),
            record_count=d.get("record_count", 0),
            last_updated=d.get("last_updated", ""),
            created_at=d.get("created_at", ""),
        )


@dataclass
class FieldProfile:
    field_name: str = ""
    field_type: str = "string"  # string | number | boolean | timestamp | json | unknown
    null_count: int = 0
    total_count: int = 0
    sample_values: list[str] = field(default_factory=list)
    distinct_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_name": self.field_name,
            "field_type": self.field_type,
            "null_count": self.null_count,
            "total_count": self.total_count,
            "sample_values": self.sample_values[:5],
            "distinct_count": self.distinct_count,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> FieldProfile:
        return cls(
            field_name=d.get("field_name", ""),
            field_type=d.get("field_type", "string"),
            null_count=d.get("null_count", 0),
            total_count=d.get("total_count", 0),
            sample_values=list(d.get("sample_values", [])),
            distinct_count=d.get("distinct_count", 0),
        )


@dataclass
class SourceProfile:
    id: str = ""
    source_id: str = ""
    org_id: str = ""
    status: str = "queued"  # queued | profiling | completed | failed
    record_count: int = 0
    field_profiles: list[FieldProfile] = field(default_factory=list)
    error_message: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            object.__setattr__(self, "id", f"prof-{uuid.uuid4().hex[:12]}")
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "org_id": self.org_id,
            "status": self.status,
            "record_count": self.record_count,
            "field_profiles": [f.to_dict() for f in self.field_profiles],
            "error_message": self.error_message,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SourceProfile:
        return cls(
            id=d.get("id", f"prof-{uuid.uuid4().hex[:12]}"),
            source_id=d.get("source_id", ""),
            org_id=d.get("org_id", ""),
            status=d.get("status", "queued"),
            record_count=d.get("record_count", 0),
            field_profiles=[FieldProfile.from_dict(fp) for fp in d.get("field_profiles", [])],
            error_message=d.get("error_message", ""),
            created_at=d.get("created_at", ""),
        )


@dataclass
class FieldMappingEntry:
    source_field: str = ""
    dep_field: str = ""
    transformation: str = "direct"  # direct | concat | extract | lookup | custom
    confidence: str = "inferred"  # inferred | confirmed

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_field": self.source_field,
            "dep_field": self.dep_field,
            "transformation": self.transformation,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> FieldMappingEntry:
        return cls(
            source_field=d.get("source_field", ""),
            dep_field=d.get("dep_field", ""),
            transformation=d.get("transformation", "direct"),
            confidence=d.get("confidence", "inferred"),
        )


@dataclass
class FieldMappingVersion:
    id: str = ""
    source_id: str = ""
    org_id: str = ""
    version: int = 1
    status: str = "inferred"  # inferred | confirmed
    mappings: list[FieldMappingEntry] = field(default_factory=list)
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            object.__setattr__(self, "id", f"map-{uuid.uuid4().hex[:12]}")
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "org_id": self.org_id,
            "version": self.version,
            "status": self.status,
            "mappings": [m.to_dict() for m in self.mappings],
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> FieldMappingVersion:
        return cls(
            id=d.get("id", f"map-{uuid.uuid4().hex[:12]}"),
            source_id=d.get("source_id", ""),
            org_id=d.get("org_id", ""),
            version=d.get("version", 1),
            status=d.get("status", "inferred"),
            mappings=[FieldMappingEntry.from_dict(m) for m in d.get("mappings", [])],
            created_at=d.get("created_at", ""),
        )
