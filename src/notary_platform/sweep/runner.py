"""Sweep Runner — execute planned jobs, track progress, handle errors."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from notary_platform.sweep.budgets import BudgetState
from notary_platform.sweep.models import (
    AssessmentRecord,
    SweepDefinition,
    SweepRun,
)


class SweepRunner:
    """Execute planned Sweep jobs and update run state."""

    def __init__(self, storage: Any) -> None:  # noqa: ANN401
        self._storage = storage

    def start_run(self, run_id: str, org_id: str) -> SweepRun | None:
        run = self._storage.get_sweep_run(run_id)
        if run is None or run.org_id != org_id:
            return None
        if run.status not in ("queued",):
            return None
        run.status = "profiling"
        run.started_at = datetime.now(timezone.utc).isoformat()
        return self._storage.update_sweep_run(run)

    def complete_run(self, run_id: str, org_id: str, status: str = "completed") -> SweepRun | None:
        run = self._storage.get_sweep_run(run_id)
        if run is None or run.org_id != org_id:
            return None
        run.status = status
        run.completed_at = datetime.now(timezone.utc).isoformat()
        return self._storage.update_sweep_run(run)

    def cancel_run(self, run_id: str, org_id: str) -> SweepRun | None:
        run = self._storage.get_sweep_run(run_id)
        if run is None or run.org_id != org_id:
            return None
        if run.status in ("completed", "completed_with_errors", "failed", "cancelled"):
            return None
        run.status = "cancelled"
        run.completed_at = datetime.now(timezone.utc).isoformat()
        return self._storage.update_sweep_run(run)

    def record_evaluation(
        self,
        evaluation: AssessmentRecord,
        org_id: str,
    ) -> AssessmentRecord | None:
        if evaluation.org_id != org_id:
            return None
        return self._storage.create_assessment(evaluation)

    def advance_run_status(
        self,
        run: SweepRun,
        definition: SweepDefinition,
        budget: BudgetState,
    ) -> SweepRun:
        if not budget.check():
            run.status = "failed"
            run.error_message = f"budget exceeded: {', '.join(budget.exceeded_reasons)}"
            run.completed_at = datetime.now(timezone.utc).isoformat()
            return self._storage.update_sweep_run(run)

        if run.status == "profiling":
            run.status = "resolving"
        elif run.status == "resolving":
            run.status = "evaluating"
        elif run.status == "evaluating":
            run.status = "assembling"
        elif run.status == "assembling":
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc).isoformat()

        return self._storage.update_sweep_run(run)
