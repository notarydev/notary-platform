"""Budget enforcement for Sweep Runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class BudgetState:
    record_count: int = 0
    evaluator_count: int = 0
    elapsed_seconds: float = 0.0
    record_limit: int = 10000
    evaluator_limit: int = 50
    timeout_seconds: int = 300
    start_time: float = 0.0
    exceeded_reasons: list[str] = field(default_factory=list)

    def check(self) -> bool:
        self.exceeded_reasons = []
        if self.record_count >= self.record_limit:
            self.exceeded_reasons.append(f"record limit ({self.record_limit})")
        if self.evaluator_count >= self.evaluator_limit:
            self.exceeded_reasons.append(f"evaluator limit ({self.evaluator_limit})")
        if self.start_time and (datetime.now(timezone.utc).timestamp() - self.start_time) > self.timeout_seconds:
            self.exceeded_reasons.append(f"timeout ({self.timeout_seconds}s)")
        return len(self.exceeded_reasons) == 0
