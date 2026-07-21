"""API data models for the Notary Platform."""

from __future__ import annotations

import dataclasses
import enum
import time
import typing
import uuid
from dataclasses import dataclass, field
from typing import Any, List


class IncidentStatus(str, enum.Enum):
    ingested = "ingested"
    replayed = "replayed"
    mitigated = "mitigated"
    certified = "certified"


T = typing.TypeVar("T")


def _is_dataclass_instance_or_class(obj: Any) -> bool:
    return hasattr(obj, "__dataclass_fields__") or (isinstance(obj, type) and hasattr(obj, "__dataclass_fields__"))


def _is_list_of_dataclasses(annotation: Any) -> bool:
    origin = getattr(annotation, "__origin__", None)
    if origin not in (list, List):
        return False
    args = getattr(annotation, "__args__", ())
    return bool(args and _is_dataclass_instance_or_class(args[0]))


def _dataclass_inner_type(annotation: Any) -> Any:
    args = getattr(annotation, "__args__", ())
    return args[0] if args else None


def _coerce_value(value: Any, annotation: Any) -> Any:
    if value is None:
        return None
    if isinstance(annotation, type) and issubclass(annotation, enum.Enum):
        return annotation(value)
    if _is_dataclass_instance_or_class(annotation):
        return annotation.from_dict(value)
    if _is_list_of_dataclasses(annotation):
        inner = _dataclass_inner_type(annotation)
        return [inner.from_dict(v) for v in value] if inner is not None else value
    return value


def _dataclass_from_dict(cls: type[T], d: dict[str, Any]) -> T:
    import dataclasses

    type_hints = typing.get_type_hints(cls)
    kwargs: dict[str, Any] = {}
    for fld in dataclasses.fields(cls):  # type: ignore[arg-type]
        if fld.name in d:
            kwargs[fld.name] = _coerce_value(d[fld.name], type_hints.get(fld.name, fld.type))
    return cls(**kwargs)


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
    "input": EventKind.human_action,
    "rule": EventKind.policy_check,
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


# ---------------------------------------------------------------------------
# WO-28 — Durable product objects for the active product horizon
# ---------------------------------------------------------------------------


@dataclass
class EvidenceArtifact:
    """Immutable evidence reference for a snapshot, replay, mutation, proof, or scenario run."""

    id: str
    org_id: str = "demo-org"
    incident_id: str = ""
    verification_record_id: str = ""
    kind: str = "snapshot"  # snapshot | replay_result | mutation_result | certificate | scenario_run | readiness
    reference: str = ""  # storage reference or inline id
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "incident_id": self.incident_id,
            "verification_record_id": self.verification_record_id,
            "kind": self.kind,
            "reference": self.reference,
            "payload": self.payload,
            "created_at": self.created_at,
        }


@dataclass
class KnownLimitation:
    """Structured limitation for a replay, mutation, proof, or scenario run."""

    code: str
    severity: str  # NON_DETERMINISTIC_CORE | NON_DETERMINISTIC_SIDE_EFFECT | BYOK | MISSING_KEY | INTEGRITY
    message: str
    subject: str = ""  # component or source system id
    certificate_blocking: bool = False
    remediation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "subject": self.subject,
            "certificate_blocking": self.certificate_blocking,
            "remediation": self.remediation,
        }


@dataclass
class ReplayRun:
    """One replay attempt for a Verification Record."""

    id: str
    org_id: str = "demo-org"
    verification_record_id: str = ""
    incident_id: str = ""
    status: str = "not_started"  # not_started | replayed | incomplete | error | escalation_required
    replay_method: str = "cassette"  # cassette | sandbox | mixed
    original_decision: str = ""
    replayed_decision: str = ""
    missing_calls: list[str] = field(default_factory=list)
    deterministic_controls: dict[str, Any] = field(default_factory=dict)
    known_limitations: list[KnownLimitation] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "verification_record_id": self.verification_record_id,
            "incident_id": self.incident_id,
            "status": self.status,
            "replay_method": self.replay_method,
            "original_decision": self.original_decision,
            "replayed_decision": self.replayed_decision,
            "missing_calls": self.missing_calls,
            "deterministic_controls": self.deterministic_controls,
            "known_limitations": [lim.to_dict() for lim in self.known_limitations],
            "evidence_refs": self.evidence_refs,
            "created_at": self.created_at,
        }


