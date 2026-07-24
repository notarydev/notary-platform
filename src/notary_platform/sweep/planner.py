"""Sweep Planner — creates sweep plans from definitions, validates prerequisites."""

from __future__ import annotations

from typing import Any

from notary_platform.sweep.budgets import BudgetState
from notary_platform.sweep.jobs import SweepJob
from notary_platform.sweep.models import (
    SweepDefinition,
    SweepRun,
)


class SweepPlanner:
    """Plan a Sweep Run: resolve sources, DERs, evaluators, and create jobs."""

    def __init__(self, storage: Any) -> None:  # noqa: ANN401
        self._storage = storage

    def plan(
        self,
        definition: SweepDefinition,
        available_ders: list[str],
    ) -> SweepRun:
        run = SweepRun(
            org_id=definition.org_id,
            environment_id=definition.environment_id,
            definition_id=definition.id,
            status="queued",
        )
        created = self._storage.create_sweep_run(run)

        profile_job = SweepJob(
            org_id=definition.org_id,
            run_id=created.id,
            job_type="profile",
            payload={"source_ids": definition.source_ids},
        )
        self._storage.create_sweep_job(profile_job)

        resolve_job = SweepJob(
            org_id=definition.org_id,
            run_id=created.id,
            job_type="resolve",
            payload={"der_ids": available_ders},
        )
        self._storage.create_sweep_job(resolve_job)

        for evaluator_id in definition.evaluator_ids:
            evaluate_job = SweepJob(
                org_id=definition.org_id,
                run_id=created.id,
                job_type="evaluate",
                payload={
                    "evaluator_id": evaluator_id,
                    "der_ids": available_ders,
                },
            )
            self._storage.create_sweep_job(evaluate_job)

        assemble_job = SweepJob(
            org_id=definition.org_id,
            run_id=created.id,
            job_type="assemble",
            payload={},
        )
        self._storage.create_sweep_job(assemble_job)

        return created

    def check_prerequisites(
        self,
        evaluator_id: str,
        der: Any,  # DecisionEvidenceRecord
    ) -> tuple[bool, list[str]]:
        contract = self._storage.get_evaluator_contract(evaluator_id)
        if contract is None:
            return False, ["evaluator_not_found"]

        available: set[str] = set()
        if der.resolution_trace_id:
            available.add("context_resolved")
        if der.context_binding_ids:
            available.add("context_bindings")
        if der.source_resource_ids:
            available.add("source_resources")
        if der.link_assertion_ids:
            available.add("link_assertions")

        missing = [p for p in contract.required_prerequisites if p not in available]
        if missing:
            return False, missing
        return True, []

    def estimate_budget(
        self,
        definition: SweepDefinition,
        ders: list[Any],
    ) -> BudgetState:
        return BudgetState(
            record_limit=definition.budget_record_limit,
            evaluator_limit=definition.budget_evaluator_limit,
            timeout_seconds=definition.budget_timeout_seconds,
        )
