"""API data models for the Notary Platform."""

from __future__ import annotations

import enum
import time
import uuid
from typing import Any


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
