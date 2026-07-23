"""Frozen manifest creation and verification for Sweep Runs."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from notary_platform.sweep.models import SweepDefinition, SweepRun


def build_manifest(
    definition: SweepDefinition,
    run: SweepRun,
    evaluator_versions: dict[str, str],
    resolution_trace_ids: list[str],
    der_digests: dict[str, str],
) -> dict[str, Any]:
    """Build a frozen manifest for a Sweep Run.

    Content (roadmap §WP-060):
        - organization and environment
        - Sweep Definition ID and version
        - source cursors and time window
        - mapping versions
        - DER versions and resource digests
        - Resolution Trace references
        - evaluator IDs, versions, contracts, and parameters
        - suppressions and delegation rules
        - run budgets and sample limits
        - code build identifier
        - start/end timestamps and terminal status
    """
    manifest: dict[str, Any] = {
        "manifest_id": f"mf-{uuid.uuid4().hex[:12]}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "organization_id": definition.org_id,
        "environment_id": definition.environment_id,
        "sweep_definition_id": definition.id,
        "sweep_definition_version": definition.version,
        "sweep_run_id": run.id,
        "source_ids": list(definition.source_ids),
        "mapping_version_ids": list(definition.mapping_version_ids),
        "suppressions": list(definition.suppressions),
        "evaluator_versions": dict(evaluator_versions),
        "resolution_trace_ids": list(resolution_trace_ids),
        "der_digests": dict(der_digests),
        "budget_record_limit": definition.budget_record_limit,
        "budget_evaluator_limit": definition.budget_evaluator_limit,
        "budget_timeout_seconds": definition.budget_timeout_seconds,
        "build_id": "",
        "started_at": run.started_at,
        "status": run.status,
    }
    return manifest


def serialize_manifest(manifest: dict[str, Any]) -> str:
    return json.dumps(manifest, sort_keys=True, default=str)


def digest_manifest(manifest: dict[str, Any]) -> str:
    import hashlib
    return hashlib.sha256(serialize_manifest(manifest).encode()).hexdigest()


def verify_manifest_frozen(original: dict[str, Any], candidate: dict[str, Any]) -> bool:
    """Check that a candidate manifest matches a frozen original.

    Ignores timestamps and status fields that may legitimately differ.
    """
    frozen_fields = {
        "organization_id", "environment_id", "sweep_definition_id",
        "sweep_definition_version", "source_ids", "mapping_version_ids",
        "suppressions", "evaluator_versions", "budget_record_limit",
        "budget_evaluator_limit", "budget_timeout_seconds", "build_id",
        "der_digests", "resolution_trace_ids",
    }
    for field in frozen_fields:
        if original.get(field) != candidate.get(field):
            return False
    return True
