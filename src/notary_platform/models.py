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
    ) -> None:
        self.event_id = uuid.uuid4().hex
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
    kind: str = "api"  # api | sdk | webhook | sandbox | grc
    status: str = "unknown"  # connected | disconnected | stale | planned
    last_checked: str = ""
    capability: str = ""
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

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
            "created_at": self.created_at,
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