@dataclass
class ReplayExecutionEvent:
    """One step in a replay execution trace."""

    step: str
    source: str
    expected: str
    actual: str
    status: str
    sequence: int = 0
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "source": self.source,
            "expected": self.expected,
            "actual": self.actual,
            "status": self.status,
            "sequence": self.sequence,
            "timestamp": self.timestamp,
        }


@dataclass
class FixReference:
    """Reference to a fix applied to an agent for mutation testing."""

    id: str
    config: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    agent_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "config": self.config,
            "description": self.description,
            "agent_id": self.agent_id,
        }


@dataclass
class MutationTest:
    """One fix-verification attempt for a reproduced record."""

    id: str
    org_id: str = "demo-org"
    verification_record_id: str = ""
    incident_id: str = ""
    replay_run_id: str = ""
    fix_reference: FixReference = field(default_factory=lambda: FixReference(id=""))
    expected_outcome: str = ""
    label_id: str = ""
    original_decision: str = ""
    mutated_decision: str = ""
    decision_changed: bool = False
    verdict: str = "not_started"  # not_started | verified | not_verified | error
    replay_method: str = "cassette"
    known_limitations: list[KnownLimitation] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "verification_record_id": self.verification_record_id,
            "incident_id": self.incident_id,
            "replay_run_id": self.replay_run_id,
            "fix_reference": self.fix_reference.to_dict(),
            "expected_outcome": self.expected_outcome,
            "label_id": self.label_id,
            "original_decision": self.original_decision,
            "mutated_decision": self.mutated_decision,
            "decision_changed": self.decision_changed,
            "verdict": self.verdict,
            "replay_method": self.replay_method,
            "known_limitations": [lim.to_dict() for lim in self.known_limitations],
            "evidence_refs": self.evidence_refs,
            "created_at": self.created_at,
        }


@dataclass
class ProofClaim:
    """Bounded statement of what a proof certifies."""

    id: str
    org_id: str = "demo-org"
    scenario_id: str = ""
    scenario_run_id: str = ""
    agent_version: str = ""
    fix_reference: FixReference = field(default_factory=lambda: FixReference(id=""))
    release_context: str = ""
    expected_outcome: str = ""
    label_id: str = ""
    replay_method: str = "cassette"
    known_limitations: list[KnownLimitation] = field(default_factory=list)
    scope_disclaimer: str = "This proof applies to the tested scenario conditions and does not certify general AI safety."
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "scenario_id": self.scenario_id,
            "scenario_run_id": self.scenario_run_id,
            "agent_version": self.agent_version,
            "fix_reference": self.fix_reference.to_dict(),
            "release_context": self.release_context,
            "expected_outcome": self.expected_outcome,
            "label_id": self.label_id,
            "replay_method": self.replay_method,
            "known_limitations": [lim.to_dict() for lim in self.known_limitations],
            "scope_disclaimer": self.scope_disclaimer,
            "created_at": self.created_at,
        }


@dataclass
class ProofCertificate:
    """Signed proof artifact (Proof of Mitigation or Proof of Readiness)."""

    id: str
    org_id: str = "demo-org"
    certificate_id: str = ""
    certificate_type: str = "proof_of_mitigation"  # proof_of_mitigation | proof_of_readiness
    subject_id: str = ""  # incident_id or readiness_check_id
    claim: ProofClaim = field(default_factory=lambda: ProofClaim(id=""))
    issued_at: str = ""
    expires_at: str = ""
    signature: str = ""
    signed_payload: dict[str, Any] = field(default_factory=dict)
    integrity_status: str = "unverified"
    known_limitations: list[KnownLimitation] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "certificate_id": self.certificate_id,
            "certificate_type": self.certificate_type,
            "subject_id": self.subject_id,
            "claim": self.claim.to_dict(),
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "signature": self.signature,
            "signed_payload": self.signed_payload,
            "integrity_status": self.integrity_status,
            "known_limitations": [lim.to_dict() for lim in self.known_limitations],
            "created_at": self.created_at,
        }


