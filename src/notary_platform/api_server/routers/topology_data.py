"""Command Center topology data — node-type model for the internal operating map.

This module is the source of truth for ``GET /v1/topology`` and ``GET /v1/build-info``
under WO-30. It expresses the Notary system as typed nodes (repositories, services,
components, AWS resources, work orders, external dependencies, future capabilities)
with plain-language explanations, per the Command Center IA
(``notary-viz/docs/command-center-ia.md``).

The data here is intentionally declarative and static (the human-authored map of
what exists and what it means). Live status signals (commit SHAs, CI status, deploy
environment) are layered on from the environment so the map stays honest about what
is unknown versus verified.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Status / maturity vocabularies (mirror the IA; never invent "green").
# ---------------------------------------------------------------------------

NODE_TYPES = {
    "repository",
    "service",
    "component",
    "aws_resource",
    "evidence_artifact",
    "work_order",
    "external_dependency",
    "future_capability",
}

STATUSES = {
    "complete",
    "in_review",
    "blocked",
    "backlog",
    "demo_only",
    "aws_backed",
    "unknown",
    "future",
}

MATURITIES = {"demo", "prototype", "platform"}

# Domain grouping for the System Map (WO-31 target: grouped by area, not node_type).
DOMAINS = {
    "customer_side",
    "notary_platform",
    "aws_infra",
    "internal_ops",
    "go_to_market",
    "future_platform",
}


@dataclass
class Node:
    """A single node in the Command Center system map."""

    id: str
    node_type: str
    name: str
    plain_purpose: str
    why_it_matters: str
    dependencies: list[str] = field(default_factory=list)
    dependents: list[str] = field(default_factory=list)
    owner_repo: Optional[str] = None
    key_files: list[str] = field(default_factory=list)
    linked_work_orders: list[str] = field(default_factory=list)
    status: str = "unknown"
    maturity: str = "demo"
    domain: str = "notary_platform"
    risk: Optional[str] = None
    next_action: Optional[str] = None


@dataclass
class Edge:
    source: str
    target: str
    kind: str = "dependency"  # "dependency" | "future"


# ---------------------------------------------------------------------------
# Node records — the canonical map (IA §8).
# ---------------------------------------------------------------------------

_NODES: list[Node] = [
    Node(
        id="repository:notary-sdk",
        node_type="repository",
        name="notary-sdk",
        plain_purpose="The client library that captures and seals a decision so it can be proven later.",
        why_it_matters="Without it, there is nothing to replay or certify — it is the source of truth for evidence.",
        owner_repo="repository:notary-sdk",
        key_files=["src/notary_sdk/crypto_core.py", "src/notary_sdk/interception.py"],
        linked_work_orders=["WO-1", "WO-2"],
        dependencies=[],
        status="complete",
        maturity="demo",
    ),
    Node(
        id="service:api-server",
        node_type="service",
        name="API Server",
        plain_purpose="The backend that receives decisions, replays them, tests fixes, and issues certificates.",
        why_it_matters="It is the engine that turns a captured decision into a verifiable proof of mitigation.",
        owner_repo="repository:notary-platform",
        key_files=["src/notary_platform/api_server/main.py", "src/notary_platform/api_server/routers/"],
        linked_work_orders=["WO-3", "WO-4", "WO-5", "WO-30"],
        dependencies=["repository:notary-sdk", "component:evidence-store", "aws:s3-evidence", "aws:rds"],
        status="complete",
        maturity="prototype",
        risk="Viz/status endpoints are auth-optional; not hardened for non-demo exposure (WO-33).",
        next_action="Enforce NOTARY_API_AUTH_TOKEN + lock CORS before any shared deployment.",
    ),
    Node(
        id="component:evidence-store",
        node_type="component",
        name="Evidence Store",
        plain_purpose="Saves each decision and its proof so nothing can be silently changed.",
        why_it_matters="Tamper-evident storage is what makes a later audit trustworthy.",
        owner_repo="repository:notary-platform",
        key_files=["src/notary_platform/storage.py", "src/notary_platform/snapshot.py"],
        linked_work_orders=["WO-3", "WO-21"],
        dependencies=["aws:s3-evidence", "aws:rds"],
        status="complete",
        maturity="prototype",
    ),
    Node(
        id="component:replay-engine",
        node_type="component",
        name="Replay Engine",
        plain_purpose="Re-runs the original decision against the same inputs to prove what happened.",
        why_it_matters="Replay is what makes the decision auditable instead of taken on trust.",
        owner_repo="repository:notary-platform",
        key_files=["src/notary_platform/replay_engine/replay.py", "replay_engine/cassette.py"],
        linked_work_orders=["WO-4"],
        dependencies=["repository:notary-sdk", "component:evidence-store"],
        status="complete",
        maturity="prototype",
        risk="Live replay against a real sandbox pending credentials; synchronous dispatch today (async = Phase 2).",
        next_action="Wire replay-sandbox credentials so live replay can be exercised end to end.",
    ),
    Node(
        id="component:mutation-tester",
        node_type="component",
        name="Mutation Tester",
        plain_purpose="Proves a proposed fix actually changes the bad decision to the right one.",
        why_it_matters="Without it, a 'fix' could be cosmetic and still wrong.",
        owner_repo="repository:notary-platform",
        key_files=["src/notary_platform/replay_engine/mutation.py"],
        linked_work_orders=["WO-5"],
        dependencies=["component:replay-engine"],
        status="complete",
        maturity="prototype",
    ),
    Node(
        id="service:certificate-service",
        node_type="service",
        name="Certificate Service",
        plain_purpose="Signs a Proof of Mitigation certificate that proves a fix was verified.",
        why_it_matters="The certificate is the deliverable customers rely on to show a decision was corrected.",
        owner_repo="repository:notary-platform",
        key_files=["src/notary_platform/certificates.py"],
        linked_work_orders=["WO-5"],
        dependencies=["component:mutation-tester", "aws:kms"],
        status="complete",
        maturity="prototype",
        risk="Deployed image previously crashed (missing boto3) — fixed via INSTALL_CLOUD=1 rebuild (WO-17).",
    ),
    Node(
        id="evidence_artifact:pom-certificate",
        node_type="evidence_artifact",
        name="Proof of Mitigation Certificate",
        plain_purpose="The signed document proving a decision was replayed, fixed, and verified.",
        why_it_matters="It is the artifact a customer shows to demonstrate assurance.",
        owner_repo="repository:notary-platform",
        key_files=["src/notary_platform/certificates.py"],
        linked_work_orders=["WO-5"],
        dependencies=["service:certificate-service"],
        status="complete",
        maturity="prototype",
    ),
    Node(
        id="service:web-dashboard",
        node_type="service",
        name="Web Dashboard (Forensic Control Center)",
        plain_purpose="The customer-facing screen where proofs and incident detail are viewed.",
        why_it_matters="This is the product surface customers actually see and trust.",
        owner_repo="repository:notary-platform",
        key_files=["src/notary_platform/api_server/routers/dashboard.py"],
        linked_work_orders=["WO-6", "WO-25"],
        dependencies=["service:api-server", "evidence_artifact:pom-certificate"],
        status="complete",
        maturity="demo",
    ),
    Node(
        id="service:command-center",
        node_type="service",
        name="Command Center (notary-viz)",
        plain_purpose="The internal map this document describes — shows what is built and what is blocked.",
        why_it_matters="Lets the team and founders see platform status without reading code or GitHub.",
        owner_repo="repository:notary-viz",
        key_files=["src/App.tsx", "src/components/ArchitectureMap.tsx"],
        linked_work_orders=["WO-31", "WO-32", "WO-33", "WO-34"],
        dependencies=["service:command-center-api"],
        status="in_review",
        maturity="demo",
        risk="Currently a technical architecture/runtime view; plain-language operating map not yet built.",
        next_action="Implement Executive Summary, System Map, Build Journey, Blockers per WO-31.",
    ),
    Node(
        id="service:command-center-api",
        node_type="service",
        name="Command Center Status APIs",
        plain_purpose="Read-only backend endpoints that feed the Command Center map.",
        why_it_matters="Without them the map would have nothing safe to display.",
        owner_repo="repository:notary-platform",
        key_files=["src/notary_platform/api_server/routers/viz.py"],
        linked_work_orders=["WO-30", "WO-33"],
        dependencies=["service:api-server"],
        status="in_review",
        maturity="demo",
        risk="Auth/CORS hardening still pending (WO-33).",
        next_action="Complete redaction + status-label tests; harden per WO-33.",
    ),
    Node(
        id="repository:notary-platform",
        node_type="repository",
        name="notary-platform",
        plain_purpose="The main backend codebase: ingest, verify, store, replay, certify, dashboard.",
        why_it_matters="It is where the core Notary functionality lives.",
        owner_repo="repository:notary-platform",
        key_files=["src/notary_platform/"],
        linked_work_orders=["WO-3", "WO-4", "WO-5", "WO-6", "WO-17", "WO-18"],
        dependencies=[],
        status="complete",
        maturity="prototype",
    ),
    Node(
        id="repository:notary-viz",
        node_type="repository",
        name="notary-viz",
        plain_purpose="The codebase for the internal Command Center frontend.",
        why_it_matters="Holds the app that makes platform status readable to non-technical people.",
        owner_repo="repository:notary-viz",
        key_files=["src/App.tsx"],
        linked_work_orders=["WO-31", "WO-32"],
        dependencies=[],
        status="in_review",
        maturity="demo",
        risk="No CI/deploy pipeline yet (WO-32).",
        next_action="Add CI + Cloudflare deploy (WO-32).",
    ),
    Node(
        id="repository:notary-site",
        node_type="repository",
        name="notary-site",
        plain_purpose="The marketing website that explains Notary to the world.",
        why_it_matters="It is how prospects first learn what Notary does.",
        owner_repo="repository:notary-site",
        key_files=["wrangler.toml"],
        linked_work_orders=["WO-20"],
        dependencies=[],
        status="backlog",
        maturity="demo",
    ),
    Node(
        id="aws:s3-evidence",
        node_type="aws_resource",
        name="S3 Evidence Bucket",
        plain_purpose="Locked storage that keeps evidence unchanged and undeletable.",
        why_it_matters="Tamper-proof evidence is the whole point of an assurance product.",
        owner_repo="repository:notary-platform",
        key_files=["infra/terraform/s3.tf"],
        linked_work_orders=["WO-21"],
        dependencies=[],
        status="complete",
        maturity="prototype",
    ),
    Node(
        id="aws:rds",
        node_type="aws_resource",
        name="RDS (Postgres)",
        plain_purpose="The cloud database that stores incident and certificate records.",
        why_it_matters="Persistent, managed storage so data survives restarts.",
        owner_repo="repository:notary-platform",
        key_files=["infra/terraform/rds.tf"],
        linked_work_orders=["WO-23"],
        dependencies=[],
        status="complete",
        maturity="prototype",
    ),
    Node(
        id="aws:kms",
        node_type="aws_resource",
        name="KMS (Key Management)",
        plain_purpose="The cloud service that holds the signing key used to certify proofs.",
        why_it_matters="A certificate is only trustworthy if its key is protected by real infrastructure.",
        owner_repo="repository:notary-platform",
        key_files=["infra/terraform/kms.tf"],
        linked_work_orders=["WO-24"],
        dependencies=[],
        status="complete",
        maturity="prototype",
    ),
    Node(
        id="aws:secrets",
        node_type="aws_resource",
        name="Secrets Manager",
        plain_purpose="Secure storage for credentials the platform needs (DB, signing, API keys).",
        why_it_matters="Keeps secrets out of code and out of the Command Center display.",
        owner_repo="repository:notary-platform",
        key_files=["infra/terraform/secrets.tf"],
        linked_work_orders=["WO-24"],
        dependencies=[],
        status="complete",
        maturity="prototype",
    ),
    Node(
        id="aws:ecs",
        node_type="aws_resource",
        name="ECS (Container Service)",
        plain_purpose="Runs the backend as a managed container in the cloud.",
        why_it_matters="Turns the local demo into a real, running service.",
        owner_repo="repository:notary-platform",
        key_files=["infra/terraform/ecs.tf"],
        linked_work_orders=["WO-23"],
        dependencies=["aws:ecr"],
        status="complete",
        maturity="prototype",
        risk="Exposed via public IP, no ALB; auth not enforced (demo-only, WO-33).",
        next_action="Add ALB + enforce auth before non-demo use.",
    ),
    Node(
        id="aws:ecr",
        node_type="aws_resource",
        name="ECR (Container Registry)",
        plain_purpose="Stores the built backend container images.",
        why_it_matters="The deploy pipeline pushes images here before ECS runs them.",
        owner_repo="repository:notary-platform",
        key_files=["infra/terraform/ecr.tf"],
        linked_work_orders=["WO-23"],
        dependencies=[],
        status="complete",
        maturity="prototype",
    ),
    Node(
        id="external:replay-sandbox",
        node_type="external_dependency",
        name="Replay Sandbox",
        plain_purpose="A safe, isolated test environment used to replay real decision flows end to end.",
        why_it_matters="Live replay proof needs a real sandbox, not a mock — without it the replay engine cannot be exercised against live inputs.",
        owner_repo="repository:notary-platform",
        key_files=[],
        linked_work_orders=["WO-4"],
        dependencies=[],
        status="unknown",
        maturity="demo",
        risk="Sandbox credentials not yet wired for live replay.",
        next_action="Provision replay-sandbox access so live replay can run end to end.",
    ),
    Node(
        id="external:github-actions",
        node_type="external_dependency",
        name="GitHub Actions",
        plain_purpose="Runs tests and checks on every code change.",
        why_it_matters="Confirms the build is green before changes ship.",
        owner_repo="repository:notary-platform",
        key_files=[],
        linked_work_orders=["WO-22"],
        dependencies=[],
        status="complete",
        maturity="prototype",
    ),
    Node(
        id="external:cloudflare",
        node_type="external_dependency",
        name="Cloudflare",
        plain_purpose="Hosting target for the static Command Center frontend.",
        why_it_matters="Where the internal map will be deployed.",
        owner_repo="repository:notary-viz",
        key_files=["wrangler.toml"],
        linked_work_orders=["WO-32"],
        dependencies=[],
        status="unknown",
        maturity="demo",
        risk="Deploy pipeline not yet configured (WO-32).",
        next_action="Configure Cloudflare Pages deploy for notary-viz.",
    ),
    Node(
        id="wo:29",
        node_type="work_order",
        name="WO-29 — Phase 1 Status Sync",
        plain_purpose="The living record that keeps the build state and work orders in sync.",
        why_it_matters="It is the canonical status Software Factory reads to stay accurate.",
        owner_repo="repository:notary-platform",
        key_files=[],
        linked_work_orders=["WO-29"],
        dependencies=[],
        status="in_review",
        maturity="prototype",
    ),
    Node(
        id="wo:phase-1",
        node_type="work_order",
        name="Phase 1 Milestone (end-to-end demo)",
        plain_purpose="The goal of proving the full capture→replay→fix→certify→verify loop works.",
        why_it_matters="Phase 1 done means the core idea is demonstrably real, not just planned.",
        owner_repo="repository:notary-platform",
        key_files=[],
        linked_work_orders=["WO-18"],
        dependencies=["service:certificate-service", "aws:kms", "aws:s3-evidence"],
        status="complete",
        maturity="prototype",
    ),
    Node(
        id="future:testing-playground",
        node_type="future_capability",
        name="Scenario Testing Playground",
        plain_purpose="A self-serve surface to build and run new decision scenarios.",
        why_it_matters="Lets customers validate their own decisions, not just demo ones.",
        owner_repo="repository:notary-platform",
        key_files=[],
        linked_work_orders=[],
        dependencies=["service:api-server"],
        status="future",
        maturity="demo",
    ),
    Node(
        id="future:async-workers",
        node_type="future_capability",
        name="Async Replay/Mutation Workers",
        plain_purpose="Background workers that run replay and mutation off the request path.",
        why_it_matters="Needed for scale and long-running proofs.",
        owner_repo="repository:notary-platform",
        key_files=[],
        linked_work_orders=[],
        dependencies=["service:api-server"],
        status="future",
        maturity="demo",
    ),
    Node(
        id="future:customer-portal",
        node_type="future_capability",
        name="Customer Portal",
        plain_purpose="A login-protected area where customers manage their own proofs.",
        why_it_matters="Turns the demo into a real multi-tenant product.",
        owner_repo="repository:notary-platform",
        key_files=[],
        linked_work_orders=[],
        dependencies=["service:web-dashboard"],
        status="future",
        maturity="demo",
    ),
    Node(
        id="future:capture-rules",
        node_type="future_capability",
        name="Capture Rules",
        plain_purpose="Declarative rules that decide which decisions get captured and sealed automatically.",
        why_it_matters="Lets teams scope assurance to the decisions that matter instead of capturing everything.",
        owner_repo="repository:notary-platform",
        key_files=[],
        linked_work_orders=[],
        dependencies=["repository:notary-sdk"],
        status="future",
        maturity="demo",
    ),
    Node(
        id="future:proof-of-readiness",
        node_type="future_capability",
        name="Proof of Readiness",
        plain_purpose="A certificate that proves a system or process is ready to go live, not just a single decision.",
        why_it_matters="Extends the assurance model from incident-level to system-level readiness.",
        owner_repo="repository:notary-platform",
        key_files=[],
        linked_work_orders=[],
        dependencies=["service:certificate-service"],
        status="future",
        maturity="demo",
    ),
    Node(
        id="future:evidence-export",
        node_type="future_capability",
        name="Evidence Export",
        plain_purpose="Exports proofs and custody records in audit-ready formats for customers and regulators.",
        why_it_matters="Auditors and enterprise buyers need portable evidence, not a locked-in dashboard.",
        owner_repo="repository:notary-platform",
        key_files=[],
        linked_work_orders=[],
        dependencies=["evidence_artifact:pom-certificate"],
        status="future",
        maturity="demo",
    ),
    Node(
        id="future:grc-integrations",
        node_type="future_capability",
        name="GRC Integrations",
        plain_purpose="Connectors to governance, risk, and compliance tools (e.g. ticketing, SIEM, control frameworks).",
        why_it_matters="Proofs only create value when they flow into the compliance systems teams already use.",
        owner_repo="repository:notary-platform",
        key_files=[],
        linked_work_orders=[],
        dependencies=["service:command-center"],
        status="future",
        maturity="demo",
    ),
]


def _build_edges(nodes: list[Node]) -> list[Edge]:
    """Derive dependency edges from each node's dependencies; mark future edges."""
    edges: list[Edge] = []
    ids = {n.id for n in nodes}
    for n in nodes:
        for dep in n.dependencies:
            if dep in ids:
                kind = "future" if n.status == "future" or dep.startswith("future:") else "dependency"
                edges.append(Edge(source=dep, target=n.id, kind=kind))
    return edges


