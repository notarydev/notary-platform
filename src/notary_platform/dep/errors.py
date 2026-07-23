"""DEP error hierarchy — all validation and conformance errors use these types."""

from __future__ import annotations

from typing import Any


class DepError(Exception):
    """Base for all DEP errors."""

    code: str
    message: str
    json_pointer: str
    resource_id: str
    details: dict[str, Any]
    retryable: bool
    remediation: str

    def __init__(
        self,
        code: str,
        message: str,
        json_pointer: str = "",
        resource_id: str = "",
        details: dict[str, Any] | None = None,
        retryable: bool = False,
        remediation: str = "",
    ) -> None:
        self.code = code
        self.message = message
        self.json_pointer = json_pointer
        self.resource_id = resource_id
        self.details = details or {}
        self.retryable = retryable
        self.remediation = remediation
        super().__init__(f"[{code}] {message}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "json_pointer": self.json_pointer,
            "resource_id": self.resource_id,
            "details": self.details,
            "retryable": self.retryable,
            "remediation": self.remediation,
        }


class SchemaValidationError(DepError):
    """A DEP resource failed schema validation."""

    def __init__(
        self,
        message: str,
        json_pointer: str = "",
        resource_id: str = "",
        details: dict[str, Any] | None = None,
        remediation: str = "Review the resource payload against the published schema.",
    ) -> None:
        super().__init__(
            code="dep_schema_invalid",
            message=message,
            json_pointer=json_pointer,
            resource_id=resource_id,
            details=details,
            retryable=False,
            remediation=remediation,
        )


class DigestMismatchError(DepError):
    """The declared digest does not match the recomputed digest."""

    def __init__(
        self,
        message: str,
        json_pointer: str = "",
        resource_id: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="resource_digest_mismatch",
            message=message,
            json_pointer=json_pointer,
            resource_id=resource_id,
            details=details,
            retryable=False,
            remediation="Recompute the digest from canonical JSON and update the envelope.",
        )


class VersionUnsupportedError(DepError):
    """The DEP protocol version is not supported."""

    def __init__(
        self,
        message: str,
        json_pointer: str = "",
        resource_id: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="dep_version_unsupported",
            message=message,
            json_pointer=json_pointer,
            resource_id=resource_id,
            details=details,
            retryable=False,
            remediation="Use a supported protocol version (0.1.x).",
        )


class ResourceIdentityConflictError(DepError):
    """A resource with the same identity but different content was received."""

    def __init__(
        self,
        message: str,
        json_pointer: str = "",
        resource_id: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="resource_identity_conflict",
            message=message,
            json_pointer=json_pointer,
            resource_id=resource_id,
            details=details,
            retryable=False,
            remediation="Resolve the identity conflict or use a new resource ID.",
        )


class SchemaNotFoundError(DepError):
    """The requested schema is not registered in the schema registry."""

    def __init__(
        self,
        message: str,
        json_pointer: str = "",
        resource_id: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="dep_schema_not_found",
            message=message,
            json_pointer=json_pointer,
            resource_id=resource_id,
            details=details,
            retryable=True,
            remediation="Check that the schema file exists in the registry directory.",
        )
