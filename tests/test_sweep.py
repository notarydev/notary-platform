"""WP-060: Sweep runtime tests — definitions, runs, jobs, evaluator contracts, assessments."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from notary_platform.api_server.main import app
from notary_platform.storage import StorageBackend, get_storage, reset_storage
from notary_platform.sweep.budgets import BudgetState
from notary_platform.sweep.jobs import SweepJob
from notary_platform.sweep.models import (
    AssessmentRecord,
    EvaluatorContractRecord,
    SweepDefinition,
    SweepRun,
)
from notary_platform.sweep.planner import SweepPlanner
from notary_platform.sweep.runner import SweepRunner


@pytest.fixture(autouse=True)
def _reset() -> StorageBackend:
    reset_storage()
    return get_storage()


client = TestClient(app)


# ── Sweep Definition CRUD (router) ──


class TestSweepDefinitions:
    def test_create_sweep_definition(self) -> None:
        resp = client.post("/v1/discovery/sweep-definitions", json={
            "name": "weekly-audit",
            "environment_id": "env-prod",
            "evaluator_ids": ["eval-001"],
            "budget_record_limit": 5000,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "weekly-audit"
        assert data["org_id"] == "demo-org"
        assert data["id"].startswith("sd-")

    def test_list_sweep_definitions(self) -> None:
        client.post("/v1/discovery/sweep-definitions", json={"name": "a"})
        client.post("/v1/discovery/sweep-definitions", json={"name": "b"})
        resp = client.get("/v1/discovery/sweep-definitions")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_get_sweep_definition(self) -> None:
        created = client.post("/v1/discovery/sweep-definitions", json={
            "name": "get-me",
        }).json()
        resp = client.get(f"/v1/discovery/sweep-definitions/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "get-me"

    def test_get_sweep_definition_not_found(self) -> None:
        resp = client.get("/v1/discovery/sweep-definitions/sd-nonexistent")
        assert resp.status_code == 404

    def test_sweep_definition_org_isolation(self) -> None:
        s = get_storage()
        sd = SweepDefinition(name="other-org", org_id="other-org")
        s.create_sweep_definition(sd)
        resp = client.get("/v1/discovery/sweep-definitions")
        assert len(resp.json()) == 0


# ── Sweep Run lifecycle ──


class TestSweepRuns:
    def test_create_sweep_run(self) -> None:
        sd = client.post("/v1/discovery/sweep-definitions", json={
            "name": "run-test",
            "evaluator_ids": [],
        }).json()
        resp = client.post(f"/v1/discovery/sweep-definitions/{sd['id']}/runs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["definition_id"] == sd["id"]
        assert data["status"] in ("profiling", "queued")

    def test_get_sweep_run(self) -> None:
        sd = client.post("/v1/discovery/sweep-definitions", json={
            "name": "run-get",
        }).json()
        created = client.post(f"/v1/discovery/sweep-definitions/{sd['id']}/runs").json()
        resp = client.get(f"/v1/discovery/sweep-runs/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    def test_get_sweep_run_not_found(self) -> None:
        resp = client.get("/v1/discovery/sweep-runs/sr-nonexistent")
        assert resp.status_code == 404

    def test_cancel_sweep_run(self) -> None:
        sd = client.post("/v1/discovery/sweep-definitions", json={
            "name": "run-cancel",
        }).json()
        run = client.post(f"/v1/discovery/sweep-definitions/{sd['id']}/runs").json()
        resp = client.post(f"/v1/discovery/sweep-runs/{run['id']}/cancel")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    def test_cancel_already_cancelled(self) -> None:
        sd = client.post("/v1/discovery/sweep-definitions", json={
            "name": "cancel-twice",
        }).json()
        run = client.post(f"/v1/discovery/sweep-definitions/{sd['id']}/runs").json()
        client.post(f"/v1/discovery/sweep-runs/{run['id']}/cancel")
        resp = client.post(f"/v1/discovery/sweep-runs/{run['id']}/cancel")
        assert resp.status_code == 409

    def test_rerun_sweep(self) -> None:
        sd = client.post("/v1/discovery/sweep-definitions", json={
            "name": "rerun-test",
        }).json()
        run = client.post(f"/v1/discovery/sweep-definitions/{sd['id']}/runs").json()
        resp = client.post(f"/v1/discovery/sweep-runs/{run['id']}/rerun")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] != run["id"]
        assert data["definition_id"] == sd["id"]

    def test_rerun_not_found(self) -> None:
        resp = client.post("/v1/discovery/sweep-runs/sr-nonexistent/rerun")
        assert resp.status_code == 404


# ── Evaluator Contracts ──


class TestEvaluatorContracts:
    def test_register_evaluator(self) -> None:
        resp = client.post("/v1/discovery/evaluators", json={
            "name": "replay-checker",
            "version": "2.0.0",
            "method_class": "deterministic",
            "required_prerequisites": ["context_resolved"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "replay-checker"
        assert data["version"] == "2.0.0"
        assert data["org_id"] == "demo-org"

    def test_list_evaluators(self) -> None:
        client.post("/v1/discovery/evaluators", json={"name": "e1"})
        client.post("/v1/discovery/evaluators", json={"name": "e2"})
        resp = client.get("/v1/discovery/evaluators")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_get_evaluator_version(self) -> None:
        created = client.post("/v1/discovery/evaluators", json={
            "name": "ver-test",
            "version": "1.5.0",
        }).json()
        resp = client.get(f"/v1/discovery/evaluators/{created['id']}/versions/1.5.0")
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    def test_get_evaluator_wrong_version(self) -> None:
        created = client.post("/v1/discovery/evaluators", json={
            "name": "ver-mismatch",
        }).json()
        resp = client.get(f"/v1/discovery/evaluators/{created['id']}/versions/9.9.9")
        assert resp.status_code == 404

    def test_evaluator_org_isolation(self) -> None:
        s = get_storage()
        c = EvaluatorContractRecord(name="other", org_id="other-org")
        s.create_evaluator_contract(c)
        resp = client.get("/v1/discovery/evaluators")
        assert len(resp.json()) == 0


# ── Storage-level tests for SweepJob and AssessmentRecord ──


class TestSweepJobStorage:
    def test_create_and_get_job(self) -> None:
        s = get_storage()
        job = SweepJob(org_id="test-org", run_id="sr-test", job_type="profile")
        created = s.create_sweep_job(job)
        assert created.id.startswith("j-")
        fetched = s.get_sweep_job(created.id)
        assert fetched is not None
        assert fetched.job_type == "profile"

    def test_list_jobs_by_run(self) -> None:
        s = get_storage()
        s.create_sweep_job(SweepJob(org_id="test-org", run_id="sr-a", job_type="profile"))
        s.create_sweep_job(SweepJob(org_id="test-org", run_id="sr-a", job_type="evaluate"))
        s.create_sweep_job(SweepJob(org_id="test-org", run_id="sr-b", job_type="resolve"))
        jobs = s.list_sweep_jobs("sr-a")
        assert len(jobs) == 2

    def test_update_job(self) -> None:
        s = get_storage()
        job = s.create_sweep_job(SweepJob(org_id="test-org", run_id="sr-upd", job_type="evaluate"))
        job.status = "running"
        job.claimed_at = datetime.now(timezone.utc).isoformat()
        updated = s.update_sweep_job(job)
        assert updated.status == "running"
        assert updated.claimed_at != ""


class TestAssessmentRecordStorage:
    def test_create_and_get_assessment(self) -> None:
        s = get_storage()
        ar = AssessmentRecord(
            org_id="test-org",
            run_id="sr-ar",
            evaluator_id="eval-001",
            der_id="der-001",
            finding_type="expected_outcome_mismatch",
            summary="output did not match expected",
        )
        created = s.create_assessment(ar)
        assert created.id.startswith("ar-")
        fetched = s.get_assessment(created.id)
        assert fetched is not None
        assert fetched.finding_type == "expected_outcome_mismatch"

    def test_list_assessments_by_run(self) -> None:
        s = get_storage()
        s.create_assessment(AssessmentRecord(org_id="test-org", run_id="sr-ar-a", evaluator_id="e1", der_id="d1"))
        s.create_assessment(AssessmentRecord(org_id="test-org", run_id="sr-ar-a", evaluator_id="e2", der_id="d2"))
        s.create_assessment(AssessmentRecord(org_id="test-org", run_id="sr-ar-b", evaluator_id="e3", der_id="d3"))
        assessments = s.list_assessments("sr-ar-a")
        assert len(assessments) == 2


# ── Planner unit tests ──


class TestSweepPlanner:
    def test_plan_creates_run_and_jobs(self) -> None:
        s = get_storage()
        sd = SweepDefinition(
            org_id="test-org",
            name="plan-test",
            evaluator_ids=["eval-001", "eval-002"],
        )
        s.create_sweep_definition(sd)
        planner = SweepPlanner(s)
        run = planner.plan(sd, ["der-001", "der-002"])
        assert run.definition_id == sd.id
        jobs = s.list_sweep_jobs(run.id)
        # expect profile + resolve + 2 evaluate + assemble = 5 jobs
        assert len(jobs) == 5
        job_types = {j.job_type for j in jobs}
        assert job_types == {"profile", "resolve", "evaluate", "assemble"}

    def test_check_prerequisites_passes(self) -> None:
        s = get_storage()
        contract = EvaluatorContractRecord(
            org_id="test-org",
            name="strict-eval",
            required_prerequisites=["context_resolved", "source_resources"],
        )
        s.create_evaluator_contract(contract)
        planner = SweepPlanner(s)
        from notary_platform.discovery.models import DecisionEvidenceRecord
        der = DecisionEvidenceRecord(
            org_id="test-org",
            resolution_trace_id="rt-1",
            source_resource_ids=["res-1"],
        )
        ok, missing = planner.check_prerequisites(contract.id, der)
        assert ok
        assert missing == []

    def test_check_prerequisites_fails(self) -> None:
        s = get_storage()
        contract = EvaluatorContractRecord(
            org_id="test-org",
            name="strict-eval",
            required_prerequisites=["context_resolved", "link_assertions"],
        )
        s.create_evaluator_contract(contract)
        planner = SweepPlanner(s)
        from notary_platform.discovery.models import DecisionEvidenceRecord
        der = DecisionEvidenceRecord(
            org_id="test-org",
            source_resource_ids=["res-1"],
        )
        ok, missing = planner.check_prerequisites(contract.id, der)
        assert not ok
        assert "link_assertions" in missing

    def test_estimate_budget(self) -> None:
        s = get_storage()
        sd = SweepDefinition(org_id="test-org", budget_record_limit=100, budget_evaluator_limit=5, budget_timeout_seconds=60)
        planner = SweepPlanner(s)
        budget = planner.estimate_budget(sd, [])
        assert budget.record_limit == 100
        assert budget.evaluator_limit == 5
        assert budget.timeout_seconds == 60


# ── Runner unit tests ──


class TestSweepRunner:
    def test_start_run(self) -> None:
        s = get_storage()
        run = s.create_sweep_run(SweepRun(org_id="test-org", definition_id="sd-001"))
        runner = SweepRunner(s)
        result = runner.start_run(run.id, "test-org")
        assert result is not None
        assert result.status == "profiling"
        assert result.started_at != ""

    def test_start_run_wrong_org(self) -> None:
        s = get_storage()
        run = s.create_sweep_run(SweepRun(org_id="test-org", definition_id="sd-001"))
        runner = SweepRunner(s)
        result = runner.start_run(run.id, "other-org")
        assert result is None

    def test_complete_run(self) -> None:
        s = get_storage()
        run = s.create_sweep_run(SweepRun(org_id="test-org", definition_id="sd-001"))
        runner = SweepRunner(s)
        result = runner.complete_run(run.id, "test-org", "completed")
        assert result is not None
        assert result.status == "completed"
        assert result.completed_at != ""

    def test_cancel_run(self) -> None:
        s = get_storage()
        run = s.create_sweep_run(SweepRun(org_id="test-org", definition_id="sd-001"))
        runner = SweepRunner(s)
        result = runner.cancel_run(run.id, "test-org")
        assert result is not None
        assert result.status == "cancelled"

    def test_cancel_already_completed(self) -> None:
        s = get_storage()
        run = s.create_sweep_run(SweepRun(org_id="test-org", definition_id="sd-001", status="completed"))
        runner = SweepRunner(s)
        result = runner.cancel_run(run.id, "test-org")
        assert result is None

    def test_record_evaluation(self) -> None:
        s = get_storage()
        assessment = AssessmentRecord(org_id="test-org", run_id="sr-rec", evaluator_id="e1", der_id="d1")
        runner = SweepRunner(s)
        result = runner.record_evaluation(assessment, "test-org")
        assert result is not None
        assert result.id.startswith("ar-")

    def test_record_evaluation_wrong_org(self) -> None:
        s = get_storage()
        assessment = AssessmentRecord(org_id="other-org", run_id="sr-rec", evaluator_id="e1", der_id="d1")
        runner = SweepRunner(s)
        result = runner.record_evaluation(assessment, "test-org")
        assert result is None

    def test_advance_run_status(self) -> None:
        s = get_storage()
        sd = SweepDefinition(org_id="test-org")
        run = s.create_sweep_run(SweepRun(org_id="test-org", definition_id="sd-001", status="profiling"))
        runner = SweepRunner(s)
        from notary_platform.sweep.budgets import BudgetState
        budget = BudgetState(record_limit=100, evaluator_limit=10, timeout_seconds=300)
        result = runner.advance_run_status(run, sd, budget)
        assert result.status == "resolving"

    def test_advance_run_status_budget_exceeded(self) -> None:
        s = get_storage()
        sd = SweepDefinition(org_id="test-org")
        run = s.create_sweep_run(SweepRun(org_id="test-org", definition_id="sd-001", status="profiling"))
        runner = SweepRunner(s)
        budget = BudgetState(record_limit=0, evaluator_limit=0, timeout_seconds=0)
        result = runner.advance_run_status(run, sd, budget)
        assert result.status == "failed"

    def test_advance_run_assembling_to_completed(self) -> None:
        s = get_storage()
        sd = SweepDefinition(org_id="test-org")
        run = s.create_sweep_run(SweepRun(org_id="test-org", definition_id="sd-001", status="assembling"))
        runner = SweepRunner(s)
        from notary_platform.sweep.budgets import BudgetState
        budget = BudgetState(record_limit=100, evaluator_limit=10, timeout_seconds=300)
        result = runner.advance_run_status(run, sd, budget)
        assert result.status == "completed"
        assert result.completed_at != ""