@dataclass
class Scenario:
    """Promoted reusable test case derived from a reproduced Verification Record or ScenarioCandidate."""

    id: str
    org_id: str = "demo-org"
    environment_id: str = "env:demo"
    source_vr_id: str = ""
    source_incident_id: str = ""
    business_title: str = ""
    source_system_id: str = ""
    expected_outcome: str = ""
    approved_label_id: str = ""
    replayability: str = "unknown"
    replayability_score: float = 0.0
    required_sandbox_id: str = ""
    evidence_refs: list[str] = field(default_factory=list)
    state: str = "active"  # active | retired
    last_run_status: str = "not_started"
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "environment_id": self.environment_id,
            "source_vr_id": self.source_vr_id,
            "source_incident_id": self.source_incident_id,
            "business_title": self.business_title,
            "source_system_id": self.source_system_id,
            "expected_outcome": self.expected_outcome,
            "approved_label_id": self.approved_label_id,
            "replayability": self.replayability,
            "replayability_score": self.replayability_score,
            "required_sandbox_id": self.required_sandbox_id,
            "evidence_refs": self.evidence_refs,
            "state": self.state,
            "last_run_status": self.last_run_status,
            "created_at": self.created_at,
        }


@dataclass
class ScenarioRunResult:
    """Per-scenario result within a ScenarioRun."""

    scenario_id: str
    status: str = "not_started"  # passed | failed | errored | escalation_required | non_deterministic
    expected_decision: str = ""
    actual_decision: str = ""
    reason: str = ""
    evidence_ref: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "status": self.status,
            "expected_decision": self.expected_decision,
            "actual_decision": self.actual_decision,
            "reason": self.reason,
            "evidence_ref": self.evidence_ref,
        }


@dataclass
class ScenarioRun:
    """Run of one or more Scenarios against an agent version."""

    id: str
    org_id: str = "demo-org"
    environment_id: str = "env:demo"
    agent_version: str = ""
    scenario_ids: list[str] = field(default_factory=list)
    status: str = "not_started"  # not_started | running | completed | error
    results: list[ScenarioRunResult] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "environment_id": self.environment_id,
            "agent_version": self.agent_version,
            "scenario_ids": self.scenario_ids,
            "status": self.status,
            "results": [r.to_dict() for r in self.results],
            "summary": self.summary,
            "created_at": self.created_at,
        }


@dataclass
class ReadinessPolicy:
    """Release policy containing required Scenarios and pass condition."""

    id: str
    org_id: str = "demo-org"
    environment_id: str = "env:demo"
    name: str = ""
    required_scenario_ids: list[str] = field(default_factory=list)
    pass_condition: str = "all_pass"  # all_pass | majority
    enabled: bool = True
    version: int = 1
    change_history: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "environment_id": self.environment_id,
            "name": self.name,
            "required_scenario_ids": self.required_scenario_ids,
            "pass_condition": self.pass_condition,
            "enabled": self.enabled,
            "version": self.version,
            "change_history": self.change_history,
            "created_at": self.created_at,
        }


@dataclass
class ReadinessCheck:
    """Evaluation of an agent version against a Readiness Policy."""

    id: str
    org_id: str = "demo-org"
    environment_id: str = "env:demo"
    policy_id: str = ""
    agent_version: str = ""
    scenario_run_id: str = ""
    verdict: str = "not_started"  # not_started | passed | failed | error
    failing_scenarios: list[str] = field(default_factory=list)
    errored_scenarios: list[str] = field(default_factory=list)
    certificate_id: str = ""
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "environment_id": self.environment_id,
            "policy_id": self.policy_id,
            "agent_version": self.agent_version,
            "scenario_run_id": self.scenario_run_id,
            "verdict": self.verdict,
            "failing_scenarios": self.failing_scenarios,
            "errored_scenarios": self.errored_scenarios,
            "certificate_id": self.certificate_id,
            "created_at": self.created_at,
        }


