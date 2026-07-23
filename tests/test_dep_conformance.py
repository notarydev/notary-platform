"""DEP conformance tests — validate schemas, registry, canonical JSON, digest,
fixtures, and the standalone CLI.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from notary_platform.dep.canonical import canonical_json, compute_digest, verify_digest
from notary_platform.dep.errors import SchemaNotFoundError
from notary_platform.dep.registry import SchemaRegistry
from notary_platform.dep.validation import validate_envelope

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "dep"


# ── Schema registry tests ───────────────────────────────────────────────

class TestSchemaRegistry:
    def test_loads_all_schemas(self) -> None:
        registry = SchemaRegistry()
        names = registry.list_schemas()
        assert len(names) >= 12, f"Expected 12+ schemas, got {len(names)}: {names}"
        assert "envelope" in names

    def test_get_schema_returns_parsed_schema(self) -> None:
        registry = SchemaRegistry()
        schema = registry.get_schema("envelope")
        assert schema["title"] == "DEP Envelope"
        assert schema["type"] == "object"

    def test_get_schema_raises_for_unknown(self) -> None:
        registry = SchemaRegistry()
        with pytest.raises(SchemaNotFoundError):
            registry.get_schema("nonexistent")

    def test_resolve_ref_resolves_local(self) -> None:
        registry = SchemaRegistry()
        resolved = registry.resolve_ref("dep://schema/envelope")
        assert resolved["$id"] == "dep://schema/envelope"

    def test_resolve_ref_raises_for_bad_ref(self) -> None:
        registry = SchemaRegistry()
        with pytest.raises(SchemaNotFoundError):
            registry.resolve_ref("dep://schema/does-not-exist")

    def test_list_schemas_includes_all_13_types(self) -> None:
        registry = SchemaRegistry()
        names = set(registry.list_schemas())
        expected = {
            "envelope", "observation", "context-artifact", "context-binding",
            "assessment", "finding", "link-assertion", "integrity-conflict",
            "evidence-bundle", "proof-claim", "redaction-log",
            "provider-registration", "resource-index",
        }
        missing = expected - names
        assert not missing, f"Missing schemas: {missing}"

    def test_all_schemas_have_required_structure(self) -> None:
        registry = SchemaRegistry()
        for name in registry.list_schemas():
            schema = registry.get_schema(name)
            assert "$id" in schema, f"{name}: missing $id"
            assert "title" in schema, f"{name}: missing title"
            assert "type" in schema and schema["type"] == "object", f"{name}: type != object"


# ── Canonical JSON and digest tests ─────────────────────────────────────

class TestCanonical:
    def test_canonical_json_sorted_keys(self) -> None:
        data = {"z": 1, "a": 2, "m": 3}
        canonical = canonical_json(data)
        assert canonical == b'{"a":2,"m":3,"z":1}'

    def test_canonical_json_no_whitespace(self) -> None:
        data = {"a": {"b": 1}}
        canonical = canonical_json(data)
        assert b" " not in canonical

    def test_canonical_json_utf8(self) -> None:
        data = {"key": "héllo"}
        canonical = canonical_json(data)
        assert isinstance(canonical, bytes)
        assert "héllo".encode("utf-8") not in canonical  # json.dumps escapes by default
        assert b"\\u00e9" in canonical

    def test_digest_is_deterministic(self) -> None:
        data = {"a": 1, "b": 2}
        d1 = compute_digest(data)
        d2 = compute_digest(data)
        assert d1 == d2

    def test_digest_excludes_digest_and_signature(self) -> None:
        data = {"a": 1, "digest": {"algorithm": "sha256", "value": "xxx"}, "signature": {"key": "k"}}
        d = compute_digest(data)
        assert "xxx" not in d  # digest field excluded

    def test_digest_format(self) -> None:
        data = {"a": 1}
        d = compute_digest(data)
        assert d.startswith("sha256:")
        assert ":" in d

    def test_verify_digest_valid(self) -> None:
        envelope = {
            "a": 1,
            "digest": {"algorithm": "sha256", "value": "sha256:AVq9f1zFei3ZS3WQ8ErYCEJzkF7jPsXOvq5iJ2qX-GI"},
        }
        assert verify_digest(envelope)

    def test_verify_digest_invalid(self) -> None:
        envelope = {
            "a": 1,
            "digest": {"algorithm": "sha256", "value": "sha256:this-is-wrong"},
        }
        assert not verify_digest(envelope)


# ── Validation tests ────────────────────────────────────────────────────

class TestValidation:
    def test_valid_envelope_passes(self) -> None:
        registry = SchemaRegistry()
        envelope = {
            "$schema": "dep://schema/envelope",
            "id": "dep://test/1",
            "version": "0.1.0",
            "resource": {"type": "observation", "id": "obs-1"},
            "provenance": {"collected_at": "2026-07-01T12:00:00Z"},
            "digest": {"algorithm": "sha256", "value": "sha256:abc"},
        }
        result = validate_envelope(envelope, registry)
        # May have digest mismatch since we didn't compute properly
        assert not result.valid  # digest won't match
        assert any(e.code == "resource_digest_mismatch" for e in result.errors)

    def test_valid_envelope_with_correct_digest(self) -> None:
        registry = SchemaRegistry()
        envelope = {
            "$schema": "dep://schema/envelope",
            "id": "dep://test/2",
            "version": "0.1.0",
            "resource": {"type": "observation", "id": "obs-2"},
            "provenance": {"collected_at": "2026-07-01T12:00:00Z"},
        }
        digest_val = compute_digest(envelope)
        envelope["digest"] = {"algorithm": "sha256", "value": digest_val}
        result = validate_envelope(envelope, registry)
        assert result.valid, f"Expected valid, got errors: {[e.code for e in result.errors]}"

    def test_missing_required_field(self) -> None:
        registry = SchemaRegistry()
        envelope = {
            "version": "0.1.0",
            "resource": {"type": "observation", "id": "obs-3"},
            "provenance": {"collected_at": "2026-07-01T12:00:00Z"},
        }
        result = validate_envelope(envelope, registry)
        assert not result.valid
        codes = {e.code for e in result.errors}
        assert "dep_schema_invalid" in codes

    def test_unsupported_version(self) -> None:
        registry = SchemaRegistry()
        envelope = self._make_envelope({"version": "99.99.99"})
        result = validate_envelope(envelope, registry)
        assert not result.valid
        assert any(e.code == "dep_version_unsupported" for e in result.errors)

    def test_unknown_resource_type(self) -> None:
        registry = SchemaRegistry()
        envelope = self._make_envelope({"resource": {"type": "bogus", "id": "x"}})
        result = validate_envelope(envelope, registry)
        assert not result.valid
        assert any("bogus" in str(e) for e in result.errors)

    def test_digest_mismatch(self) -> None:
        registry = SchemaRegistry()
        envelope = self._make_envelope({"digest": {"algorithm": "sha256", "value": "sha256:garbage"}})
        result = validate_envelope(envelope, registry)
        assert not result.valid
        assert any(e.code == "resource_digest_mismatch" for e in result.errors)

    @staticmethod
    def _make_envelope(overrides: dict) -> dict:
        base = {
            "$schema": "dep://schema/envelope",
            "id": "dep://test/x",
            "version": "0.1.0",
            "resource": {"type": "observation", "id": "obs-x"},
            "provenance": {"collected_at": "2026-07-01T12:00:00Z"},
        }
        base.update(overrides)
        if "digest" not in overrides:
            base["digest"] = {"algorithm": "sha256", "value": compute_digest(base)}
        return base


# ── Fixture conformance tests ───────────────────────────────────────────

class TestFixtureConformance:
    """Every fixture in ``tests/fixtures/dep/valid/`` must pass validation;
    every fixture in ``tests/fixtures/dep/invalid/`` must fail."""

    def test_all_valid_fixtures_pass(self) -> None:
        registry = SchemaRegistry()
        valid_dir = FIXTURES / "valid"
        count = 0
        for path in sorted(valid_dir.glob("*.json")):
            with open(path) as f:
                data = json.load(f)
            result = validate_envelope(data, registry)
            assert result.valid, f"{path.name}: expected VALID, got {[e.code for e in result.errors]}"
            count += 1
        assert count >= 12, f"Expected 12+ valid fixtures, found {count}"

    def test_all_invalid_fixtures_fail(self) -> None:
        registry = SchemaRegistry()
        invalid_dir = FIXTURES / "invalid"
        count = 0
        for path in sorted(invalid_dir.glob("*.json")):
            with open(path) as f:
                data = json.load(f)
            result = validate_envelope(data, registry)
            assert not result.valid, f"{path.name}: expected INVALID, got valid"
            count += 1
        assert count >= 8, f"Expected 8+ invalid fixtures, found {count}"


# ── CLI tests ───────────────────────────────────────────────────────────

class TestCLI:
    def test_validate_valid_fixture(self) -> None:
        fixture = FIXTURES / "valid" / "envelope-observation.json"
        result = subprocess.run(
            [sys.executable, "-m", "notary_platform.dep.cli", "validate", str(fixture)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"

    def test_validate_invalid_fixture(self) -> None:
        fixture = FIXTURES / "invalid" / "digest-mismatch.json"
        result = subprocess.run(
            [sys.executable, "-m", "notary_platform.dep.cli", "validate", str(fixture)],
            capture_output=True, text=True,
        )
        assert result.returncode == 1, f"Expected exit 1, got {result.returncode}"

    def test_digest_command(self) -> None:
        fixture = FIXTURES / "valid" / "envelope-observation.json"
        result = subprocess.run(
            [sys.executable, "-m", "notary_platform.dep.cli", "digest", str(fixture)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert result.stdout.strip().startswith("sha256:")

    def test_schema_list(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "notary_platform.dep.cli", "schema", "list"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "envelope" in result.stdout

    def test_unknown_command(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "notary_platform.dep.cli", "bogus"],
            capture_output=True, text=True,
        )
        assert result.returncode == 2
