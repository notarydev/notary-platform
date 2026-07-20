"""Release Gate vertical slice router (WO-28).

Exposes the product-grade path from Verification Record → ReplayRun →
MutationTest → Proof of Mitigation → Scenario → ScenarioRun → ReadinessPolicy →
ReadinessCheck → ReleaseGateResult.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from notary_platform.api_server.auth import require_auth
from notary_platform.api_server.routers.ingestion import storage
from notary_platform.services import (
    ActionEligibilityService,
    CertificateService,
    MutationService,
    ReadinessService,
    ReleaseGateService,
    ReplayService,
    ScenarioLibraryService,
    ScenarioRunService,
    ServiceRegistry,
)

router = APIRouter(tags=["release_gate"])


def _registry() -> ServiceRegistry:
    return ServiceRegistry(storage)


# ---------------------------------------------------------------------------
# Demo catalog seed
# ---------------------------------------------------------------------------


@router.post("/demo/catalog/seed")
def seed_demo_catalog(org_id: str = Depends(require_auth)) -> dict[str, Any]:
    """Seed the full 20-case demo catalog using product services."""
    from notary_platform.demo_catalog import build_catalog

    registry = _registry()
    result = build_catalog(registry, org_id=org_id)
    return result


# ---------------------------------------------------------------------------
# Verification Records
# ---------------------------------------------------------------------------


@router.get("/verification-records")
def list_vrs(
    source_type: Optional[str] = Query(None),
    replayability: Optional[str] = Query(None),
    agent_id: Optional[str] = Query(None),
    org_id: str = Depends(require_auth),
) -> list[dict]:
    results = storage.list_vrs(org_id=org_id)
    if source_type:
        results = [r for r in results if r.source_type.value == source_type]
    if replayability:
        results = [r for r in results if r.replayability.value == replayability]
    if agent_id:
        results = [r for r in results if r.agent_id == agent_id]
    return [r.to_dict() for r in results]


@router.get("/verification-records/{vr_id}")
def get_vr(vr_id: str, org_id: str = Depends(require_auth)) -> dict:
    vr = storage.get_vr(vr_id)
    if vr is None or vr.org_id != org_id:
        raise HTTPException(status_code=404, detail="Verification Record not found")
    return vr.to_dict()


@router.get("/verification-records/{vr_id}/evidence")
def get_vr_evidence(vr_id: str, org_id: str = Depends(require_auth)) -> list[dict]:
    vr = storage.get_vr(vr_id)
    if vr is None or vr.org_id != org_id:
        raise HTTPException(status_code=404, detail="Verification Record not found")
    artifacts = storage.list_evidence_artifacts_for_vr(vr_id, org_id)
    return [a.to_dict() for a in artifacts]


@router.get("/verification-records/{vr_id}/eligibility/{action}")
def get_vr_eligibility(vr_id: str, action: str, org_id: str = Depends(require_auth)) -> dict:
    eligibility = ActionEligibilityService(_registry()).check(vr_id, action)
    return eligibility.to_dict()


# ---------------------------------------------------------------------------
# Replay Runs
# ---------------------------------------------------------------------------


class ReplayRequest(BaseModel):
    pass


@router.post("/verification-records/{vr_id}/replay-runs")
def create_replay_run(vr_id: str, org_id: str = Depends(require_auth)) -> dict:
    service = ReplayService(_registry())
    try:
        run = service.run_replay(vr_id, org_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return run.to_dict()


@router.get("/verification-records/{vr_id}/replay-runs")
def list_replay_runs(vr_id: str, org_id: str = Depends(require_auth)) -> list[dict]:
    vr = storage.get_vr(vr_id)
    if vr is None or vr.org_id != org_id:
        raise HTTPException(status_code=404, detail="Verification Record not found")
    return [r.to_dict() for r in storage.list_replay_runs_for_vr(vr_id)]


@router.get("/replay-runs/{run_id}")
def get_replay_run(run_id: str, org_id: str = Depends(require_auth)) -> dict:
    run = storage.get_replay_run(run_id)
    if run is None or run.org_id != org_id:
        raise HTTPException(status_code=404, detail="Replay Run not found")
    return run.to_dict()


# ---------------------------------------------------------------------------
# Mutation Tests
# ---------------------------------------------------------------------------


class MutationRequest(BaseModel):
    fix_config: dict[str, Any]
    expected_correct_behavior: str = ""


@router.post("/verification-records/{vr_id}/mutation-tests")
def create_mutation_test(vr_id: str, body: MutationRequest, org_id: str = Depends(require_auth)) -> dict:
    service = MutationService(_registry())
    try:
        test = service.run_mutation(vr_id, org_id, body.fix_config, expected_correct_behavior=body.expected_correct_behavior)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return test.to_dict()


@router.get("/verification-records/{vr_id}/mutation-tests")
def list_mutation_tests(vr_id: str, org_id: str = Depends(require_auth)) -> list[dict]:
    vr = storage.get_vr(vr_id)
    if vr is None or vr.org_id != org_id:
        raise HTTPException(status_code=404, detail="Verification Record not found")
    return [m.to_dict() for m in storage.list_mutation_tests_for_vr(vr_id)]


@router.get("/mutation-tests/{test_id}")
def get_mutation_test(test_id: str, org_id: str = Depends(require_auth)) -> dict:
    test = storage.get_mutation_test(test_id)
    if test is None or test.org_id != org_id:
        raise HTTPException(status_code=404, detail="Mutation Test not found")
    return test.to_dict()


# ---------------------------------------------------------------------------
# Proof of Mitigation
# ---------------------------------------------------------------------------


@router.post("/verification-records/{vr_id}/proof-of-mitigation")
def issue_proof_of_mitigation(vr_id: str, org_id: str = Depends(require_auth)) -> dict:
    service = CertificateService(_registry())
    try:
        cert = service.issue_proof_of_mitigation(vr_id, org_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return cert.to_dict()


@router.get("/certificates/{certificate_id}")
def get_certificate(certificate_id: str, org_id: str = Depends(require_auth)) -> dict:
    cert = storage.get_proof_certificate(certificate_id)
    if cert is None or cert.org_id != org_id:
        raise HTTPException(status_code=404, detail="Certificate not found")
    return cert.to_dict()


@router.get("/certificates/{certificate_id}/verify")
def verify_certificate(certificate_id: str, org_id: str = Depends(require_auth)) -> dict:
    cert = storage.get_proof_certificate(certificate_id)
    if cert is None or cert.org_id != org_id:
        raise HTTPException(status_code=404, detail="Certificate not found")
    valid = CertificateService(_registry()).verify(certificate_id)
    return {"certificate_id": certificate_id, "signature_valid": valid}


# ---------------------------------------------------------------------------
# Scenario Candidates
# ---------------------------------------------------------------------------


@router.get("/scenario-candidates")
def list_scenario_candidates(
    state: Optional[str] = Query(None),
    environment_id: str = Query("env:demo"),
    org_id: str = Depends(require_auth),
) -> list[dict]:
    candidates = storage.list_scenario_candidates(org_id, environment_id)
    if state:
        candidates = [c for c in candidates if c.state == state]
    return [c.to_dict() for c in candidates]


@router.post("/scenario-candidates/{candidate_id}/promote")
def promote_candidate(candidate_id: str, org_id: str = Depends(require_auth)) -> dict:
    service = ScenarioLibraryService(_registry())
    try:
        scenario = service.promote_candidate(candidate_id, org_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return scenario.to_dict()


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


@router.post("/scenarios")
def promote_vr_to_scenario(vr_id: str = Query(""), org_id: str = Depends(require_auth)) -> dict:
    if not vr_id:
        raise HTTPException(status_code=400, detail="vr_id is required")
    service = ScenarioLibraryService(_registry())
    try:
        scenario = service.promote_vr(vr_id, org_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return scenario.to_dict()


@router.get("/scenarios")
def list_scenarios(
    environment_id: str = Query("env:demo"),
    org_id: str = Depends(require_auth),
) -> list[dict]:
    return [s.to_dict() for s in storage.list_scenarios(org_id, environment_id)]


@router.get("/scenarios/{scenario_id}")
def get_scenario(scenario_id: str, org_id: str = Depends(require_auth)) -> dict:
    scenario = storage.get_scenario(scenario_id)
    if scenario is None or scenario.org_id != org_id:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario.to_dict()


@router.patch("/scenarios/{scenario_id}")
def update_scenario(scenario_id: str, body: dict, org_id: str = Depends(require_auth)) -> dict:
    scenario = storage.get_scenario(scenario_id)
    if scenario is None or scenario.org_id != org_id:
        raise HTTPException(status_code=404, detail="Scenario not found")
    if "state" in body and body["state"] in {"active", "retired"}:
        scenario.state = body["state"]
    if "business_title" in body:
        scenario.business_title = body["business_title"]
    if "expected_outcome" in body:
        scenario.expected_outcome = body["expected_outcome"]
    storage.update_scenario(scenario)
    return scenario.to_dict()


# ---------------------------------------------------------------------------
# Scenario Runs
# ---------------------------------------------------------------------------


class ScenarioRunRequest(BaseModel):
    scenario_ids: list[str] = []
    agent_version: str


@router.post("/scenario-runs")
def create_scenario_run(body: ScenarioRunRequest, org_id: str = Depends(require_auth), environment_id: str = Query("env:demo")) -> dict:
    service = ScenarioRunService(_registry())
    try:
        run = service.run(body.scenario_ids, body.agent_version, org_id, environment_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return run.to_dict()


@router.get("/scenario-runs")
def list_scenario_runs(
    environment_id: str = Query("env:demo"),
    org_id: str = Depends(require_auth),
) -> list[dict]:
    return [r.to_dict() for r in storage.list_scenario_runs(org_id, environment_id)]


@router.get("/scenario-runs/{run_id}")
def get_scenario_run(run_id: str, org_id: str = Depends(require_auth)) -> dict:
    run = storage.get_scenario_run(run_id)
    if run is None or run.org_id != org_id:
        raise HTTPException(status_code=404, detail="Scenario Run not found")
    return run.to_dict()


# ---------------------------------------------------------------------------
# Readiness Policies
# ---------------------------------------------------------------------------


class ReadinessPolicyRequest(BaseModel):
    name: str
    required_scenario_ids: list[str]
    pass_condition: str = "all_pass"


@router.post("/readiness-policies")
def create_readiness_policy(
    body: ReadinessPolicyRequest,
    org_id: str = Depends(require_auth),
    environment_id: str = Query("env:demo"),
) -> dict:
    service = ReadinessService(_registry())
    policy = service.create_policy(org_id, environment_id, body.name, body.required_scenario_ids, body.pass_condition)
    return policy.to_dict()


@router.get("/readiness-policies")
def list_readiness_policies(
    environment_id: str = Query("env:demo"),
    org_id: str = Depends(require_auth),
) -> list[dict]:
    return [p.to_dict() for p in storage.list_readiness_policies(org_id, environment_id)]


@router.get("/readiness-policies/{policy_id}")
def get_readiness_policy(policy_id: str, org_id: str = Depends(require_auth)) -> dict:
    policy = storage.get_readiness_policy(policy_id)
    if policy is None or policy.org_id != org_id:
        raise HTTPException(status_code=404, detail="Readiness Policy not found")
    return policy.to_dict()


@router.patch("/readiness-policies/{policy_id}")
def update_readiness_policy(policy_id: str, body: dict, org_id: str = Depends(require_auth)) -> dict:
    policy = storage.get_readiness_policy(policy_id)
    if policy is None or policy.org_id != org_id:
        raise HTTPException(status_code=404, detail="Readiness Policy not found")
    if "required_scenario_ids" in body:
        policy.required_scenario_ids = body["required_scenario_ids"]
        policy.version += 1
    if "enabled" in body:
        policy.enabled = body["enabled"]
        policy.version += 1
    policy.change_history.append({"action": "updated", "timestamp": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime())})
    storage.update_readiness_policy(policy)
    return policy.to_dict()


# ---------------------------------------------------------------------------
# Readiness Checks
# ---------------------------------------------------------------------------


class ReadinessCheckRequest(BaseModel):
    policy_id: str
    agent_version: str


@router.post("/readiness-checks")
def create_readiness_check(
    body: ReadinessCheckRequest,
    org_id: str = Depends(require_auth),
    environment_id: str = Query("env:demo"),
) -> dict:
    service = ReadinessService(_registry())
    try:
        check = service.run_check(body.policy_id, body.agent_version, org_id, environment_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return check.to_dict()


@router.get("/readiness-checks")
def list_readiness_checks(
    environment_id: str = Query("env:demo"),
    org_id: str = Depends(require_auth),
) -> list[dict]:
    return [c.to_dict() for c in storage.list_readiness_checks(org_id, environment_id)]


@router.get("/readiness-checks/{check_id}")
def get_readiness_check(check_id: str, org_id: str = Depends(require_auth)) -> dict:
    check = storage.get_readiness_check(check_id)
    if check is None or check.org_id != org_id:
        raise HTTPException(status_code=404, detail="Readiness Check not found")
    return check.to_dict()


# ---------------------------------------------------------------------------
# Release Gate
# ---------------------------------------------------------------------------


@router.post("/release-gate/checks")
def create_release_gate_check(
    body: ReadinessCheckRequest,
    org_id: str = Depends(require_auth),
    environment_id: str = Query("env:demo"),
) -> dict:
    service = ReleaseGateService(_registry())
    try:
        result = service.check(body.policy_id, body.agent_version, org_id, environment_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return result.to_dict()


@router.get("/release-gate/checks/{result_id}")
def get_release_gate_check(result_id: str, org_id: str = Depends(require_auth)) -> dict:
    result = storage.get_release_gate_result(result_id)
    if result is None or result.org_id != org_id:
        raise HTTPException(status_code=404, detail="Release Gate Result not found")
    return result.to_dict()