def _derive_blockers(nodes: list[Node]) -> list[dict]:
    """Blockers = nodes that are blocked or unknown (honest, never green)."""
    blockers: list[dict] = []
    for n in nodes:
        if n.status in ("blocked", "unknown"):
            blockers.append(
                {
                    "id": n.id,
                    "label": n.name,
                    "status": n.status,
                    "reason": n.risk or "State could not be determined.",
                    "next_action": n.next_action,
                }
            )
    return blockers


def _overall_maturity(nodes: list[Node]) -> str:
    """Platform maturity = best stage any completed node has reached."""
    reached = {
        n.maturity
        for n in nodes
        if n.status in ("complete", "in_review", "aws_backed", "demo_only")
    }
    if "platform" in reached:
        return "platform"
    if "prototype" in reached:
        return "prototype"
    return "demo"


def build_topology() -> dict:
    """Return the extended TopologyResponse (node-type model)."""
    nodes = list(_NODES)
    edges = _build_edges(nodes)
    dependents = _derive_dependents(nodes, edges)
    blockers = _derive_blockers(nodes)
    status_counts: dict[str, int] = {}
    for n in nodes:
        status_counts[n.status] = status_counts.get(n.status, 0) + 1

    node_dicts = [_node_to_dict(n, dependents.get(n.id, [])) for n in nodes]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "maturity_stage": _overall_maturity(nodes),
        "nodes": node_dicts,
        "edges": [{"source": e.source, "target": e.target, "kind": e.kind} for e in edges],
        "blockers": blockers,
        "status_counts": status_counts,
        # Backward-compatible legacy shape (deprecated; frontend should use nodes).
        "stages": _legacy_stages(),
        "legacy_edges": [[e.source, e.target] for e in edges],
    }


