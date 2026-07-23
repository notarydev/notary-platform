"""Assurance Candidate router (WP-080 + WP-090).

Spec:
  GET    /v1/discovery/candidates
  GET    /v1/discovery/candidates/{candidate_id}
  POST   /v1/discovery/candidates/{candidate_id}/reviews
  GET    /v1/discovery/candidates/{candidate_id}/reviews
  POST   /v1/discovery/suppressions
  GET    /v1/discovery/suppressions
  POST   /v1/discovery/promotion-delegations
  GET    /v1/discovery/promotion-delegations
  POST   /v1/discovery/candidates/{candidate_id}/promote
  GET    /v1/discovery/candidates/{candidate_id}/proof-eligibility
  GET    /v1/discovery/candidates/{candidate_id}/lineage
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from notary_platform.api_server.auth import require_auth
from notary_platform.storage import get_storage
from notary_platform.sweep.bridge import ProofBridgeService
from notary_platform.sweep.candidates import CandidateReviewService
from notary_platform.sweep.models import (
    PromotionDelegation,
    ReviewDecision,
    SuppressionRule,
)

router = APIRouter(tags=["discovery"])
storage = get_storage()


def _review_svc() -> CandidateReviewService:
    return CandidateReviewService(storage)


# Lazy registry for IngestionService (avoids circular imports with certificates)
_registry: Any | None = None


def _get_registry() -> Any:
    global _registry
    if _registry is None:
        from notary_platform.services import ServiceRegistry

        _registry = ServiceRegistry(storage)
    return _registry


def _bridge_svc() -> ProofBridgeService:
    from notary_platform.services import IngestionService

    return ProofBridgeService(storage, IngestionService(_get_registry()))


def _principal_id(request: Request) -> str:
    authorization = request.headers.get("authorization", "")
    credential = (
        authorization.removeprefix("Bearer ").strip()
        or request.headers.get("x-api-key", "")
        or request.query_params.get("api_key", "")
    )
    if not credential:
        return "local-demo-principal"
    return f"api-token:{hashlib.sha256(credential.encode()).hexdigest()[:16]}"


@router.get("/discovery/candidates")
def list_candidates(
    org_id: str = Depends(require_auth),
) -> list[dict[str, Any]]:
    return [c.to_dict() for c in storage.list_assurance_candidates(org_id)]


@router.get("/discovery/candidates/{candidate_id}")
def get_candidate(
    candidate_id: str,
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    c = storage.get_assurance_candidate(candidate_id)
    if c is None or c.org_id != org_id:
        raise HTTPException(status_code=404, detail="candidate not found")
    return c.to_dict()


@router.post("/discovery/candidates/{candidate_id}/reviews")
def create_review(
    candidate_id: str,
    body: dict[str, Any],
    request: Request,
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    candidate = storage.get_assurance_candidate(candidate_id)
    if candidate is None or candidate.org_id != org_id:
        raise HTTPException(status_code=404, detail="candidate not found")

    decision = ReviewDecision(
        candidate_id=candidate_id,
        org_id=org_id,
        environment_id=candidate.environment_id,
        actor=_principal_id(request),
        role="organization_reviewer",
        decision=str(body.get("decision", "")),
        basis=str(body.get("basis", "")),
        scope=str(body.get("scope", "")),
        effective_period=str(body.get("effective_period", "")),
        superseded_decision_id=str(body.get("superseded_decision_id", "")),
    )

    svc = _review_svc()
    created = svc.record_review(candidate_id, decision)
    if created is None:
        raise HTTPException(status_code=409, detail="review could not be recorded")
    return created.to_dict()


@router.get("/discovery/candidates/{candidate_id}/reviews")
def list_reviews(
    candidate_id: str,
    org_id: str = Depends(require_auth),
) -> list[dict[str, Any]]:
    candidate = storage.get_assurance_candidate(candidate_id)
    if candidate is None or candidate.org_id != org_id:
        raise HTTPException(status_code=404, detail="candidate not found")
    svc = _review_svc()
    return [r.to_dict() for r in svc.get_reviews(candidate_id)]


@router.post("/discovery/suppressions")
def create_suppression(
    body: dict[str, Any],
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    rule = SuppressionRule.from_dict(body)
    rule.org_id = org_id
    svc = _review_svc()
    created = svc.create_suppression(rule)
    return created.to_dict()


@router.get("/discovery/suppressions")
def list_suppressions(
    org_id: str = Depends(require_auth),
) -> list[dict[str, Any]]:
    svc = _review_svc()
    return [r.to_dict() for r in svc.list_suppressions(org_id)]


@router.post("/discovery/promotion-delegations")
def create_delegation(
    body: dict[str, Any],
    request: Request,
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    delegation = PromotionDelegation(
        org_id=org_id,
        environment_id=str(body.get("environment_id", "")),
        created_by=_principal_id(request),
        name=str(body.get("name", "")),
        version=str(body.get("version", "1.0.0")),
        rule_type=str(body.get("rule_type", "")),
        conditions=dict(body.get("conditions", {})),
        scope=str(body.get("scope", "")),
        effective_period=str(body.get("effective_period", "")),
        active=bool(body.get("active", True)),
    )
    svc = _review_svc()
    created = svc.create_delegation(delegation)
    return created.to_dict()


@router.get("/discovery/promotion-delegations")
def list_delegations(
    org_id: str = Depends(require_auth),
) -> list[dict[str, Any]]:
    svc = _review_svc()
    return [d.to_dict() for d in svc.list_delegations(org_id)]


@router.post("/discovery/promotion-delegations/{delegation_id}/revoke")
def revoke_delegation(
    delegation_id: str,
    request: Request,
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    delegation = next(
        (item for item in storage.list_promotion_delegations(org_id) if item.id == delegation_id),
        None,
    )
    if delegation is None:
        raise HTTPException(status_code=404, detail="promotion delegation not found")
    delegation.active = False
    delegation.revoked_by = _principal_id(request)
    delegation.revoked_at = datetime.now(timezone.utc).isoformat()
    return storage.create_promotion_delegation(delegation).to_dict()


# ── WP-090: Proof Bridge ──


@router.post("/discovery/candidates/{candidate_id}/promote")
def promote_candidate(
    candidate_id: str,
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    candidate = storage.get_assurance_candidate(candidate_id)
    if candidate is None or candidate.org_id != org_id:
        raise HTTPException(status_code=404, detail="candidate not found")
    svc = _bridge_svc()
    result = svc.promote(candidate_id, org_id)
    if not result["success"]:
        raise HTTPException(
            status_code=409,
            detail={
                "error_code": result.get("error_code", "PROMOTION_FAILED"),
                "message": result.get("error", "promotion failed"),
                "next_actions": result.get("next_actions", []),
                "prerequisites": result.get("prerequisites", []),
            },
        )
    return result


@router.get("/discovery/candidates/{candidate_id}/proof-eligibility")
def proof_eligibility(
    candidate_id: str,
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    candidate = storage.get_assurance_candidate(candidate_id)
    if candidate is None or candidate.org_id != org_id:
        raise HTTPException(status_code=404, detail="candidate not found")
    svc = _bridge_svc()
    return svc.check_eligibility(candidate_id, org_id)


@router.get("/discovery/candidates/{candidate_id}/lineage")
def candidate_lineage(
    candidate_id: str,
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    candidate = storage.get_assurance_candidate(candidate_id)
    if candidate is None or candidate.org_id != org_id:
        raise HTTPException(status_code=404, detail="candidate not found")
    svc = _bridge_svc()
    return svc.get_lineage(candidate_id, org_id)
