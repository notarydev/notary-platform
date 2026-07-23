from __future__ import annotations

from datetime import datetime
from typing import Any

from notary_platform.discovery.models import (
    ContextBinding,
    ContextConflict,
    DecisionEvidenceRecord,
    ResolutionTrace,
)
from notary_platform.storage import StorageBackend


class TemporalContextResolver:
    """Resolve context bindings applicable at decision time.

    Resolution order:
        1. Select bindings whose subject scope and selector match the DER.
        2. Evaluate effective_from <= decision_time < effective_until.
        3. Apply explicit supersession.
        4. Apply configured authority.
        5. Preserve equal-authority disagreement as ContextConflict.
        6. Return a ResolutionTrace.
    """

    def __init__(self, storage: StorageBackend):
        self._storage = storage

    AUTHORITY_RANK = {
        "customer_confirmed": 4,
        "provider_declared": 3,
        "dep_relationship": 2,
        "inferred": 1,
    }

    def resolve(
        self,
        der: DecisionEvidenceRecord,
        org_id: str,
        decision_time: str | None = None,
        subject_scope: str | None = None,
        subject_selector: str | None = None,
    ) -> ResolutionTrace:
        scope = subject_scope or der.decision_identity
        selector = subject_selector or ""

        candidates = self._storage.list_context_bindings_for_scope(org_id, scope, selector)
        if not candidates:
            candidates = self._storage.list_context_bindings(org_id)
            candidates = [cb for cb in candidates if cb.subject_scope == scope or cb.subject_scope == ""]

        dt = decision_time or der.created_at
        dt_parsed = self._parse_time(dt)

        included: list[ContextBinding] = []
        excluded: list[ContextBinding] = []
        superseded: list[ContextBinding] = []
        missing: list[str] = []
        stale: list[str] = []
        redacted: list[str] = []
        conflicted: list[ContextBinding] = []
        reasons: dict[str, str] = {}

        for cb in candidates:
            cb_from = cb.effective_from
            cb_until = cb.effective_until

            if cb_from and dt_parsed < self._parse_time(cb_from):
                excluded.append(cb)
                reasons[cb.id] = f"before effective_from ({cb_from})"
                continue

            if cb_until and dt_parsed >= self._parse_time(cb_until):
                excluded.append(cb)
                reasons[cb.id] = f"at or after effective_until ({cb_until})"
                continue

            if cb.superseded_by:
                superseder = self._storage.get_context_binding(cb.superseded_by)
                if superseder is not None:
                    if superseder.effective_from and dt_parsed >= self._parse_time(superseder.effective_from):
                        included.append(superseder)
                        superseded.append(cb)
                        reasons[cb.id] = f"superseded by {cb.superseded_by}"
                        continue

            if cb.binding_type == "redacted":
                redacted.append(cb.artifact_ref)
                excluded.append(cb)
                reasons[cb.id] = "artifact is redacted"
                continue

            if cb.artifact_ref and not self._artifact_available(cb.artifact_ref):
                missing.append(cb.artifact_ref)
                stale.append(cb.artifact_ref)
                excluded.append(cb)
                reasons[cb.id] = f"artifact not available ({cb.artifact_ref})"
                continue

            included.append(cb)

        grouped: dict[str, list[ContextBinding]] = {}
        for cb in included:
            key = f"{cb.subject_scope}:{cb.binding_type}"
            grouped.setdefault(key, []).append(cb)

        final_included: list[ContextBinding] = []
        for key, group in grouped.items():
            group.sort(key=lambda x: self.AUTHORITY_RANK.get(x.authority, 0), reverse=True)
            top = group[0]
            ties = [g for g in group if self.AUTHORITY_RANK.get(g.authority, 0) == self.AUTHORITY_RANK.get(top.authority, 0)]
            if len(ties) > 1 and top.authority != "customer_confirmed":
                conflict = ContextConflict(
                    org_id=org_id,
                    der_id=der.id,
                    field_or_binding=key,
                    binding_a_id=ties[0].id,
                    binding_b_id=ties[1].id,
                    authority_a=ties[0].authority,
                    authority_b=ties[1].authority,
                )
                self._storage.create_context_conflict(conflict)
                conflicted.append(top)
                reasons[top.id] = f"equal-authority conflict with {ties[1].id} ({key})"
                continue
            final_included.append(top)

        rt = ResolutionTrace(
            der_id=der.id,
            org_id=org_id,
            included_bindings=[cb.id for cb in final_included],
            excluded_bindings=[cb.id for cb in excluded],
            superseded_bindings=[cb.id for cb in superseded],
            missing_artifacts=missing,
            stale_artifacts=stale,
            redacted_artifacts=redacted,
            conflicted_bindings=[cc.id for cc in conflicted if isinstance(cc, ContextConflict)],
            reasons=reasons,
        )
        created = self._storage.create_resolution_trace(rt)
        self._update_der_bindings(der, created)
        return created

    def _update_der_bindings(self, der: DecisionEvidenceRecord, rt: ResolutionTrace) -> None:
        der.resolution_trace_id = rt.id
        der.context_binding_ids = list(rt.included_bindings)
        self._storage.create_decision_evidence_record(der)

    def _parse_time(self, ts: str) -> datetime:
        try:
            return datetime.fromisoformat(ts)
        except (ValueError, TypeError):
            return datetime.min

    def _artifact_available(self, artifact_ref: str) -> bool:
        if not artifact_ref:
            return False
        if artifact_ref.startswith("dep://"):
            payload = self._storage.get_payload(artifact_ref)
            return payload is not None
        return True

    def resolve_conflict(
        self,
        conflict_id: str,
        resolution: str,
        resolved_by: str,
        org_id: str,
    ) -> ContextConflict | None:
        cc = self._storage.get_context_conflict(conflict_id)
        if cc is None or cc.org_id != org_id:
            return None
        from datetime import datetime, timezone

        cc.resolution = resolution
        cc.resolved_by = resolved_by
        cc.resolved_at = datetime.now(timezone.utc).isoformat()
        return self._storage.update_context_conflict(cc)

    def suggest_context_sources(
        self,
        workflow_id: str,
        org_id: str,
    ) -> list[dict[str, Any]]:
        suggestions = self._storage.list_advisory_suggestions(org_id, workflow_id)
        return [
            s for s in (s.to_dict() for s in suggestions)
            if s.get("suggestion_type") == "context_source_candidate"
        ]