def _derive_dependents(nodes: list[Node], edges: list[Edge]) -> dict[str, list[str]]:
    """Incoming edges per node id (who relies on this node)."""
    by_id = {n.id for n in nodes}
    deps: dict[str, list[str]] = {n.id: [] for n in nodes}
    for e in edges:
        if e.target in by_id:
            deps.setdefault(e.target, [])
            if e.source not in deps[e.target]:
                deps[e.target].append(e.source)
    return deps


# Default domain per node_type; specific nodes can override via the DOMAIN_OVERRIDES map.
_DOMAIN_BY_TYPE: dict[str, str] = {
    "repository": "internal_ops",
    "service": "notary_platform",
    "component": "notary_platform",
    "aws_resource": "aws_infra",
    "evidence_artifact": "notary_platform",
    "work_order": "internal_ops",
    "external_dependency": "notary_platform",
    "future_capability": "future_platform",
}

# Per-node domain overrides for nodes that don't follow the type default.
DOMAIN_OVERRIDES: dict[str, str] = {
    "repository:notary-sdk": "customer_side",
    "external:replay-sandbox": "notary_platform",
    "evidence_artifact:pom-certificate": "notary_platform",
    "service:web-dashboard": "customer_side",
    "repository:notary-site": "go_to_market",
    "external:cloudflare": "go_to_market",
}


