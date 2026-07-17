"""Replay worker — orchestrates replay for incidents."""

from __future__ import annotations

from typing import Any, Callable, Optional

from notary_platform.models import Incident, IncidentStatus
from notary_platform.replay_engine.replay import replay_snapshot


def run_replay(
    incident: Incident,
    snapshot_dict: dict[str, Any],
    agent_fn: Callable[..., Any],
    agent_kwargs: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Execute replay for an incident and update its status."""
    result = replay_snapshot(snapshot_dict, agent_fn, agent_kwargs)
    incident.replay_result = result
    incident.status = IncidentStatus.replayed
    return result
