"""Notary Python SDK — minimal capture and seal client.

Produces snapshots compatible with the Notary Platform ingestion endpoint.
This is a local development package; install with `pip install -e packages/notary-sdk-py`.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class CapturedElement:
    kind: str
    payload: dict[str, Any]

    def canonical_bytes(self) -> bytes:
        parts = [self.kind.encode("utf-8")]
        for key in sorted(self.payload.keys()):
            value = self.payload[key]
            parts.append(f"{key}={value}".encode("utf-8"))
        return b"\n".join(parts)


def _seal_element(prev_hash: bytes, element_bytes: bytes, secret: bytes) -> bytes:
    return hmac.new(secret, prev_hash + element_bytes, hashlib.sha256).digest()


def _compute_root_hash(element_hashes: list[bytes]) -> str:
    root = b"\x00" * 32
    for h in element_hashes:
        root = hashlib.sha256(root + h).digest()
    return root.hex()


class RunCapture:
    """Capture an AI decision execution for Notary."""

    def __init__(self, secret_key: bytes | None = None, api_url: str = "", api_token: str = "") -> None:
        self.secret_key = secret_key or b"notary-dev-secret"
        self.api_url = api_url
        self.api_token = api_token
        self._elements: list[CapturedElement] = []

    def capture_llm(self, prompt: str, response: str, model: str = "", temperature: float = 0.0, seed: int | None = None) -> None:
        payload: dict[str, Any] = {"prompt": prompt, "response": response}
        if model:
            payload["model"] = model
        if temperature is not None:
            payload["temperature"] = temperature
        if seed is not None:
            payload["seed"] = seed
        self._elements.append(CapturedElement(kind="llm", payload=payload))

    def capture_tool(
        self,
        method: str,
        url: str,
        response: dict[str, Any],
        request_body: str = "",
        status: int = 200,
    ) -> None:
        self._elements.append(
            CapturedElement(
                kind="http",
                payload={
                    "request": {"method": method.upper(), "url": url, "body": request_body},
                    "response": response,
                    "status": status,
                },
            )
        )

    def capture_decision(self, decision: str, expected_correct_behavior: str = "") -> None:
        payload: dict[str, Any] = {"decision": decision}
        if expected_correct_behavior:
            payload["expected_correct_behavior"] = expected_correct_behavior
        self._elements.append(CapturedElement(kind="decision", payload=payload))

    def capture_retrieval(self, query: str, documents: list[str]) -> None:
        self._elements.append(CapturedElement(kind="retrieval", payload={"query": query, "documents": documents}))

    def capture_guardrail(self, check: str, passed: bool) -> None:
        self._elements.append(CapturedElement(kind="guardrail", payload={"check": check, "passed": passed}))

    def capture_human_action(self, source_record_ref: str, domain: str = "") -> None:
        payload: dict[str, Any] = {"source_record_ref": source_record_ref}
        if domain:
            payload["domain"] = domain
        self._elements.append(CapturedElement(kind="human", payload=payload))

    def capture_timestamp(self, timestamp: str | None = None) -> None:
        self._elements.append(
            CapturedElement(
                kind="timestamp",
                payload={"timestamp": timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
            )
        )

    def capture_rng_seed(self, seed: int) -> None:
        self._elements.append(CapturedElement(kind="rng_seed", payload={"seed": seed}))

    def finalize(self, agent_version: str = "", policy_version: str = "") -> "Snapshot":
        prev_hash = b"\x00" * 32
        elem_hashes: list[bytes] = []
        sealed: list[dict[str, Any]] = []
        for ce in self._elements:
            h = _seal_element(prev_hash, ce.canonical_bytes(), self.secret_key)
            elem_hashes.append(h)
            sealed.append({"kind": ce.kind, "payload": ce.payload, "element_hash": h.hex()})
            prev_hash = h

        root = _compute_root_hash(elem_hashes)
        snapshot = Snapshot(
            schema_version=1,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            elements=sealed,
            merkle_chain=[h.hex() for h in elem_hashes],
            root_hash=root,
            secret_key=self.secret_key,
            api_url=self.api_url,
            api_token=self.api_token,
            agent_version=agent_version,
            policy_version=policy_version,
        )
        return snapshot


@dataclass
class Snapshot:
    schema_version: int
    timestamp: str
    elements: list[dict[str, Any]]
    merkle_chain: list[str]
    root_hash: str
    secret_key: bytes
    api_url: str
    api_token: str
    agent_version: str = ""
    policy_version: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "timestamp": self.timestamp,
            "elements": self.elements,
            "merkle_chain": self.merkle_chain,
            "root_hash": self.root_hash,
            "agent_version": self.agent_version,
            "policy_version": self.policy_version,
        }

    def submit(
        self,
        source_system_id: str = "",
        source_record_ref: str = "",
        agent_id: str = "",
        business_function: str = "",
        environment_id: str = "env:demo",
        model_provider: str = "",
        model_name: str = "",
        label_source: str = "",
        expected_outcome: str = "",
    ) -> dict[str, Any]:
        """Submit snapshot to the Verification Record endpoint with metadata."""
        import requests

        snapshot = self.to_dict()
        # Attach metadata into the snapshot for the ingestion endpoint
        snapshot["source_system_id"] = source_system_id
        snapshot["source_record_ref"] = source_record_ref
        snapshot["agent_id"] = agent_id
        snapshot["business_function"] = business_function
        snapshot["environment_id"] = environment_id
        snapshot["model_provider"] = model_provider
        snapshot["model_name"] = model_name
        snapshot["label_source"] = label_source
        snapshot["expected_outcome"] = expected_outcome

        base_url = (self.api_url or "http://localhost:8000").rstrip("/")
        # Primary: submit to Verification Record endpoint
        url = base_url + "/v1/verification-records/from-snapshot"
        headers = {"Authorization": f"Bearer {self.api_token}", "Content-Type": "application/json"}
        response = requests.post(url, headers=headers, json=snapshot)
        if response.status_code == 404:
            # Fallback to legacy incidents endpoint
            url = base_url + "/v1/incidents/ingest"
            response = requests.post(url, headers=headers, json={"snapshot": self.to_dict()})
        response.raise_for_status()
        return response.json()


def verify_snapshot(snapshot_dict: dict[str, Any], secret_key: bytes) -> bool:
    """Verify a snapshot dictionary with the given secret key."""
    elements = snapshot_dict.get("elements", [])
    prev_hash = b"\x00" * 32
    elem_hashes: list[bytes] = []
    for e in elements:
        ce = CapturedElement(kind=e["kind"], payload=e["payload"])
        h = _seal_element(prev_hash, ce.canonical_bytes(), secret_key)
        elem_hashes.append(h)
        if h.hex() != e.get("element_hash"):
            return False
        prev_hash = h
    return _compute_root_hash(elem_hashes) == snapshot_dict.get("root_hash")


__all__ = ["RunCapture", "Snapshot", "verify_snapshot", "CapturedElement"]
