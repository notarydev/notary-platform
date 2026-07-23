"""Sweep runtime router (WP-060).

Spec:
  POST /v1/discovery/sweep-definitions
  POST /v1/discovery/sweep-definitions/{definition_id}/runs
  GET  /v1/discovery/sweep-runs/{run_id}
  POST /v1/discovery/sweep-runs/{run_id}/cancel
  POST /v1/discovery/sweep-runs/{run_id}/rerun
  GET  /v1/discovery/evaluators
  GET  /v1/discovery/evaluators/{evaluator_id}/versions/{version}
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from notary_platform.api_server.auth import require_auth
from notary_platform.storage import get_storage
from notary_platform.sweep.models import (
    EvaluatorContractRecord,
    SweepDefinition,
)
from notary_platform.sweep.planner import SweepPlanner
from notary_platform.sweep.runner import SweepRunner

router = APIRouter(tags=["discovery"])
storage = get_storage()


def _get_planner() -> SweepPlanner:
    return SweepPlanner(storage)


def _get_runner() -> SweepRunner:
    return SweepRunner(storage)


@router.post("/discovery/sweep-definitions")
def create_sweep_definition(
    body: dict[str, Any],
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    sd = SweepDefinition.from_dict(body)
    sd.org_id = org_id
    created = storage.create_sweep_definition(sd)
    return created.to_dict()


@router.get("/discovery/sweep-definitions")
def list_sweep_definitions(
    org_id: str = Depends(require_auth),
) -> list[dict[str, Any]]:
    return [d.to_dict() for d in storage.list_sweep_definitions(org_id)]


@router.get("/discovery/sweep-definitions/{definition_id}")
def get_sweep_definition(
    definition_id: str,
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    sd = storage.get_sweep_definition(definition_id)
    if sd is None or sd.org_id != org_id:
        raise HTTPException(status_code=404, detail="sweep definition not found")
    return sd.to_dict()


@router.post("/discovery/sweep-definitions/{definition_id}/runs")
def create_sweep_run(
    definition_id: str,
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    sd = storage.get_sweep_definition(definition_id)
    if sd is None or sd.org_id != org_id:
        raise HTTPException(status_code=404, detail="sweep definition not found")
    ders = storage.list_decision_evidence_records(org_id)
    planner = _get_planner()
    run = planner.plan(sd, [d.id for d in ders])
    runner = _get_runner()
    runner.start_run(run.id, org_id)
    final = storage.get_sweep_run(run.id)
    if final is None:
        raise HTTPException(status_code=500, detail="failed to create sweep run")
    return final.to_dict()


@router.get("/discovery/sweep-runs/{run_id}")
def get_sweep_run(
    run_id: str,
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    run = storage.get_sweep_run(run_id)
    if run is None or run.org_id != org_id:
        raise HTTPException(status_code=404, detail="sweep run not found")
    return run.to_dict()


@router.post("/discovery/sweep-runs/{run_id}/cancel")
def cancel_sweep_run(
    run_id: str,
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    runner = _get_runner()
    result = runner.cancel_run(run_id, org_id)
    if result is None:
        run = storage.get_sweep_run(run_id)
        if run is None or run.org_id != org_id:
            raise HTTPException(status_code=404, detail="sweep run not found")
        raise HTTPException(status_code=409, detail="sweep run already completed or cancelled")
    return result.to_dict()


@router.post("/discovery/sweep-runs/{run_id}/rerun")
def rerun_sweep(
    run_id: str,
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    existing = storage.get_sweep_run(run_id)
    if existing is None or existing.org_id != org_id:
        raise HTTPException(status_code=404, detail="sweep run not found")
    sd = storage.get_sweep_definition(existing.definition_id)
    if sd is None:
        raise HTTPException(status_code=404, detail="sweep definition not found")
    ders = storage.list_decision_evidence_records(org_id)
    planner = _get_planner()
    new_run = planner.plan(sd, [d.id for d in ders])
    runner = _get_runner()
    runner.start_run(new_run.id, org_id)
    final = storage.get_sweep_run(new_run.id)
    if final is None:
        raise HTTPException(status_code=500, detail="failed to create rerun")
    return final.to_dict()


@router.get("/discovery/evaluators")
def list_evaluators(
    org_id: str = Depends(require_auth),
) -> list[dict[str, Any]]:
    return [e.to_dict() for e in storage.list_evaluator_contracts(org_id)]


@router.post("/discovery/evaluators")
def register_evaluator(
    body: dict[str, Any],
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    contract = EvaluatorContractRecord.from_dict(body)
    contract.org_id = org_id
    created = storage.create_evaluator_contract(contract)
    return created.to_dict()


@router.get("/discovery/evaluators/{evaluator_id}/versions/{version}")
def get_evaluator_version(
    evaluator_id: str,
    version: str,
    org_id: str = Depends(require_auth),
) -> dict[str, Any]:
    contract = storage.get_evaluator_contract(evaluator_id)
    if contract is None or contract.org_id != org_id:
        raise HTTPException(status_code=404, detail="evaluator not found")
    if contract.version != version:
        raise HTTPException(status_code=404, detail="version not found")
    return contract.to_dict()
