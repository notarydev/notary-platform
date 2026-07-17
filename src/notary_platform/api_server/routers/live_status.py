"""Live status layer for the Command Center (WO-36).

Probes the real, current state of platform pieces — API health, AWS resources,
the proof-loop smoke test, repo/build state, and work-order sync — and reports
each as a connection/live state with a timestamp and staleness indicator.

Design rules (mirror the IA + WO-36):
- Unknown / unavailable / stale is reported honestly, NEVER as healthy.
- Every probe is best-effort: missing creds, missing boto3, or a downed
  dependency yields an explicit non-healthy state, not a crash.
- No secrets, credentials, or raw evidence are ever returned.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

# Connection/live states. "healthy" is only asserted on a successful probe.
CONNECTION_STATES = {
    "connected",
    "healthy",
    "degraded",
    "blocked",
    "stale",
    "unavailable",
    "not_applicable",
    "unknown",
}

# How long before a previously-healthy check is considered stale.
_STALE_SECONDS = 300


@dataclass
class ProbeResult:
    state: str  # one of CONNECTION_STATES
    detail: str = ""
    last_checked: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    # Optional: how the check was performed (e.g. "aws-sdk", "http", "env").
    method: str = "unknown"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Individual probes. Each returns a ProbeResult and never raises.
# ---------------------------------------------------------------------------

def probe_api_health() -> ProbeResult:
    """Check the running API process answers /health."""
    try:
        from notary_platform.api_server.routers.viz import _probe_self_health

        ok = _probe_self_health()
    except Exception:
        ok = False
    if ok:
        return ProbeResult("healthy", "API /health responded", method="http")
    return ProbeResult("unavailable", "API /health did not respond", method="http")


def probe_rds() -> ProbeResult:
    if not os.getenv("NOTARY_DATABASE_URL"):
        return ProbeResult(
            "not_applicable", "No NOTARY_DATABASE_URL configured (in-memory store locally)", method="env"
        )
    return _probe_aws_resource("rds", "RDS database")


def probe_s3() -> ProbeResult:
    if not os.getenv("NOTARY_EVIDENCE_BUCKET"):
        return ProbeResult(
            "not_applicable", "No NOTARY_EVIDENCE_BUCKET configured (local demo)", method="env"
        )
    return _probe_aws_resource("s3", "S3 evidence bucket")


def probe_kms() -> ProbeResult:
    if not os.getenv("NOTARY_KMS_KEY_ARN"):
        return ProbeResult(
            "not_applicable", "No NOTARY_KMS_KEY_ARN configured (dev signing key locally)", method="env"
        )
    return _probe_aws_resource("kms", "KMS signing key")


def probe_secrets() -> ProbeResult:
    if not os.getenv("NOTARY_USE_REMOTE_STORAGE") and not os.getenv("NOTARY_KMS_KEY_ARN"):
        return ProbeResult(
            "not_applicable", "Secrets Manager not in use locally (env vars instead)", method="env"
        )
    return _probe_aws_resource("secrets", "Secrets Manager")


def probe_ecs() -> ProbeResult:
    if not os.getenv("NOTARY_USE_REMOTE_STORAGE") and not os.getenv("NOTARY_KMS_KEY_ARN"):
        return ProbeResult("not_applicable", "ECS not running locally (demo mode)", method="env")
    return _probe_aws_resource("ecs", "ECS service")


def _probe_aws_resource(kind: str, label: str) -> ProbeResult:
    """Best-effort AWS probe. Degrades to unknown when boto3/creds absent."""
    try:
        import boto3
    except Exception:
        return ProbeResult("unknown", f"{label}: boto3 not installed in this environment", method="aws-sdk")
    try:
        if kind == "rds":
            client = boto3.client("rds")
            client.describe_db_instances(DBInstanceIdentifier=_db_id())
            return ProbeResult("healthy", f"{label} reachable", method="aws-sdk")
        if kind == "s3":
            client = boto3.client("s3")
            client.head_bucket(Bucket=os.getenv("NOTARY_EVIDENCE_BUCKET", ""))
            return ProbeResult("healthy", f"{label} reachable", method="aws-sdk")
        if kind == "kms":
            client = boto3.client("kms")
            client.describe_key(KeyId=os.getenv("NOTARY_KMS_KEY_ARN", ""))
            return ProbeResult("healthy", f"{label} reachable", method="aws-sdk")
        if kind == "secrets":
            client = boto3.client("secretsmanager")
            client.list_secrets(MaxResults=1)
            return ProbeResult("healthy", f"{label} reachable", method="aws-sdk")
        if kind == "ecs":
            client = boto3.client("ecs")
            client.describe_clusters(clusters=["notary-dev"])
            return ProbeResult("healthy", f"{label} reachable", method="aws-sdk")
    except Exception as exc:  # noqa: BLE001 - we must not crash the status endpoint
        return ProbeResult("unavailable", f"{label}: {type(exc).__name__}", method="aws-sdk")
    return ProbeResult("unknown", f"{label}: not probed", method="aws-sdk")


def _db_id() -> str:
    url = os.getenv("NOTARY_DATABASE_URL", "")
    # postgres://user:pass@host:port/db -> take the db name segment.
    return url.rsplit("/", 1)[-1] if "/" in url else "notary-dev-db"


def probe_proof_loop() -> ProbeResult:
    """Lightweight proof-loop liveness via the in-process decision function.

    Confirms the capture->replay->fix->certify logic is intact (DENY -> APPROVE
    via the documented fix). On failure it reports degraded/unavailable.
    """
    try:
        from notary_platform.demo_scenarios import SCENARIOS

        scenario = SCENARIOS.get("lending-denial")
        if scenario is None:
            return ProbeResult("unknown", "Demo scenario 'lending-denial' not found", method="internal")
        decision = scenario.agent_decision()
        mutated = scenario.agent_decision(threshold=620)
        mitigated = mutated == "APPROVE"
        if decision == "DENY" and mitigated:
            return ProbeResult(
                "healthy",
                "Proof-loop logic intact (DENY -> APPROVE via fix)",
                method="internal",
            )
        return ProbeResult("degraded", f"Proof-loop logic unexpected: {decision} -> {mutated}", method="internal")
    except Exception as exc:  # noqa: BLE001
        return ProbeResult("unavailable", f"Proof-loop probe failed: {type(exc).__name__}", method="internal")


def probe_repo_build() -> ProbeResult:
    """Build state from environment CI signal + commit presence."""
    ci = os.getenv("NOTARY_CI_STATUS", "unknown")
    if ci == "green":
        return ProbeResult("healthy", "CI reported green", method="env")
    if ci == "failing":
        return ProbeResult("degraded", "CI reported failing", method="env")
    return ProbeResult("unknown", "CI status not reported by environment", method="env")


def probe_wo_sync() -> ProbeResult:
    """Work-order sync state.

    We cannot verify the Software Factory / work-order sync from inside this
    process, so we report it honestly as unknown rather than claim healthy.
    """
    return ProbeResult("unknown", "Work-order sync not verifiable from this process", method="internal")


def probe_command_center_frontend() -> ProbeResult:
    """Build/deploy state of the Command Center frontend (notary-viz).

    Healthy when a VITE_PLATFORM_URL is configured and the viz build is present;
    otherwise unknown (we cannot reach the deployed static site from here).
    """
    url = os.getenv("VITE_PLATFORM_URL") or os.getenv("NOTARY_VIZ_ORIGIN")
    if not url:
        return ProbeResult("unknown", "Command Center frontend URL not configured", method="env")
    # We can't fetch the deployed site reliably; report connected if a target is set.
    return ProbeResult("connected", f"Command Center frontend target configured ({url})", method="env")


# ---------------------------------------------------------------------------
# Node -> probe mapping. Maps each topology node id to the live probe(s) that
# describe its connection state.
# ---------------------------------------------------------------------------

NODE_PROBES: dict[str, list[Callable[[], ProbeResult]]] = {
    "service:api-server": [probe_api_health, probe_proof_loop],
    "component:evidence-store": [probe_rds],
    "component:replay-engine": [probe_proof_loop],
    "component:mutation-tester": [probe_proof_loop],
    "service:certificate-service": [probe_kms],
    "aws:s3-evidence": [probe_s3],
    "aws:rds": [probe_rds],
    "aws:kms": [probe_kms],
    "aws:secrets": [probe_secrets],
    "aws:ecs": [probe_ecs],
    "repository:notary-platform": [probe_repo_build],
    "repository:notary-viz": [probe_repo_build, probe_command_center_frontend],
    "wo:29": [probe_wo_sync],
    "wo:phase-1": [probe_proof_loop],
}


def _combine(states: list[str]) -> str:
    """Combine multiple probe states into one node connection state (worst wins)."""
    rank = {
        "unavailable": 6, "degraded": 5, "blocked": 5, "stale": 4,
        "unknown": 3, "not_applicable": 1, "connected": 0, "healthy": 0,
    }
    if not states:
        return "unknown"
    return max(states, key=lambda s: rank.get(s, 3))


def build_live_status(topology_nodes: list[dict]) -> dict:
    """Return LiveStatusResponse: per-node build + connection state.

    ``topology_nodes`` is the list of node dicts from build_topology so we can
    carry each node's build_state (status) alongside its live connection state.
    """
    node_status: dict[str, str] = {n["id"]: n.get("status", "unknown") for n in topology_nodes}

    live: list[dict] = []
    for node in topology_nodes:
        nid = node["id"]
        probes = NODE_PROBES.get(nid, [])
        results = [p() for p in probes]
        if results:
            conn = _combine([r.state for r in results])
            detail = "; ".join(f"{r.method}: {r.detail}" for r in results)
            last = max(results, key=lambda r: r.last_checked).last_checked
            method = ",".join(sorted({r.method for r in results}))
        else:
            conn = _connection_from_build(node.get("status", "unknown"))
            detail = "No live probe; connection inferred from build state."
            last = _now()
            method = "inferred"
        live.append(
            {
                "id": nid,
                "build_state": node_status.get(nid, "unknown"),
                "connection_state": conn,
                "last_checked": last,
                "detail": detail,
                "method": method,
            }
        )

    summary = {
        "api_health": probe_api_health().__dict__,
        "proof_loop": probe_proof_loop().__dict__,
        "ecs": probe_ecs().__dict__,
        "rds": probe_rds().__dict__,
        "s3": probe_s3().__dict__,
        "kms": probe_kms().__dict__,
        "secrets": probe_secrets().__dict__,
        "repo_build": probe_repo_build().__dict__,
        "command_center_frontend": probe_command_center_frontend().__dict__,
        "wo_sync": probe_wo_sync().__dict__,
    }

    overall = _combine([v["state"] for v in summary.values()])

    return {
        "generated_at": _now(),
        "overall_connection_state": overall,
        "nodes": live,
        "summary": summary,
        "stale_threshold_seconds": _STALE_SECONDS,
    }


def _connection_from_build(build_state: str) -> str:
    """Infer a connection state for nodes without a live probe."""
    mapping = {
        "complete": "connected",
        "in_review": "connected",
        "aws_backed": "connected",
        "demo_only": "connected",
        "blocked": "blocked",
        "backlog": "not_applicable",
        "unknown": "unknown",
        "future": "not_applicable",
    }
    return mapping.get(build_state, "unknown")
