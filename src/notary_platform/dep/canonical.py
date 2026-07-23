"""Canonical JSON serialization and digest computation for DEP.

Canonical form:
  - Serialize with sorted keys at every nesting level.
  - No whitespace between tokens.
  - UTF-8 encoding.
  - Use json.dumps(data, sort_keys=True, separators=(",", ":")).

Digest format (RFC 6920):
  {algorithm}:{base64url-encoded-hash}
"""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any


def canonical_json(data: dict[str, Any]) -> bytes:
    """Serialize *data* to canonical JSON bytes.

    Keys are sorted recursively (via ``sort_keys``).  The output is
    deterministic and suitable for digest computation.
    """
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_digest(data: dict[str, Any], algorithm: str = "sha256") -> str:
    """Compute a DEP-style digest for *data*.

    The envelope's ``digest`` and ``signature`` fields are excluded from
    the canonical input (a digest cannot include itself).
    """
    exclude_keys = {"digest", "signature"}
    payload = {k: v for k, v in data.items() if k not in exclude_keys}
    canonical = canonical_json(payload)
    h = hashlib.new(algorithm, canonical).digest()
    encoded = base64.urlsafe_b64encode(h).rstrip(b"=").decode("ascii")
    return f"{algorithm}:{encoded}"


def verify_digest(envelope: dict[str, Any]) -> bool:
    """Return ``True`` if the envelope's declared digest matches a recomputation."""
    declared = envelope.get("digest", {})
    algorithm = declared.get("algorithm", "sha256")
    expected = compute_digest(envelope, algorithm)
    return expected == declared.get("value", "")
