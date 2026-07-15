"""Mutation verification — replay with modified config and compare."""

from __future__ import annotations

from typing import Any, Callable, Optional

from notary_platform.replay_engine.replay import replay_snapshot


def run_mutation(
    snapshot_dict: dict[str, Any],
    agent_fn: Callable[..., Any],
    fix_config: dict[str, Any],
    agent_kwargs: Optional[dict[str, Any]] = None,
    expected_correct_behavior: str = "APPROVE",
) -> dict[str, Any]:
    """Replay with the mutated config and return both decisions.

    Returns ``{"original_decision": ..., "mutated_decision": ...,
    "mitigated": bool}``.
    """
    kwargs = dict(agent_kwargs or {})
    kwargs.update(fix_config)

    original_result = replay_snapshot(snapshot_dict, agent_fn, agent_kwargs)
    mutated_result = replay_snapshot(snapshot_dict, agent_fn, kwargs)

    original_decision = original_result.get("decision")
    mutated_decision = mutated_result.get("decision")

    mitigated = mutated_decision == expected_correct_behavior

    return {
        "original_decision": original_decision,
        "mutated_decision": mutated_decision,
        "mitigated": mitigated,
        "replay_status": mutated_result.get("replay_status", "unknown"),
        "fix_config": fix_config,
        "expected_correct_behavior": expected_correct_behavior,
    }
