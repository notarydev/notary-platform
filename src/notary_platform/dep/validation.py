"""DEP envelope validation — validates envelopes and resource payloads
against the published JSON Schemas using ``jsonschema``.
"""

from __future__ import annotations

from typing import Any

import jsonschema
from jsonschema import Draft202012Validator, FormatChecker

from notary_platform.dep.canonical import compute_digest
from notary_platform.dep.errors import (
    DepError,
    DigestMismatchError,
    SchemaNotFoundError,
    SchemaValidationError,
    VersionUnsupportedError,
)
from notary_platform.dep.registry import SchemaRegistry

SUPPORTED_VERSIONS = {"0.1.0"}


class ValidationResult:
    """Result of a validation pass."""

    def __init__(self) -> None:
        self._errors: list[DepError] = []

    def add_error(self, error: DepError) -> None:
        self._errors.append(error)

    def extend(self, errors: list[DepError]) -> None:
        self._errors.extend(errors)

    @property
    def valid(self) -> bool:
        return len(self._errors) == 0

    @property
    def errors(self) -> list[DepError]:
        return list(self._errors)

    def to_dicts(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._errors]


def validate_envelope(envelope: dict[str, Any], registry: SchemaRegistry) -> ValidationResult:
    """Validate an inner DEP resource envelope.

    The outer CloudEvents exchange envelope is a transport concern and has its
    own ``cloudevent-envelope`` schema. CloudEvents ingestion unwraps its
    ``data`` field before calling this validator.
    """
    result = ValidationResult()

    if not isinstance(envelope, dict):
        result.add_error(SchemaValidationError("Envelope must be a JSON object"))
        return result

    resource_id = envelope.get("resource", {}).get("id", "")

    # ── Step 1: validate the inner resource envelope structure ──
    envelope_schema = registry.get_schema("envelope")

    store: dict[str, dict[str, Any]] = {}
    for s in registry.list_schemas():
        sid = registry.get_schema(s).get("$id")
        if sid:
            store[sid] = registry.get_schema(s)
    resolver = jsonschema.RefResolver.from_schema(envelope_schema, store=store)

    validator = Draft202012Validator(envelope_schema, resolver=resolver, format_checker=FormatChecker())
    try:
        validator.validate(envelope)
    except jsonschema.ValidationError as e:
        _add_jsonschema_error(result, e, resource_id, "dep_schema_invalid")
        return result

    # ── Step 2: version gate ──
    version = envelope.get("version", "")
    if version not in SUPPORTED_VERSIONS:
        result.add_error(
            VersionUnsupportedError(
                f"DEP version '{version}' is not supported",
                json_pointer="/version",
                resource_id=resource_id,
                details={"version": version, "supported": sorted(SUPPORTED_VERSIONS)},
            )
        )

    # ── Step 3: verify resource type exists in registry ──
    resource_type = envelope.get("resource", {}).get("type", "")
    if resource_type:
        try:
            registry.get_schema(resource_type)
        except SchemaNotFoundError:
            result.add_error(
                SchemaValidationError(
                    f"Unknown resource type: '{resource_type}'",
                    json_pointer="/resource/type",
                    resource_id=resource_id,
                    details={"resource_type": resource_type},
                )
            )

    # ── Step 4: digest verification ──
    try:
        if not _check_digest(envelope):
            declared = envelope.get("digest", {}).get("value", "")
            expected = compute_digest(envelope)
            result.add_error(
                DigestMismatchError(
                    "Declared digest does not match recomputed digest",
                    json_pointer="/digest/value",
                    resource_id=resource_id,
                    details={
                        "declared": declared,
                        "expected": expected,
                        "algorithm": envelope.get("digest", {}).get("algorithm", "sha256"),
                    },
                )
            )
    except Exception as exc:
        result.add_error(
            SchemaValidationError(
                f"Digest computation failed: {exc}",
                resource_id=resource_id,
            )
        )

    return result


def _add_jsonschema_error(
    result: ValidationResult,
    e: jsonschema.ValidationError,
    resource_id: str,
    code: str,
) -> None:
    """Convert a ``jsonschema.ValidationError`` into a ``SchemaValidationError``
    and add it to the result.
    """
    path = "/" + "/".join(str(p) for p in e.absolute_path) if e.absolute_path else ""
    result.add_error(
        SchemaValidationError(
            message=e.message,
            json_pointer=path,
            resource_id=resource_id,
        )
    )


def _check_digest(envelope: dict[str, Any]) -> bool:
    declared = envelope.get("digest", {})
    algorithm = declared.get("algorithm", "sha256")
    expected = compute_digest(envelope, algorithm)
    return expected == declared.get("value", "")