def _domain_for(n: Node) -> str:
    return DOMAIN_OVERRIDES.get(n.id, _DOMAIN_BY_TYPE.get(n.node_type, "notary_platform"))


def _node_to_dict(n: Node, dependents: list[str]) -> dict:
    return {
        "id": n.id,
        "node_type": n.node_type,
        "name": n.name,
        "plain_purpose": n.plain_purpose,
        "why_it_matters": n.why_it_matters,
        "owner_repo": n.owner_repo,
        "key_files": n.key_files,
        "linked_work_orders": n.linked_work_orders,
        "dependencies": n.dependencies,
        "dependents": dependents,
        "status": n.status,
        "domain": _domain_for(n),
        "maturity": n.maturity,
        "risk": n.risk,
        "next_action": n.next_action,
    }


def _legacy_stages() -> list[dict]:
    """Approximate the old pipeline-stage shape for backward compatibility."""
    return [
        {"id": "sdk", "label": "SDK (client)", "status": "stub", "detail": "sealing/interception implemented in notary-sdk"},
        {"id": "ingest", "label": "Ingest", "status": "implemented", "endpoint": "POST /v1/incidents/ingest"},
        {"id": "evidence-store", "label": "Evidence Store", "status": "implemented", "endpoint": "Memory/Postgres+S3"},
        {"id": "replay", "label": "Replay", "status": "implemented", "endpoint": "POST /v1/incidents/{id}/replay"},
        {"id": "mutation", "label": "Mutation Test", "status": "implemented", "endpoint": "POST /v1/incidents/{id}/mutation-tests"},
        {"id": "certificate", "label": "Certificate", "status": "implemented", "endpoint": "POST /v1/incidents/{id}/certificates"},
        {"id": "dashboard", "label": "Dashboard", "status": "implemented", "endpoint": "GET /dashboard"},
    ]


