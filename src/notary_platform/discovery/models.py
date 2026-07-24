"""Domain models for DEP discovery — providers, resources, conflicts, and ingestion receipts."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ProviderRegistration:
    provider_id: str

    @property
    def id(self) -> str:
        return self.provider_id

    @id.setter
    def id(self, value: str) -> None:
        self.provider_id = value

    org_id: str
    name: str
    provider_type: str  # sdk, platform, trace_system, connector, manual
    contact: str = ""
    public_key: str = ""
    asserted_capabilities: list[str] = field(default_factory=list)
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "org_id": self.org_id,
            "name": self.name,
            "provider_type": self.provider_type,
            "contact": self.contact,
            "public_key": self.public_key,
            "asserted_capabilities": self.asserted_capabilities.copy(),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ProviderRegistration:
        return cls(
            provider_id=d.get("provider_id", ""),
            org_id=d.get("org_id", "demo-org"),
            name=d.get("name", ""),
            provider_type=d.get("provider_type", ""),
            contact=d.get("contact", ""),
            public_key=d.get("public_key", ""),
            asserted_capabilities=list(d.get("asserted_capabilities", [])),
            created_at=d.get("created_at", ""),
        )


@dataclass
class DecisionEvidenceResource:
    resource_id: str

    @property
    def id(self) -> str:
        return self.resource_id

    @id.setter
    def id(self, value: str) -> None:
        self.resource_id = value

    org_id: str
    envelope_id: str
    resource_type: str
    provider_id: str
    digest_algorithm: str
    digest_value: str
    payload_ref: str
    environment_id: str = ""
    provenance_collected_at: str = ""
    provenance_source_ref: str = ""
    version: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "org_id": self.org_id,
            "environment_id": self.environment_id,
            "envelope_id": self.envelope_id,
            "resource_type": self.resource_type,
            "provider_id": self.provider_id,
            "digest_algorithm": self.digest_algorithm,
            "digest_value": self.digest_value,
            "payload_ref": self.payload_ref,
            "provenance_collected_at": self.provenance_collected_at,
            "provenance_source_ref": self.provenance_source_ref,
            "version": self.version,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DecisionEvidenceResource:
        return cls(
            resource_id=d.get("resource_id", ""),
            org_id=d.get("org_id", "demo-org"),
            environment_id=d.get("environment_id", ""),
            envelope_id=d.get("envelope_id", ""),
            resource_type=d.get("resource_type", ""),
            provider_id=d.get("provider_id", ""),
            digest_algorithm=d.get("digest_algorithm", ""),
            digest_value=d.get("digest_value", ""),
            payload_ref=d.get("payload_ref", ""),
            provenance_collected_at=d.get("provenance_collected_at", ""),
            provenance_source_ref=d.get("provenance_source_ref", ""),
            version=d.get("version", ""),
            created_at=d.get("created_at", ""),
        )


@dataclass
class IntegrityConflict:
    conflict_id: str

    @property
    def id(self) -> str:
        return self.conflict_id

    @id.setter
    def id(self, value: str) -> None:
        self.conflict_id = value

    org_id: str
    resource_id: str
    provider_id: str
    existing_digest: str
    conflicting_digest: str
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.conflict_id:
            self.conflict_id = f"con-{uuid.uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "org_id": self.org_id,
            "resource_id": self.resource_id,
            "provider_id": self.provider_id,
            "existing_digest": self.existing_digest,
            "conflicting_digest": self.conflicting_digest,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> IntegrityConflict:
        return cls(
            conflict_id=d.get("conflict_id", ""),
            org_id=d.get("org_id", "demo-org"),
            resource_id=d.get("resource_id", ""),
            provider_id=d.get("provider_id", ""),
            existing_digest=d.get("existing_digest", ""),
            conflicting_digest=d.get("conflicting_digest", ""),
            created_at=d.get("created_at", ""),
        )


class IngestionResultStatus:
    ACCEPTED = "accepted"
    DUPLICATE = "duplicate"
    REJECTED = "rejected"
    QUARANTINED = "quarantined"


@dataclass
class IngestionReceipt:
    resource_id: str
    status: str  # accepted | duplicate | rejected | quarantined
    envelope_id: str = ""
    digest_value: str = ""
    conflict_id: str = ""
    errors: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "status": self.status,
            "envelope_id": self.envelope_id,
            "digest_value": self.digest_value,
            "conflict_id": self.conflict_id,
            "errors": self.errors.copy(),
        }


# ── WP-050: Identity & Context ──


@dataclass
class LinkAssertion:
    id: str = ""
    org_id: str = ""
    source_resource_id: str = ""
    target_resource_id: str = ""
    relationship: str = ""  # governed_by_policy, expected_outcome, guarded_by, etc.
    basis: str = ""  # exact_id, dep_relationship, namespace, composite_key, human_confirmed, similarity
    status: str = "inferred"  # inferred | confirmed | rejected
    created_by: str = ""
    created_at: str = ""
    confirmed_at: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            object.__setattr__(self, "id", f"la-{uuid.uuid4().hex[:12]}")
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "source_resource_id": self.source_resource_id,
            "target_resource_id": self.target_resource_id,
            "relationship": self.relationship,
            "basis": self.basis,
            "status": self.status,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "confirmed_at": self.confirmed_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> LinkAssertion:
        return cls(
            id=d.get("id", f"la-{uuid.uuid4().hex[:12]}"),
            org_id=d.get("org_id", ""),
            source_resource_id=d.get("source_resource_id", ""),
            target_resource_id=d.get("target_resource_id", ""),
            relationship=d.get("relationship", ""),
            basis=d.get("basis", "inferred"),
            status=d.get("status", "inferred"),
            created_by=d.get("created_by", ""),
            created_at=d.get("created_at", ""),
            confirmed_at=d.get("confirmed_at", ""),
        )


@dataclass
class ContextBinding:
    id: str = ""
    org_id: str = ""
    environment_id: str = ""
    subject_scope: str = ""  # decision_family, workflow, agent, resource_type
    subject_selector: str = ""  # e.g., "lending/underwriting", specific resource type
    binding_type: str = ""  # governed_by_policy, expected_outcome, guarded_by, evidence_required_by, executed_by_deployment
    artifact_ref: str = ""  # reference to the context artifact (policy doc, rule, etc.)
    effective_from: str = ""
    effective_until: str = ""  # empty = no end
    authority: str = "customer_confirmed"  # customer_confirmed, provider_declared, inferred
    superseded_by: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            object.__setattr__(self, "id", f"cb-{uuid.uuid4().hex[:12]}")
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "environment_id": self.environment_id,
            "subject_scope": self.subject_scope,
            "subject_selector": self.subject_selector,
            "binding_type": self.binding_type,
            "artifact_ref": self.artifact_ref,
            "effective_from": self.effective_from,
            "effective_until": self.effective_until,
            "authority": self.authority,
            "superseded_by": self.superseded_by,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ContextBinding:
        return cls(
            id=d.get("id", f"cb-{uuid.uuid4().hex[:12]}"),
            org_id=d.get("org_id", ""),
            environment_id=d.get("environment_id", ""),
            subject_scope=d.get("subject_scope", ""),
            subject_selector=d.get("subject_selector", ""),
            binding_type=d.get("binding_type", ""),
            artifact_ref=d.get("artifact_ref", ""),
            effective_from=d.get("effective_from", ""),
            effective_until=d.get("effective_until", ""),
            authority=d.get("authority", "customer_confirmed"),
            superseded_by=d.get("superseded_by", ""),
            created_at=d.get("created_at", ""),
        )


@dataclass
class ContextConflict:
    id: str = ""
    org_id: str = ""
    der_id: str = ""
    field_or_binding: str = ""
    binding_a_id: str = ""
    binding_b_id: str = ""
    authority_a: str = ""
    authority_b: str = ""
    resolution: str = ""  # "" | resolved_use_a | resolved_use_b | resolved_superseded
    resolved_by: str = ""
    resolved_at: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            object.__setattr__(self, "id", f"cc-{uuid.uuid4().hex[:12]}")
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "der_id": self.der_id,
            "field_or_binding": self.field_or_binding,
            "binding_a_id": self.binding_a_id,
            "binding_b_id": self.binding_b_id,
            "authority_a": self.authority_a,
            "authority_b": self.authority_b,
            "resolution": self.resolution,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ContextConflict:
        return cls(
            id=d.get("id", f"cc-{uuid.uuid4().hex[:12]}"),
            org_id=d.get("org_id", ""),
            der_id=d.get("der_id", ""),
            field_or_binding=d.get("field_or_binding", ""),
            binding_a_id=d.get("binding_a_id", ""),
            binding_b_id=d.get("binding_b_id", ""),
            authority_a=d.get("authority_a", ""),
            authority_b=d.get("authority_b", ""),
            resolution=d.get("resolution", ""),
            resolved_by=d.get("resolved_by", ""),
            resolved_at=d.get("resolved_at", ""),
            created_at=d.get("created_at", ""),
        )


@dataclass
class ResolutionTrace:
    id: str = ""
    der_id: str = ""
    org_id: str = ""
    included_bindings: list[str] = field(default_factory=list)
    excluded_bindings: list[str] = field(default_factory=list)
    superseded_bindings: list[str] = field(default_factory=list)
    missing_artifacts: list[str] = field(default_factory=list)
    stale_artifacts: list[str] = field(default_factory=list)
    redacted_artifacts: list[str] = field(default_factory=list)
    conflicted_bindings: list[str] = field(default_factory=list)
    reasons: dict[str, str] = field(default_factory=dict)
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            object.__setattr__(self, "id", f"rt-{uuid.uuid4().hex[:12]}")
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "der_id": self.der_id,
            "org_id": self.org_id,
            "included_bindings": list(self.included_bindings),
            "excluded_bindings": list(self.excluded_bindings),
            "superseded_bindings": list(self.superseded_bindings),
            "missing_artifacts": list(self.missing_artifacts),
            "stale_artifacts": list(self.stale_artifacts),
            "redacted_artifacts": list(self.redacted_artifacts),
            "conflicted_bindings": list(self.conflicted_bindings),
            "reasons": dict(self.reasons),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ResolutionTrace:
        return cls(
            id=d.get("id", f"rt-{uuid.uuid4().hex[:12]}"),
            der_id=d.get("der_id", ""),
            org_id=d.get("org_id", ""),
            included_bindings=list(d.get("included_bindings", [])),
            excluded_bindings=list(d.get("excluded_bindings", [])),
            superseded_bindings=list(d.get("superseded_bindings", [])),
            missing_artifacts=list(d.get("missing_artifacts", [])),
            stale_artifacts=list(d.get("stale_artifacts", [])),
            redacted_artifacts=list(d.get("redacted_artifacts", [])),
            conflicted_bindings=list(d.get("conflicted_bindings", [])),
            reasons=d.get("reasons", {}),
            created_at=d.get("created_at", ""),
        )


@dataclass
class DecisionEvidenceRecord:
    id: str = ""
    org_id: str = ""
    environment_id: str = ""
    decision_identity: str = ""  # the resolved decision identifier
    identity_method: str = ""  # exact_id, dep_relationship, namespace, composite_key, link_assertion, similarity
    source_resource_ids: list[str] = field(default_factory=list)
    context_binding_ids: list[str] = field(default_factory=list)
    link_assertion_ids: list[str] = field(default_factory=list)
    resolution_trace_id: str = ""
    evidence_level: str = ""
    enriched: bool = False
    version: int = 1
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            object.__setattr__(self, "id", f"der-{uuid.uuid4().hex[:12]}")
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "environment_id": self.environment_id,
            "decision_identity": self.decision_identity,
            "identity_method": self.identity_method,
            "source_resource_ids": list(self.source_resource_ids),
            "context_binding_ids": list(self.context_binding_ids),
            "link_assertion_ids": list(self.link_assertion_ids),
            "resolution_trace_id": self.resolution_trace_id,
            "evidence_level": self.evidence_level,
            "enriched": self.enriched,
            "version": self.version,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DecisionEvidenceRecord:
        return cls(
            id=d.get("id", f"der-{uuid.uuid4().hex[:12]}"),
            org_id=d.get("org_id", ""),
            environment_id=d.get("environment_id", ""),
            decision_identity=d.get("decision_identity", ""),
            identity_method=d.get("identity_method", "exact_id"),
            source_resource_ids=list(d.get("source_resource_ids", [])),
            context_binding_ids=list(d.get("context_binding_ids", [])),
            link_assertion_ids=list(d.get("link_assertion_ids", [])),
            resolution_trace_id=d.get("resolution_trace_id", ""),
            evidence_level=d.get("evidence_level", ""),
            enriched=d.get("enriched", False),
            version=d.get("version", 1),
            created_at=d.get("created_at", ""),
        )


@dataclass
class AdvisorySuggestion:
    id: str = ""
    org_id: str = ""
    suggestion_type: str = ""  # policy_candidate, context_source_candidate, unlock_plan, link_hypothesis
    workflow_id: str = ""
    content: dict[str, Any] = field(default_factory=dict)
    basis: str = ""
    expected_unlock_value: str = ""
    status: str = "inferred"  # inferred | confirmed | rejected
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            object.__setattr__(self, "id", f"as-{uuid.uuid4().hex[:12]}")
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "suggestion_type": self.suggestion_type,
            "workflow_id": self.workflow_id,
            "content": dict(self.content),
            "basis": self.basis,
            "expected_unlock_value": self.expected_unlock_value,
            "status": self.status,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AdvisorySuggestion:
        return cls(
            id=d.get("id", f"as-{uuid.uuid4().hex[:12]}"),
            org_id=d.get("org_id", ""),
            suggestion_type=d.get("suggestion_type", ""),
            workflow_id=d.get("workflow_id", ""),
            content=d.get("content", {}),
            basis=d.get("basis", ""),
            expected_unlock_value=d.get("expected_unlock_value", ""),
            status=d.get("status", "inferred"),
            created_at=d.get("created_at", ""),
        )
