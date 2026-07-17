"""Read-only viz router — serves topology, scenarios, and build-info for notary-viz.

These endpoints never mutate platform state and are intentionally public-ish:
they work with auth disabled (get_optional_org) so the local viz SPA requires
no credentials to show the architecture map and scenario list.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from notary_platform.api_server.auth import get_optional_org
from notary_platform.api_server.routers.live_status import build_live_status
from notary_platform.api_server.routers.topology_data import (
    build_build_info,
    build_recent_changes,
    build_topology,
)
from notary_platform.config import SETTINGS
from notary_platform.demo_scenarios import SCENARIOS

router = APIRouter(tags=["viz"])


def require_command_center_auth(request: Request) -> None:
    """Enforce NOTARY_COMMAND_CENTER_TOKEN on viz endpoints when configured.

    When unset (local/demo), the endpoints remain auth-optional. When set, the
    caller must present the token via ``Authorization: Bearer`` or the
    ``X-Command-Center-Token`` header. This is the WO-33 hardening gate for any
    shared or production deployment of the Command Center.
    """
    if not SETTINGS.command_center_token:
        return
    token = request.headers.get("X-Command-Center-Token")
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[len("Bearer ") :]
    if token != SETTINGS.command_center_token:
        raise HTTPException(status_code=401, detail="invalid or missing Command Center token")


def _probe_self_health() -> bool:
    """Best-effort liveness check of this running API process.

    Used by the live-status layer (WO-36) to report API health without an extra
    HTTP round-trip. Returns False on any error so the probe degrades safely.
    """
    try:
        from notary_platform.api_server.main import app

        # The app imported cleanly => the process is up and routes are registered.
        return app is not None
    except Exception:
        return False

# Topology file written by scripts/gen_topology.py (make topology). Retained as a
# legacy fallback; the Command Center now uses the node-type model in topology_data.
_TOPOLOGY_PATH = Path(__file__).resolve().parents[5] / "topology.json"

# Canonical pipeline order used as the fallback when topology.json is missing.
_FALLBACK_STAGES = [
    {"id": "sdk", "label": "SDK (client)", "status": "stub", "detail": "sealing/interception not yet implemented"},
    {"id": "ingest", "label": "Ingest", "status": "implemented", "endpoint": "POST /v1/incidents/ingest"},
    {"id": "evidence-store", "label": "Evidence Store", "status": "implemented", "endpoint": "Memory/Postgres+S3"},
    {"id": "replay", "label": "Replay", "status": "implemented", "endpoint": "POST /v1/incidents/{id}/replay"},
    {"id": "mutation", "label": "Mutation Test", "status": "implemented", "endpoint": "POST /v1/incidents/{id}/mutation-tests"},
    {"id": "certificate", "label": "Certificate", "status": "implemented", "endpoint": "POST /v1/incidents/{id}/certificates"},
    {"id": "dashboard", "label": "Dashboard", "status": "implemented", "endpoint": "GET /dashboard"},
]
_FALLBACK_EDGES = [
    ["sdk", "ingest"],
    ["ingest", "evidence-store"],
    ["evidence-store", "replay"],
    ["replay", "mutation"],
    ["mutation", "certificate"],
    ["certificate", "dashboard"],
]


@router.get("/topology")
def get_topology(
    _org: str = Depends(get_optional_org),
    _auth: None = Depends(require_command_center_auth),
) -> dict[str, Any]:
    """Return the Command Center node-type topology.

    The primary payload is the node-type model (``nodes`` / ``edges`` / ``blockers``
    / ``maturity_stage``) built from ``topology_data``. A legacy ``stages`` /
    ``legacy_edges`` shape is included for backward compatibility with older
    frontends.
    """
    return build_topology()


@router.get("/scenarios")
def list_scenarios(
    _org: str = Depends(get_optional_org),
    _auth: None = Depends(require_command_center_auth),
) -> list[dict[str, Any]]:
    """Return all demo scenarios with their node graphs."""
    result = []
    for scenario in SCENARIOS.values():
        result.append(
            {
                "scenario_id": scenario.scenario_id,
                "title": scenario.title,
                "industry": scenario.industry,
                "risk": scenario.risk,
                "nodes": [
                    {
                        "node_id": node.node_id,
                        "label": node.label,
                        "kind": node.kind,
                        "detail": node.detail,
                        "failure": node.failure,
                    }
                    for node in scenario.nodes
                ],
            }
        )
    return result


@router.get("/build-info")
def build_info(
    _org: str = Depends(get_optional_org),
    _auth: None = Depends(require_command_center_auth),
) -> dict[str, Any]:
    """Return extended build/commit/environment metadata for the Command Center.

    Unknown values are reported explicitly as ``"unknown"`` rather than invented.
    Secrets, credentials, and Terraform state are never included (see redaction
    rules in the Command Center IA).
    """
    return build_build_info()


@router.get("/changes")
def recent_changes(
    _org: str = Depends(get_optional_org),
    _auth: None = Depends(require_command_center_auth),
) -> dict[str, Any]:
    """Return a redacted, plain-English recent-changes feed (WO-31).

    Static, derived from topology + build info. No SF API, no raw evidence,
    no secrets. Each item states what changed/verified and the source WO/repo.
    """
    return build_recent_changes()


@router.get("/live-status")
def live_status(
    _org: str = Depends(get_optional_org),
    _auth: None = Depends(require_command_center_auth),
) -> dict[str, Any]:
    """Return the live build/connection/status layer (WO-36).

    For each topology node, reports both its build state (what is built) and its
    connection state (what is live/connected/healthy now), with timestamps and a
    staleness threshold. Unknown / unavailable / stale are reported honestly and
    never as healthy. No secrets, credentials, or raw evidence are returned.
    """
    topology = build_topology()
    return build_live_status(topology["nodes"])