# ---------------------------------------------------------------------------
# Build info — layered with live environment signals (unknown when absent).
# ---------------------------------------------------------------------------

def _env_commit(var: str, default: str = "unknown") -> str:
    val = os.getenv(var, "").strip()
    return val or default


def _git_commit(repo_root: str, default: str = "unknown") -> str:
    """Resolve the current commit SHA of a repo via `git rev-parse HEAD`.

    Falls back to an env override (NOTARY_*_COMMIT) and then to 'unknown'.
    Never invents a value.
    """
    env_key = {
        "notary-platform": "NOTARY_PLATFORM_COMMIT",
        "notary-sdk": "NOTARY_SDK_COMMIT",
        "notary-viz": "NOTARY_VIZ_COMMIT",
    }.get(os.path.basename(repo_root.rstrip("/")), "")
    if env_key:
        env_val = os.getenv(env_key, "").strip()
        if env_val:
            return env_val
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=2,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:
        pass
    return default


def _environment() -> str:
    if os.getenv("NOTARY_USE_REMOTE_STORAGE") or os.getenv("NOTARY_KMS_KEY_ARN"):
        return "aws-prototype"
    return "local"


def build_recent_changes() -> dict:
    """Return a redacted, plain-English recent-changes feed for the Command Center.

    Derived statically from the topology + build info (no live SF API). Each entry
    is honest: it states what was verified and never fabricates a timestamp.
    """
    info = build_build_info()
    nodes = list(_NODES)

    items: list[dict] = []

    # Most-recently-built signal: the platform/SDK/viz commits + generated time.
    items.append(
        {
            "id": "change:build-provenance",
            "title": "Build provenance refreshed",
            "detail": (
                f"platform={info['platform_commit']}, sdk={info['sdk_commit']}, "
                f"viz={info['viz_commit']} (environment: {info['environment']})"
            ),
            "source": "build-info",
            "when": info["generated_at"],
            "next_action": None,
        }
    )

    # Verified-complete nodes become "recently verified" entries.
    verified = [n for n in nodes if n.status == "complete"]
    for n in verified[:6]:
        items.append(
            {
                "id": f"change:verified:{n.id}",
                "title": f"{n.name} verified complete",
                "detail": n.plain_purpose,
                "source": ", ".join(n.linked_work_orders) or n.owner_repo or "Command Center",
                "when": info["generated_at"],
                "next_action": n.next_action,
            }
        )

    # Blockers/unknowns become open items with next action.
    open_items = [n for n in nodes if n.status in ("blocked", "unknown")]
    for n in open_items:
        items.append(
            {
                "id": f"change:open:{n.id}",
                "title": f"{n.name} needs attention",
                "detail": n.risk or "State could not be determined.",
                "source": ", ".join(n.linked_work_orders) or n.owner_repo or "Command Center",
                "when": info["generated_at"],
                "next_action": n.next_action,
            }
        )

    return {
        "generated_at": info["generated_at"],
        "items": items,
    }


