"""Tests for certificate signing semantics.

Proves:
- Dev signing has honest limitation labels
- KMS sealed mode is labeled correctly
- No public-verification claim is made without asymmetric signing
"""

from __future__ import annotations

import os
from unittest.mock import patch

from notary_platform.certificates import _signing_algorithm, generate_certificate, verify_certificate_signature


class TestCertificateSemantics:
    def test_dev_signing_has_limitation(self) -> None:
        cert = generate_certificate(
            incident_id="inc-000001",
            original_decision="DENY",
            mutated_decision="APPROVE",
            fix_config={"threshold": 620},
        )
        assert cert["signing_algorithm"] == "HMAC-SHA256-DEV"
        assert "signing_note" in cert
        assert "public-key" not in cert.get("signing_algorithm", "").lower()

    def test_dev_signing_not_independently_verifiable(self) -> None:
        cert = generate_certificate(
            incident_id="inc-000001",
            original_decision="DENY",
            mutated_decision="APPROVE",
            fix_config={},
        )
        assert "Dev" in cert["signing_note"]
        assert "not independently verifiable" in cert["signing_note"]

    def test_kms_mode_labeled_correctly(self) -> None:
        with patch.dict(os.environ, {"NOTARY_KMS_KEY_ARN": "arn:aws:kms:us-east-1:123456:key/mock"}):
            with patch("notary_platform.certificates._sign", return_value="kms:mocked"):
                assert _signing_algorithm() == "KMS_ENCRYPT_DECRYPT"

                cert = generate_certificate(
                    incident_id="inc-000001",
                    original_decision="DENY",
                    mutated_decision="APPROVE",
                    fix_config={},
                )
                assert cert["signing_algorithm"] == "KMS_ENCRYPT_DECRYPT"
                assert "server-side only" in cert["signing_note"]
                assert "not a public-key signature" in cert["signing_note"]

    def test_certificate_scope_disclaimer_present(self) -> None:
        cert = generate_certificate(
            incident_id="inc-000001",
            original_decision="DENY",
            mutated_decision="APPROVE",
            fix_config={},
        )
        assert "claim_scope" in cert
        assert "not certify general AI safety" in cert["claim_scope"]

    def test_tampered_cert_still_fails(self) -> None:
        cert = generate_certificate(
            incident_id="inc-000001",
            original_decision="DENY",
            mutated_decision="APPROVE",
            fix_config={"threshold": 620},
        )
        assert verify_certificate_signature(cert) is True
        cert["mutated_decision"] = "DENY"
        assert verify_certificate_signature(cert) is False
