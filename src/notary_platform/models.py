"""API data models for the Notary Platform."""

from __future__ import annotations

import enum
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, List


class IncidentStatus(str, enum.Enum):
    ingested = "ingested"
    replayed = "replayed"
    mitigated = "mitigated"
    certified = "certified"


class CustodyEvent:
    """An append-only forensic custody event recorded against an incident."""

    def __init__(
        self,
        action: str,
        actor: str = "system",
        detail: str = "",
        timestamp: str | None = None,
        event_id: str | None = None,
    ) -> None:
        self.event_id = event_id or uuid.uuid4().hex
        self.action = action
        self.actor = actor
        self.detail = detail
        self.timestamp = timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "action": self.action,
            "actor": self.actor,
            "detail": self.detail,
            "timestamp": self.timestamp,
        }


class Incident:
    """An incident record stored by the platform."""

    def __init__(
        self,
        incident_id: str,
        org_id: str = "demo-org",
        status: IncidentStatus = IncidentStatus.ingested,
        snapshot_summary: dict[str, Any] | None = None,
        replay_result: dict[str, Any] | None = None,
        mutation_result: dict[str, Any] | None = None,
        certificate: dict[str, Any] | None = None,
    ) -> None:
        self.incident_id = incident_id
        self.org_id = org_id
        self.status = status
        self.snapshot_summary: dict[str, Any] = snapshot_summary or {}
        self.replay_result: dict[str, Any] = replay_result or {}
        self.mutation_result: dict[str, Any] = mutation_result or {}
        self.certificate: dict[str, Any] = certificate or {}
        self.custody: list[CustodyEvent] = []
        self._record_custody("created", detail=f"incident {incident_id} created")

    def _record_custody(self, action: str, actor: str = "system", detail: str = "") -> None:
        self.custody.append(CustodyEvent(action=action, actor=actor, detail=detail))

    def to_dict(self) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "org_id": self.org_id,
            "status": self.status.value,
            "snapshot_summary": self.snapshot_summary,
            "replay_result": self.replay_result,
            "mutation_result": self.mutation_result,
            "certificate": self.certificate,
            "custody": [c.to_dict() for c in self.custody],
        }


class IntegrityValidationResult:
    """Result of verifying a snapshot's integrity."""

    def __init__(self, valid: bool, reason: str = "") -> None:
        self.valid = valid
        self.reason = reason

    def to_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "reason": self.reason}


# ---------------------------------------------------------------------------
# Notary Platform customer-facing domain models (WO-48+)
# ---------------------------------------------------------------------------


@dataclass
class Organization:
    id: str
    name: str
    environments: List[str] = field(default_factory=lambda: ["demo", "staging", "production"])
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "environments": self.environments, "created_at": self.created_at}


@dataclass
class Environment:
    id: str
    name: str
    org_id: str
    kind: str = "demo"  # demo | staging | production
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "org_id": self.org_id, "kind": self.kind, "created_at": self.created_at}


@dataclass
class Agent:
    id: str
    name: str
    org_id: str
    environment_id: str
    risk_tier: str = "standard"
    sdk_status: str = "unknown"  # unknown | connected | stale | not_installed
    sdk_version: str = ""
    last_seen: str = ""
    scenario_count: int = 0
    capture_policy_count: int = 0
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "org_id": self.org_id,
            "environment_id": self.environment_id,
            "risk_tier": self.risk_tier,
            "sdk_status": self.sdk_status,
            "sdk_version": self.sdk_version,
            "last_seen": self.last_seen,
            "scenario_count": self.scenario_count,
            "capture_policy_count": self.capture_policy_count,
            "created_at": self.created_at,
        }


