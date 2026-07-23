"""Backend-specific tests for PostgresS3Storage S3 path contract (WP-010)."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import MagicMock, patch

import boto3
import pytest

from notary_platform.config import SETTINGS
from notary_platform.storage import PostgresS3Storage


@pytest.fixture
def storage(monkeypatch):
    monkeypatch.setattr(SETTINGS, "evidence_bucket", "test-bucket")
    monkeypatch.setattr(SETTINGS, "evidence_prefix", "evidence/")

    fake_s3 = MagicMock()
    store: dict[str, bytes] = {}

    def put_object(Bucket, Key, Body, **kwargs):
        store[Key] = Body

    def get_object(Bucket, Key, **kwargs):
        data = store.get(Key)
        if data is None:
            from botocore.exceptions import ClientError
            raise ClientError({"Error": {"Code": "NoSuchKey", "Message": ""}}, "GetObject")
        return {"Body": BytesIO(data)}

    fake_s3.put_object.side_effect = put_object
    fake_s3.get_object.side_effect = get_object

    with patch.object(boto3.session.Session, "client", return_value=fake_s3):
        obj = PostgresS3Storage.__new__(PostgresS3Storage)
        obj._bucket = "test-bucket"
        obj._prefix = "evidence/"
        obj._s3 = fake_s3
        obj._session = boto3.session.Session()
        yield obj


class TestPostgresS3StorageContract:
    """S3 path contract: snapshot/certificate use fixed filenames; other evidence uses UUID subdirectories."""

    def test_snapshot_writes_fixed_path(self, storage):
        storage.persist_evidence("inc-1", "snapshot", {"root": "abc"})
        key = "evidence/inc-1/snapshot.json"
        assert any(
            call[1]["Key"] == key for call in storage._s3.put_object.call_args_list
        ), f"snapshot must be written to {key}"

    def test_snapshot_roundtrip(self, storage):
        snap = {"root_hash": "abc", "elements": [{"id": 1}]}
        storage.persist_evidence("inc-1", "snapshot", snap)
        assert storage.get_snapshot("inc-1") == snap

    def test_snapshot_none_when_missing(self, storage):
        assert storage.get_snapshot("no-such-incident") is None

    def test_certificate_writes_fixed_path(self, storage):
        storage.persist_evidence("inc-1", "certificate", {"claim": "test"})
        key = "evidence/inc-1/certificate.json"
        assert any(
            call[1]["Key"] == key for call in storage._s3.put_object.call_args_list
        ), f"certificate must be written to {key}"

    def test_certificate_roundtrip(self, storage):
        cert = {"claim": "test-mitigation", "signature": "sig123"}
        storage.persist_evidence("inc-1", "certificate", cert)
        assert storage.get_certificate("inc-1") == cert

    def test_certificate_none_when_missing(self, storage):
        assert storage.get_certificate("no-such-incident") is None

    def test_other_evidence_uses_uuid_path(self, storage):
        storage.persist_evidence("inc-1", "replay", {"status": "pass"})
        keys = [call[1]["Key"] for call in storage._s3.put_object.call_args_list]
        assert len(keys) == 1
        k = keys[0]
        assert k.startswith("evidence/inc-1/replay/")
        assert k.endswith(".json")
        assert k != "evidence/inc-1/replay.json"
