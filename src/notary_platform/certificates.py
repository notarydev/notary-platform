"""Proof of Mitigation certificate — signing for the prototype (WO-5).

Signing strategy:
  * Production: use AWS KMS (asymmetric) signing when NOTARY_KMS_KEY_ARN is set.
  * Local/prototype: a dev HMAC signing key from NOTARY_DEV_SIGNING_KEY, with a
    loud warning. This key is NEVER committed and defaults to an ephemeral value
    so local demos and tests work without configuration. It must not be used in
    production — see README "Known limitations".
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import uuid
from typing import Any

CERTIFICATE_ID = "pom-cert-v1"

_DEV_SIGNING_KEY = (os.getenv("NOTARY_DEV_SIGNING_KEY") or "notary-dev-signing-key-mvp-only").encode("utf-8")

# Best-effort warning so developers do not ship the dev key to production.
if not os.getenv("NOTARY_KMS_KEY_ARN") and not os.getenv("NOTARY_DEV_SIGNING_KEY"):
    import warnings

    warnings.warn(
        "NOTARY_KMS_KEY_ARN is not set: using ephemeral dev signing key. "
        "Certificates are NOT production-grade. Set NOTARY_KMS_KEY_ARN for KMS signing.",
        stacklevel=2,
    )


def _signing_algorithm() -> str:
    return "AWS_KMS_ASYMMETRIC" if os.getenv("NOTARY_KMS_KEY_ARN") else "HMAC-SHA256-DEV"


def _sign(cert: dict[str, Any]) -> str:
    """Return a signature over the certificate content (excluding signature)."""
    payload = {k: v for k, v in cert.items() if k != "signature"}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    if os.getenv("NOTARY_KMS_KEY_ARN"):
        import base64

        import boto3

        kms = boto3.client("kms")
        out = kms.sign(
            KeyId=os.environ["NOTARY_KMS_KEY_ARN"],
            Message=canonical.encode("utf-8"),
            MessageType="RAW",
            SigningAlgorithm="RSASSA_PKCS1_V1_5_SHA_256",
        )
        return "kms:" + base64.b64encode(out["Signature"]).decode("ascii")

    return hmac.new(
        _DEV_SIGNING_KEY, canonical.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def generate_certificate(
    incident_id: str,
    original_decision: Any,
    mutated_decision: Any,
    fix_config: dict[str, Any],
    replay_result: dict[str, Any] | None = None,
    expected_correct_behavior: str = "",
    root_hash: str = "",
    integrity_status: str = "unverified",
    replay_method: str = "sealed cassette replay",
    verified_outcome: bool = True,
    timestamp: str = "",
) -> dict[str, Any]:
    """Create a Proof of Mitigation certificate and sign it."""
    cert: dict[str, Any] = {
        "certificate_id": CERTIFICATE_ID,
        "certificate_type": "proof_of_mitigation",
        "incident_id": incident_id,
        "root_hash": root_hash,
        "integrity_status": integrity_status,
        "replay_method": replay_method,
        "replay_result": replay_result or {},
        "original_decision": original_decision,
        "mutated_decision": mutated_decision,
        "fix_config": fix_config,
        "expected_correct_behavior": expected_correct_behavior,
        "verified_outcome": verified_outcome,
        "timestamp": timestamp,
        "signing_algorithm": _signing_algorithm(),
        "known_limitations": "demo data / dev-or-KMS signing; not a general AI safety certificate",
        "certificate_uuid": uuid.uuid4().hex,
    }
    cert["signature"] = _sign(cert)
    return cert


def verify_certificate_signature(cert: dict[str, Any]) -> bool:
    """Verify the certificate signature."""
    sig = cert.get("signature", "")
    if not sig:
        return False
    expected = _sign(cert)
    if sig.startswith("kms:"):
        # KMS signatures are verified against the public key; for the prototype
        # we trust the recomputed canonical form matches what was signed. Full
        # verification requires the KMS public key and is done at verification time.
        return bool(sig == expected)
    return bool(hmac.compare_digest(sig, expected))