@dataclass
class SystemConnection:
    id: str
    name: str
    org_id: str
    environment_id: str
    kind: str = "api"
    status: str = "unknown"
    last_checked: str = ""
    capability: str = ""
    # Sandbox readiness (WO-77)
    sandbox_supported: bool = False
    sandbox_replay_modes: List[str] = field(default_factory=list)
    auth_status: str = "unknown"
    safety_boundary: str = ""
    fallback: str = ""
    supported_agents: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    # Product surface registry fields (WO-80)
    type: str = "source_system"  # agent_runtime, capture_source, source_system, model_provider, tool_api, sandbox_provider, grc_system, cicd_system
    model_provider: str = ""
    source_system: str = ""
    capture_policies: List[str] = field(default_factory=list)
    linked_vrs: List[str] = field(default_factory=list)
    linked_incidents: List[str] = field(default_factory=list)
    linked_proofs: List[str] = field(default_factory=list)
    linked_scenarios: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    next_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "org_id": self.org_id,
            "environment_id": self.environment_id,
            "kind": self.kind,
            "status": self.status,
            "last_checked": self.last_checked,
            "capability": self.capability,
            "sandbox_supported": self.sandbox_supported,
            "sandbox_replay_modes": self.sandbox_replay_modes,
            "auth_status": self.auth_status,
            "safety_boundary": self.safety_boundary,
            "fallback": self.fallback,
            "supported_agents": self.supported_agents,
            "created_at": self.created_at,
            "type": self.type,
            "model_provider": self.model_provider,
            "source_system": self.source_system,
            "capture_policies": self.capture_policies,
            "linked_vrs": self.linked_vrs,
            "linked_incidents": self.linked_incidents,
            "linked_proofs": self.linked_proofs,
            "linked_scenarios": self.linked_scenarios,
            "limitations": self.limitations,
            "next_action": self.next_action,
        }


@dataclass
class CapturePolicy:
    id: str
    name: str
    org_id: str
    environment_id: str
    agent_id: str = ""
    status: str = "active"  # active | inactive | inherited
    coverage: str = "all"  # all | redacted | omitted
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "org_id": self.org_id,
            "environment_id": self.environment_id,
            "agent_id": self.agent_id,
            "status": self.status,
            "coverage": self.coverage,
            "created_at": self.created_at,
        }


@dataclass
class HomeStats:
    org_id: str
    environment_id: str
    agent_count: int = 0
    system_count: int = 0
    incident_count: int = 0
    replay_ready: int = 0
    fixes_verified: int = 0
    proofs_issued: int = 0
    scenario_count: int = 0
    pending_replay: int = 0
    pending_verification: int = 0
    pending_proof: int = 0
    # Product surface queues (WO-80)
    vrs_total: int = 0
    vrs_replayable: int = 0
    vrs_requires_label: int = 0
    vrs_requires_sandbox: int = 0
    vrs_evidence_only: int = 0
    labels_needing_review: int = 0
    systems_disconnected: int = 0
    systems_sandbox_ready: int = 0
    scenario_candidates: int = 0
    blocked_items: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "org_id": self.org_id,
            "environment_id": self.environment_id,
            "agent_count": self.agent_count,
            "system_count": self.system_count,
            "incident_count": self.incident_count,
            "replay_ready": self.replay_ready,
            "fixes_verified": self.fixes_verified,
            "proofs_issued": self.proofs_issued,
            "scenario_count": self.scenario_count,
            "pending_replay": self.pending_replay,
            "pending_verification": self.pending_verification,
            "pending_proof": self.pending_proof,
            "vrs_total": self.vrs_total,
            "vrs_replayable": self.vrs_replayable,
            "vrs_requires_label": self.vrs_requires_label,
            "vrs_requires_sandbox": self.vrs_requires_sandbox,
            "vrs_evidence_only": self.vrs_evidence_only,
            "labels_needing_review": self.labels_needing_review,
            "systems_disconnected": self.systems_disconnected,
            "systems_sandbox_ready": self.systems_sandbox_ready,
            "scenario_candidates": self.scenario_candidates,
            "blocked_items": self.blocked_items,
        }


# ---------------------------------------------------------------------------
# Phase 2 — Verification Record and AI Execution Event model (WO-69/70)
# ---------------------------------------------------------------------------


