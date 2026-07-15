"""Response cassette — extract and match recorded responses from a snapshot."""

from __future__ import annotations

import hashlib
from typing import Any, Optional


def _call_signature(method: str, url: str, body: Optional[str] = None) -> str:
    """Compute a deterministic call signature for matching."""
    parts = [method.upper(), url]
    if body:
        parts.append(body)
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class ResponseCassette:
    """Extract recorded HTTP responses from a forensic snapshot.

    Matches calls by a deterministic signature derived from
    method / url / body.
    """

    def __init__(self, elements: list[dict[str, Any]]) -> None:
        self._entries: dict[str, dict[str, Any]] = {}
        for elem in elements:
            if elem.get("kind") != "http":
                continue
            payload = elem.get("payload", {})
            req = payload.get("request", {})
            if isinstance(req, dict):
                method = req.get("method", "GET")
                url = req.get("url", "")
                body = req.get("body")
            else:
                method = "GET"
                url = str(req)
                body = None
            sig = _call_signature(method, url, body)
            self._entries[sig] = {
                "method": method,
                "url": url,
                "response": payload.get("response"),
                "status": payload.get("status"),
            }

    def lookup(self, method: str, url: str, body: Optional[str] = None) -> Optional[dict[str, Any]]:
        """Look up a recorded response by call signature."""
        sig = _call_signature(method, url, body)
        entry = self._entries.get(sig)
        if entry is None:
            return None
        return {"response": entry["response"], "status": entry["status"]}

    def has_entry(self, method: str, url: str, body: Optional[str] = None) -> bool:
        return self.lookup(method, url, body) is not None

    @property
    def entry_count(self) -> int:
        return len(self._entries)