@dataclass
class ReleaseGateResult:
    """CI/CD-facing result for a release gate check."""

    id: str
    org_id: str = "demo-org"
    readiness_check_id: str = ""
    status: str = "not_started"  # pass | fail | error
    failing_scenarios: list[str] = field(default_factory=list)
    errored_scenarios: list[str] = field(default_factory=list)
    certificate_id: str = ""
    scenario_run_id: str = ""
    scenario_results: list[dict[str, Any]] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    error_code: str = ""
    retry_guidance: str = ""
    ci_cd_command: str = ""
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "readiness_check_id": self.readiness_check_id,
            "status": self.status,
            "failing_scenarios": self.failing_scenarios,
            "errored_scenarios": self.errored_scenarios,
            "certificate_id": self.certificate_id,
            "scenario_run_id": self.scenario_run_id,
            "scenario_results": self.scenario_results,
            "evidence_refs": self.evidence_refs,
            "error_code": self.error_code,
            "retry_guidance": self.retry_guidance,
            "ci_cd_command": self.ci_cd_command,
            "created_at": self.created_at,
        }


@dataclass
class ActionEligibility:
    """Server-side eligibility check result for a product action."""

    action: str
    eligible: bool = False
    reason: str = ""
    blocking_limitations: list[KnownLimitation] = field(default_factory=list)
    next_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "eligible": self.eligible,
            "reason": self.reason,
            "blocking_limitations": [lim.to_dict() for lim in self.blocking_limitations],
            "next_action": self.next_action,
        }


# ---------------------------------------------------------------------------
# Integrations & Capture models (Phase E)
# ---------------------------------------------------------------------------


@dataclass
class AISystem:
    id: str
    org_id: str
    environment_id: str
    name: str
    system_type: str = "agent"
    deployment_version: str = ""
    decision_endpoint: str = ""
    external_caller: bool = False
    risk_classification: str = ""
    business_owner: str = ""
    technical_owner: str = ""
    status: str = "draft"
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in dataclasses.fields(self)}


@dataclass
class CaptureConnector:
    id: str
    ai_system_id: str
    org_id: str
    connector_type: str
    name: str = ""
    status: str = "not_configured"
    config_json: str = "{}"
    last_tested_at: str = ""
    error_message: str = ""
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in dataclasses.fields(self)}


@dataclass
class FieldHandlingRule:
    id: str
    ai_system_id: str
    field_pattern: str
    action: str = "store"
    retention_days: int = 365
    sensitive: bool = False
    use_for_replay: bool = True
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in dataclasses.fields(self)}


@dataclass
class CoverageAssessment:
    decision_detected: bool = False
    input_captured: bool = False
    model_version_captured: bool = False
    prompt_captured: bool = False
    tool_responses_available: bool = False
    final_decision_captured: bool = False
    root_hash_valid: bool = False
    cassette_material_available: bool = False
    expected_outcome_source_available: bool = False
    replay_readiness: str = "insufficient_context"
    assessment: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in dataclasses.fields(self)}


@dataclass
class CaptureValidationRun:
    id: str
    ai_system_id: str
    org_id: str
    status: str = "pending"
    checks_json: str = "{}"
    coverage_json: str = "{}"
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in dataclasses.fields(self)}


@dataclass
class DecisionFamilyCandidate:
    id: str
    org_id: str
    ai_system_id: str
    pattern_name: str
    decision_count: int = 0
    confirmed: bool = False
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in dataclasses.fields(self)}


# Attach generic from_dict to all dataclasses for storage reconstruction.
_DATACLASS_MODELS = [
    Organization,
    Environment,
    Agent,
    SystemConnection,
    CapturePolicy,
    HomeStats,
    AIExecutionEvent,
    VerificationRecord,
    HumanLabel,
    APIKey,
    ScenarioCandidate,
    AuditEvent,
    EvidenceArtifact,
    KnownLimitation,
    ReplayRun,
    FixReference,
    MutationTest,
    ProofClaim,
    ProofCertificate,
    Scenario,
    ScenarioRunResult,
    ScenarioRun,
    ReadinessPolicy,
    ReadinessCheck,
    ReleaseGateResult,
    ActionEligibility,
    AISystem,
    CaptureConnector,
    FieldHandlingRule,
    CoverageAssessment,
    CaptureValidationRun,
    DecisionFamilyCandidate,
]
for _model_cls in _DATACLASS_MODELS:
    if not hasattr(_model_cls, "from_dict"):
        _model_cls.from_dict = classmethod(_dataclass_from_dict)  # type: ignore[attr-defined]
