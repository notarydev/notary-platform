"""Response cassette — extract and match recorded responses from a snapshot."""

from __future__ import annotations

import hashlib
from typing import Any, Callable, Optional

from notary_platform.models import ReplayExecutionEvent


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

    def __init__(
        self,
        elements: list[dict[str, Any]],
        *,
        strict_order: bool = False,
        event_callback: Callable[[ReplayExecutionEvent], None] | None = None,
        event_sequence: int = 0,
    ) -> None:
        self._entries: dict[str, dict[str, Any]] = {}
        self._ordered_entries: list[dict[str, Any]] = []
        self._cursor = 0
        self._strict_order = strict_order
        self._misses: list[dict[str, Any]] = []
        self._event_callback = event_callback
        self._event_sequence = event_sequence
        for elem in elements:
            if elem.get("kind") not in {"http", "tool_call", "api_response"}:
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
            entry = {
                "method": method,
                "url": url,
                "body": body,
                "response": payload.get("response"),
                "status": payload.get("status"),
            }
            self._entries[sig] = entry
            self._ordered_entries.append(entry)

    def lookup(self, method: str, url: str, body: Optional[str] = None) -> Optional[dict[str, Any]]:
        """Look up a recorded response by call signature.

        Falls back to an exact-method+url+body match when a body-less lookup
        does not resolve, so agents may call ``lookup(method, url)`` without
        passing the recorded request body.
        """
        if self._strict_order:
            entry = self._ordered_entries[self._cursor] if self._cursor < len(self._ordered_entries) else None
            if entry is not None and self._matches(entry, method, url, body):
                self._cursor += 1
                self._emit_response_event(method, url, entry)
                return {"response": entry["response"], "status": entry["status"]}
            self._misses.append({"method": method.upper(), "url": url, "body": body})
            self._emit_miss_event(method, url)
            return None

        sig = _call_signature(method, url, body)
        entry = self._entries.get(sig)
        if entry is not None:
            self._emit_response_event(method, url, entry)
            return {"response": entry["response"], "status": entry["status"]}
        if body is None:
            for entry in self._entries.values():
                if (
                    entry.get("method", "").upper() == method.upper()
                    and entry.get("url") == url
                    and entry.get("body") is not None
                ):
                    self._emit_response_event(method, url, entry)
                    return {"response": entry["response"], "status": entry["status"]}
        self._misses.append({"method": method.upper(), "url": url, "body": body})
        self._emit_miss_event(method, url)
        return None

    def _emit_response_event(self, method: str, url: str, entry: dict[str, Any]) -> None:
        if self._event_callback:
            self._event_callback(ReplayExecutionEvent(
                step="System/tool response returned from cassette",
                source="cassette",
                expected=f"Match {method.upper()} {url}",
                actual=f"status={entry.get('status')}; response returned",
                status="pass",
                sequence=self._event_sequence,
            ))
            self._event_sequence += 1

    def _emit_miss_event(self, method: str, url: str) -> None:
        if self._event_callback:
            self._event_callback(ReplayExecutionEvent(
                step="System/tool response returned from cassette",
                source="cassette",
                expected=f"Match {method.upper()} {url}",
                actual="no recorded response",
                status="escalation_required",
                sequence=self._event_sequence,
            ))
            self._event_sequence += 1

    def has_entry(self, method: str, url: str, body: Optional[str] = None) -> bool:
        return self.lookup(method, url, body) is not None

    def _matches(self, entry: dict[str, Any], method: str, url: str, body: Optional[str]) -> bool:
        if entry.get("method", "").upper() != method.upper() or entry.get("url") != url:
            return False
        return body == entry.get("body") or (body is None and entry.get("body") is not None)

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    @property
    def consumed_count(self) -> int:
        return self._cursor

    @property
    def misses(self) -> list[dict[str, Any]]:
        return list(self._misses)

    @property
    def unconsumed_count(self) -> int:
        return max(0, len(self._ordered_entries) - self._cursor)
