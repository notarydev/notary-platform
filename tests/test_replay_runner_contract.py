"""Tests for the ReplayRunner abstraction contract.

Proves:
- DemoReplayRunner is explicitly a demo runner
- Unsupported runner returns clear status
- No generic customer replay is faked
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from notary_platform.api_server.main import app
from notary_platform.api_server.routers.ingestion import storage
from notary_platform.services import DemoReplayRunner, ReplayExecutionResult, ReplayRunner

client = TestClient(app)


def _clear_storage() -> None:
    storage._vrs.clear()
    storage._replay_runs.clear()
    storage._labels.clear()
    storage._incidents.clear()
    storage._snapshots.clear()
    storage._evidence_artifacts.clear()
    storage._counter = 0


class TestReplayRunnerContract:
    def setup_method(self) -> None:
        _clear_storage()

    def test_demo_runner_is_explicitly_demo(self) -> None:
        runner = DemoReplayRunner(scenario_id="lending-denial")
        assert isinstance(runner, ReplayRunner)
        assert isinstance(runner, DemoReplayRunner)

    def test_demo_runner_produces_replay_result(self) -> None:
        runner = DemoReplayRunner(scenario_id="lending-denial")
        snapshot = {
            "schema_version": 1,
            "elements": [
                {"kind": "http", "payload": {"request": {"method": "POST", "url": "https://demo.notary.local/credit-api"}, "response": {"score": 650}, "status": 200}},  # noqa: E501
                {"kind": "decision", "payload": {"decision": "DENY"}},
            ],
        }
        result = runner.run(snapshot)
        assert isinstance(result, ReplayExecutionResult)
        assert result.status == "replayed"
        assert result.decision

    def test_no_replay_runner_on_non_demo_record(self) -> None:
        """Non-demo records without a configured runner return unsupported_runner."""
        # Create a non-demo VR with cassette data
        snapshot = {
            "elements": [
                {"kind": "http", "payload": {"request": {"method": "POST", "url": "https://api.example.com/check"}, "response": {"score": 650}, "status": 200}},
                {"kind": "decision", "payload": {"decision": "DENY"}},
            ],
            "root_hash": "test-root",
        }
        vr_resp = client.post("/v1/verification-records/from-snapshot", json=snapshot)
        assert vr_resp.status_code == 200
        vr = vr_resp.json()
        assert vr["is_demo"] is False

        # Clear the replay runner to simulate no runner configured
        from notary_platform.api_server.routers.ingestion import set_replay_runner
        set_replay_runner(None)

        # Attempt replay
        replay_resp = client.post(f"/v1/verification-records/{vr['id']}/replay-runs")
        set_replay_runner(DemoReplayRunner())  # restore
        assert replay_resp.status_code == 200
        run = replay_resp.json()
        assert run["status"] == "unsupported_runner"

    def test_demo_record_replay_works(self) -> None:
        """Demo records with a configured runner can replay."""
        from notary_platform.api_server.routers.ingestion import set_replay_runner
        set_replay_runner(DemoReplayRunner(scenario_id="lending-denial"))

        snapshot = {
            "elements": [
                {
                    "kind": "http",
                    "payload": {
                        "request": {"method": "POST", "url": "https://demo.notary.local/credit-api"},
                        "response": {"score": 650},
                        "status": 200,
                    },
                },
                {"kind": "decision", "payload": {"decision": "DENY"}},
            ],
            "root_hash": "test-root",
            "is_demo": True,
        }
        vr_resp = client.post("/v1/verification-records/from-snapshot", json=snapshot)
        assert vr_resp.status_code == 200

        replay_resp = client.post(f"/v1/verification-records/{vr_resp.json()['id']}/replay-runs")
        assert replay_resp.status_code == 200
        run = replay_resp.json()
        assert run["status"] == "replayed"
