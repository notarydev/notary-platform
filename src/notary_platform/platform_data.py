"""Seeded demo data for the Notary Platform (WO-48/REQ-NP-012).

Creates a demo organization with environments, agents, systems, and sample
incidents so the Notary Platform has data to display on first load.
"""

from __future__ import annotations

from notary_platform.models import (
    Agent,
    CapturePolicy,
    Environment,
    Organization,
    SystemConnection,
)

DEMO_ORG = Organization(
    id="org:acme-demo",
    name="Acme Assurance Demo",
    environments=["env:demo", "env:staging", "env:production"],
)

DEMO_ENVIRONMENTS = {
    "env:demo": Environment(id="env:demo", name="Demo", org_id="org:acme-demo", kind="demo"),
    "env:staging": Environment(id="env:staging", name="Staging", org_id="org:acme-demo", kind="staging"),
    "env:production": Environment(
        id="env:production", name="Production", org_id="org:acme-demo", kind="production"
    ),
}

DEMO_AGENTS = [
    Agent(
        id="agent:lending",
        name="Lending Decision Agent",
        org_id="org:acme-demo",
        environment_id="env:demo",
        risk_tier="high",
        sdk_status="connected",
        sdk_version="1.2.0",
        last_seen="2026-07-18T00:00:00Z",
        scenario_count=3,
        capture_policy_count=1,
    ),
    Agent(
        id="agent:support-handoff",
        name="Support Handoff Agent",
        org_id="org:acme-demo",
        environment_id="env:demo",
        risk_tier="medium",
        sdk_status="connected",
        sdk_version="1.1.0",
        last_seen="2026-07-17T12:00:00Z",
        scenario_count=1,
        capture_policy_count=1,
    ),
    Agent(
        id="agent:prior-auth",
        name="Prior Authorization Agent",
        org_id="org:acme-demo",
        environment_id="env:demo",
        risk_tier="high",
        sdk_status="stale",
        sdk_version="0.9.0",
        last_seen="2026-07-01T00:00:00Z",
        scenario_count=0,
        capture_policy_count=0,
    ),
    Agent(
        id="agent:hiring-screen",
        name="Hiring Screen Agent",
        org_id="org:acme-demo",
        environment_id="env:demo",
        risk_tier="medium",
        sdk_status="not_installed",
        scenario_count=0,
        capture_policy_count=0,
    ),
]

DEMO_SYSTEMS = [
    SystemConnection(
        id="sys:notary-sdk",
        name="Notary Python SDK",
        org_id="org:acme-demo",
        environment_id="env:demo",
        kind="sdk",
        status="connected",
        capability="Capture, Seal, Submit",
    ),
    SystemConnection(
        id="sys:notary-api",
        name="Notary API",
        org_id="org:acme-demo",
        environment_id="env:demo",
        kind="api",
        status="connected",
        capability="Ingest, Replay, Certify",
    ),
    SystemConnection(
        id="sys:credit-bureau",
        name="Credit Bureau API",
        org_id="org:acme-demo",
        environment_id="env:demo",
        kind="api",
        status="connected",
        capability="Cassette-backed response",
    ),
    SystemConnection(
        id="sys:support-ticketing",
        name="Support Ticketing",
        org_id="org:acme-demo",
        environment_id="env:demo",
        kind="webhook",
        status="disconnected",
        capability="Demo connector — not live",
    ),
    SystemConnection(
        id="sys:grc",
        name="GRC System",
        org_id="org:acme-demo",
        environment_id="env:demo",
        kind="grc",
        status="planned",
        capability="Planned integration",
    ),
    SystemConnection(
        id="sys:kms",
        name="AWS KMS",
        org_id="org:acme-demo",
        environment_id="env:demo",
        kind="api",
        status="connected",
        capability="Certificate signing",
    ),
    SystemConnection(
        id="sys:evidence-store",
        name="S3 Evidence Store",
        org_id="org:acme-demo",
        environment_id="env:demo",
        kind="api",
        status="connected",
        capability="Immutable evidence storage",
    ),
]

DEMO_POLICIES = [
    CapturePolicy(
        id="policy:default-capture",
        name="Default Capture Policy",
        org_id="org:acme-demo",
        environment_id="env:demo",
        status="active",
        coverage="all",
    ),
    CapturePolicy(
        id="policy:lending-capture",
        name="Lending Agent Policy",
        org_id="org:acme-demo",
        environment_id="env:demo",
        agent_id="agent:lending",
        status="active",
        coverage="all",
    ),
]


def seed() -> dict:
    return {
        "organization": DEMO_ORG,
        "environments": list(DEMO_ENVIRONMENTS.values()),
        "agents": DEMO_AGENTS,
        "systems": DEMO_SYSTEMS,
        "policies": DEMO_POLICIES,
    }
