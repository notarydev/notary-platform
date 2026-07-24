"""Source profiling and field mapping services for WP-040."""

from __future__ import annotations

from typing import Any

from notary_platform.discovery.sources import (
    FieldMappingEntry,
    FieldMappingVersion,
    FieldProfile,
    SourceProfile,
)
from notary_platform.storage import StorageBackend

_DEP_FIELDS = [
    "id", "version", "timestamp", "decision_id",
    "case_id", "session_id", "customer_id",
    "outcome", "decision", "result",
    "type", "action", "status",
    "amount", "score", "confidence",
    "reason", "reason_code", "explanation",
    "policy", "policy_version",
    "agent", "model", "provider",
    "input", "output", "response",
    "prompt", "completion",
    "tool", "tool_call", "tool_response",
    "error", "error_code", "error_message",
    "duration_ms", "latency",
    "source", "source_system", "channel",
    "created_at", "updated_at", "timestamp",
]


def _infer_field_type(values: list[Any]) -> str:
    numeric = 0
    bool_count = 0
    ts_count = 0
    json_count = 0
    total = len(values) or 1
    for v in values:
        if v is None:
            continue
        if isinstance(v, bool):
            bool_count += 1
        elif isinstance(v, (int, float)):
            numeric += 1
        elif isinstance(v, dict):
            json_count += 1
        elif isinstance(v, str):
            if v.startswith("20") and "T" in v:
                ts_count += 1
    if bool_count / total > 0.5:
        return "boolean"
    if numeric / total > 0.5:
        return "number"
    if ts_count / total > 0.5:
        return "timestamp"
    if json_count / total > 0.5:
        return "json"
    return "string"


def _infer_mappings(field_names: list[str], source_name: str = "") -> list[FieldMappingEntry]:
    mappings: list[FieldMappingEntry] = []
    matched = set()
    for fn in field_names:
        fn_lower = fn.lower().strip()
        best_match = ""
        best_score = 0
        for dep in _DEP_FIELDS:
            dep_lower = dep.lower()
            if fn_lower == dep_lower:
                best_match = dep
                best_score = 3
                break
            if dep_lower in fn_lower or fn_lower in dep_lower:
                score = 2 if dep_lower in fn_lower else 1
                if score > best_score:
                    best_match = dep
                    best_score = score
        if best_match:
            mappings.append(FieldMappingEntry(
                source_field=fn,
                dep_field=best_match,
                confidence="inferred",
            ))
            matched.add(fn)
    return mappings


class SourceProfileService:
    def __init__(self, storage: StorageBackend):
        self._storage = storage

    def profile_records(self, source_id: str, org_id: str, records: list[dict[str, Any]]) -> SourceProfile:
        if not records:
            profile = SourceProfile(
                source_id=source_id, org_id=org_id,
                status="completed", record_count=0,
                field_profiles=[],
            )
            return self._storage.create_source_profile(profile)

        field_values: dict[str, list[Any]] = {}
        for record in records:
            for key, val in record.items():
                field_values.setdefault(key, []).append(val)

        field_profiles: list[FieldProfile] = []
        for field_name, values in field_values.items():
            non_null = [v for v in values if v is not None]
            sample_raw = [str(v) for v in non_null[:5]]
            fp = FieldProfile(
                field_name=field_name,
                field_type=_infer_field_type(values),
                null_count=len(values) - len(non_null),
                total_count=len(values),
                sample_values=sample_raw,
                distinct_count=len(set(str(v) for v in non_null)),
            )
            field_profiles.append(fp)

        field_profiles.sort(key=lambda fp: fp.field_name)

        profile = SourceProfile(
            source_id=source_id, org_id=org_id,
            status="completed", record_count=len(records),
            field_profiles=field_profiles,
        )
        return self._storage.create_source_profile(profile)

    def propose_mappings(self, source_id: str, org_id: str) -> FieldMappingVersion:
        profiles = self._storage.list_source_profiles(source_id)
        if not profiles:
            return FieldMappingVersion(
                source_id=source_id, org_id=org_id,
                version=1, status="inferred",
            )

        latest = profiles[0]
        field_names = [fp.field_name for fp in latest.field_profiles]
        source_name = ""
        conn = self._storage.get_source_connection(source_id, org_id)
        if conn:
            source_name = conn.name

        mappings = _infer_mappings(field_names, source_name)

        existing = self._storage.list_field_mapping_versions(source_id)
        next_version = (existing[0].version + 1) if existing else 1

        mapping = FieldMappingVersion(
            source_id=source_id, org_id=org_id,
            version=next_version, status="inferred",
            mappings=mappings,
        )
        return self._storage.create_field_mapping_version(mapping)

    def confirm_mapping(self, mapping_id: str, org_id: str, edits: list[dict[str, Any]] | None = None) -> FieldMappingVersion | None:
        mapping = self._storage.get_field_mapping_version(mapping_id)
        if not mapping:
            return None
        if edits:
            mapping.mappings = [FieldMappingEntry.from_dict(e) for e in edits]
        mapping.status = "confirmed"
        return self._storage.create_field_mapping_version(mapping)

    def get_coverage(self, source_id: str, org_id: str) -> dict[str, Any]:
        profiles = self._storage.list_source_profiles(source_id)
        mappings = self._storage.list_field_mapping_versions(source_id)
        conn = self._storage.get_source_connection(source_id, org_id)

        latest_profile = profiles[0] if profiles else None
        latest_mapping = mappings[0] if mappings else None

        field_count = len(latest_profile.field_profiles) if latest_profile else 0
        mapped_count = len(latest_mapping.mappings) if latest_mapping else 0
        confirmed = latest_mapping.status == "confirmed" if latest_mapping else False

        return {
            "source_id": source_id,
            "source_name": conn.name if conn else "",
            "profiled": latest_profile is not None,
            "record_count": latest_profile.record_count if latest_profile else 0,
            "field_count": field_count,
            "mapped_fields": mapped_count,
            "mapping_status": latest_mapping.status if latest_mapping else "none",
            "mapping_confirmed": confirmed,
            "available_dep_types": list(set(m.dep_field for m in (latest_mapping.mappings if latest_mapping else []))),
            "unmapped_fields": field_count - mapped_count,
        }