class DataSourceType(str, enum.Enum):
    sdk_snapshot = "sdk_snapshot"
    api_submission = "api_submission"
    manual_submission = "manual_submission"
    webhook = "webhook"
    batch_import = "batch_import"
    trace_import = "trace_import"
    provider_adapter = "provider_adapter"
    framework_adapter = "framework_adapter"
    source_system_adapter = "source_system_adapter"
    eval_adapter = "eval_adapter"


class ReplayabilityStatus(str, enum.Enum):
    replayable = "replayable"
    partially_replayable = "partially_replayable"
    evidence_only = "evidence_only"
    missing_context = "missing_context"
    requires_sandbox = "requires_sandbox"
    requires_human_label = "requires_human_label"
    blocked = "blocked"
    unknown = "unknown"


class EventKind(str, enum.Enum):
    model_call = "model_call"
    tool_call = "tool_call"
    api_response = "api_response"
    retrieval = "retrieval"
    policy_check = "policy_check"
    guardrail_check = "guardrail_check"
    human_action = "human_action"
    decision = "decision"
    side_effect = "side_effect"
    evaluation_result = "evaluation_result"
    timestamp = "timestamp"
    rng_seed = "rng_seed"


class DataScope(str, enum.Enum):
    raw = "raw"
    redacted = "redacted"
    hashed = "hashed"
    reference_only = "reference_only"
    omitted = "omitted"


@dataclass
class AIExecutionEvent:
    id: str
    kind: EventKind
    payload: dict
    scope: DataScope = DataScope.raw
    source_system: str = ""
    order: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "payload": {k: str(v)[:200] if isinstance(v, (dict, list)) and len(str(v)) > 200 else v for k, v in self.payload.items()},
            "scope": self.scope.value,
            "source_system": self.source_system,
            "order": self.order,
        }


@dataclass
class VerificationRecord:
    id: str
    org_id: str = "demo-org"
    environment_id: str = "env:demo"
    source_type: DataSourceType = DataSourceType.api_submission
    external_ref: str = ""
    agent_id: str = ""
    business_function: str = ""
    events: List[AIExecutionEvent] = field(default_factory=list)
    root_hash: str = ""
    replayability: ReplayabilityStatus = ReplayabilityStatus.unknown
    replayability_reason: str = ""
    missing_prerequisites: List[str] = field(default_factory=list)
    promoted_to_incident: str = ""
    current_label_id: str = ""
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    is_demo: bool = False
    # WO-78: Determinism contract
    replayability_score: float = 0.0
    non_deterministic_flags: list[dict] = field(default_factory=list)
    defensibility_summary: str = ""
    # WO-80: Product surface registry
    source_system_id: str = ""
    source_record_ref: str = ""
    agent_version: str = ""
    model_provider: str = ""
    model_name: str = ""
    policy_version: str = ""
    capture_policy_id: str = ""
    expected_outcome: str = ""
    label_source: str = ""
    sandbox_readiness: dict = field(default_factory=dict)
    next_action: str = ""
    suggested_labels: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "environment_id": self.environment_id,
            "source_type": self.source_type.value,
            "external_ref": self.external_ref,
            "agent_id": self.agent_id,
            "business_function": self.business_function,
            "events": [e.to_dict() for e in self.events],
            "root_hash": self.root_hash,
            "replayability": self.replayability.value,
            "replayability_reason": self.replayability_reason,
            "missing_prerequisites": self.missing_prerequisites,
            "promoted_to_incident": self.promoted_to_incident,
            "current_label_id": self.current_label_id,
            "created_at": self.created_at,
            "is_demo": self.is_demo,
            "replayability_score": self.replayability_score,
            "non_deterministic_flags": self.non_deterministic_flags,
            "defensibility_summary": self.defensibility_summary,
            "source_system_id": self.source_system_id,
            "source_record_ref": self.source_record_ref,
            "agent_version": self.agent_version,
            "model_provider": self.model_provider,
            "model_name": self.model_name,
            "policy_version": self.policy_version,
            "capture_policy_id": self.capture_policy_id,
            "expected_outcome": self.expected_outcome,
            "label_source": self.label_source,
            "sandbox_readiness": self.sandbox_readiness,
            "next_action": self.next_action,
            "suggested_labels": self.suggested_labels,
        }