def _known_limitations() -> list[str]:
    limits: list[str] = []
    if not os.getenv("NOTARY_API_AUTH_TOKEN"):
        limits.append("Viz/status endpoints are auth-optional (demo-only); harden before shared deploy (WO-33).")
    limits.append("ECS exposed via public IP without an ALB; restrict before non-demo use (WO-33).")
    if os.getenv("NOTARY_CI_STATUS", "unknown") == "unknown":
        limits.append("CI status not reported by the environment.")
    return limits


def build_build_info() -> dict:
    """Return the extended BuildInfoResponse."""
    # Resolve repo roots relative to this file so commit SHAs are real, not "unknown".
    here = Path(__file__).resolve()
    platform_root = here.parents[4]
    viz_root = platform_root.parent / "notary-viz"
    sdk_root = platform_root.parent / "notary-sdk-main" / "notary-sdk"
    return {
        "version": "0.0.1",
        "ci_status": os.getenv("NOTARY_CI_STATUS", "unknown"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "platform_commit": _git_commit(str(platform_root)),
        "sdk_commit": _git_commit(str(sdk_root)),
        "viz_commit": _git_commit(str(viz_root)),
        "environment": _environment(),
        "api_base_url": os.getenv("NOTARY_BASE_URL", "http://localhost:8001"),
        "known_limitations": _known_limitations(),
    }
