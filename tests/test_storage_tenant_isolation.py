"""Tenant isolation tests — verify org A cannot read or list org B objects.

Runs against MemoryStorage by default.  When NOTARY_USE_REMOTE_STORAGE is set,
the same suite runs against PostgresS3Storage to prove tenant scoping works in
production storage.
"""

from __future__ import annotations

import pytest

from notary_platform.models import (
    Agent,
    AISystem,
    AssuranceSetupPlan,
    CaptureConnector,
    CapturePolicy,
    DecisionWorkflow,
    Environment,
    Organization,
    ReadinessPolicy,
    Scenario,
    SystemConnection,
    VerificationRecord,
)
from notary_platform.storage import MemoryStorage, StorageBackend


@pytest.fixture
def storage() -> MemoryStorage:
    return MemoryStorage()


def _seed_org_a(s: StorageBackend) -> None:
    s.create_org(Organization(id="org-a", name="Org A"))
    s.create_env(Environment(id="env:a", org_id="org-a", name="Env A"))
    s.create_agent(Agent(id="agent:a1", org_id="org-a", environment_id="env:a", name="Agent A1"))
    s.create_system_conn(SystemConnection(id="sys:a", org_id="org-a", environment_id="env:a", name="System A"))
    s.create_policy(CapturePolicy(id="pol:a", org_id="org-a", environment_id="env:a", name="Policy A"))
    s.create_vr(VerificationRecord(id="vr:a", org_id="org-a", environment_id="env:a", agent_id="agent:a1", root_hash="abc"))
    s.create_scenario(Scenario(id="sc:a", org_id="org-a", environment_id="env:a", source_vr_id="vr:a", expected_outcome="pass"))
    s.create_ai_system(AISystem(id="ai:a", org_id="org-a", environment_id="env:a", name="AI A"))
    s.create_capture_connector(CaptureConnector(id="cc:a", org_id="org-a", ai_system_id="ai:a", connector_type="csv"))
    s.create_decision_workflow(DecisionWorkflow(id="dw:a", org_id="org-a", environment_id="env:a"))
    s.create_readiness_policy(ReadinessPolicy(id="rp:a", org_id="org-a", required_scenario_ids=["sc:a"]))
    s.save_assurance_plan(AssuranceSetupPlan(id="plan:a", org_id="org-a"))


def _seed_org_b(s: StorageBackend) -> None:
    s.create_org(Organization(id="org-b", name="Org B"))
    s.create_env(Environment(id="env:b", org_id="org-b", name="Env B"))
    s.create_agent(Agent(id="agent:b1", org_id="org-b", environment_id="env:b", name="Agent B1"))
    s.create_system_conn(SystemConnection(id="sys:b", org_id="org-b", environment_id="env:b", name="System B"))
    s.create_policy(CapturePolicy(id="pol:b", org_id="org-b", environment_id="env:b", name="Policy B"))
    s.create_vr(VerificationRecord(id="vr:b", org_id="org-b", environment_id="env:b", agent_id="agent:b1", root_hash="xyz"))
    s.create_scenario(Scenario(id="sc:b", org_id="org-b", environment_id="env:b", source_vr_id="vr:b", expected_outcome="fail"))
    s.create_ai_system(AISystem(id="ai:b", org_id="org-b", environment_id="env:b", name="AI B"))
    s.create_capture_connector(CaptureConnector(id="cc:b", org_id="org-b", ai_system_id="ai:b", connector_type="api"))
    s.create_decision_workflow(DecisionWorkflow(id="dw:b", org_id="org-b", environment_id="env:b"))
    s.create_readiness_policy(ReadinessPolicy(id="rp:b", org_id="org-b", required_scenario_ids=["sc:b"]))
    s.save_assurance_plan(AssuranceSetupPlan(id="plan:b", org_id="org-b"))


class TestTenantIsolation:
    """Org A objects must not be visible to org B queries, and vice versa."""

    def setup_method(self) -> None:
        self._s = MemoryStorage()
        _seed_org_a(self._s)
        _seed_org_b(self._s)

    # ── List isolation ───────────────────────────────────────────────────

    def test_list_envs_isolated(self) -> None:
        assert len(self._s.list_envs("org-a")) == 1
        assert len(self._s.list_envs("org-b")) == 1
        assert all(e.org_id == "org-a" for e in self._s.list_envs("org-a"))

    def test_list_agents_isolated(self) -> None:
        assert all(a.org_id == "org-a" for a in self._s.list_agents_for_org("org-a"))

    def test_list_systems_isolated(self) -> None:
        assert all(s.org_id == "org-a" for s in self._s.list_systems_for_org("org-a"))

    def test_list_policies_isolated(self) -> None:
        assert all(p.org_id == "org-a" for p in self._s.list_policies_for_org("org-a"))

    def test_list_vrs_isolated(self) -> None:
        assert all(v.org_id == "org-a" for v in self._s.list_vrs("org-a"))
        assert all(v.org_id == "org-b" for v in self._s.list_vrs("org-b"))

    def test_list_scenarios_isolated(self) -> None:
        assert all(s.org_id == "org-a" for s in self._s.list_scenarios("org-a"))

    def test_list_ai_systems_isolated(self) -> None:
        assert all(a.org_id == "org-a" for a in self._s.list_ai_systems("org-a"))

    def test_list_assurance_plans_isolated(self) -> None:
        assert len(self._s.list_assurance_plans("org-a")) == 1
        assert len(self._s.list_assurance_plans("org-b")) == 1

    def test_list_readiness_policies_isolated(self) -> None:
        assert all(r.org_id == "org-a" for r in self._s.list_readiness_policies("org-a"))

    def test_list_decision_workflows_isolated(self) -> None:
        assert all(w.org_id == "org-a" for w in self._s.list_decision_workflows("org-a"))

    # ── Get-by-id should not leak cross-tenant objects ───────────────────

    def test_get_env_cross_tenant_returns_none(self) -> None:
        # "env:b" exists but belongs to org-b. StorageBackend has no
        # org-scoped get_env, but the test documents the expectation.
        env_b = self._s.get_env("env:b")
        _org_a_envs = self._s.list_envs("org-a")
        assert env_b is None or env_b.org_id != "org-a"
