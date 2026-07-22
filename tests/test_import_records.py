"""Tests for the import records endpoint.

Proves:
- Import JSON records creates Verification Records
- Imported records appear in list
- Import handles array of records
- Import captures source_record_ref and business_function
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from notary_platform.api_server.main import app

client = TestClient(app)


class TestImportRecords:
    def _cleanup(self, ids: list[str]) -> None:
        pass  # In-memory storage resets between tests; no cleanup needed

    def test_import_single_record(self) -> None:
        """POST /v1/verification-records/import creates a VR."""
        resp = client.post(
            "/v1/verification-records/import",
            json={
                "workflow_id": "test-wf",
                "records": [
                    {
                        "source_record_ref": "TKT-001",
                        "source_system_id": "zendesk",
                        "business_function": "customer_support",
                        "elements": [
                            {"kind": "input", "sequence": 0, "payload": {"text": "Can I get a refund?"}},
                            {"kind": "decision", "sequence": 1, "payload": {"decision": "OFFER_REFUND"}},
                        ],
                    }
                ],
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["imported"] == 1
        assert len(data["records"]) == 1
        assert data["records"][0]["id"].startswith("vr-")

    def test_import_multiple_records(self) -> None:
        """Import handles multiple records."""
        resp = client.post(
            "/v1/verification-records/import",
            json={
                "records": [
                    {"source_record_ref": "TKT-001", "elements": [{"kind": "decision", "sequence": 0, "payload": {"decision": "DENY"}}]},
                    {"source_record_ref": "TKT-002", "elements": [{"kind": "decision", "sequence": 0, "payload": {"decision": "APPROVE"}}]},
                    {"source_record_ref": "TKT-003", "elements": [{"kind": "decision", "sequence": 0, "payload": {"decision": "ESCALATE"}}]},
                ],
            },
        )
        assert resp.status_code == 200
        assert resp.json()["imported"] == 3

    def test_import_captures_metadata(self) -> None:
        """Imported VR preserves source_record_ref and business_function."""
        resp = client.post(
            "/v1/verification-records/import",
            json={
                "records": [
                    {
                        "source_record_ref": "REF-TEST-42",
                        "business_function": "loan_underwriting",
                        "expected_outcome": "UNDERWRITING_REVIEW",
                        "elements": [{"kind": "decision", "sequence": 0, "payload": {"decision": "DENY"}}],
                    }
                ],
            },
        )
        assert resp.status_code == 200
        vr_id = resp.json()["records"][0]["id"]
        vr_resp = client.get(f"/v1/verification-records/{vr_id}")
        assert vr_resp.status_code == 200
        vr = vr_resp.json()
        assert vr["source_record_ref"] == "REF-TEST-42"
        assert vr["business_function"] == "loan_underwriting"

    def test_import_empty_records(self) -> None:
        """Empty records array returns zero imported."""
        resp = client.post(
            "/v1/verification-records/import",
            json={"records": []},
        )
        assert resp.status_code == 200
        assert resp.json()["imported"] == 0

    def test_imported_records_appear_in_list(self) -> None:
        """Imported records appear in the VR list."""
        before = client.get("/v1/verification-records").json()
        count_before = len(before)
        client.post(
            "/v1/verification-records/import",
            json={"records": [{"source_record_ref": "LIST-TEST", "elements": []}]},
        )
        after = client.get("/v1/verification-records").json()
        assert len(after) == count_before + 1
