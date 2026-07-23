from __future__ import annotations

from typing import Any

from notary_platform.discovery.context import TemporalContextResolver
from notary_platform.discovery.identity import DecisionIdentityResolver
from notary_platform.discovery.models import (
    AdvisorySuggestion,
    DecisionEvidenceRecord,
)
from notary_platform.storage import StorageBackend


class DecisionEvidenceRecordService:
    """Assemble and manage Decision Evidence Records.

    DERs are logical graphs built from resource references and relationship
    references — never copied flattened source data.
    """

    def __init__(self, storage: StorageBackend):
        self._storage = storage
        self._id_resolver = DecisionIdentityResolver(storage)
        self._ctx_resolver = TemporalContextResolver(storage)

    def build(
        self,
        resource_ids: list[str],
        org_id: str,
        decision_time: str | None = None,
        namespace_mappings: dict[str, str] | None = None,
    ) -> DecisionEvidenceRecord:
        identity, method, link_assertions = self._id_resolver.resolve(
            resource_ids,
            org_id,
            namespace_mappings,
        )
        la_ids = [la.id for la in link_assertions]
        environments = {
            resource.environment_id
            for resource_id in resource_ids
            if (resource := self._storage.get_resource(resource_id, org_id)) is not None and resource.environment_id
        }

        der = DecisionEvidenceRecord(
            org_id=org_id,
            environment_id=next(iter(environments)) if len(environments) == 1 else "",
            decision_identity=identity,
            identity_method=method,
            source_resource_ids=resource_ids,
            link_assertion_ids=la_ids,
        )
        created = self._storage.create_decision_evidence_record(der)
        dt = decision_time or created.created_at

        if identity:
            self._ctx_resolver.resolve(created, org_id, decision_time=dt)

        final = self._storage.get_decision_evidence_record(created.id)
        return final or created

    def get(self, der_id: str, org_id: str) -> DecisionEvidenceRecord | None:
        der = self._storage.get_decision_evidence_record(der_id)
        if der is None or der.org_id != org_id:
            return None
        return der

    def list_records(self, org_id: str) -> list[DecisionEvidenceRecord]:
        return self._storage.list_decision_evidence_records(org_id)

    def get_resolution_trace(self, der_id: str, org_id: str) -> dict[str, Any] | None:
        der = self.get(der_id, org_id)
        if der is None:
            return None
        rt = self._storage.get_resolution_trace(der.resolution_trace_id)
        if rt is None:
            return None
        return rt.to_dict()

    def suggest_policy_candidates(
        self,
        workflow_id: str,
        org_id: str,
        basis: str = "inferred",
    ) -> AdvisorySuggestion:
        suggestion = AdvisorySuggestion(
            org_id=org_id,
            suggestion_type="policy_candidate",
            workflow_id=workflow_id,
            content={"workflow_id": workflow_id, "status": "candidate"},
            basis=basis,
            expected_unlock_value="structured policy evaluator",
        )
        return self._storage.create_advisory_suggestion(suggestion)

    def suggest_context_roadmap(
        self,
        workflow_id: str,
        org_id: str,
    ) -> list[AdvisorySuggestion]:
        suggestions = self._storage.list_advisory_suggestions(org_id, workflow_id)
        return [s for s in suggestions if s.suggestion_type in ("context_source_candidate", "unlock_plan")]

    def get_policy_candidates(
        self,
        workflow_id: str,
        org_id: str,
    ) -> list[AdvisorySuggestion]:
        suggestions = self._storage.list_advisory_suggestions(org_id, workflow_id)
        return [s for s in suggestions if s.suggestion_type == "policy_candidate"]
