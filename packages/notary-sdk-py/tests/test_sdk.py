"""Tests for the Notary Python SDK."""

from __future__ import annotations

import pytest
from notary_sdk import RunCapture, verify_snapshot


@pytest.fixture
def capture() -> RunCapture:
    return RunCapture(secret_key=b"test-secret-key-32-bytes!!!")


def test_finalize_produces_snapshot(capture: RunCapture) -> None:
    capture.capture_llm(prompt="test", response="ok", model="test-model", temperature=0.0)
    capture.capture_tool(method="POST", url="/score", response={"score": 650})
    capture.capture_decision(decision="DENY")
    snapshot = capture.finalize()
    assert snapshot.root_hash
    assert len(snapshot.elements) == 3


def test_verify_snapshot(capture: RunCapture) -> None:
    capture.capture_llm(prompt="test", response="ok")
    capture.capture_decision(decision="APPROVE")
    snapshot = capture.finalize()
    assert snapshot.verify() is True
    assert verify_snapshot(snapshot.to_dict(), b"test-secret-key-32-bytes!!!") is True


def test_verify_snapshot_fails_with_wrong_key(capture: RunCapture) -> None:
    capture.capture_llm(prompt="test", response="ok")
    capture.capture_decision(decision="APPROVE")
    snapshot = capture.finalize()
    assert verify_snapshot(snapshot.to_dict(), b"wrong-key") is False


def test_capture_all_event_kinds(capture: RunCapture) -> None:
    capture.capture_human_action(source_record_ref="APP-123", domain="Lending")
    capture.capture_llm(prompt="test", response="ok")
    capture.capture_tool(method="POST", url="/score", response={"score": 650})
    capture.capture_retrieval(query="policy", documents=["doc-1"])
    capture.capture_guardrail(check="fair_lending", passed=True)
    capture.capture_decision(decision="APPROVE")
    capture.capture_timestamp()
    capture.capture_rng_seed(seed=42)
    snapshot = capture.finalize()
    assert len(snapshot.elements) == 8
    assert snapshot.verify() is True
