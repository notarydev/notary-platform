from notary_platform.config import SETTINGS
from notary_platform.models import Organization, ReadinessPolicy, ReleaseGateResult, Scenario, VerificationRecord
from notary_platform.storage import MemoryStorage, SharedDemoFileStorage, get_storage, reset_storage


def test_shared_demo_file_storage_survives_restart(tmp_path) -> None:
    path = tmp_path / "shared-demo.json"
    storage = SharedDemoFileStorage(path)
    incident = storage.create_incident({"schema_version": "1.0", "root_hash": "abc", "elements": []}, org_id="demo-org")
    storage.create_org(Organization(id="demo-org", name="Harborline Credit Union"))
    storage.create_vr(VerificationRecord(id="vr-1", org_id="demo-org", environment_id="env:demo", agent_id="agent:harborline"))
    storage.create_scenario(Scenario(id="scenario-1", org_id="demo-org", source_vr_id="vr-1"))
    storage.create_readiness_policy(ReadinessPolicy(id="policy-1", org_id="demo-org", required_scenario_ids=["scenario-1"]))
    storage.create_release_gate_result(ReleaseGateResult(id="rg-1", org_id="demo-org", status="pass", evidence_refs=["scenario:scenario-1"]))
    storage.persist_evidence(incident.incident_id, "snapshot", {"root_hash": "abc"})

    restarted = SharedDemoFileStorage(path)

    assert restarted.get_incident(incident.incident_id) is not None
    assert restarted.get_org("demo-org").name == "Harborline Credit Union"
    assert restarted.get_vr("vr-1").agent_id == "agent:harborline"
    assert restarted.get_scenario("scenario-1").source_vr_id == "vr-1"
    assert restarted.get_readiness_policy("policy-1").required_scenario_ids == ["scenario-1"]
    assert restarted.get_release_gate_result("rg-1").status == "pass"


def test_shared_demo_file_storage_reset_is_deterministic(tmp_path) -> None:
    path = tmp_path / "shared-demo.json"
    storage = SharedDemoFileStorage(path)
    first = storage.create_incident({"elements": []}, org_id="demo-org")
    assert first.incident_id == "inc-000001"

    storage.reset()
    restarted = SharedDemoFileStorage(path)
    second = restarted.create_incident({"elements": []}, org_id="demo-org")

    assert restarted.get_incident(first.incident_id) is not None
    assert len(restarted.list_incidents("demo-org")) == 1
    assert second.incident_id == "inc-000001"


def test_get_storage_uses_shared_demo_profile(monkeypatch, tmp_path) -> None:
    reset_storage()
    monkeypatch.setattr(SETTINGS, "use_remote_storage", False)
    monkeypatch.setattr(SETTINGS, "storage_profile", "shared_demo")
    monkeypatch.setattr(SETTINGS, "shared_demo_storage_path", str(tmp_path / "profile.json"))

    assert isinstance(get_storage(), SharedDemoFileStorage)


def test_get_storage_defaults_to_memory(monkeypatch) -> None:
    reset_storage()
    monkeypatch.setattr(SETTINGS, "use_remote_storage", False)
    monkeypatch.setattr(SETTINGS, "storage_profile", "memory")

    assert isinstance(get_storage(), MemoryStorage)
