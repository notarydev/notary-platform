"""Replay runner — deterministic replay using sealed cassette data."""

from __future__ import annotations

from typing import Any, Callable, Optional

from notary_platform.models import ReplayExecutionEvent
from notary_platform.replay_engine.cassette import ResponseCassette


def _emit(
    callback: Callable[[ReplayExecutionEvent], None] | None,
    step: str,
    source: str,
    expected: str,
    actual: str,
    status: str,
    sequence: int,
) -> None:
    if callback:
        callback(ReplayExecutionEvent(
            step=step, source=source, expected=expected,
            actual=actual, status=status, sequence=sequence,
        ))


def replay_call(
    cassette: ResponseCassette,
    method: str,
    url: str,
    body: Optional[str] = None,
    event_callback: Callable[[ReplayExecutionEvent], None] | None = None,
    sequence: int = 0,
) -> dict[str, Any]:
    """Replay a single call from the cassette.

    Returns ``{"response": ..., "status": ...}`` or an escalation result
    if the call is not in the cassette.
    """
    _emit(event_callback, "Lookup cassette", "cassette",
          f"Match {method} {url}", "searching", "running", sequence)
    result = cassette.lookup(method, url, body)
    if result is None:
        _emit(event_callback, "Cassette miss", "cassette",
              f"Match {method} {url}", "no entry found", "escalation_required", sequence + 1)
        return {
            "response": None,
            "status": None,
            "replay_status": "escalation_required",
            "reason": "no matching cassette entry",
        }
    _emit(event_callback, "Cassette hit", "cassette",
          f"Match {method} {url}", "recorded response supplied", "pass", sequence + 1)
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
    event_callback: Callable[[ReplayExecutionEvent], None] | None = None,
) -> dict[str, Any]:
    """Replay an agent function using the snapshot's HTTP cassette.

    The agent function receives a ``cassette`` keyword argument so it can
    call ``cassette.lookup(...)`` instead of making real HTTP calls.
    Emits ``ReplayExecutionEvent`` objects via ``event_callback`` during execution.

    Returns a dict with ``{"decision": ..., "replay_status": ...}``.
    """
    seq = 0
    elements = snapshot_dict.get("elements", [])

    _emit(event_callback, "Load sealed evidence", "snapshot",
          f"{len(elements)} elements", "loaded", "pass", seq)
    seq += 1

    input_el = next((e for e in elements if e.get("kind") == "input"), None)
    if input_el:
        applicant_id = input_el.get("payload", {}).get("applicant_id", "—")
        _emit(event_callback, "Applicant facts loaded", "sealed input",
              "match", applicant_id, "pass", seq)
        seq += 1

    seq += 1  # reserve for cassette construction below
    cassette = ResponseCassette(elements, strict_order=strict_order)

    http_elements = [e for e in elements if e.get("kind") in ("http", "tool_call", "api_response")]
    _emit(event_callback, "Build response cassette", "cassette",
          f"{len(http_elements)} recorded calls", "built", "pass", seq)
    seq += 1

    for i, hel in enumerate(http_elements):
        req = hel.get("payload", {}).get("request", {})
        method = req.get("method", "POST") if isinstance(req, dict) else "POST"
        url = req.get("url", "—") if isinstance(req, dict) else "—"
        _emit(event_callback, f"Cassette entry {i+1}", "cassette",
              f"{method} {url}", "recorded", "pass", seq)
        seq += 1

    policy_el = next((e for e in elements if e.get("kind") == "policy"), None)
    if policy_el:
        pv = policy_el.get("payload", {}).get("version", "—")
        _emit(event_callback, "Policy version loaded", "sealed metadata",
              pv, pv, "pass", seq)
        seq += 1

    decision_el = next((e for e in elements if e.get("kind") == "decision"), None)
    original_decision = (decision_el or {}).get("payload", {}).get("decision", "—") if decision_el else "—"

    _emit(event_callback, "Execute replay agent", "replay",
          "agent_fn(cassette=cassette)", "running", "running", seq)
    seq += 1

    try:
        result = agent_fn(cassette=cassette, **(agent_kwargs or {}))
        replayed_decision = str(result) if result is not None else "—"

        if strict_order and cassette.misses:
            _emit(event_callback, "Cassette strict-order miss", "cassette",
                  "all calls matched in order", f"misses: {len(cassette.misses)}", "escalation_required", seq)
            seq += 1
            return {
                "decision": result,
                "replay_status": "escalation_required",
                "reason": "agent call did not match cassette order",
                "misses": cassette.misses,
            }
        if strict_order and cassette.unconsumed_count:
            _emit(event_callback, "Cassette unconsumed entries", "cassette",
                  "all entries consumed", f"{cassette.unconsumed_count} unused", "escalation_required", seq)
            seq += 1
            return {
                "decision": result,
                "replay_status": "escalation_required",
                "reason": "agent did not consume all cassette entries",
                "unconsumed_entries": cassette.unconsumed_count,
            }

        _emit(event_callback, "Agent decision produced", "replay",
              original_decision, replayed_decision, "pass", seq)
        seq += 1

        _emit(event_callback, "Compare decisions", "comparison",
              original_decision, replayed_decision,
              "reproduced" if replayed_decision == original_decision else "diverged", seq)
        seq += 1

        _emit(event_callback, "Replay verdict", "comparison",
              "reproduce known failure",
              "reproduced" if replayed_decision == original_decision else "diverged",
              "replayed" if replayed_decision == original_decision else "diverged", seq)

        return {"decision": result, "replay_status": "replayed"}
    except Exception as exc:
        _emit(event_callback, "Agent execution error", "replay",
              "agent_fn completes", f"error: {exc}", "error", seq)
        return {"decision": None, "replay_status": "error", "error": str(exc)}