# SDK element kind → AIExecutionEvent kind mapping
_SDK_TO_EVENT_MAP = {
    "llm": EventKind.model_call,
    "http": EventKind.api_response,
    "decision": EventKind.decision,
    "rng_seed": EventKind.rng_seed,
    "timestamp": EventKind.timestamp,
    "tool": EventKind.tool_call,
    "retrieval": EventKind.retrieval,
    "guardrail": EventKind.guardrail_check,
    "human": EventKind.human_action,
}


def sdk_element_to_event(element: dict, order: int = 0) -> AIExecutionEvent:
    kind_str = element.get("kind", "unknown")
    kind = _SDK_TO_EVENT_MAP.get(kind_str, EventKind.model_call)
    payload = element.get("payload", {})
    if kind_str == "http" and isinstance(payload, dict) and "request" in payload:
        kind = EventKind.tool_call
    return AIExecutionEvent(
        id=uuid.uuid4().hex,
        kind=kind,
        payload=payload,
        order=order,
    )


# ---------------------------------------------------------------------------
# Phase 2 — Human Label (WO-62)
# ---------------------------------------------------------------------------


@dataclass
class HumanLabel:
    id: str
    verification_record_id: str = ""
    expected_outcome: str = ""
    reviewer: str = ""
    role: str = ""
    reason: str = ""
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    status: str = "active"  # active | superseded | revoked
    version: int = 1
    superseded_by: str = ""
    # WO-79: Label provenance
    category: str = "incident_type"
    suggested_by: str = ""
    suggested_confidence: float = 0.0
    approval_reason: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "verification_record_id": self.verification_record_id,
            "expected_outcome": self.expected_outcome,
            "reviewer": self.reviewer,
            "role": self.role,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "status": self.status,
            "version": self.version,
            "superseded_by": self.superseded_by,
            "category": self.category,
            "suggested_by": self.suggested_by,
            "suggested_confidence": self.suggested_confidence,
            "approval_reason": self.approval_reason,
        }


# ---------------------------------------------------------------------------
# Phase 2 — API Keys, Audit Log (WO-66)
# ---------------------------------------------------------------------------


@dataclass
class APIKey:
    id: str
    org_id: str = "demo-org"
    key_type: str = "api"  # api | sdk
    key_hash: str = ""
    label: str = ""
    scopes: List[str] = field(default_factory=lambda: ["read"])
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    last_used: str = ""
    revoked: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "key_type": self.key_type,
            "label": self.label,
            "scopes": self.scopes,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "revoked": self.revoked,
        }


@dataclass
class ScenarioCandidate:
    id: str
    org_id: str = "demo-org"
    environment_id: str = "env:demo"
    source_vr_id: str = ""
    source_incident_id: str = ""
    business_title: str = ""
    source_system_id: str = ""
    approved_label_id: str = ""
    replayability: str = "unknown"
    replayability_score: float = 0.0
    required_sandbox_id: str = ""
    last_run_status: str = "not_started"
    release_gate_ids: List[str] = field(default_factory=list)
    next_action: str = ""
    state: str = "candidate"  # candidate | ready | blocked
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "environment_id": self.environment_id,
            "source_vr_id": self.source_vr_id,
            "source_incident_id": self.source_incident_id,
            "business_title": self.business_title,
            "source_system_id": self.source_system_id,
            "approved_label_id": self.approved_label_id,
            "replayability": self.replayability,
            "replayability_score": self.replayability_score,
            "required_sandbox_id": self.required_sandbox_id,
            "last_run_status": self.last_run_status,
            "release_gate_ids": self.release_gate_ids,
            "next_action": self.next_action,
            "state": self.state,
            "created_at": self.created_at,
        }


@dataclass
class AuditEvent:
    id: str
    org_id: str = "demo-org"
    action: str = ""
    actor: str = "system"
    detail: str = ""
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "action": self.action,
            "actor": self.actor,
            "detail": self.detail,
            "timestamp": self.timestamp,
        }
