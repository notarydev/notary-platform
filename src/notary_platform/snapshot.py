"""SDK-compatible snapshot types for the platform.

These mirror the SDK's ``CapturedElement`` and ``ForensicSnapshot`` dataclasses
so the platform can deserialize snapshots produced by the SDK without importing
the SDK package directly.  The field names, canonical serialization, and
verification algorithms are kept identical.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

_HASH_LEN = 32


class CapturedElement:
    """Minimal snapshot element compatible with the SDK."""

    def __init__(
        self,
        kind: str = "",
        payload: dict[str, Any] | None = None,
        element_hash: str = "",
    ) -> None:
        self.kind = kind
        self.payload: dict[str, Any] = payload if payload is not None else {}
        self.element_hash = element_hash

    def canonical_bytes(self) -> bytes:
        """Deterministic JSON bytes for hashing (excludes element_hash)."""
        return json.dumps(
            {"kind": self.kind, "payload": self.payload},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "payload": self.payload, "element_hash": self.element_hash}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CapturedElement:
        return cls(
            kind=str(d.get("kind", "")),
            payload=dict(d.get("payload", {})),
            element_hash=str(d.get("element_hash", "")),
        )


class ForensicSnapshot:
    """Minimal snapshot model compatible with the SDK."""

    def __init__(
        self,
        schema_version: int = 0,
        timestamp: str = "",
        elements: list[CapturedElement] | None = None,
        merkle_chain: list[str] | None = None,
        root_hash: str = "",
    ) -> None:
        self.schema_version = schema_version
        self.timestamp = timestamp
        self.elements: list[CapturedElement] = elements if elements is not None else []
        self.merkle_chain: list[str] = merkle_chain if merkle_chain is not None else []
        self.root_hash = root_hash

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "timestamp": self.timestamp,
            "elements": [e.to_dict() for e in self.elements],
            "merkle_chain": self.merkle_chain,
            "root_hash": self.root_hash,
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ForensicSnapshot:
        elements_raw = d.get("elements", [])
        return cls(
            schema_version=int(d.get("schema_version", 0)),
            timestamp=str(d.get("timestamp", "")),
            elements=[CapturedElement.from_dict(e) for e in elements_raw],
            merkle_chain=list(d.get("merkle_chain", [])),
            root_hash=str(d.get("root_hash", "")),
        )

    @classmethod
    def from_json(cls, raw: str) -> ForensicSnapshot:
        return cls.from_dict(json.loads(raw))


def _seal_element(prev_hash: bytes, data: bytes, secret_key: bytes) -> bytes:
    """HMAC-SHA256 seal — mirrors notary.sealing.seal_element."""
    return hmac.new(secret_key, prev_hash + data, hashlib.sha256).digest()


def _compute_root_hash(element_hashes: list[bytes]) -> str:
    """Pairwise SHA-256 folding — mirrors notary.sealing.compute_root_hash."""
    if not element_hashes:
        raise ValueError("element_hashes must not be empty")
    current: list[bytes] = list(element_hashes)
    while len(current) > 1:
        next_round: list[bytes] = []
        for i in range(0, len(current), 2):
            left = current[i]
            right = current[i + 1] if i + 1 < len(current) else current[i]
            next_round.append(hashlib.sha256(left + right).digest())
        current = next_round
    return current[0].hex()


def verify_snapshot(snapshot: ForensicSnapshot, secret_key: bytes) -> bool:
    """Verify a snapshot locally — mirrors notary.verify.verify."""
    if not isinstance(secret_key, bytes) or not secret_key:
        return False
    if not snapshot.elements:
        return False

    prev_hash = b"\x00" * _HASH_LEN
    recomputed_hashes: list[bytes] = []

    for elem in snapshot.elements:
        recomputed = _seal_element(prev_hash, elem.canonical_bytes(), secret_key)
        recomputed_hashes.append(recomputed)

        if not isinstance(elem.element_hash, str) or not elem.element_hash:
            return False
        try:
            stored = bytes.fromhex(elem.element_hash)
        except ValueError:
            return False
        if len(stored) != _HASH_LEN:
            return False
        if not hmac.compare_digest(recomputed, stored):
            return False
        prev_hash = recomputed

    if not isinstance(snapshot.root_hash, str) or not snapshot.root_hash:
        return False
    try:
        recomputed_root = _compute_root_hash(recomputed_hashes)
    except ValueError:
        return False
    return hmac.compare_digest(recomputed_root, snapshot.root_hash)
