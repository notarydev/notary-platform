from __future__ import annotations

from notary_platform.discovery.models import (
    LinkAssertion,
)
from notary_platform.storage import StorageBackend


class DecisionIdentityResolver:
    """Resolve decision identity from source records and link assertions.

    Precedence (roadmap §WP-050):
        1. Exact decision ID from a confirmed mapping.
        2. Explicit DEP relationship.
        3. Exact case/session/source record ID under confirmed namespace mapping.
        4. Exact system/version/environment + configured composite key.
        5. Human-confirmed link assertion.
        6. Similarity proposal (retained as inferred only).
    """

    def __init__(self, storage: StorageBackend):
        self._storage = storage

    def resolve(
        self,
        resource_ids: list[str],
        org_id: str,
        namespace_mappings: dict[str, str] | None = None,
    ) -> tuple[str, str, list[LinkAssertion]]:
        """Return (decision_identity, method, link_assertions).

        Iterates the precedence table and returns the first match.
        """
        resources = []
        for rid in resource_ids:
            r = self._storage.get_resource(rid, org_id)
            if r is not None:
                resources.append(r)

        for rid in resource_ids:
            exact = self._try_exact_id(rid, org_id)
            if exact:
                return exact, "exact_id", []

        for rid in resource_ids:
            dep_rel = self._try_dep_relationship(rid, org_id)
            if dep_rel:
                return dep_rel, "dep_relationship", []

        for rid in resource_ids:
            ns = self._try_namespace(rid, org_id, namespace_mappings or {})
            if ns:
                return ns, "namespace", []

        composite = self._try_composite_key(resource_ids, org_id)
        if composite:
            return composite, "composite_key", []

        for rid in resource_ids:
            confirmed = self._try_confirmed_link_assertion(rid, org_id)
            if confirmed:
                return confirmed, "link_assertion", []

        if resource_ids:
            return (resource_ids[0], "inferred", [])

        return ("", "unknown", [])

    def _try_exact_id(self, resource_id: str, org_id: str) -> str | None:
        existing = self._storage.list_decision_evidence_records_by_identity(resource_id, org_id)
        if existing:
            return resource_id
        return None

    def _try_dep_relationship(self, resource_id: str, org_id: str) -> str | None:
        las = self._storage.list_link_assertions_for_resource(resource_id, org_id)
        for la in las:
            if la.status == "confirmed" and la.relationship in ("exact_match", "same_decision"):
                return la.target_resource_id if la.source_resource_id == resource_id else la.source_resource_id
        return None

    def _try_namespace(self, resource_id: str, org_id: str, namespace_mappings: dict[str, str]) -> str | None:
        for prefix, ns_id in namespace_mappings.items():
            if resource_id.startswith(prefix):
                mapped = resource_id.replace(prefix, ns_id, 1)
                existing = self._storage.list_decision_evidence_records_by_identity(mapped, org_id)
                if existing:
                    return mapped
        return None

    def _try_composite_key(self, resource_ids: list[str], org_id: str) -> str | None:
        if not resource_ids:
            return None
        composite = "+".join(sorted(resource_ids))
        existing = self._storage.list_decision_evidence_records_by_identity(composite, org_id)
        if existing:
            return composite
        return None

    def _try_confirmed_link_assertion(self, resource_id: str, org_id: str) -> str | None:
        las = self._storage.list_link_assertions_for_resource(resource_id, org_id)
        for la in las:
            if la.status == "confirmed":
                target = la.target_resource_id if la.source_resource_id == resource_id else la.source_resource_id
                existing = self._storage.list_decision_evidence_records_by_identity(target, org_id)
                if existing:
                    return target
                return target
        return None

    def suggest_link(
        self,
        source_resource_id: str,
        target_resource_id: str,
        relationship: str,
        org_id: str,
        basis: str = "similarity",
        created_by: str = "system",
    ) -> LinkAssertion:
        la = LinkAssertion(
            org_id=org_id,
            source_resource_id=source_resource_id,
            target_resource_id=target_resource_id,
            relationship=relationship,
            basis=basis,
            status="inferred",
            created_by=created_by,
        )
        return self._storage.create_link_assertion(la)

    def confirm_link(self, la_id: str, org_id: str) -> LinkAssertion | None:
        la = self._storage.get_link_assertion(la_id)
        if la is None or la.org_id != org_id:
            return None
        from datetime import datetime, timezone

        la.status = "confirmed"
        la.confirmed_at = datetime.now(timezone.utc).isoformat()
        return self._storage.update_link_assertion(la)

    def reject_link(self, la_id: str, org_id: str) -> LinkAssertion | None:
        la = self._storage.get_link_assertion(la_id)
        if la is None or la.org_id != org_id:
            return None
        la.status = "rejected"
        return self._storage.update_link_assertion(la)
