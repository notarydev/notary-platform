"""Storage backends for the Notary Platform.

The default backend is in-memory so the prototype runs with zero cloud setup.
When ``NOTARY_USE_REMOTE_STORAGE`` is enabled, incidents metadata are written
to PostgreSQL (via SQLAlchemy) and evidence/certificates to the immutable S3
bucket (Object Lock + versioning). Importers must never hardcode credentials;
they are read from the environment / IAM role at runtime.
"""

from __future__ import annotations

import abc
import json
import uuid
from pathlib import Path
from typing import Any

from notary_platform.config import SETTINGS
from notary_platform.models import (
    Agent,
    AISystem,
    CaptureConnector,
    CapturePolicy,
    CaptureValidationRun,
    DecisionFamilyCandidate,
    DecisionWorkflow,
    Environment,
    EvidenceArtifact,
    FieldHandlingRule,
    HumanLabel,
    Incident,
    MutationTest,
    Organization,
    ProofCertificate,
    ReadinessCheck,
    ReadinessPolicy,
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

_PERSISTED_COLLECTIONS: dict[str, tuple[str, type[Any]]] = {
    "orgs": ("_orgs", Organization),
    "envs": ("_envs", Environment),
    "agents": ("_agents", Agent),
    "systems": ("_systems", SystemConnection),
    "policies": ("_policies", CapturePolicy),
    "vrs": ("_vrs", VerificationRecord),
    "labels": ("_labels", HumanLabel),
    "evidence_artifacts": ("_evidence_artifacts", EvidenceArtifact),
    "replay_runs": ("_replay_runs", ReplayRun),
    "mutation_tests": ("_mutation_tests", MutationTest),
    "proof_certs": ("_proof_certs", ProofCertificate),
    "scenarios": ("_scenarios", Scenario),
    "scenario_candidates": ("_scenario_candidates", ScenarioCandidate),
    "scenario_runs": ("_scenario_runs", ScenarioRun),
    "readiness_policies": ("_readiness_policies", ReadinessPolicy),
    "readiness_checks": ("_readiness_checks", ReadinessCheck),
    "release_gate_results": ("_release_gate_results", ReleaseGateResult),
    "ai_systems": ("_ai_systems", AISystem),
    "capture_connectors": ("_capture_connectors", CaptureConnector),
    "field_handling_rules": ("_field_handling_rules", FieldHandlingRule),
    "capture_validation_runs": ("_capture_validation_runs", CaptureValidationRun),
    "decision_family_candidates": ("_decision_family_candidates", DecisionFamilyCandidate),
}


class StorageBackend(abc.ABC):
    """Contract for incident/snapshot/certificate persistence."""

    @abc.abstractmethod
    def create_incident(self, snapshot_dict: dict[str, Any], org_id: str = "demo-org") -> Incident: ...

    @abc.abstractmethod
    def get_incident(self, incident_id: str) -> Incident | None: ...

    @abc.abstractmethod
    def list_incidents(self, org_id: str | None = None) -> list[Incident]: ...

    @abc.abstractmethod
    def get_snapshot(self, incident_id: str) -> dict[str, Any] | None: ...

    @abc.abstractmethod
    def update_incident(self, incident: Incident) -> None: ...

    @abc.abstractmethod
    def store_certificate(self, incident_id: str, cert: dict[str, Any]) -> None: ...

    @abc.abstractmethod
    def get_certificate(self, incident_id: str) -> dict[str, Any] | None: ...

    @abc.abstractmethod
    def persist_evidence(self, incident_id: str, kind: str, payload: dict[str, Any]) -> str:
        """Persist an evidence blob; returns a stable evidence reference."""

    # ── Platform objects (WO-64) ──

    @abc.abstractmethod
    def create_org(self, org: Organization) -> Organization: ...

    @abc.abstractmethod
    def get_org(self, org_id: str) -> Organization | None: ...

    @abc.abstractmethod
    def create_env(self, env: Environment) -> Environment: ...

    @abc.abstractmethod
    def get_env(self, env_id: str) -> Environment | None: ...

    @abc.abstractmethod
    def list_envs(self, org_id: str) -> list[Environment]: ...

    @abc.abstractmethod
    def create_agent(self, agent: Agent) -> Agent: ...

    @abc.abstractmethod
    def get_agent(self, agent_id: str) -> Agent | None: ...

    @abc.abstractmethod
    def list_agents_for_org(self, org_id: str, environment_id: str = "") -> list[Agent]: ...

    @abc.abstractmethod
    def create_system_conn(self, conn: SystemConnection) -> SystemConnection: ...

    @abc.abstractmethod
    def list_systems_for_org(self, org_id: str, environment_id: str = "") -> list[SystemConnection]: ...

    @abc.abstractmethod
    def create_policy(self, policy: CapturePolicy) -> CapturePolicy: ...

    @abc.abstractmethod
    def list_policies_for_org(self, org_id: str, environment_id: str = "") -> list[CapturePolicy]: ...

    # ── Product objects (WO-28) ──

    @abc.abstractmethod
    def create_vr(self, vr: VerificationRecord) -> VerificationRecord: ...

    @abc.abstractmethod
    def get_vr(self, vr_id: str) -> VerificationRecord | None: ...

    @abc.abstractmethod
    def list_vrs(self, org_id: str, environment_id: str = "") -> list[VerificationRecord]: ...

    @abc.abstractmethod
    def update_vr(self, vr: VerificationRecord) -> VerificationRecord: ...

    @abc.abstractmethod
    def create_label(self, label: HumanLabel) -> HumanLabel: ...

    @abc.abstractmethod
    def get_label(self, label_id: str) -> HumanLabel | None: ...

    @abc.abstractmethod
    def list_labels_for_vr(self, vr_id: str) -> list[HumanLabel]: ...

    @abc.abstractmethod
    def create_evidence_artifact(self, artifact: EvidenceArtifact) -> EvidenceArtifact: ...

    @abc.abstractmethod
    def get_evidence_artifact(self, artifact_id: str) -> EvidenceArtifact | None: ...

    @abc.abstractmethod
    def list_evidence_artifacts_for_vr(self, vr_id: str, org_id: str) -> list[EvidenceArtifact]: ...

    @abc.abstractmethod
    def create_replay_run(self, run: ReplayRun) -> ReplayRun: ...

    @abc.abstractmethod
    def get_replay_run(self, run_id: str) -> ReplayRun | None: ...

    @abc.abstractmethod
    def list_replay_runs_for_vr(self, vr_id: str) -> list[ReplayRun]: ...

    @abc.abstractmethod
    def create_replay_execution_events(self, run_id: str, events: list[ReplayExecutionEvent]) -> None: ...

    @abc.abstractmethod
    def list_replay_execution_events(self, run_id: str) -> list[ReplayExecutionEvent]: ...

    @abc.abstractmethod
    def create_mutation_test(self, test: MutationTest) -> MutationTest: ...

    @abc.abstractmethod
    def get_mutation_test(self, test_id: str) -> MutationTest | None: ...

    @abc.abstractmethod
    def list_mutation_tests_for_vr(self, vr_id: str) -> list[MutationTest]: ...

    @abc.abstractmethod
    def create_proof_certificate(self, cert: ProofCertificate) -> ProofCertificate: ...

    @abc.abstractmethod
    def get_proof_certificate(self, cert_id: str) -> ProofCertificate | None: ...

    @abc.abstractmethod
    def create_scenario(self, scenario: Scenario) -> Scenario: ...

    @abc.abstractmethod
    def get_scenario(self, scenario_id: str) -> Scenario | None: ...

    @abc.abstractmethod
    def list_scenarios(self, org_id: str, environment_id: str = "") -> list[Scenario]: ...

    @abc.abstractmethod
    def update_scenario(self, scenario: Scenario) -> Scenario: ...

    @abc.abstractmethod
    def create_scenario_candidate(self, candidate: ScenarioCandidate) -> ScenarioCandidate: ...

    @abc.abstractmethod
    def get_scenario_candidate(self, candidate_id: str) -> ScenarioCandidate | None: ...

    @abc.abstractmethod
    def list_scenario_candidates(self, org_id: str, environment_id: str = "") -> list[ScenarioCandidate]: ...

    @abc.abstractmethod
    def update_scenario_candidate(self, candidate: ScenarioCandidate) -> ScenarioCandidate: ...

    @abc.abstractmethod
    def create_scenario_run(self, run: ScenarioRun) -> ScenarioRun: ...

    @abc.abstractmethod
    def get_scenario_run(self, run_id: str) -> ScenarioRun | None: ...

    @abc.abstractmethod
    def update_scenario_run(self, run: ScenarioRun) -> ScenarioRun: ...

    @abc.abstractmethod
    def list_scenario_runs(self, org_id: str, environment_id: str = "") -> list[ScenarioRun]: ...

    @abc.abstractmethod
    def create_readiness_policy(self, policy: ReadinessPolicy) -> ReadinessPolicy: ...

    @abc.abstractmethod
    def get_readiness_policy(self, policy_id: str) -> ReadinessPolicy | None: ...

    @abc.abstractmethod
    def list_readiness_policies(self, org_id: str, environment_id: str = "") -> list[ReadinessPolicy]: ...

    @abc.abstractmethod
    def update_readiness_policy(self, policy: ReadinessPolicy) -> ReadinessPolicy: ...

    @abc.abstractmethod
    def create_readiness_check(self, check: ReadinessCheck) -> ReadinessCheck: ...

    @abc.abstractmethod
    def get_readiness_check(self, check_id: str) -> ReadinessCheck | None: ...

    @abc.abstractmethod
    def list_readiness_checks(self, org_id: str, environment_id: str = "") -> list[ReadinessCheck]: ...

    @abc.abstractmethod
    def create_release_gate_result(self, result: ReleaseGateResult) -> ReleaseGateResult: ...

    @abc.abstractmethod
    def get_release_gate_result(self, result_id: str) -> ReleaseGateResult | None: ...

    # ── Integrations & Capture (Phase E) ──

    @abc.abstractmethod
    def create_ai_system(self, system: AISystem) -> AISystem: ...

    @abc.abstractmethod
    def get_ai_system(self, system_id: str) -> AISystem | None: ...

    @abc.abstractmethod
    def list_ai_systems(self, org_id: str, environment_id: str = "") -> list[AISystem]: ...

    @abc.abstractmethod
    def update_ai_system(self, system: AISystem) -> AISystem: ...

    @abc.abstractmethod
    def create_capture_connector(self, conn: CaptureConnector) -> CaptureConnector: ...

    @abc.abstractmethod
    def get_capture_connector(self, conn_id: str) -> CaptureConnector | None: ...

    @abc.abstractmethod
    def list_capture_connectors(self, ai_system_id: str) -> list[CaptureConnector]: ...

    @abc.abstractmethod
    def update_capture_connector(self, conn: CaptureConnector) -> CaptureConnector: ...

    @abc.abstractmethod
    def create_field_handling_rule(self, rule: FieldHandlingRule) -> FieldHandlingRule: ...

    @abc.abstractmethod
    def list_field_handling_rules(self, ai_system_id: str) -> list[FieldHandlingRule]: ...

    @abc.abstractmethod
    def delete_field_handling_rules(self, ai_system_id: str) -> None: ...

    @abc.abstractmethod
    def create_capture_validation_run(self, run: CaptureValidationRun) -> CaptureValidationRun: ...

    @abc.abstractmethod
    def list_capture_validation_runs(self, ai_system_id: str) -> list[CaptureValidationRun]: ...

    @abc.abstractmethod
    def create_decision_family_candidate(self, candidate: DecisionFamilyCandidate) -> DecisionFamilyCandidate: ...

    @abc.abstractmethod
    def list_decision_family_candidates(self, org_id: str, ai_system_id: str = "") -> list[DecisionFamilyCandidate]: ...

    @abc.abstractmethod
    def update_decision_family_candidate(self, candidate: DecisionFamilyCandidate) -> DecisionFamilyCandidate: ...

    # ── Decision Workflow ──

    @abc.abstractmethod
    def create_decision_workflow(self, wf: DecisionWorkflow) -> DecisionWorkflow: ...

    @abc.abstractmethod
    def get_decision_workflow(self, wf_id: str) -> DecisionWorkflow | None: ...

    @abc.abstractmethod
    def list_decision_workflows(self, org_id: str, environment_id: str = "") -> list[DecisionWorkflow]: ...

    @abc.abstractmethod
    def update_decision_workflow(self, wf: DecisionWorkflow) -> DecisionWorkflow: ...

    # ── Workflow Evidence Sources ──

    @abc.abstractmethod
    def list_workflow_evidence_sources(self, workflow_id: str) -> list[WorkflowEvidenceSource]: ...

    @abc.abstractmethod
    def save_workflow_evidence_sources(self, workflow_id: str, sources: list[WorkflowEvidenceSource]) -> list[WorkflowEvidenceSource]: ...


class MemoryStorage(StorageBackend):
    """In-memory repository for incidents and certificates (local/dev)."""

    def __init__(self) -> None:
        self._reset_memory()

    def _reset_memory(self) -> None:
        self._incidents: dict[str, Incident] = {}
        self._snapshots: dict[str, dict[str, Any]] = {}
        self._certificates: dict[str, dict[str, Any]] = {}
        self._evidence: dict[str, dict[str, Any]] = {}
        self._counter = 0
        # Platform objects (WO-64)
        self._orgs: dict[str, Organization] = {}
        self._envs: dict[str, Environment] = {}
        self._agents: dict[str, Agent] = {}
        self._systems: dict[str, SystemConnection] = {}
        self._policies: dict[str, CapturePolicy] = {}
        # Product objects (WO-28)
        self._vrs: dict[str, VerificationRecord] = {}
        self._labels: dict[str, HumanLabel] = {}
        self._evidence_artifacts: dict[str, EvidenceArtifact] = {}
        self._replay_runs: dict[str, ReplayRun] = {}
        self._mutation_tests: dict[str, MutationTest] = {}
        self._proof_certs: dict[str, ProofCertificate] = {}
        self._scenarios: dict[str, Scenario] = {}
        self._scenario_candidates: dict[str, ScenarioCandidate] = {}
        self._scenario_runs: dict[str, ScenarioRun] = {}
        self._readiness_policies: dict[str, ReadinessPolicy] = {}
        self._readiness_checks: dict[str, ReadinessCheck] = {}
        self._release_gate_results: dict[str, ReleaseGateResult] = {}
        self._replay_execution_events: dict[str, list[ReplayExecutionEvent]] = {}
        self._ai_systems: dict[str, AISystem] = {}
        self._capture_connectors: dict[str, CaptureConnector] = {}
        self._field_handling_rules: dict[str, FieldHandlingRule] = {}
        self._capture_validation_runs: dict[str, CaptureValidationRun] = {}
        self._decision_family_candidates: dict[str, DecisionFamilyCandidate] = {}
        self._decision_workflows: dict[str, DecisionWorkflow] = {}
        self._workflow_evidence_sources: dict[str, list[WorkflowEvidenceSource]] = {}

    def reset(self) -> None:
        """Clear local/dev state for repeatable demos and tests."""
        self._reset_memory()

    def create_incident(self, snapshot_dict: dict[str, Any], org_id: str = "demo-org") -> Incident:
        self._counter += 1
        incident_id = f"inc-{self._counter:06d}"
        snapshot_summary = {
            "schema_version": snapshot_dict.get("schema_version"),
            "timestamp": snapshot_dict.get("timestamp"),
            "element_count": len(snapshot_dict.get("elements", [])),
            "root_hash": snapshot_dict.get("root_hash", ""),
            "scenario_id": snapshot_dict.get("scenario_id"),
        }
        incident = Incident(incident_id=incident_id, org_id=org_id, snapshot_summary=snapshot_summary)
        self._incidents[incident_id] = incident
        self._snapshots[incident_id] = snapshot_dict
        return incident

    def get_incident(self, incident_id: str) -> Incident | None:
        return self._incidents.get(incident_id)

    def list_incidents(self, org_id: str | None = None) -> list[Incident]:
        items = list(self._incidents.values())
        if org_id is not None:
            items = [i for i in items if i.org_id == org_id]
        return items

    def get_snapshot(self, incident_id: str) -> dict[str, Any] | None:
        return self._snapshots.get(incident_id)

    def update_incident(self, incident: Incident) -> None:
        self._incidents[incident.incident_id] = incident

    def store_certificate(self, incident_id: str, cert: dict[str, Any]) -> None:
        self._certificates[incident_id] = cert

    def get_certificate(self, incident_id: str) -> dict[str, Any] | None:
        return self._certificates.get(incident_id)

    def persist_evidence(self, incident_id: str, kind: str, payload: dict[str, Any]) -> str:
        ref = f"{incident_id}/{kind}/{uuid.uuid4().hex}.json"
        self._evidence[ref] = payload
        return ref

    # ── Platform objects (WO-64) ──

    def create_org(self, org: Organization) -> Organization:
        self._orgs[org.id] = org
        return org

    def get_org(self, org_id: str) -> Organization | None:
        return self._orgs.get(org_id)

    def create_env(self, env: Environment) -> Environment:
        self._envs[env.id] = env
        return env

    def get_env(self, env_id: str) -> Environment | None:
        return self._envs.get(env_id)

    def list_envs(self, org_id: str) -> list[Environment]:
        return [e for e in self._envs.values() if e.org_id == org_id]

    def create_agent(self, agent: Agent) -> Agent:
        self._agents[agent.id] = agent
        return agent

    def get_agent(self, agent_id: str) -> Agent | None:
        return self._agents.get(agent_id)

    def list_agents_for_org(self, org_id: str, environment_id: str = "") -> list[Agent]:
        agents = [a for a in self._agents.values() if a.org_id == org_id]
        if environment_id:
            agents = [a for a in agents if a.environment_id == environment_id]
        return agents

    def create_system_conn(self, conn: SystemConnection) -> SystemConnection:
        self._systems[conn.id] = conn
        return conn

    def list_systems_for_org(self, org_id: str, environment_id: str = "") -> list[SystemConnection]:
        systems = [s for s in self._systems.values() if s.org_id == org_id]
        if environment_id:
            systems = [s for s in systems if s.environment_id == environment_id]
        return systems

    def create_policy(self, policy: CapturePolicy) -> CapturePolicy:
        self._policies[policy.id] = policy
        return policy

    def list_policies_for_org(self, org_id: str, environment_id: str = "") -> list[CapturePolicy]:
        policies = [p for p in self._policies.values() if p.org_id == org_id]
        if environment_id:
            policies = [p for p in policies if p.environment_id == environment_id]
        return policies

    # ── Product objects (WO-28) ──

    def create_vr(self, vr: VerificationRecord) -> VerificationRecord:
        self._vrs[vr.id] = vr
        return vr

    def get_vr(self, vr_id: str) -> VerificationRecord | None:
        return self._vrs.get(vr_id)

    def list_vrs(self, org_id: str, environment_id: str = "") -> list[VerificationRecord]:
        vrs = [v for v in self._vrs.values() if v.org_id == org_id]
        if environment_id:
            vrs = [v for v in vrs if v.environment_id == environment_id]
        return vrs

    def update_vr(self, vr: VerificationRecord) -> VerificationRecord:
        self._vrs[vr.id] = vr
        return vr

    def create_label(self, label: HumanLabel) -> HumanLabel:
        self._labels[label.id] = label
        return label

    def get_label(self, label_id: str) -> HumanLabel | None:
        return self._labels.get(label_id)

    def list_labels_for_vr(self, vr_id: str) -> list[HumanLabel]:
        return [lbl for lbl in self._labels.values() if lbl.verification_record_id == vr_id]

    def create_evidence_artifact(self, artifact: EvidenceArtifact) -> EvidenceArtifact:
        self._evidence_artifacts[artifact.id] = artifact
        return artifact

    def get_evidence_artifact(self, artifact_id: str) -> EvidenceArtifact | None:
        return self._evidence_artifacts.get(artifact_id)

    def list_evidence_artifacts_for_vr(self, vr_id: str, org_id: str) -> list[EvidenceArtifact]:
        return [a for a in self._evidence_artifacts.values() if a.verification_record_id == vr_id and a.org_id == org_id]

    def create_replay_run(self, run: ReplayRun) -> ReplayRun:
        self._replay_runs[run.id] = run
        return run

    def get_replay_run(self, run_id: str) -> ReplayRun | None:
        return self._replay_runs.get(run_id)

    def list_replay_runs_for_vr(self, vr_id: str) -> list[ReplayRun]:
        return [r for r in self._replay_runs.values() if r.verification_record_id == vr_id]

    def create_replay_execution_events(self, run_id: str, events: list[ReplayExecutionEvent]) -> None:
        self._replay_execution_events[run_id] = events

    def list_replay_execution_events(self, run_id: str) -> list[ReplayExecutionEvent]:
        return self._replay_execution_events.get(run_id, [])

    def create_mutation_test(self, test: MutationTest) -> MutationTest:
        self._mutation_tests[test.id] = test
        return test

    def get_mutation_test(self, test_id: str) -> MutationTest | None:
        return self._mutation_tests.get(test_id)

    def list_mutation_tests_for_vr(self, vr_id: str) -> list[MutationTest]:
        return [m for m in self._mutation_tests.values() if m.verification_record_id == vr_id]

    def create_proof_certificate(self, cert: ProofCertificate) -> ProofCertificate:
        self._proof_certs[cert.id] = cert
        return cert

    def get_proof_certificate(self, cert_id: str) -> ProofCertificate | None:
        return self._proof_certs.get(cert_id)

    def create_scenario(self, scenario: Scenario) -> Scenario:
        self._scenarios[scenario.id] = scenario
        return scenario

    def get_scenario(self, scenario_id: str) -> Scenario | None:
        return self._scenarios.get(scenario_id)

    def list_scenarios(self, org_id: str, environment_id: str = "") -> list[Scenario]:
        scenarios = [s for s in self._scenarios.values() if s.org_id == org_id]
        if environment_id:
            scenarios = [s for s in scenarios if s.environment_id == environment_id]
        return scenarios

    def update_scenario(self, scenario: Scenario) -> Scenario:
        self._scenarios[scenario.id] = scenario
        return scenario

    def create_scenario_candidate(self, candidate: ScenarioCandidate) -> ScenarioCandidate:
        self._scenario_candidates[candidate.id] = candidate
        return candidate

    def get_scenario_candidate(self, candidate_id: str) -> ScenarioCandidate | None:
        return self._scenario_candidates.get(candidate_id)

    def list_scenario_candidates(self, org_id: str, environment_id: str = "") -> list[ScenarioCandidate]:
        candidates = [c for c in self._scenario_candidates.values() if c.org_id == org_id]
        if environment_id:
            candidates = [c for c in candidates if c.environment_id == environment_id]
        return candidates

    def update_scenario_candidate(self, candidate: ScenarioCandidate) -> ScenarioCandidate:
        self._scenario_candidates[candidate.id] = candidate
        return candidate

    def create_scenario_run(self, run: ScenarioRun) -> ScenarioRun:
        self._scenario_runs[run.id] = run
        return run

    def get_scenario_run(self, run_id: str) -> ScenarioRun | None:
        return self._scenario_runs.get(run_id)

    def update_scenario_run(self, run: ScenarioRun) -> ScenarioRun:
        self._scenario_runs[run.id] = run
        return run

    def list_scenario_runs(self, org_id: str, environment_id: str = "") -> list[ScenarioRun]:
        runs = [r for r in self._scenario_runs.values() if r.org_id == org_id]
        if environment_id:
            runs = [r for r in runs if r.environment_id == environment_id]
        return runs

    def create_readiness_policy(self, policy: ReadinessPolicy) -> ReadinessPolicy:
        self._readiness_policies[policy.id] = policy
        return policy

    def get_readiness_policy(self, policy_id: str) -> ReadinessPolicy | None:
        return self._readiness_policies.get(policy_id)

    def list_readiness_policies(self, org_id: str, environment_id: str = "") -> list[ReadinessPolicy]:
        policies = [p for p in self._readiness_policies.values() if p.org_id == org_id]
        if environment_id:
            policies = [p for p in policies if p.environment_id == environment_id]
        return policies

    def update_readiness_policy(self, policy: ReadinessPolicy) -> ReadinessPolicy:
        self._readiness_policies[policy.id] = policy
        return policy

    def create_readiness_check(self, check: ReadinessCheck) -> ReadinessCheck:
        self._readiness_checks[check.id] = check
        return check

    def get_readiness_check(self, check_id: str) -> ReadinessCheck | None:
        return self._readiness_checks.get(check_id)

    def list_readiness_checks(self, org_id: str, environment_id: str = "") -> list[ReadinessCheck]:
        checks = [c for c in self._readiness_checks.values() if c.org_id == org_id]
        if environment_id:
            checks = [c for c in checks if c.environment_id == environment_id]
        return checks

    def create_release_gate_result(self, result: ReleaseGateResult) -> ReleaseGateResult:
        self._release_gate_results[result.id] = result
        return result

    def get_release_gate_result(self, result_id: str) -> ReleaseGateResult | None:
        return self._release_gate_results.get(result_id)

    # ── Integrations & Capture (Phase E) ──

    def create_ai_system(self, system: AISystem) -> AISystem:
        self._ai_systems[system.id] = system
        return system

    def get_ai_system(self, system_id: str) -> AISystem | None:
        return self._ai_systems.get(system_id)

    def list_ai_systems(self, org_id: str, environment_id: str = "") -> list[AISystem]:
        systems = [s for s in self._ai_systems.values() if s.org_id == org_id]
        if environment_id:
            systems = [s for s in systems if s.environment_id == environment_id]
        return systems

    def update_ai_system(self, system: AISystem) -> AISystem:
        self._ai_systems[system.id] = system
        return system

    def create_capture_connector(self, conn: CaptureConnector) -> CaptureConnector:
        self._capture_connectors[conn.id] = conn
        return conn

    def get_capture_connector(self, conn_id: str) -> CaptureConnector | None:
        return self._capture_connectors.get(conn_id)

    def list_capture_connectors(self, ai_system_id: str) -> list[CaptureConnector]:
        return [c for c in self._capture_connectors.values() if c.ai_system_id == ai_system_id]

    def update_capture_connector(self, conn: CaptureConnector) -> CaptureConnector:
        self._capture_connectors[conn.id] = conn
        return conn

    def create_field_handling_rule(self, rule: FieldHandlingRule) -> FieldHandlingRule:
        self._field_handling_rules[rule.id] = rule
        return rule

    def list_field_handling_rules(self, ai_system_id: str) -> list[FieldHandlingRule]:
        return [r for r in self._field_handling_rules.values() if r.ai_system_id == ai_system_id]

    def delete_field_handling_rules(self, ai_system_id: str) -> None:
        keep: dict[str, FieldHandlingRule] = {}
        for rid, rule in self._field_handling_rules.items():
            if rule.ai_system_id != ai_system_id:
                keep[rid] = rule
        self._field_handling_rules = keep

    def create_capture_validation_run(self, run: CaptureValidationRun) -> CaptureValidationRun:
        self._capture_validation_runs[run.id] = run
        return run

    def list_capture_validation_runs(self, ai_system_id: str) -> list[CaptureValidationRun]:
        return [r for r in self._capture_validation_runs.values() if r.ai_system_id == ai_system_id]

    def create_decision_family_candidate(self, candidate: DecisionFamilyCandidate) -> DecisionFamilyCandidate:
        self._decision_family_candidates[candidate.id] = candidate
        return candidate

    def list_decision_family_candidates(self, org_id: str, ai_system_id: str = "") -> list[DecisionFamilyCandidate]:
        candidates = [c for c in self._decision_family_candidates.values() if c.org_id == org_id]
        if ai_system_id:
            candidates = [c for c in candidates if c.ai_system_id == ai_system_id]
        return candidates

    def update_decision_family_candidate(self, candidate: DecisionFamilyCandidate) -> DecisionFamilyCandidate:
        self._decision_family_candidates[candidate.id] = candidate
        return candidate

    # ── Decision Workflow ──

    def create_decision_workflow(self, wf: DecisionWorkflow) -> DecisionWorkflow:
        self._decision_workflows[wf.id] = wf
        return wf

    def get_decision_workflow(self, wf_id: str) -> DecisionWorkflow | None:
        return self._decision_workflows.get(wf_id)

    def list_decision_workflows(self, org_id: str, environment_id: str = "") -> list[DecisionWorkflow]:
        return [wf for wf in self._decision_workflows.values()
                if wf.org_id == org_id and (not environment_id or wf.environment_id == environment_id)]

    def update_decision_workflow(self, wf: DecisionWorkflow) -> DecisionWorkflow:
        self._decision_workflows[wf.id] = wf
        return wf

    # ── Workflow Evidence Sources ──

    def list_workflow_evidence_sources(self, workflow_id: str) -> list[WorkflowEvidenceSource]:
        return self._workflow_evidence_sources.get(workflow_id, [])

    def save_workflow_evidence_sources(self, workflow_id: str, sources: list[WorkflowEvidenceSource]) -> list[WorkflowEvidenceSource]:
        self._workflow_evidence_sources[workflow_id] = sources
        return sources


class SharedDemoFileStorage(MemoryStorage):
    """JSON-backed shared-demo storage that survives process restarts.

    This is intentionally local file persistence, not immutable cloud evidence
    storage. It gives presenter-safe restart behavior without requiring AWS.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or SETTINGS.shared_demo_storage_path)
        self._loading = True
        super().__init__()
        self._load()
        self._loading = False

    def reset(self) -> None:
        self._reset_memory()
        self._save()

    def _load(self) -> None:
        if not self.path.exists():
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self._counter = int(data.get("counter", 0))
        self._snapshots = dict(data.get("snapshots", {}))
        self._certificates = dict(data.get("certificates", {}))
        self._evidence = dict(data.get("evidence", {}))
        self._incidents = {iid: self._incident_from_dict(raw) for iid, raw in data.get("incidents", {}).items()}
        for public_name, (attr_name, cls) in _PERSISTED_COLLECTIONS.items():
            raw_items = data.get(public_name, {})
            setattr(self, attr_name, {item_id: cls.from_dict(raw) for item_id, raw in raw_items.items()})

    def _save(self) -> None:
        if self._loading:
            return
        data: dict[str, Any] = {
            "schema_version": 1,
            "counter": self._counter,
            "incidents": {iid: inc.to_dict() for iid, inc in self._incidents.items()},
            "snapshots": self._snapshots,
            "certificates": self._certificates,
            "evidence": self._evidence,
        }
        for public_name, (attr_name, _) in _PERSISTED_COLLECTIONS.items():
            data[public_name] = {item_id: item.to_dict() for item_id, item in getattr(self, attr_name).items()}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        tmp_path.write_text(json.dumps(data, sort_keys=True, indent=2), encoding="utf-8")
        tmp_path.replace(self.path)

    def _incident_from_dict(self, data: dict[str, Any]) -> Incident:
        incident = Incident(
            incident_id=data["incident_id"],
            org_id=data.get("org_id", "demo-org"),
            status=__import__("notary_platform.models", fromlist=["IncidentStatus"]).IncidentStatus(data.get("status", "ingested")),
            snapshot_summary=data.get("snapshot_summary") or {},
            replay_result=data.get("replay_result") or {},
            mutation_result=data.get("mutation_result") or {},
            certificate=data.get("certificate") or {},
        )
        incident.custody = [__import__("notary_platform.models", fromlist=["CustodyEvent"]).CustodyEvent(**c) for c in data.get("custody", [])]
        return incident

    def create_incident(self, snapshot_dict: dict[str, Any], org_id: str = "demo-org") -> Incident:
        incident = super().create_incident(snapshot_dict, org_id)
        self._save()
        return incident

    def update_incident(self, incident: Incident) -> None:
        super().update_incident(incident)
        self._save()

    def store_certificate(self, incident_id: str, cert: dict[str, Any]) -> None:
        super().store_certificate(incident_id, cert)
        self._save()

    def persist_evidence(self, incident_id: str, kind: str, payload: dict[str, Any]) -> str:
        ref = super().persist_evidence(incident_id, kind, payload)
        self._save()
        return ref

    def create_org(self, org: Organization) -> Organization:
        result = super().create_org(org)
        self._save()
        return result

    def create_env(self, env: Environment) -> Environment:
        result = super().create_env(env)
        self._save()
        return result

    def create_agent(self, agent: Agent) -> Agent:
        result = super().create_agent(agent)
        self._save()
        return result

    def create_system_conn(self, conn: SystemConnection) -> SystemConnection:
        result = super().create_system_conn(conn)
        self._save()
        return result

    def create_policy(self, policy: CapturePolicy) -> CapturePolicy:
        result = super().create_policy(policy)
        self._save()
        return result

    def create_vr(self, vr: VerificationRecord) -> VerificationRecord:
        result = super().create_vr(vr)
        self._save()
        return result

    def update_vr(self, vr: VerificationRecord) -> VerificationRecord:
        result = super().update_vr(vr)
        self._save()
        return result

    def create_label(self, label: HumanLabel) -> HumanLabel:
        result = super().create_label(label)
        self._save()
        return result

    def create_evidence_artifact(self, artifact: EvidenceArtifact) -> EvidenceArtifact:
        result = super().create_evidence_artifact(artifact)
        self._save()
        return result

    def create_replay_run(self, run: ReplayRun) -> ReplayRun:
        result = super().create_replay_run(run)
        self._save()
        return result

    def create_mutation_test(self, test: MutationTest) -> MutationTest:
        result = super().create_mutation_test(test)
        self._save()
        return result

    def create_proof_certificate(self, cert: ProofCertificate) -> ProofCertificate:
        result = super().create_proof_certificate(cert)
        self._save()
        return result

    def create_scenario(self, scenario: Scenario) -> Scenario:
        result = super().create_scenario(scenario)
        self._save()
        return result

    def update_scenario(self, scenario: Scenario) -> Scenario:
        result = super().update_scenario(scenario)
        self._save()
        return result

    def create_scenario_candidate(self, candidate: ScenarioCandidate) -> ScenarioCandidate:
        result = super().create_scenario_candidate(candidate)
        self._save()
        return result

    def update_scenario_candidate(self, candidate: ScenarioCandidate) -> ScenarioCandidate:
        result = super().update_scenario_candidate(candidate)
        self._save()
        return result

    def create_scenario_run(self, run: ScenarioRun) -> ScenarioRun:
        result = super().create_scenario_run(run)
        self._save()
        return result

    def update_scenario_run(self, run: ScenarioRun) -> ScenarioRun:
        result = super().update_scenario_run(run)
        self._save()
        return result

    def create_readiness_policy(self, policy: ReadinessPolicy) -> ReadinessPolicy:
        result = super().create_readiness_policy(policy)
        self._save()
        return result

    def update_readiness_policy(self, policy: ReadinessPolicy) -> ReadinessPolicy:
        result = super().update_readiness_policy(policy)
        self._save()
        return result

    def create_readiness_check(self, check: ReadinessCheck) -> ReadinessCheck:
        result = super().create_readiness_check(check)
        self._save()
        return result

    def create_release_gate_result(self, result: ReleaseGateResult) -> ReleaseGateResult:
        stored = super().create_release_gate_result(result)
        self._save()
        return stored

    def create_ai_system(self, system: AISystem) -> AISystem:
        result = super().create_ai_system(system)
        self._save()
        return result

    def update_ai_system(self, system: AISystem) -> AISystem:
        result = super().update_ai_system(system)
        self._save()
        return result

    def create_capture_connector(self, conn: CaptureConnector) -> CaptureConnector:
        result = super().create_capture_connector(conn)
        self._save()
        return result

    def update_capture_connector(self, conn: CaptureConnector) -> CaptureConnector:
        result = super().update_capture_connector(conn)
        self._save()
        return result

    def create_field_handling_rule(self, rule: FieldHandlingRule) -> FieldHandlingRule:
        result = super().create_field_handling_rule(rule)
        self._save()
        return result

    def delete_field_handling_rules(self, ai_system_id: str) -> None:
        super().delete_field_handling_rules(ai_system_id)
        self._save()

    def create_capture_validation_run(self, run: CaptureValidationRun) -> CaptureValidationRun:
        result = super().create_capture_validation_run(run)
        self._save()
        return result

    def create_decision_family_candidate(self, candidate: DecisionFamilyCandidate) -> DecisionFamilyCandidate:
        result = super().create_decision_family_candidate(candidate)
        self._save()
        return result

    def update_decision_family_candidate(self, candidate: DecisionFamilyCandidate) -> DecisionFamilyCandidate:
        result = super().update_decision_family_candidate(candidate)
        self._save()
        return result


class PostgresS3Storage(StorageBackend):
    """PostgreSQL metadata + S3 immutable evidence storage.

    Credentials come from the environment / IAM role — never hardcoded. This
    backend is only constructed when ``NOTARY_USE_REMOTE_STORAGE`` is set.
    """

    def __init__(self) -> None:
        if not SETTINGS.database_url:
            raise RuntimeError("NOTARY_DATABASE_URL must be set for remote storage")
        if not SETTINGS.evidence_bucket:
            raise RuntimeError("NOTARY_EVIDENCE_BUCKET must be set for remote storage")
        # Imported lazily so the in-memory path never requires these packages.
        import boto3  # noqa: F401  (validated at construction)
        import sqlalchemy  # noqa: F401

        self._engine = sqlalchemy.create_engine(SETTINGS.database_url, future=True)
        self._bucket = SETTINGS.evidence_bucket
        self._prefix = SETTINGS.evidence_prefix
        self._session = boto3.session.Session()
        self._s3 = self._session.client("s3")
        self._ensure_schema()
        self._replay_execution_events: dict[str, list[ReplayExecutionEvent]] = {}

    # -- metadata (Postgres) -------------------------------------------------
    def _ensure_schema(self) -> None:
        with self._engine.begin() as conn:
            conn.exec_driver_sql(
                """
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    org_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    snapshot_summary JSONB,
                    replay_result JSONB,
                    mutation_result JSONB,
                    certificate JSONB,
                    custody JSONB,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            conn.exec_driver_sql(
                """
                CREATE TABLE IF NOT EXISTS wo28_objects (
                    id TEXT PRIMARY KEY,
                    org_id TEXT NOT NULL,
                    environment_id TEXT NOT NULL DEFAULT 'env:demo',
                    kind TEXT NOT NULL,
                    data JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            conn.exec_driver_sql(
                "CREATE INDEX IF NOT EXISTS idx_wo28_kind_org_env ON wo28_objects(kind, org_id, environment_id)"
            )

    def _write_wo28(self, kind: str, obj: Any) -> None:
        data = obj.to_dict()
        with self._engine.begin() as conn:
            conn.exec_driver_sql(
                """
                INSERT INTO wo28_objects (id, org_id, environment_id, kind, data)
                VALUES (%(id)s, %(org)s, %(env)s, %(kind)s, %(data)s)
                ON CONFLICT (id) DO UPDATE SET
                    data = EXCLUDED.data,
                    updated_at = now()
                """,
                {
                    "id": getattr(obj, "id", ""),
                    "org": getattr(obj, "org_id", ""),
                    "env": getattr(obj, "environment_id", "env:demo"),
                    "kind": kind,
                    "data": json.dumps(data),
                },
            )

    def _get_wo28(self, kind: str, id: str, cls: type[Any]) -> Any | None:
        with self._engine.connect() as conn:
            row = conn.exec_driver_sql(
                "SELECT data FROM wo28_objects WHERE kind = %(kind)s AND id = %(id)s",
                {"kind": kind, "id": id},
            ).mappings().first()
        if not row:
            return None
        return cls.from_dict(dict(row["data"]))

    def _list_wo28(self, kind: str, org_id: str, environment_id: str, cls: type[Any]) -> list[Any]:
        with self._engine.connect() as conn:
            if environment_id:
                rows = conn.exec_driver_sql(
                    "SELECT data FROM wo28_objects WHERE kind = %(kind)s AND org_id = %(org)s AND environment_id = %(env)s ORDER BY created_at",
                    {"kind": kind, "org": org_id, "env": environment_id},
                ).mappings().all()
            else:
                rows = conn.exec_driver_sql(
                    "SELECT data FROM wo28_objects WHERE kind = %(kind)s AND org_id = %(org)s ORDER BY created_at",
                    {"kind": kind, "org": org_id},
                ).mappings().all()
        return [cls.from_dict(dict(r["data"])) for r in rows]

    def _row_to_incident(self, row: dict[str, Any]) -> Incident:
        inc = Incident(
            incident_id=row["incident_id"],
            org_id=row["org_id"],
            status=__import__("notary_platform.models", fromlist=["IncidentStatus"]).IncidentStatus(
                row["status"]
            ),
            snapshot_summary=row.get("snapshot_summary") or {},
            replay_result=row.get("replay_result") or {},
            mutation_result=row.get("mutation_result") or {},
            certificate=row.get("certificate") or {},
        )
        inc.custody = [
            __import__("notary_platform.models", fromlist=["CustodyEvent"]).CustodyEvent(**c)
            for c in (row.get("custody") or [])
        ]
        return inc

    def create_incident(self, snapshot_dict: dict[str, Any], org_id: str = "demo-org") -> Incident:
        snapshot_summary = {
            "schema_version": snapshot_dict.get("schema_version"),
            "timestamp": snapshot_dict.get("timestamp"),
            "element_count": len(snapshot_dict.get("elements", [])),
            "root_hash": snapshot_dict.get("root_hash", ""),
            "scenario_id": snapshot_dict.get("scenario_id"),
        }
        incident = Incident(incident_id=self._next_id(), org_id=org_id, snapshot_summary=snapshot_summary)
        self._write_incident(incident)
        return incident

    def _next_id(self) -> str:
        with self._engine.connect() as conn:
            row = conn.exec_driver_sql(
                "SELECT COUNT(*) AS c FROM incidents"
            ).mappings().first()
        n = (row["c"] if row else 0) + 1
        return f"inc-{n:06d}"

    def _write_incident(self, incident: Incident) -> None:
        data = incident.to_dict()
        with self._engine.begin() as conn:
            conn.exec_driver_sql(
                """
                INSERT INTO incidents
                    (incident_id, org_id, status, snapshot_summary, replay_result,
                     mutation_result, certificate, custody)
                VALUES (%(iid)s, %(org)s, %(status)s, %(sum)s, %(replay)s, %(mut)s, %(cert)s, %(cust)s)
                ON CONFLICT (incident_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    snapshot_summary = EXCLUDED.snapshot_summary,
                    replay_result = EXCLUDED.replay_result,
                    mutation_result = EXCLUDED.mutation_result,
                    certificate = EXCLUDED.certificate,
                    custody = EXCLUDED.custody
                """,
                {
                    "iid": incident.incident_id,
                    "org": incident.org_id,
                    "status": incident.status.value,
                    "sum": json.dumps(data["snapshot_summary"]),
                    "replay": json.dumps(data["replay_result"]),
                    "mut": json.dumps(data["mutation_result"]),
                    "cert": json.dumps(data["certificate"]),
                    "cust": json.dumps(data["custody"]),
                },
            )

    def get_incident(self, incident_id: str) -> Incident | None:
        with self._engine.connect() as conn:
            row = conn.exec_driver_sql(
                "SELECT * FROM incidents WHERE incident_id = %(iid)s", {"iid": incident_id}
            ).mappings().first()
        return self._row_to_incident(dict(row)) if row else None

    def list_incidents(self, org_id: str | None = None) -> list[Incident]:
        with self._engine.connect() as conn:
            if org_id is not None:
                rows = conn.exec_driver_sql(
                    "SELECT * FROM incidents WHERE org_id = %(org)s ORDER BY created_at",
                    {"org": org_id},
                ).mappings().all()
            else:
                rows = conn.exec_driver_sql(
                    "SELECT * FROM incidents ORDER BY created_at"
                ).mappings().all()
        return [self._row_to_incident(dict(r)) for r in rows]

    def get_snapshot(self, incident_id: str) -> dict[str, Any] | None:
        key = f"{self._prefix.rstrip('/')}/{incident_id}/snapshot.json"
        try:
            obj = self._s3.get_object(Bucket=self._bucket, Key=key)
            data: dict[str, Any] = json.loads(obj["Body"].read())
            return data
        except Exception:
            return None

    def update_incident(self, incident: Incident) -> None:
        self._write_incident(incident)

    def store_certificate(self, incident_id: str, cert: dict[str, Any]) -> None:
        incident = self.get_incident(incident_id)
        if incident is not None:
            incident.certificate = cert
            self._write_incident(incident)
        self.persist_evidence(incident_id, "certificate", cert)

    def get_certificate(self, incident_id: str) -> dict[str, Any] | None:
        key = f"{self._prefix.rstrip('/')}/{incident_id}/certificate.json"
        try:
            obj = self._s3.get_object(Bucket=self._bucket, Key=key)
            data: dict[str, Any] = json.loads(obj["Body"].read())
            return data
        except Exception:
            return None

    def persist_evidence(self, incident_id: str, kind: str, payload: dict[str, Any]) -> str:
        ref = f"{self._prefix.rstrip('/')}/{incident_id}/{kind}/{uuid.uuid4().hex}.json"
        self._s3.put_object(
            Bucket=self._bucket,
            Key=ref,
            Body=json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"),
            ContentType="application/json",
        )
        return ref

    # ── Platform objects (WO-64) — Postgres stubs ──
    def create_org(self, org: Organization) -> Organization: return org
    def get_org(self, org_id: str) -> Organization | None: return None
    def create_env(self, env: Environment) -> Environment: return env
    def get_env(self, env_id: str) -> Environment | None: return None
    def list_envs(self, org_id: str) -> list[Environment]: return []
    def create_agent(self, agent: Agent) -> Agent: return agent
    def get_agent(self, agent_id: str) -> Agent | None: return None
    def list_agents_for_org(self, org_id: str, environment_id: str = "") -> list[Agent]: return []
    def create_system_conn(self, conn: SystemConnection) -> SystemConnection: return conn
    def list_systems_for_org(self, org_id: str, environment_id: str = "") -> list[SystemConnection]: return []
    def create_policy(self, policy: CapturePolicy) -> CapturePolicy: return policy
    def list_policies_for_org(self, org_id: str, environment_id: str = "") -> list[CapturePolicy]: return []

    # ── Product objects (WO-28) — JSONB persistence in Postgres ──
    def create_vr(self, vr: VerificationRecord) -> VerificationRecord:
        self._write_wo28("verification_record", vr)
        return vr
    def get_vr(self, vr_id: str) -> VerificationRecord | None:
        return self._get_wo28("verification_record", vr_id, VerificationRecord)
    def list_vrs(self, org_id: str, environment_id: str = "") -> list[VerificationRecord]:
        return self._list_wo28("verification_record", org_id, environment_id, VerificationRecord)
    def update_vr(self, vr: VerificationRecord) -> VerificationRecord:
        self._write_wo28("verification_record", vr)
        return vr
    def create_label(self, label: HumanLabel) -> HumanLabel:
        self._write_wo28("human_label", label)
        return label
    def get_label(self, label_id: str) -> HumanLabel | None:
        return self._get_wo28("human_label", label_id, HumanLabel)
    def list_labels_for_vr(self, vr_id: str) -> list[HumanLabel]:
        return [lbl for lbl in self._list_wo28("human_label", "", "", HumanLabel) if lbl.verification_record_id == vr_id]
    def create_evidence_artifact(self, artifact: EvidenceArtifact) -> EvidenceArtifact:
        self._write_wo28("evidence_artifact", artifact)
        return artifact
    def get_evidence_artifact(self, artifact_id: str) -> EvidenceArtifact | None:
        return self._get_wo28("evidence_artifact", artifact_id, EvidenceArtifact)
    def list_evidence_artifacts_for_vr(self, vr_id: str, org_id: str) -> list[EvidenceArtifact]:
        return [a for a in self._list_wo28("evidence_artifact", org_id, "", EvidenceArtifact) if a.verification_record_id == vr_id]
    def create_replay_run(self, run: ReplayRun) -> ReplayRun:
        self._write_wo28("replay_run", run)
        return run
    def get_replay_run(self, run_id: str) -> ReplayRun | None:
        return self._get_wo28("replay_run", run_id, ReplayRun)
    def list_replay_runs_for_vr(self, vr_id: str) -> list[ReplayRun]:
        return [r for r in self._list_wo28("replay_run", "", "", ReplayRun) if r.verification_record_id == vr_id]
    def create_replay_execution_events(self, run_id: str, events: list[ReplayExecutionEvent]) -> None:
        self._replay_execution_events[run_id] = events
    def list_replay_execution_events(self, run_id: str) -> list[ReplayExecutionEvent]:
        return self._replay_execution_events.get(run_id, [])
    def create_mutation_test(self, test: MutationTest) -> MutationTest:
        self._write_wo28("mutation_test", test)
        return test
    def get_mutation_test(self, test_id: str) -> MutationTest | None:
        return self._get_wo28("mutation_test", test_id, MutationTest)
    def list_mutation_tests_for_vr(self, vr_id: str) -> list[MutationTest]:
        return [t for t in self._list_wo28("mutation_test", "", "", MutationTest) if t.verification_record_id == vr_id]
    def create_proof_certificate(self, cert: ProofCertificate) -> ProofCertificate:
        self._write_wo28("proof_certificate", cert)
        return cert
    def get_proof_certificate(self, cert_id: str) -> ProofCertificate | None:
        return self._get_wo28("proof_certificate", cert_id, ProofCertificate)
    def create_scenario(self, scenario: Scenario) -> Scenario:
        self._write_wo28("scenario", scenario)
        return scenario
    def get_scenario(self, scenario_id: str) -> Scenario | None:
        return self._get_wo28("scenario", scenario_id, Scenario)
    def list_scenarios(self, org_id: str, environment_id: str = "") -> list[Scenario]:
        return self._list_wo28("scenario", org_id, environment_id, Scenario)
    def update_scenario(self, scenario: Scenario) -> Scenario:
        self._write_wo28("scenario", scenario)
        return scenario
    def create_scenario_candidate(self, candidate: ScenarioCandidate) -> ScenarioCandidate:
        self._write_wo28("scenario_candidate", candidate)
        return candidate
    def get_scenario_candidate(self, candidate_id: str) -> ScenarioCandidate | None:
        return self._get_wo28("scenario_candidate", candidate_id, ScenarioCandidate)
    def list_scenario_candidates(self, org_id: str, environment_id: str = "") -> list[ScenarioCandidate]:
        return self._list_wo28("scenario_candidate", org_id, environment_id, ScenarioCandidate)
    def update_scenario_candidate(self, candidate: ScenarioCandidate) -> ScenarioCandidate:
        self._write_wo28("scenario_candidate", candidate)
        return candidate
    def create_scenario_run(self, run: ScenarioRun) -> ScenarioRun:
        self._write_wo28("scenario_run", run)
        return run
    def get_scenario_run(self, run_id: str) -> ScenarioRun | None:
        return self._get_wo28("scenario_run", run_id, ScenarioRun)
    def update_scenario_run(self, run: ScenarioRun) -> ScenarioRun:
        self._write_wo28("scenario_run", run)
        return run
    def list_scenario_runs(self, org_id: str, environment_id: str = "") -> list[ScenarioRun]:
        return self._list_wo28("scenario_run", org_id, environment_id, ScenarioRun)
    def create_readiness_policy(self, policy: ReadinessPolicy) -> ReadinessPolicy:
        self._write_wo28("readiness_policy", policy)
        return policy
    def get_readiness_policy(self, policy_id: str) -> ReadinessPolicy | None:
        return self._get_wo28("readiness_policy", policy_id, ReadinessPolicy)
    def list_readiness_policies(self, org_id: str, environment_id: str = "") -> list[ReadinessPolicy]:
        return self._list_wo28("readiness_policy", org_id, environment_id, ReadinessPolicy)
    def update_readiness_policy(self, policy: ReadinessPolicy) -> ReadinessPolicy:
        self._write_wo28("readiness_policy", policy)
        return policy
    def create_readiness_check(self, check: ReadinessCheck) -> ReadinessCheck:
        self._write_wo28("readiness_check", check)
        return check
    def get_readiness_check(self, check_id: str) -> ReadinessCheck | None:
        return self._get_wo28("readiness_check", check_id, ReadinessCheck)
    def list_readiness_checks(self, org_id: str, environment_id: str = "") -> list[ReadinessCheck]:
        return self._list_wo28("readiness_check", org_id, environment_id, ReadinessCheck)
    def create_release_gate_result(self, result: ReleaseGateResult) -> ReleaseGateResult:
        self._write_wo28("release_gate_result", result)
        return result
    def get_release_gate_result(self, result_id: str) -> ReleaseGateResult | None:
        return self._get_wo28("release_gate_result", result_id, ReleaseGateResult)

    # ── Integrations & Capture (Phase E) ──
    def create_ai_system(self, system: AISystem) -> AISystem: return system
    def get_ai_system(self, system_id: str) -> AISystem | None: return None
    def list_ai_systems(self, org_id: str, environment_id: str = "") -> list[AISystem]: return []
    def update_ai_system(self, system: AISystem) -> AISystem: return system
    def create_capture_connector(self, conn: CaptureConnector) -> CaptureConnector: return conn
    def get_capture_connector(self, conn_id: str) -> CaptureConnector | None: return None
    def list_capture_connectors(self, ai_system_id: str) -> list[CaptureConnector]: return []
    def update_capture_connector(self, conn: CaptureConnector) -> CaptureConnector: return conn
    def create_field_handling_rule(self, rule: FieldHandlingRule) -> FieldHandlingRule: return rule
    def list_field_handling_rules(self, ai_system_id: str) -> list[FieldHandlingRule]: return []
    def delete_field_handling_rules(self, ai_system_id: str) -> None: pass
    def create_capture_validation_run(self, run: CaptureValidationRun) -> CaptureValidationRun: return run
    def list_capture_validation_runs(self, ai_system_id: str) -> list[CaptureValidationRun]: return []
    def create_decision_family_candidate(self, candidate: DecisionFamilyCandidate) -> DecisionFamilyCandidate: return candidate
    def list_decision_family_candidates(self, org_id: str, ai_system_id: str = "") -> list[DecisionFamilyCandidate]: return []
    def update_decision_family_candidate(self, candidate: DecisionFamilyCandidate) -> DecisionFamilyCandidate: return candidate
    def create_decision_workflow(self, wf: DecisionWorkflow) -> DecisionWorkflow: return wf
    def get_decision_workflow(self, wf_id: str) -> DecisionWorkflow | None: return None
    def list_decision_workflows(self, org_id: str, environment_id: str = "") -> list[DecisionWorkflow]: return []
    def update_decision_workflow(self, wf: DecisionWorkflow) -> DecisionWorkflow: return wf
    def list_workflow_evidence_sources(self, workflow_id: str) -> list[WorkflowEvidenceSource]: return []
    def save_workflow_evidence_sources(self, workflow_id: str, sources: list[WorkflowEvidenceSource]) -> list[WorkflowEvidenceSource]: return sources


def get_storage() -> StorageBackend:
    """Return the configured storage backend (singleton per process)."""
    if SETTINGS.use_remote_storage:
        return PostgresS3Storage()
    if SETTINGS.storage_profile == "shared_demo":
        return SharedDemoFileStorage()
    return MemoryStorage()
