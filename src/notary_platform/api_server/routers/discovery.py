"""Discovery router — source inventory, provider registration, Decision Landscape.

Spec (WP-030):
  GET  /v1/discovery/sources              — list all indexed resources for the org
  POST /v1/discovery/providers             — register a provider
  GET  /v1/discovery/providers/{provider_id}  — get provider details

Spec (WP-100):
  GET  /v1/discovery/landscape             — aggregated Decision Landscape
"""

from __future__ import annotations

from collections import Counter
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


# ── WP-100: Decision Landscape ──


@router.get("/discovery/landscape")
def get_landscape(
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    ders = storage.list_decision_evidence_records(org_id)
    resources = storage.list_resources(org_id)
    source_connections = storage.list_source_connections(org_id)
    context_bindings = storage.list_context_bindings(org_id)
    link_assertions = storage.list_link_assertions(org_id)
    evaluators = storage.list_evaluator_contracts(org_id)
    sweep_runs = storage.list_sweep_runs(org_id)
    candidates = storage.list_assurance_candidates(org_id)
    conflicts = storage.list_context_conflicts(org_id)
    suggestions = storage.list_advisory_suggestions(org_id)

    resource_ids = {r.resource_id for r in resources}
    connected_sources = [
        {
            "id": r.resource_id,
            "type": r.resource_type,
            "provider_id": r.provider_id,
            "environment_id": r.environment_id,
            "created_at": r.created_at,
        }
        for r in resources
    ]

    source_profile_summary = _source_profile_info(source_connections)

    decision_families = [
        {
            "identity": der.decision_identity,
            "identity_method": der.identity_method,
            "evidence_level": der.evidence_level or "",
            "enriched": der.enriched,
            "environment_id": der.environment_id,
            "created_at": der.created_at,
        }
        for der in ders
        if der.decision_identity
    ]

    context_coverage = [
        {
            "id": cb.id,
            "subject_scope": cb.subject_scope,
            "subject_selector": cb.subject_selector,
            "binding_type": cb.binding_type,
            "artifact_ref": cb.artifact_ref,
            "authority": cb.authority,
            "environment_id": cb.environment_id,
            "effective_from": cb.effective_from,
            "effective_until": cb.effective_until,
        }
        for cb in context_bindings
    ]

    relationships = [
        {
            "id": la.id,
            "source_resource_id": la.source_resource_id,
            "target_resource_id": la.target_resource_id,
            "relationship": la.relationship,
            "basis": la.basis,
            "status": la.status,
            "created_by": la.created_by,
        }
        for la in link_assertions
    ]

    evaluator_list = [
        {
            "id": e.id,
            "name": e.name,
            "version": e.version,
            "method_class": e.method_class,
            "trust_class": e.trust_class,
            "description": e.description,
        }
        for e in evaluators
    ]

    evidence_gaps = []
    used_resource_ids_in_ders = set()
    der_identity_counter: Counter = Counter()
    for der in ders:
        used_resource_ids_in_ders.update(der.source_resource_ids)
        if der.decision_identity:
            der_identity_counter[der.decision_identity] += 1
    uncovered_resource_ids = resource_ids - used_resource_ids_in_ders
    for rid in sorted(uncovered_resource_ids):
        evidence_gaps.append({
            "resource_id": rid,
            "gap_type": "not_covered_by_any_der",
        })
    for dc in sorted(conflicts, key=lambda x: x.created_at):
        evidence_gaps.append({
            "resource_id": dc.resource_id if hasattr(dc, "resource_id") else "",
            "gap_type": "context_conflict",
            "conflict_id": dc.id,
            "field_or_binding": dc.field_or_binding,
            "resolution": dc.resolution,
        })

    active_candidates = [c for c in candidates if c.lifecycle_state in ("needs_context", "reviewable")]
    sweep_summary = {
        "total_runs": len(sweep_runs),
        "completed_runs": sum(1 for r in sweep_runs if r.status == "completed"),
        "failed_runs": sum(1 for r in sweep_runs if r.status in ("failed", "completed_with_errors")),
        "active_runs": sum(1 for r in sweep_runs if r.status in ("queued", "profiling", "resolving", "evaluating", "assembling")),
        "total_candidates": len(candidates),
        "active_candidates": len(active_candidates),
        "latest_run_status": sweep_runs[-1].status if sweep_runs else "",
    }

    next_actions = _derive_next_actions(org_id, ders, source_connections, evaluators, candidates)

    advisory_signals = [
        {
            "id": s.id,
            "suggestion_type": s.suggestion_type,
            "workflow_id": s.workflow_id,
            "content": s.content,
            "basis": s.basis,
            "status": s.status,
        }
        for s in suggestions
    ]

    required_corrections = []
    optional_enrichment = []

    if not source_connections:
        required_corrections.append("no_sources_connected")
    if not evaluators:
        required_corrections.append("no_evaluators_registered")
    if conflicts:
        for dc in conflicts:
            if not dc.resolution:
                required_corrections.append(f"unresolved_conflict:{dc.id}")

    if not ders:
        optional_enrichment.append("no_decision_records_built")
    if not context_bindings:
        optional_enrichment.append("no_context_bindings_configured")

    return {
        "org_id": org_id,
        "decision_families": decision_families,
        "sources": connected_sources,
        "source_profiles": source_profile_summary,
        "context_coverage": context_coverage,
        "relationships": relationships,
        "evaluators": evaluator_list,
        "required_corrections": required_corrections,
        "optional_enrichment": optional_enrichment,
        "evidence_gaps": evidence_gaps,
        "sweep_summary": sweep_summary,
        "next_actions": next_actions,
        "advisory_signals": advisory_signals,
    }


def _source_profile_info(source_connections: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": sc.id,
            "name": sc.name,
            "source_type": getattr(sc, "source_type", ""),
            "status": getattr(sc, "status", "connected"),
        }
        for sc in source_connections
    ]


def _derive_next_actions(
    org_id: str,
    ders: list[Any],
    source_connections: list[Any],
    evaluators: list[Any],
    candidates: list[Any],
) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    if not source_connections:
        actions.append({"action": "connect_source", "label": "Connect a data source to begin discovery"})
    if not evaluators:
        actions.append({"action": "register_evaluator", "label": "Register at least one evaluator contract"})
    if not ders:
        actions.append({"action": "ingest_resources", "label": "Ingest decision evidence resources via DEP ingress"})
    reviewable = [c for c in candidates if c.lifecycle_state == "reviewable"]
    if reviewable:
        actions.append({"action": "review_candidates", "label": f"{len(reviewable)} assurance candidate(s) ready for review"})
    return actions
