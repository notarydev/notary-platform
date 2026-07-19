"""Tests for Phase 2 Verification Record intake (WO-69/70/71)."""
from fastapi.testclient import TestClient

from notary_platform.api_server.main import app
from notary_platform.api_server.routers.verification import _label_store, _vr_store

client = TestClient(app)

SNAP = {"elements": [{"kind": "http", "payload": {"req": "GET", "res": {"score": 650}}},
    {"kind": "decision", "payload": {"decision": "DENY"}}], "root_hash": "x"}
LLM_SNAP = {"elements": [{"kind": "llm", "payload": {"prompt": "hi"}},
    {"kind": "decision", "payload": {"decision": "DENY"}}], "root_hash": "abc"}

def setup():
    _vr_store.clear()
    _label_store.clear()

def test_create_vr():
    setup()
    resp = client.post("/v1/verification-records?source_type=manual_submission&agent_id=agent:test")
    assert resp.status_code == 200
    assert resp.json()["source_type"] == "manual_submission"

def test_create_vr_from_snapshot():
    setup()
    resp = client.post("/v1/verification-records/from-snapshot", json=SNAP)
    assert resp.status_code == 200
    d = resp.json()
    assert d["replayability"] == "requires_human_label"

def test_llm_snapshot_evidence_only():
    setup()
    resp = client.post("/v1/verification-records/from-snapshot", json=LLM_SNAP)
    assert resp.json()["replayability"] == "evidence_only"

def test_list_vrs():
    setup()
    client.post("/v1/verification-records/manual", json={"ticket_id": "TKT-1", "decision": "DENIED"})
    assert len(client.get("/v1/verification-records").json()) == 1

def test_add_label_and_replayable():
    setup()
    r = client.post("/v1/verification-records/from-snapshot", json=SNAP)
    vid = r.json()["id"]
    client.post(f"/v1/verification-records/{vid}/label?expected_outcome=APPROVE&reviewer=Test&role=QA&reason=Should")
    assert client.get(f"/v1/verification-records/{vid}/replayability").json()["replayability"] == "replayable"

def test_promote_to_incident():
    setup()
    r = client.post("/v1/verification-records/from-snapshot", json=SNAP)
    vid = r.json()["id"]
    resp = client.post(f"/v1/verification-records/{vid}/promote-to-incident")
    assert resp.json()["incident_id"].startswith("inc-")

def test_manual_intake():
    setup()
    r = client.post("/v1/verification-records/manual", json={"transcript": "Complaint", "decision": "ESCALATE"})
    assert r.json()["source_type"] == "manual_submission"

def test_webhook_intake():
    setup()
    r = client.post("/v1/verification-records/webhook", json={"events": [{"kind": "model_call", "payload": {"prompt": "t"}}]})
    assert r.json()["source_type"] == "webhook"

def test_adapter_registry():
    ads = client.get("/v1/platform/adapters").json()
    assert any(a["id"] == "python_sdk" and a["status"] == "built" for a in ads)
    assert any(a["id"] == "openai_adapter" and a["status"] == "planned" for a in ads)
