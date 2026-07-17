#!/usr/bin/env python3
"""Generate topology.json by introspecting the notary-platform router files.

Usage:
    python -m scripts.gen_topology          # from repo root
    python scripts/gen_topology.py          # or directly

Output:
    topology.json at the repo root (committed / served by GET /v1/topology).
"""

from __future__ import annotations

import ast
import json
import re
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ROUTERS_DIR = REPO_ROOT / "src" / "notary_platform" / "api_server" / "routers"
OUTPUT = REPO_ROOT / "topology.json"

# Canonical pipeline stages — order matters for the viz edge list.
# status is overridden below if we can detect a live route in the routers.
STAGES: list[dict] = [
    {
        "id": "sdk",
        "label": "SDK (client)",
        "status": "stub",
        "detail": "sealing/interception not yet implemented",
    },
    {
        "id": "ingest",
        "label": "Ingest",
        "status": "stub",
        "endpoint": "POST /v1/incidents/ingest",
    },
    {
        "id": "evidence-store",
        "label": "Evidence Store",
        "status": "stub",
        "endpoint": "Memory/Postgres+S3",
    },
    {
        "id": "replay",
        "label": "Replay",
        "status": "stub",
        "endpoint": "POST /v1/incidents/{id}/replay",
    },
    {
        "id": "mutation",
        "label": "Mutation Test",
        "status": "stub",
        "endpoint": "POST /v1/incidents/{id}/mutation-tests",
    },
    {
        "id": "certificate",
        "label": "Certificate",
        "status": "stub",
        "endpoint": "POST /v1/incidents/{id}/certificates",
    },
    {
        "id": "dashboard",
        "label": "Dashboard",
        "status": "stub",
        "endpoint": "GET /dashboard",
    },
]

EDGES = [
    ["sdk", "ingest"],
    ["ingest", "evidence-store"],
    ["evidence-store", "replay"],
    ["replay", "mutation"],
    ["mutation", "certificate"],
    ["certificate", "dashboard"],
]

# Map stage id → patterns that indicate it's implemented (regex against route paths/modules).
IMPL_SIGNALS: dict[str, list[str]] = {
    "ingest": [r"incidents/ingest"],
    "replay": [r"incidents/.+/replay"],
    "mutation": [r"incidents/.+/mutation"],
    "certificate": [r"incidents/.+/certificate"],
    "dashboard": [r"/dashboard"],
    "evidence-store": [r"persist_evidence", r"storage"],
}


def _collect_routes(routers_dir: Path) -> list[str]:
    """Walk router Python files and extract @router.<method>("<path>") strings."""
    routes: list[str] = []
    for py in routers_dir.glob("*.py"):
        if py.name == "__init__.py":
            continue
        try:
            tree = ast.parse(py.read_text(), filename=str(py))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Call):
                        func = dec.func
                        if isinstance(func, ast.Attribute) and func.attr in {
                            "get", "post", "put", "delete", "patch",
                        }:
                            if dec.args and isinstance(dec.args[0], ast.Constant):
                                routes.append(f"{func.attr.upper()} {dec.args[0].value}")
    return routes


def _collect_module_text(routers_dir: Path) -> str:
    """Return concatenated text of all router files for signal matching."""
    parts = []
    for py in routers_dir.glob("*.py"):
        try:
            parts.append(py.read_text())
        except Exception:
            pass
    return "\n".join(parts)


def main() -> None:
    routes = _collect_routes(ROUTERS_DIR)
    module_text = _collect_module_text(ROUTERS_DIR)
    combined = "\n".join(routes) + "\n" + module_text

    stages = []
    for stage in STAGES:
        s = dict(stage)
        signals = IMPL_SIGNALS.get(s["id"], [])
        if signals and any(re.search(sig, combined, re.IGNORECASE) for sig in signals):
            s["status"] = "implemented"
        # SDK is always stub until the SDK repo ships sealing.
        if s["id"] == "sdk":
            s["status"] = "stub"
        stages.append(s)

    topology = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stages": stages,
        "edges": EDGES,
    }

    OUTPUT.write_text(json.dumps(topology, indent=2))
    print(f"topology.json written → {OUTPUT}")
    for s in stages:
        mark = "✓" if s["status"] == "implemented" else "○"
        print(f"  {mark} {s['id']:20s}  {s['status']}")


if __name__ == "__main__":
    main()
