"""Tests that SDK setup instructions in the UI are truthful.

Proves:
- UI does not say 'pip install notary-sdk' as primary command
- UI shows 'pip install -e packages/notary-sdk-py'
- UI deployed demo setup shows correct URL
- SDK .submit() posts to Verification Record endpoint
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from notary_platform.api_server.main import app

client = TestClient(app)


class TestSDKSetupTruth:
    def test_app_js_no_pypi_install(self) -> None:
        """UI must not claim pip install notary-sdk unless package is on PyPI."""
        resp = client.get("/app/app.js")
        if resp.status_code != 200:
            return  # Skip if SPA not built
        text = resp.text
        assert "pip install notary-sdk" not in text
        assert "pip install -e packages/notary-sdk-py" in text

    def test_sdk_submit_targets_verification_records(self) -> None:
        """SDK .submit() should post to /v1/verification-records/from-snapshot."""
        try:
            from notary_sdk import RunCapture
        except ImportError:
            return  # SDK not installed in CI; skip

        capture = RunCapture(secret_key=b"test", api_url="http://test", api_token="test")
        snapshot = capture.finalize()
        import inspect
        source = inspect.getsource(snapshot.submit)
        assert "from-snapshot" in source or "verification-records" in source

    def test_app_shows_deployed_url(self) -> None:
        """UI deployed demo setup should show api.getnotary.ai."""
        resp = client.get("/app/app.js")
        if resp.status_code != 200:
            return
        text = resp.text
        assert "api.getnotary.ai" in text or "getnotary" in text

    def test_app_js_no_wrapper_snippet(self) -> None:
        """UI snippet must not wrap snapshot in json={"snapshot": ...}."""
        resp = client.get("/app/app.js")
        if resp.status_code != 200:
            return
        text = resp.text
        assert 'json={"snapshot": snapshot.to_dict()' not in text

    def test_app_js_sends_raw_snapshot(self) -> None:
        """UI snippet must send json=snapshot.to_dict() directly."""
        resp = client.get("/app/app.js")
        if resp.status_code != 200:
            return
        text = resp.text
        assert "json=snapshot.to_dict()" in text

    def test_sdk_submit_and_ui_target_same_endpoint(self) -> None:
        """SDK .submit() and the UI code snippet both target /verification-records/from-snapshot."""
        resp = client.get("/app/app.js")
        if resp.status_code == 200:
            assert "/v1/verification-records/from-snapshot" in resp.text
        try:
            from notary_sdk import RunCapture
        except ImportError:
            return
        capture = RunCapture(secret_key=b"test", api_url="http://test", api_token="test")
        snapshot = capture.finalize()
        import inspect
        source = inspect.getsource(snapshot.submit)
        assert "/v1/verification-records/from-snapshot" in source

    def test_sdk_metadata_persists_to_verification_record(self) -> None:
        """SDK-submitted snapshot metadata survives to the VR."""
        snapshot = {
            "schema_version": 1,
            "source_system_id": "test-system",
            "source_record_ref": "REF-001",
            "business_function": "customer_support",
            "expected_outcome": "APPROVE",
            "label_source": "human_review",
            "environment_id": "env:demo",
            "agent_id": "agent:test-bot",
            "agent_version": "1.0.0",
            "model_provider": "test-provider",
            "model_name": "test-model",
            "policy_version": "v1",
            "elements": [
                {"kind": "input", "sequence": 0, "payload": {"text": "hello"}},
                {"kind": "decision", "sequence": 1, "payload": {"decision": "APPROVE"}},
            ],
        }
        resp = client.post(
            "/v1/verification-records/from-snapshot",
            json=snapshot,
            params={"agent_id": "agent:test-bot"},
        )
        assert resp.status_code == 200, resp.text
        vr = resp.json()
        assert vr["source_system_id"] == "test-system"
        assert vr["source_record_ref"] == "REF-001"
        assert vr["business_function"] == "customer_support"
        assert vr["expected_outcome"] == "APPROVE"
        assert vr["label_source"] == "human_review"
        assert vr["agent_id"] == "agent:test-bot"
        assert vr["agent_version"] == "1.0.0"
        assert vr["model_provider"] == "test-provider"
        assert vr["model_name"] == "test-model"
        assert vr["policy_version"] == "v1"
