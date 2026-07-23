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

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

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
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    candidate = storage.get_assurance_candidate(candidate_id)
    if candidate is None or candidate.org_id != org_id:
        raise HTTPException(status_code=404, detail="candidate not found")

    decision = ReviewDecision.from_dict(body)
    decision.candidate_id = candidate_id
    decision.org_id = org_id

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
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    delegation = PromotionDelegation.from_dict(body)
    delegation.org_id = org_id
    svc = _review_svc()
    created = svc.create_delegation(delegation)
    return created.to_dict()


@router.get("/discovery/promotion-delegations")
def list_delegations(
    org_id: str = Depends(require_auth),
) -> list[dict[str, Any]]:
    svc = _review_svc()
    return [d.to_dict() for d in svc.list_delegations(org_id)]


# ── WP-090: Proof Bridge ──


def _bridge_svc() -> ProofBridgeService:
    return ProofBridgeService(storage)


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
        raise HTTPException(status_code=409, detail=result["error"])
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
