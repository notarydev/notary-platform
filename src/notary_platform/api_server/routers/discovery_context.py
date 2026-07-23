from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from notary_platform.api_server.auth import require_auth
from notary_platform.discovery.context import TemporalContextResolver
from notary_platform.discovery.evidence_records import DecisionEvidenceRecordService
from notary_platform.discovery.identity import DecisionIdentityResolver
from notary_platform.discovery.models import (
    AdvisorySuggestion,
    ContextBinding,
    LinkAssertion,
)
from notary_platform.storage import get_storage

router = APIRouter(tags=["discovery"])
storage = get_storage()


def _get_id_resolver() -> DecisionIdentityResolver:
    return DecisionIdentityResolver(storage)


def _get_ctx_resolver() -> TemporalContextResolver:
    return TemporalContextResolver(storage)


def _get_der_svc() -> DecisionEvidenceRecordService:
    return DecisionEvidenceRecordService(storage)


# ── Context Artifacts ──

@router.post("/discovery/context-artifacts")
def create_context_binding(
    body: dict[str, Any],
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    cb = ContextBinding.from_dict(body)
    cb.org_id = org_id
    created = storage.create_context_binding(cb)
    return created.to_dict()


# ── Context Bindings ──

@router.post("/discovery/context-bindings")
def create_context_binding_v2(
    body: dict[str, Any],
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    cb = ContextBinding.from_dict(body)
    cb.org_id = org_id
    created = storage.create_context_binding(cb)
    return created.to_dict()


# ── Link Assertions ──

@router.post("/discovery/link-assertions")
def create_link_assertion(
    body: dict[str, Any],
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    la = LinkAssertion.from_dict(body)
    la.org_id = org_id
    created = storage.create_link_assertion(la)
    return created.to_dict()


@router.post("/discovery/link-assertions/{assertion_id}/confirm")
def confirm_link_assertion(
    assertion_id: str,
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    svc = _get_id_resolver()
    result = svc.confirm_link(assertion_id, org_id)
    if result is None:
        raise HTTPException(status_code=404, detail="link assertion not found")
    return result.to_dict()


@router.post("/discovery/link-assertions/{assertion_id}/reject")
def reject_link_assertion(
    assertion_id: str,
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    svc = _get_id_resolver()
    result = svc.reject_link(assertion_id, org_id)
    if result is None:
        raise HTTPException(status_code=404, detail="link assertion not found")
    return result.to_dict()


# ── Decision Evidence Records ──

@router.get("/discovery/records")
def list_decision_evidence_records(
    org_id: str = Depends(require_auth),
) -> list[dict[str, Any]]:
    svc = _get_der_svc()
    return [d.to_dict() for d in svc.list_records(org_id)]


@router.post("/discovery/records")
def build_decision_evidence_record(
    body: dict[str, Any],
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    resource_ids = list(body.get("resource_ids", []))
    if not resource_ids:
        raise HTTPException(status_code=422, detail="resource_ids required")
    decision_time = body.get("decision_time")
    namespace_mappings = body.get("namespace_mappings")
    svc = _get_der_svc()
    der = svc.build(resource_ids, org_id, decision_time, namespace_mappings)
    return der.to_dict()


@router.get("/discovery/records/{der_id}")
def get_decision_evidence_record(
    der_id: str,
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    svc = _get_der_svc()
    der = svc.get(der_id, org_id)
    if der is None:
        raise HTTPException(status_code=404, detail="record not found")
    return der.to_dict()


@router.get("/discovery/records/{der_id}/resolution-trace")
def get_resolution_trace(
    der_id: str,
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    svc = _get_der_svc()
    trace = svc.get_resolution_trace(der_id, org_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="resolution trace not found")
    return trace


# ── Context Conflicts ──

@router.post("/discovery/context-conflicts/{conflict_id}/resolve")
def resolve_context_conflict(
    conflict_id: str,
    body: dict[str, Any],
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    resolution = body.get("resolution", "")
    if not resolution:
        raise HTTPException(status_code=422, detail="resolution required (resolved_use_a, resolved_use_b, resolved_superseded)")
    resolved_by = body.get("resolved_by", "user")
    svc = _get_ctx_resolver()
    result = svc.resolve_conflict(conflict_id, resolution, resolved_by, org_id)
    if result is None:
        raise HTTPException(status_code=404, detail="context conflict not found")
    return result.to_dict()


# ── Advisory Suggestions ──

@router.get("/discovery/workflows/{workflow_id}/policy-candidates")
def get_policy_candidates(
    workflow_id: str,
    org_id: str = Depends(require_auth),
) -> list[dict[str, Any]]:
    svc = _get_der_svc()
    return [s.to_dict() for s in svc.get_policy_candidates(workflow_id, org_id)]


@router.get("/discovery/workflows/{workflow_id}/context-roadmap")
def get_context_roadmap(
    workflow_id: str,
    org_id: str = Depends(require_auth),
) -> list[dict[str, Any]]:
    svc = _get_der_svc()
    return [s.to_dict() for s in svc.suggest_context_roadmap(workflow_id, org_id)]


@router.post("/discovery/suggestions")
def create_advisory_suggestion(
    body: dict[str, Any],
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    s = AdvisorySuggestion.from_dict(body)
    s.org_id = org_id
    created = storage.create_advisory_suggestion(s)
    return created.to_dict()


@router.get("/discovery/suggestions")
def list_advisory_suggestions(
    workflow_id: str = "",
    org_id: str = Depends(require_auth),
) -> list[dict[str, Any]]:
    return [s.to_dict() for s in storage.list_advisory_suggestions(org_id, workflow_id)]
