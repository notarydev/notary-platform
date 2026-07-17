"""Tests for the Command Center status APIs (WO-30).

Covers response shape, status labeling, redaction, and read-only/auth behavior
for the viz endpoints.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from notary_platform.api_server.main import app
from notary_platform.api_server.routers.topology_data import (
    MATURITIES,
    NODE_TYPES,
    STATUSES,
    build_build_info,
    build_topology,
)
from notary_platform.config import SETTINGS

client = TestClient(app)


class TestTopologyShape:
    def test_topology_returns_nodes(self) -> None:
        resp = client.get("/v1/topology")
        assert resp.status_code == 200
        body = resp.json()
        assert "nodes" in body
        assert "edges" in body
        assert "blockers" in body
        assert "maturity_stage" in body
        assert body["maturity_stage"] in MATURITIES

    def test_every_node_has_required_fields(self) -> None:
        body = client.get("/v1/topology").json()
        required = {
            "id", "node_type", "name", "plain_purpose", "why_it_matters",
            "dependencies", "status", "maturity",
        }
        for node in body["nodes"]:
            assert required.issubset(node.keys())
            assert node["node_type"] in NODE_TYPES
            assert node["status"] in STATUSES
            assert node["maturity"] in MATURITIES

    def test_edges_reference_real_nodes(self) -> None:
        body = client.get("/v1/topology").json()
        ids = {n["id"] for n in body["nodes"]}
        for edge in body["edges"]:
            assert edge["source"] in ids
            assert edge["target"] in ids
            assert edge["kind"] in ("dependency", "future")

    def test_legacy_shape_retained(self) -> None:
        body = client.get("/v1/topology").json()
        assert "stages" in body
        assert "legacy_edges" in body


class TestStatusLabeling:
    def test_unknown_is_reported_not_green(self) -> None:
        """Unknown/blocked nodes surface as blockers, never as complete."""
        body = client.get("/v1/topology").json()
        blocker_ids = {b["id"] for b in body["blockers"]}
        # the neutral replay sandbox is 'unknown' and must appear as a blocker.
        assert "external:replay-sandbox" in blocker_ids
        # no blocker should be labeled complete.
        for b in body["blockers"]:
            assert b["status"] != "complete"

    def test_node_has_dependents(self) -> None:
        body = client.get("/v1/topology").json()
        api = next(n for n in body["nodes"] if n["id"] == "service:api-server")
        assert "repository:notary-sdk" in api["dependents"]
        # replay-sandbox has no dependents (leaf external dep).
        sandbox = next(n for n in body["nodes"] if n["id"] == "external:replay-sandbox")
        assert sandbox["dependents"] == []

    def test_future_nodes_marked_future(self) -> None:
        body = client.get("/v1/topology").json()
        futures = [n for n in body["nodes"] if n["node_type"] == "future_capability"]
        assert futures
        for n in futures:
            assert n["status"] == "future"


class TestRedaction:
    def test_no_secrets_in_topology(self) -> None:
        text = client.get("/v1/topology").text
        for forbidden in ("AKIA", "sk-", "password", "tfstate", "CHANGE_ME"):
            assert forbidden not in text

    def test_no_secrets_in_build_info(self) -> None:
        text = client.get("/v1/build-info").text
        for forbidden in ("AKIA", "sk-", "password", "tfstate", "CHANGE_ME"):
            assert forbidden not in text

    def test_build_info_unknown_is_explicit(self) -> None:
        """Commit values are either real SHAs or the literal 'unknown' — never empty."""
        body = client.get("/v1/build-info").json()
        import re

        sha = re.compile(r"^[0-9a-f]{7,40}$")
        for key in ("platform_commit", "sdk_commit", "viz_commit"):
            val = body[key]
            assert val == "unknown" or sha.match(val), f"{key}={val!r} neither SHA nor 'unknown'"


class TestBuildInfoShape:
    def test_build_info_fields(self) -> None:
        resp = client.get("/v1/build-info")
        assert resp.status_code == 200
        body = resp.json()
        for key in (
            "version", "ci_status", "generated_at", "platform_commit",
            "sdk_commit", "viz_commit", "environment", "api_base_url",
            "known_limitations",
        ):
            assert key in body
        assert body["environment"] in ("local", "aws-prototype")
        assert isinstance(body["known_limitations"], list)


class TestReadOnlyBehavior:
    def test_topology_requires_no_auth(self) -> None:
        # status endpoints are auth-optional by design (demo-only; WO-33 hardens).
        resp = client.get("/v1/topology")
        assert resp.status_code == 200

    def test_build_info_requires_no_auth(self) -> None:
        resp = client.get("/v1/build-info")
        assert resp.status_code == 200


class TestCommandCenterAuth:
    @pytest.fixture(autouse=True)
    def _cc_token(self):
        prev = SETTINGS.command_center_token
        SETTINGS.command_center_token = "secret-cc"
        try:
            yield
        finally:
            SETTINGS.command_center_token = prev

    def test_missing_token_rejected_when_configured(self) -> None:
        resp = client.get("/v1/topology")
        assert resp.status_code == 401

    def test_valid_token_accepted(self) -> None:
        resp = client.get("/v1/topology", headers={"X-Command-Center-Token": "secret-cc"})
        assert resp.status_code == 200

    def test_bearer_token_accepted(self) -> None:
        resp = client.get("/v1/build-info", headers={"Authorization": "Bearer secret-cc"})
        assert resp.status_code == 200

    def test_wrong_token_rejected(self) -> None:
        resp = client.get("/v1/topology", headers={"X-Command-Center-Token": "nope"})
        assert resp.status_code == 401


class TestDataFunctions:
    def test_build_topology_is_deterministic_in_shape(self) -> None:
        a = build_topology()
        b = build_topology()
        assert len(a["nodes"]) == len(b["nodes"])
        assert a["maturity_stage"] == b["maturity_stage"]

    def test_build_info_has_unknown_defaults(self) -> None:
        info = build_build_info()
        assert info["ci_status"] == "unknown"
        assert info["environment"] == "local"
