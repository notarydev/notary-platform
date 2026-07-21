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

SCHEMA_VERSION = "pom-v1"

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
    kms_arn = os.getenv("NOTARY_KMS_KEY_ARN")
    if kms_arn:
        return "KMS_ENCRYPT_DECRYPT"  # KMS-sealed, not publicly verifiable
    return "HMAC-SHA256-DEV"  # Dev-only, not production-grade


def _sign(cert: dict[str, Any]) -> str:
    """Return a tamper-evident seal over the certificate content (excluding signature).

    ⚠️ Known limitation: This is NOT a public-key independent signature.
    Production uses AWS KMS symmetric ENCRYPT_DECRYPT which produces a KMS-sealed
    artifact — it is verifiable only by the same KMS key (server-side). Local/prototype
    uses an HMAC dev key. Neither mode produces an independently verifiable
    public-key signature.

    For public-key verification (SIGN_VERIFY), a future version will use KMS asymmetric
    keys or a customer-managed signing key.
    """
    payload = {k: v for k, v in cert.items() if k != "signature"}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    kms_arn = os.getenv("NOTARY_KMS_KEY_ARN")
    if kms_arn:
        import base64

        import boto3

        kms = boto3.client("kms")
        out = kms.encrypt(KeyId=kms_arn, Plaintext=canonical.encode("utf-8"))
        return "kms:" + base64.b64encode(out["CiphertextBlob"]).decode("ascii")

    return hmac.new(
        _DEV_SIGNING_KEY, canonical.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def generate_certificate(
    incident_id: str,
    original_decision: Any,
    mutated_decision: Any,
    fix_config: dict[str, Any],
    certificate_id: str | None = None,
    replay_result: dict[str, Any] | None = None,
    expected_correct_behavior: str = "",
    root_hash: str = "",
    integrity_status: str = "unverified",
    replay_method: str = "sealed cassette replay",
    verified_outcome: bool = True,
    timestamp: str = "",
    claim_scope: str = "",
) -> dict[str, Any]:
    """Create a Proof of Mitigation certificate and sign it."""
    signing_alg = _signing_algorithm()
    is_kms = signing_alg == "KMS_ENCRYPT_DECRYPT"
    signing_note = (
        "KMS-sealed (ENCRYPT_DECRYPT): verifiable server-side only, not a public-key signature"
        if is_kms
        else "Dev HMAC-SHA256: not production-grade, not independently verifiable"
    )
    cert: dict[str, Any] = {
        "certificate_id": certificate_id or f"proof-{uuid.uuid4().hex}",
        "certificate_type": "proof_of_mitigation",
        "schema_version": SCHEMA_VERSION,
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
        "signing_algorithm": signing_alg,
        "signing_note": signing_note,
        "known_limitations": "dev-or-KMS signing; not a general AI safety certificate",
        "claim_scope": (
            claim_scope
            or "Verified fix for this tested scenario under recorded conditions. "
            "Does not certify general AI safety, fairness, "
            "regulatory compliance, or outside tested scenario."
        ),
        "certificate_uuid": uuid.uuid4().hex,
    }
    cert["signature"] = _sign(cert)
    return cert


def verify_certificate_signature(cert: dict[str, Any]) -> bool:
    """Verify the certificate seal.

    For KMS seals we decrypt the stored ciphertext and compare it to the
    recomputed canonical payload — only the KMS key can produce a ciphertext
    that decrypts back to the exact payload, proving integrity + authenticity.
    """
    sig = cert.get("signature", "")
    if not sig:
        return False
    payload = {k: v for k, v in cert.items() if k != "signature"}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    if sig.startswith("kms:"):
        import base64

        import boto3

        kms_arn = os.getenv("NOTARY_KMS_KEY_ARN")
        if not kms_arn:
            return False
        kms = boto3.client("kms")
        try:
            out = kms.decrypt(KeyId=kms_arn, CiphertextBlob=base64.b64decode(sig[len("kms:"):]))
        except Exception:
            return False
        return bool(out["Plaintext"] == canonical.encode("utf-8"))

    expected = hmac.new(
        _DEV_SIGNING_KEY, canonical.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return bool(hmac.compare_digest(sig, expected))
