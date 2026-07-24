"""Conformance tests for source profiling and mapping (WP-040).

Covers:
  - POST /v1/discovery/sources
  - GET /v1/discovery/sources
  - GET /v1/discovery/sources/{id}
  - POST /v1/discovery/sources/{id}/profile
  - GET /v1/discovery/sources/{id}/profiles/{profile_id}
  - POST /v1/discovery/sources/{id}/mappings/propose
  - POST /v1/discovery/sources/{id}/mappings
  - GET /v1/discovery/sources/{id}/coverage
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from notary_platform.api_server.main import app
from notary_platform.api_server.routers.source_profiling import storage

client = TestClient(app)


def _reset_storage() -> None:
    storage._source_connections.clear()
    storage._source_profiles.clear()
    storage._field_mappings.clear()


SAMPLE_RECORDS = [
    {"id": "1", "amount": 100, "outcome": "approve", "customer_id": "c1", "created_at": "2025-06-01T00:00:00Z"},
    {"id": "2", "amount": 200, "outcome": "deny", "customer_id": "c2", "created_at": "2025-06-02T00:00:00Z"},
    {"id": "3", "amount": None, "outcome": "approve", "customer_id": "c3", "created_at": "2025-06-03T00:00:00Z"},
]


class TestSourceConnections:
    def setup_method(self) -> None:
        _reset_storage()

    def test_create_source(self) -> None:
        resp = client.post("/v1/discovery/sources", json={
            "name": "Test CSV",
            "source_type": "file",
            "adapter_type": "csv_import",
        })
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["name"] == "Test CSV"
        assert data["source_type"] == "file"
        assert data["id"].startswith("src-")

    def test_list_sources(self) -> None:
        client.post("/v1/discovery/sources", json={"name": "A", "source_type": "file"})
        client.post("/v1/discovery/sources", json={"name": "B", "source_type": "api"})
        resp = client.get("/v1/discovery/source-connections")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_get_source(self) -> None:
        create = client.post("/v1/discovery/sources", json={"name": "GetTest", "source_type": "dep"}).json()
        resp = client.get(f"/v1/discovery/source-connections/{create['id']}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "GetTest"

    def test_get_source_not_found(self) -> None:
        resp = client.get("/v1/discovery/source-connections/nonexistent")
        assert resp.status_code == 404


class TestSourceProfiling:
    def setup_method(self) -> None:
        _reset_storage()

    def _create_source(self) -> str:
        return client.post("/v1/discovery/sources", json={
            "name": "ProfileTest",
            "source_type": "file",
        }).json()["id"]

    def test_profile_records(self) -> None:
        sid = self._create_source()
        resp = client.post(f"/v1/discovery/source-connections/{sid}/profile", json={
            "records": SAMPLE_RECORDS,
        })
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "completed"
        assert data["record_count"] == 3
        assert len(data["field_profiles"]) > 0

    def test_profile_empty_records_rejected(self) -> None:
        sid = self._create_source()
        resp = client.post(f"/v1/discovery/source-connections/{sid}/profile", json={"records": []})
        assert resp.status_code == 422

    def test_get_profile(self) -> None:
        sid = self._create_source()
        prof = client.post(f"/v1/discovery/source-connections/{sid}/profile", json={
            "records": SAMPLE_RECORDS,
        }).json()
        resp = client.get(f"/v1/discovery/source-connections/{sid}/profiles/{prof['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == prof["id"]

    def test_get_profile_not_found(self) -> None:
        resp = client.get("/v1/discovery/source-connections/fake-source/profiles/nonexistent")
        assert resp.status_code == 404


class TestFieldMapping:
    def setup_method(self) -> None:
        _reset_storage()

    def _create_source_and_profile(self) -> str:
        sid = client.post("/v1/discovery/sources", json={
            "name": "MappingTest",
            "source_type": "file",
        }).json()["id"]
        client.post(f"/v1/discovery/source-connections/{sid}/profile", json={"records": SAMPLE_RECORDS})
        return sid

    def test_propose_mappings(self) -> None:
        sid = self._create_source_and_profile()
        resp = client.post(f"/v1/discovery/source-connections/{sid}/mappings/propose")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "inferred"
        assert len(data["mappings"]) > 0

    def test_confirm_mapping(self) -> None:
        sid = self._create_source_and_profile()
        proposed = client.post(f"/v1/discovery/source-connections/{sid}/mappings/propose").json()
        resp = client.post(f"/v1/discovery/source-connections/{sid}/mappings", json={
            "mapping_id": proposed["id"],
        })
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "confirmed"

    def test_confirm_mapping_with_edits(self) -> None:
        sid = self._create_source_and_profile()
        proposed = client.post(f"/v1/discovery/source-connections/{sid}/mappings/propose").json()
        edits = [
            {"source_field": "amount", "dep_field": "amount", "confidence": "confirmed"},
        ]
        resp = client.post(f"/v1/discovery/source-connections/{sid}/mappings", json={
            "mapping_id": proposed["id"],
            "mappings": edits,
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "confirmed"

    def test_coverage(self) -> None:
        sid = self._create_source_and_profile()
        resp = client.get(f"/v1/discovery/source-connections/{sid}/coverage")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["profiled"] is True
        assert data["record_count"] == 3

    def test_coverage_no_profile(self) -> None:
        sid = client.post("/v1/discovery/sources", json={
            "name": "NoProfile",
            "source_type": "file",
        }).json()["id"]
        resp = client.get(f"/v1/discovery/source-connections/{sid}/coverage")
        assert resp.status_code == 200
        assert resp.json()["profiled"] is False
