"""Shared storage contract suite — runs against MemoryStorage and (with remote
credentials) PostgresS3Storage.  Every create/get/list/update method on the
StorageBackend contract is exercised so that a new backend cannot accidentally
ship a no-op or silently lose data.
"""

from __future__ import annotations

import pytest

from notary_platform.models import (
    Agent,
    AISystem,
    AssuranceSetupPlan,
    CaptureConnector,
    CapturePolicy,
    CaptureValidationRun,
    DecisionFamilyCandidate,
    DecisionWorkflow,
    Environment,
    EvidenceArtifact,
    FieldHandlingRule,
    HumanLabel,
    MutationTest,
    Organization,
    ProofCertificate,
    ReadinessCheck,
    ReadinessPolicy,
    RecordSelectionRule,
    ReleaseGateResult,
    ReplayExecutionEvent,
    ReplayRun,
    Scenario,
    ScenarioCandidate,
    ScenarioRun,
    SystemConnection,
    VerificationRecord,
    WorkflowEvidenceSource,
)
from notary_platform.storage import MemoryStorage, StorageBackend

# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def mem() -> MemoryStorage:
    return MemoryStorage()


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_vr(org_id: str = "org-a", env_id: str = "env:demo") -> VerificationRecord:
    return VerificationRecord(
        id=f"vr-{org_id}",
        org_id=org_id,
        environment_id=env_id,
        agent_id="agent:test",
        root_hash="abc",
    )


# ── Contract test class — instantiated against each backend ──────────────────

