"""Replay runner — deterministic replay using sealed cassette data."""

from __future__ import annotations

from typing import Any, Callable, Optional

from notary_platform.replay_engine.cassette import ResponseCassette


def replay_call(
    cassette: ResponseCassette,
    method: str,
    url: str,
    body: Optional[str] = None,
) -> dict[str, Any]:
    """Replay a single call from the cassette.

    Returns ``{"response": ..., "status": ...}`` or an escalation result
    if the call is not in the cassette.
    """
    result = cassette.lookup(method, url, body)
    if result is None:
        return {
            "response": None,
            "status": None,
            "replay_status": "escalation_required",
            "reason": "no matching cassette entry",
        }
    return {
        "response": result["response"],
        "status": result["status"],
        "replay_status": "replayed",
    }


def replay_snapshot(
    snapshot_dict: dict[str, Any],
    agent_fn: Callable[..., Any],
    agent_kwargs: Optional[dict[str, Any]] = None,
    strict_order: bool = False,
) -> dict[str, Any]:
    """Replay an agent function using the snapshot's HTTP cassette.

    The agent function receives a ``cassette`` keyword argument so it can
    call ``cassette.lookup(...)`` instead of making real HTTP calls.

    Returns a dict with ``{"decision": ..., "replay_status": ...}``.
    """
    elements = snapshot_dict.get("elements", [])
    cassette = ResponseCassette(elements, strict_order=strict_order)

    try:
        result = agent_fn(cassette=cassette, **(agent_kwargs or {}))
        if strict_order and cassette.misses:
            return {
                "decision": result,
                "replay_status": "escalation_required",
                "reason": "agent call did not match cassette order",
                "misses": cassette.misses,
            }
        if strict_order and cassette.unconsumed_count:
            return {
                "decision": result,
                "replay_status": "escalation_required",
                "reason": "agent did not consume all cassette entries",
                "unconsumed_entries": cassette.unconsumed_count,
            }
        return {"decision": result, "replay_status": "replayed"}
    except Exception as exc:
        return {"decision": None, "replay_status": "error", "error": str(exc)}
