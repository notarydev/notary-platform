"""Sweep Worker — processes queued Sweep jobs.

In the initial implementation, jobs are processed synchronously in-process.
Future versions will use SQS or a dedicated worker pool.
"""

from __future__ import annotations

from typing import Any

from notary_platform.sweep.jobs import SweepJob
from notary_platform.sweep.runner import SweepRunner


def process_job(job: SweepJob, runner: SweepRunner) -> None:
    """Process a single Sweep job synchronously."""
    if job.job_type == "profile":
        _run_profile(job)
    elif job.job_type == "resolve":
        _run_resolve(job)
    elif job.job_type == "evaluate":
        _run_evaluate(job)
    elif job.job_type == "assemble":
        _run_assemble(job)
    else:
        job.status = "failed"
        job.error_message = f"unknown job_type: {job.job_type}"


def _run_profile(job: SweepJob) -> None:
    job.status = "completed"


def _run_resolve(job: SweepJob) -> None:
    job.status = "completed"


def _run_evaluate(job: SweepJob) -> None:
    job.status = "completed"


def _run_assemble(job: SweepJob) -> None:
    job.status = "completed"
