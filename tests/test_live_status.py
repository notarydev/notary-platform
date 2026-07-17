"""Tests for the live status layer (WO-36)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from notary_platform.api_server.main import app
from notary_platform.api_server.routers.live_status import (
    CONNECTION_STATES,
    build_live_status,
)
from notary_platform.api_server.routers.topology_data import build_topology
from notary_platform.config import SETTINGS

client = TestClient(app)


@pytest.fixture
def _reset_token():
    prev = SETTINGS.command_center_token
    SETTINGS.command_center_token = ""
    try:
        yield
    finally:
        SETTINGS.command_center_token = prev


class TestLiveStatusShape:
    def test_endpoint_returns_nodes_and_summary(self, _reset_token) -> None:
        resp = client.get("/v1/live-status")
        assert resp.status_code == 200
        body = resp.json()
        assert "overall_connection_state" in body
        assert "nodes" in body
        assert "summary" in body
        assert "stale_threshold_seconds" in body
        assert len(body["nodes"]) == len(build_topology()["nodes"])

    def test_every_node_has_build_and_connection_state(self, _reset_token) -> None:
        body = client.get("/v1/live-status").json()
        for node in body["nodes"]:
            assert "id" in node
            assert "build_state" in node
            assert "connection_state" in node
            assert node["connection_state"] in CONNECTION_STATES
            assert "last_checked" in node

    def test_summary_states_valid(self, _reset_token) -> None:
        body = client.get("/v1/live-status").json()
        for probe in body["summary"].values():
            assert probe["state"] in CONNECTION_STATES


class TestLiveStatusHonesty:
    def test_unknown_never_reported_healthy(self, _reset_token) -> None:
        """In local demo (no CI signal, no AWS creds) nothing is fabricated green."""
        body = client.get("/v1/live-status").json()
        # AWS probes with no creds must be not_applicable/unknown, never healthy.
        aws_ids = {"aws:s3-evidence", "aws:rds", "aws:kms", "aws:secrets", "aws:ecs"}
        by_id = {n["id"]: n for n in body["nodes"]}
        for aid in aws_ids:
            state = by_id[aid]["connection_state"]
            assert state in ("not_applicable", "unknown"), f"{aid}={state}"

    def test_overall_not_falsely_healthy_without_ci(self, _reset_token) -> None:
        body = client.get("/v1/live-status").json()
        # repo_build is 'unknown' locally (no CI signal) -> overall cannot be healthy.
        assert body["overall_connection_state"] != "healthy"

    def test_no_secrets_in_payload(self, _reset_token) -> None:
        text = client.get("/v1/live-status").text
        for forbidden in ("AKIA", "sk-", "password", "tfstate", "CHANGE_ME"):
            assert forbidden not in text

    def test_wo_sync_never_claims_healthy(self, _reset_token) -> None:
        body = client.get("/v1/live-status").json()
        # We cannot verify SF/WO sync from this process; must be unknown, not healthy.
        assert body["summary"]["wo_sync"]["state"] == "unknown"


class TestLiveStatusDataFn:
    def test_build_live_status_runs_on_real_topology(self) -> None:
        topo = build_topology()
        out = build_live_status(topo["nodes"])
        assert out["overall_connection_state"] in CONNECTION_STATES
        # api-server has a live probe and should be healthy locally.
        api = next(n for n in out["nodes"] if n["id"] == "service:api-server")
        assert api["connection_state"] == "healthy"
