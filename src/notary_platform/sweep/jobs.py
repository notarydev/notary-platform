"""Job lifecycle for Sweep operations.

States: queued, claimed, running, retry_wait, completed, failed, cancelled.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class SweepJob:
    id: str = ""
    org_id: str = ""
    run_id: str = ""
    job_type: str = ""  # profile, resolve, evaluate, assemble
    status: str = "queued"  # queued, claimed, running, retry_wait, completed, failed, cancelled
    payload: dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    error_code: str = ""
    error_message: str = ""
    created_at: str = ""
    claimed_at: str = ""
    completed_at: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            object.__setattr__(self, "id", f"j-{uuid.uuid4().hex[:12]}")
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "run_id": self.run_id,
            "job_type": self.job_type,
            "status": self.status,
            "payload": dict(self.payload),
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "claimed_at": self.claimed_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SweepJob:
        return cls(
            id=d.get("id", f"j-{uuid.uuid4().hex[:12]}"),
            org_id=d.get("org_id", ""),
            run_id=d.get("run_id", ""),
            job_type=d.get("job_type", ""),
            status=d.get("status", "queued"),
            payload=d.get("payload", {}),
            retry_count=d.get("retry_count", 0),
            max_retries=d.get("max_retries", 3),
            error_code=d.get("error_code", ""),
            error_message=d.get("error_message", ""),
            created_at=d.get("created_at", ""),
            claimed_at=d.get("claimed_at", ""),
            completed_at=d.get("completed_at", ""),
        )
