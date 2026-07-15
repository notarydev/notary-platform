"""Proof of Mitigation certificate — local dev signing for MVP."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

_DEV_SIGNING_KEY = b"notary-dev-signing-key-mvp-only"


def generate_certificate(
    incident_id: str,
    original_decision: Any,
    mutated_decision: Any,
    fix_config: dict[str, Any],
    replay_method: str = "sealed cassette replay",
    verified_outcome: bool = True,
    timestamp: str = "",
) -> dict[str, Any]:
    """Create a Proof of Mitigation certificate and sign it."""
    cert: dict[str, Any] = {
        "certificate_type": "proof_of_mitigation",
        "incident_id": incident_id,
        "original_decision": original_decision,
        "mutated_decision": mutated_decision,
        "fix_config": fix_config,
        "replay_method": replay_method,
        "verified_outcome": verified_outcome,
        "timestamp": timestamp,
    }
    cert["signature"] = _sign(cert)
    return cert


def _sign(cert: dict[str, Any]) -> str:
    """HMAC-SHA256 signature over the certificate content (excluding signature)."""
    payload = {k: v for k, v in cert.items() if k != "signature"}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hmac.new(
        _DEV_SIGNING_KEY, canonical.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def verify_certificate_signature(cert: dict[str, Any]) -> bool:
    """Verify the certificate signature using the dev signing key."""
    sig = cert.get("signature", "")
    if not sig:
        return False
    expected = _sign(cert)
    return hmac.compare_digest(sig, expected)