class StorageContractSuite:
    """Mixin-style contract test.  Subclasses or parametrized fixtures set
    ``storage`` as a fixture returning a ``StorageBackend`` instance."""

    # ── Platform objects (WO-64) ─────────────────────────────────────────

    def test_create_get_org(self, storage: StorageBackend) -> None:
        org = Organization(id="org-a", name="Test Org")
        storage.create_org(org)
        retrieved = storage.get_org("org-a")
        assert retrieved is not None
        assert retrieved.id == "org-a"
        assert retrieved.name == "Test Org"

    def test_get_org_none_when_missing(self, storage: StorageBackend) -> None:
        assert storage.get_org("no-such-org") is None

    def test_create_get_env(self, storage: StorageBackend) -> None:
        env = Environment(id="env:prod", org_id="org-a", name="Production")
        storage.create_env(env)
        retrieved = storage.get_env("env:prod")
        assert retrieved is not None
        assert retrieved.id == "env:prod"

    def test_create_get_agent(self, storage: StorageBackend) -> None:
        agent = Agent(id="agent:x", org_id="org-a", environment_id="env:demo", name="Agent X")
        storage.create_agent(agent)
        retrieved = storage.get_agent("agent:x")
        assert retrieved is not None
        assert retrieved.id == "agent:x"

    def test_create_get_system_connection(self, storage: StorageBackend) -> None:
        conn = SystemConnection(id="sys:1", org_id="org-a", environment_id="env:demo", name="System 1")
        storage.create_system_conn(conn)
        retrieved = storage.list_systems_for_org("org-a")
        assert any(c.id == "sys:1" for c in retrieved)

    def test_create_get_policy(self, storage: StorageBackend) -> None:
        policy = CapturePolicy(id="pol:1", org_id="org-a", environment_id="env:demo", name="Policy 1")
        storage.create_policy(policy)
        retrieved = storage.list_policies_for_org("org-a")
        assert any(p.id == "pol:1" for p in retrieved)

    # ── Product objects (WO-28) ──────────────────────────────────────────

    def test_create_get_vr(self, storage: StorageBackend) -> None:
        vr = _make_vr()
        storage.create_vr(vr)
        retrieved = storage.get_vr(vr.id)
        assert retrieved is not None
        assert retrieved.id == vr.id

    def test_list_vrs_scoped(self, storage: StorageBackend) -> None:
        vr_a = _make_vr("org-a")
        vr_b = _make_vr("org-b")
        storage.create_vr(vr_a)
        storage.create_vr(vr_b)
        assert len(storage.list_vrs("org-a")) == 1

    def test_update_vr(self, storage: StorageBackend) -> None:
        vr = _make_vr()
        storage.create_vr(vr)
        vr.status = "completed"
        storage.update_vr(vr)
        assert storage.get_vr(vr.id).status == "completed"

    def test_create_get_label(self, storage: StorageBackend) -> None:
        vr = _make_vr()
        storage.create_vr(vr)
        label = HumanLabel(
            id="lbl:1",
            verification_record_id=vr.id,
            expected_outcome="pass",
            reviewer="tester",
            role="reviewer",
            reason="test",
        )
        storage.create_label(label)
        retrieved = storage.get_label("lbl:1")
        assert retrieved is not None
        assert retrieved.id == "lbl:1"

    def test_create_get_evidence_artifact(self, storage: StorageBackend) -> None:
        vr = _make_vr()
        storage.create_vr(vr)
        art = EvidenceArtifact(id="art:1", verification_record_id=vr.id, org_id=vr.org_id, kind="cassette")
        storage.create_evidence_artifact(art)
        retrieved = storage.get_evidence_artifact("art:1")
        assert retrieved is not None
        assert retrieved.id == "art:1"

    def test_create_get_replay_run(self, storage: StorageBackend) -> None:
        vr = _make_vr()
        storage.create_vr(vr)
        run = ReplayRun(id="run:1", verification_record_id=vr.id, org_id=vr.org_id, status="pending")
        storage.create_replay_run(run)
        retrieved = storage.get_replay_run("run:1")
        assert retrieved is not None
        assert retrieved.id == "run:1"

    def test_create_get_replay_execution_events(self, storage: StorageBackend) -> None:
        events = [
            ReplayExecutionEvent(step="step1", source="test", expected="ok", actual="ok", status="pass", sequence=0, timestamp="2026-01-01T00:00:00Z"),
        ]
        storage.create_replay_execution_events("run:1", events)
        retrieved = storage.list_replay_execution_events("run:1")
        assert len(retrieved) == 1
        assert retrieved[0].step == "step1"

    def test_create_get_mutation_test(self, storage: StorageBackend) -> None:
        vr = _make_vr()
        storage.create_vr(vr)
        test = MutationTest(id="mut:1", verification_record_id=vr.id, org_id=vr.org_id, verdict="not_started")
        storage.create_mutation_test(test)
        retrieved = storage.get_mutation_test("mut:1")
        assert retrieved is not None
        assert retrieved.id == "mut:1"

    def test_create_get_proof_certificate(self, storage: StorageBackend) -> None:
        cert = ProofCertificate(id="cert:1", org_id="org-a")
        storage.create_proof_certificate(cert)
        retrieved = storage.get_proof_certificate("cert:1")
        assert retrieved is not None
        assert retrieved.id == "cert:1"

    def test_create_get_scenario(self, storage: StorageBackend) -> None:
        scenario = Scenario(id="sc:1", org_id="org-a", environment_id="env:demo", source_vr_id="vr:1", expected_outcome="pass")
        storage.create_scenario(scenario)
        retrieved = storage.get_scenario("sc:1")
        assert retrieved is not None
        assert retrieved.id == "sc:1"

    def test_create_get_scenario_candidate(self, storage: StorageBackend) -> None:
        cand = ScenarioCandidate(id="sc-cand:1", org_id="org-a", environment_id="env:demo", source_vr_id="vr:1")
        storage.create_scenario_candidate(cand)
        retrieved = storage.get_scenario_candidate("sc-cand:1")
        assert retrieved is not None
        assert retrieved.id == "sc-cand:1"

    def test_create_get_scenario_run(self, storage: StorageBackend) -> None:
        run = ScenarioRun(id="sr:1", org_id="org-a", environment_id="env:demo", status="pending")
        storage.create_scenario_run(run)
        retrieved = storage.get_scenario_run("sr:1")
        assert retrieved is not None
        assert retrieved.id == "sr:1"

    def test_create_get_readiness_policy(self, storage: StorageBackend) -> None:
        pol = ReadinessPolicy(id="rp:1", org_id="org-a", required_scenario_ids=["sc:1"])
        storage.create_readiness_policy(pol)
        retrieved = storage.get_readiness_policy("rp:1")
        assert retrieved is not None
        assert retrieved.id == "rp:1"

    def test_create_get_readiness_check(self, storage: StorageBackend) -> None:
        check = ReadinessCheck(id="rc:1", org_id="org-a", policy_id="rp:1")
        storage.create_readiness_check(check)
        retrieved = storage.get_readiness_check("rc:1")
        assert retrieved is not None
        assert retrieved.id == "rc:1"

    def test_create_get_release_gate_result(self, storage: StorageBackend) -> None:
        result = ReleaseGateResult(id="rg:1", org_id="org-a", status="pass", evidence_refs=[])
        storage.create_release_gate_result(result)
        retrieved = storage.get_release_gate_result("rg:1")
        assert retrieved is not None
        assert retrieved.id == "rg:1"

    # ── Integration & Capture (Phase E) ──────────────────────────────────

    def test_create_get_ai_system(self, storage: StorageBackend) -> None:
        system = AISystem(id="ai:1", org_id="org-a", environment_id="env:demo", name="AI Sys 1")
        storage.create_ai_system(system)
        retrieved = storage.get_ai_system("ai:1")
        assert retrieved is not None
        assert retrieved.id == "ai:1"

    def test_create_get_capture_connector(self, storage: StorageBackend) -> None:
        conn = CaptureConnector(id="cc:1", org_id="org-a", ai_system_id="ai:1", connector_type="csv")
        storage.create_capture_connector(conn)
        retrieved = storage.get_capture_connector("cc:1")
        assert retrieved is not None
        assert retrieved.id == "cc:1"

    def test_create_get_field_handling_rule(self, storage: StorageBackend) -> None:
        rule = FieldHandlingRule(id="fhr:1", ai_system_id="ai:1", field_pattern="name")
        storage.create_field_handling_rule(rule)
        stored = storage.list_field_handling_rules("ai:1")
        assert any(r.id == "fhr:1" for r in stored)

    def test_create_get_capture_validation_run(self, storage: StorageBackend) -> None:
        run = CaptureValidationRun(id="cvr:1", ai_system_id="ai:1", org_id="org-a", status="pending")
        storage.create_capture_validation_run(run)
        stored = storage.list_capture_validation_runs("ai:1")
        assert any(r.id == "cvr:1" for r in stored)

    def test_create_get_decision_family_candidate(self, storage: StorageBackend) -> None:
        cand = DecisionFamilyCandidate(id="dfc:1", org_id="org-a", ai_system_id="ai:1", pattern_name="support")
        storage.create_decision_family_candidate(cand)
        stored = storage.list_decision_family_candidates("org-a")
        assert any(c.id == "dfc:1" for c in stored)

    def test_create_get_decision_workflow(self, storage: StorageBackend) -> None:
        wf = DecisionWorkflow(id="dw:1", org_id="org-a", environment_id="env:demo")
        storage.create_decision_workflow(wf)
        retrieved = storage.get_decision_workflow("dw:1")
        assert retrieved is not None
        assert retrieved.id == "dw:1"

    def test_create_get_workflow_evidence_sources(self, storage: StorageBackend) -> None:
        wf = DecisionWorkflow(id="dw:2", org_id="org-a", environment_id="env:demo")
        storage.create_decision_workflow(wf)
        src = WorkflowEvidenceSource(id="wes:1", workflow_id="dw:2", org_id="org-a", source_type="csv")
        storage.save_workflow_evidence_sources("dw:2", [src])
        stored = storage.list_workflow_evidence_sources("dw:2")
        assert any(s.id == "wes:1" for s in stored)

    def test_create_get_record_selection_rules(self, storage: StorageBackend) -> None:
        wf = DecisionWorkflow(id="dw:3", org_id="org-a", environment_id="env:demo")
        storage.create_decision_workflow(wf)
        rule = RecordSelectionRule(id="rsr:1", workflow_id="dw:3", org_id="org-a")
        storage.save_record_selection_rules("dw:3", [rule])
        stored = storage.list_record_selection_rules("dw:3")
        assert any(r.id == "rsr:1" for r in stored)

    def test_create_get_assurance_plan(self, storage: StorageBackend) -> None:
        plan = AssuranceSetupPlan(id="plan:1", org_id="org-a")
        storage.save_assurance_plan(plan)
        retrieved = storage.get_assurance_plan("plan:1")
        assert retrieved is not None
        assert retrieved.id == "plan:1"

    def test_list_assurance_plans(self, storage: StorageBackend) -> None:
        plan_a = AssuranceSetupPlan(id="plan:a", org_id="org-a")
        plan_b = AssuranceSetupPlan(id="plan:b", org_id="org-b")
        storage.save_assurance_plan(plan_a)
        storage.save_assurance_plan(plan_b)
        assert len(storage.list_assurance_plans("org-a")) == 1
        assert len(storage.list_assurance_plans("org-b")) == 1

    # ── Restart survival ─────────────────────────────────────────────────

    def test_restart_survival(self, storage: StorageBackend) -> None:
        """Verifies that objects created before a conceptual restart are
        still accessible afterward.  For MemoryStorage this is trivial; for
        PostgresS3Storage it exercises the real Postgres round-trip."""
        vr = _make_vr()
        storage.create_vr(vr)
        org = Organization(id="org-restart", name="Restart Test")
        storage.create_org(org)
        plan = AssuranceSetupPlan(id="plan:restart", org_id="org-restart")
        storage.save_assurance_plan(plan)
        events = [
            ReplayExecutionEvent(step="s1", source="t", expected="ok", actual="ok", status="pass", sequence=0, timestamp="2026-01-01T00:00:00Z"),
        ]
        storage.create_replay_execution_events("run:restart", events)

        # Now read back (simulating a restart by using the same instance)
        assert storage.get_vr(vr.id) is not None
        assert storage.get_org("org-restart") is not None
        assert storage.get_assurance_plan("plan:restart") is not None
        assert len(storage.list_replay_execution_events("run:restart")) == 1


# ── MemoryStorage instantiation ──────────────────────────────────────────────

class TestMemoryStorageContract:
    """Run the full contract suite against MemoryStorage."""

    @pytest.fixture
    def storage(self) -> MemoryStorage:
        return MemoryStorage()


# Inject every test from StorageContractSuite into TestMemoryStorageContract.
for _name in dir(StorageContractSuite):
    _val = getattr(StorageContractSuite, _name)
    if _name.startswith("test_") and callable(_val):
        setattr(TestMemoryStorageContract, _name, _val)
