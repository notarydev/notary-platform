"""Read-only viz router — serves topology, scenarios, and build-info for notary-viz.

These endpoints never mutate platform state and are intentionally public-ish:
they work with auth disabled (get_optional_org) so the local viz SPA requires
no credentials to show the architecture map and scenario list.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends

from notary_platform.api_server.auth import get_optional_org
from notary_platform.demo_scenarios import SCENARIOS

router = APIRouter(tags=["viz"])

# Topology file written by scripts/gen_topology.py (make topology).
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
def get_topology(_org: str = Depends(get_optional_org)) -> dict[str, Any]:
    """Return topology.json if present; fall back to the hardcoded pipeline."""
    if _TOPOLOGY_PATH.exists():
        try:
            return json.loads(_TOPOLOGY_PATH.read_text())
        except Exception:
            pass
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stages": _FALLBACK_STAGES,
        "edges": _FALLBACK_EDGES,
    }


@router.get("/scenarios")
def list_scenarios(_org: str = Depends(get_optional_org)) -> list[dict[str, Any]]:
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
def build_info(_org: str = Depends(get_optional_org)) -> dict[str, str]:
    """Return version, CI status, and generation timestamp."""
    return {
        "version": "0.0.1",
        "ci_status": os.getenv("NOTARY_CI_STATUS", "unknown"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
