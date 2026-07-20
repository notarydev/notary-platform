"""Tests for the WO-4 cassette replay MVP."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from notary_platform.api_server.main import app
from notary_platform.api_server.routers.ingestion import storage
from notary_platform.replay_engine.cassette import ResponseCassette, _call_signature
from notary_platform.replay_engine.replay import replay_call, replay_snapshot
from notary_platform.snapshot import (
    CapturedElement,
    _compute_root_hash,
    _seal_element,
)

SECRET = b"test-secret-key-32-bytes-long!!!"
client = TestClient(app)


def _lending_agent(cassette: ResponseCassette, threshold: int = 700) -> str:
    """Demo lending agent: looks up a credit score via cassette HTTP call."""
    result = cassette.lookup("POST", "https://api.example.com/credit-check")
    if result is None:
        return "UNKNOWN"
    score = result.get("response", {}).get("score", 0)
    if score >= threshold:
        return "APPROVE"
    return "DENY"


def _make_snapshot_with_http(
    http_response: dict[str, Any],  # type: ignore[type-arg]
    decision: str,
) -> dict:  # type: ignore[type-arg]
    """Build a snapshot dict with HTTP and decision elements."""
    elements = [
        {
            "kind": "http",
            "payload": {
                "request": {"method": "POST", "url": "https://api.example.com/credit-check"},
                "response": http_response,
                "status": 200,
            },
        },
        {
            "kind": "decision",
            "payload": {"decision": decision},
        },
    ]
    prev_hash = b"\x00" * 32
    elem_hashes: list[bytes] = []
    sealed: list[dict[str, Any]] = []
    for e in elements:
        ce = CapturedElement(kind=e["kind"], payload=e.get("payload", {}))
        h = _seal_element(prev_hash, ce.canonical_bytes(), SECRET)
        elem_hashes.append(h)
        sealed.append({"kind": ce.kind, "payload": ce.payload, "element_hash": h.hex()})
        prev_hash = h
    root = _compute_root_hash(elem_hashes)
    return {
        "schema_version": 1,
        "timestamp": "2025-01-01T00:00:00Z",
        "elements": sealed,
        "merkle_chain": [h.hex() for h in elem_hashes],
        "root_hash": root,
    }


def _clear_storage() -> None:
    storage._incidents.clear()
    storage._snapshots.clear()
    storage._certificates.clear()
    storage._counter = 0


class TestCassette:
    def test_lookup_hit(self) -> None:
        elements = [
            {
                "kind": "http",
                "payload": {
                    "request": {"method": "POST", "url": "https://api.example.com/credit-check"},
                    "response": {"score": 650},
                    "status": 200,
                },
            }
        ]
        cassette = ResponseCassette(elements)
        result = cassette.lookup("POST", "https://api.example.com/credit-check")
        assert result is not None
        assert result["response"]["score"] == 650

    def test_lookup_miss(self) -> None:
        cassette = ResponseCassette([])
        result = cassette.lookup("GET", "https://api.example.com/other")
        assert result is None

    def test_signature_deterministic(self) -> None:
        s1 = _call_signature("POST", "https://x.com/api", '{"a":1}')
        s2 = _call_signature("POST", "https://x.com/api", '{"a":1}')
        assert s1 == s2

    def test_entry_count(self) -> None:
        req_a = {"method": "GET", "url": "a"}
        req_b = {"method": "GET", "url": "b"}
        elements = [
            {"kind": "http", "payload": {"request": req_a, "response": "x", "status": 200}},
            {"kind": "http", "payload": {"request": req_b, "response": "y", "status": 200}},
            {"kind": "llm", "payload": {"prompt": "ignored"}},
        ]
        assert ResponseCassette(elements).entry_count == 2


class TestReplayCall:
    def test_replay_hit(self) -> None:
        elements = [
            {
                "kind": "http",
                "payload": {
                    "request": {"method": "GET", "url": "https://x.com"},
                    "response": "ok",
                    "status": 200,
                },
            }
        ]
        cassette = ResponseCassette(elements)
        result = replay_call(cassette, "GET", "https://x.com")
        assert result["replay_status"] == "replayed"
        assert result["response"] == "ok"

    def test_replay_miss(self) -> None:
        cassette = ResponseCassette([])
        result = replay_call(cassette, "GET", "https://x.com")
        assert result["replay_status"] == "escalation_required"


class TestReplayAgent:
    def test_original_deny(self) -> None:
        snap = _make_snapshot_with_http({"score": 650}, "DENY")
        result = replay_snapshot(snap, _lending_agent)
        assert result["decision"] == "DENY"
        assert result["replay_status"] == "replayed"

    def test_fixed_approve(self) -> None:
        snap = _make_snapshot_with_http({"score": 650}, "APPROVE")

        def fixed_agent(cassette: ResponseCassette) -> str:
            return _lending_agent(cassette, threshold=620)

        result = replay_snapshot(snap, fixed_agent)
        assert result["decision"] == "APPROVE"

    def test_missing_cassette_entry(self) -> None:
        snap = {
            "schema_version": 1,
            "timestamp": "2025-01-01T00:00:00Z",
            "elements": [{"kind": "llm", "payload": {"prompt": "hi"}, "element_hash": "aa"}],
            "merkle_chain": ["aa"],
            "root_hash": "bb",
        }

        def agent(cassette: ResponseCassette) -> str:
            result = cassette.lookup("POST", "https://missing.com/api")
            if result is None:
                return "UNKNOWN"
            return "OK"

        result = replay_snapshot(snap, agent, strict_order=True)
        assert result["decision"] == "UNKNOWN"
        assert result["replay_status"] == "escalation_required"
        assert result["reason"] == "agent call did not match cassette order"

    def test_replay_fails_closed_on_changed_call(self) -> None:
        snap = _make_snapshot_with_http({"score": 650}, "DENY")

        def changed_agent(cassette: ResponseCassette) -> str:
            result = cassette.lookup("POST", "https://api.example.com/credit-check-v2")
            if result is None:
                return "UNKNOWN"
            return "DENY"

        result = replay_snapshot(snap, changed_agent, strict_order=True)
        assert result["decision"] == "UNKNOWN"
        assert result["replay_status"] == "escalation_required"
        assert result["misses"] == [
            {"method": "POST", "url": "https://api.example.com/credit-check-v2", "body": None}
        ]

    def test_replay_fails_closed_on_out_of_order_call(self) -> None:
        snap = _make_snapshot_with_http({"score": 650}, "DENY")
        second = {
            "kind": "http",
            "payload": {
                "request": {"method": "GET", "url": "https://api.example.com/rate-table"},
                "response": {"apr": 7.25},
                "status": 200,
            },
            "element_hash": "bb",
        }
        snap["elements"].insert(0, second)

        def out_of_order_agent(cassette: ResponseCassette) -> str:
            result = cassette.lookup("POST", "https://api.example.com/credit-check")
            if result is None:
                return "UNKNOWN"
            return "DENY"

        result = replay_snapshot(snap, out_of_order_agent, strict_order=True)
        assert result["decision"] == "UNKNOWN"
        assert result["replay_status"] == "escalation_required"
        assert result["reason"] == "agent call did not match cassette order"

    def test_replay_fails_closed_on_unconsumed_recorded_call(self) -> None:
        snap = _make_snapshot_with_http({"score": 650}, "DENY")
        snap["elements"].append(
            {
                "kind": "http",
                "payload": {
                    "request": {"method": "GET", "url": "https://api.example.com/rate-table"},
                    "response": {"apr": 7.25},
                    "status": 200,
                },
                "element_hash": "bb",
            }
        )

        result = replay_snapshot(snap, _lending_agent, strict_order=True)
        assert result["decision"] == "DENY"
        assert result["replay_status"] == "escalation_required"
        assert result["reason"] == "agent did not consume all cassette entries"
        assert result["unconsumed_entries"] == 1

    def test_no_network_calls(self) -> None:
        import sys

        # Replay must not pull in blocking HTTP client libraries. httpx is a
        # test-harness dependency (FastAPI TestClient) so it is excluded here.
        for mod in ("requests", "urllib3"):
            assert mod not in sys.modules


class TestReplayEndpoint:
    def setup_method(self) -> None:
        _clear_storage()

    def test_replay_with_registered_agent(self) -> None:
        from notary_platform.api_server.routers.incidents import set_demo_agent

        set_demo_agent(_lending_agent)

        snap = _make_snapshot_with_http({"score": 650}, "DENY")
        ingested = client.post("/v1/incidents/ingest", json={"snapshot": snap}).json()
        incident_id = ingested["incident_id"]

        resp = client.post(f"/v1/incidents/{incident_id}/replay")
        assert resp.status_code == 200
        data = resp.json()
        assert data["replay_status"] == "replayed"
        assert data["decision"] == "DENY"

    def test_replay_without_agent(self) -> None:
        from notary_platform.api_server.routers.incidents import set_demo_agent

        set_demo_agent(None)

        snap = _make_snapshot_with_http({"score": 650}, "DENY")
        ingested = client.post("/v1/incidents/ingest", json={"snapshot": snap}).json()
        incident_id = ingested["incident_id"]

        resp = client.post(f"/v1/incidents/{incident_id}/replay")
        assert resp.status_code == 200
        assert resp.json()["replay_status"] == "escalation_required"

    def test_replay_404(self) -> None:
        resp = client.post("/v1/incidents/inc-999999/replay")
        assert resp.status_code == 404
