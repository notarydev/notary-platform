"""Capability inventory: distinguishes implemented, partial, demo-only, and planned features.

This test provides a machine-readable baseline of what the repository currently supports.
Update this file when capabilities change.
"""

from __future__ import annotations

from typing import Literal

# ── Capability definitions ────────────────────────────────────────────────

CapabilityStatus = Literal["implemented", "partial", "demo_only", "planned"]

CAPABILITIES: dict[str, dict[str, CapabilityStatus | str | list[str]]] = {
    # ── Core proof loop (WO-28) ───────────────────────────────────────────
    "verification_record_ingestion": {
        "status": "implemented",
        "evidence": ["POST /v1/verification-records/from-snapshot", "IngestionService"],
        "notes": "Accepts SDK snapshots, produces VerificationRecord with computed replayability",
    },
    "human_labeling": {
        "status": "implemented",
        "evidence": ["POST /v1/verification-records/{id}/label", "HumanLabel model"],
        "notes": "Records expected_outcome, reviewer, role, reason",
    },
    "replay_execution": {
        "status": "implemented",
        "evidence": ["ReplayService", "ReplayRun model", "ReplayExecutionEvent"],
        "notes": "DemoReplayRunner works in-memory; production runner not configured",
    },
    "mutation_testing": {
        "status": "implemented",
        "evidence": ["MutationService", "MutationTest model", "POST /v1/verification-records/{id}/mutation-tests"],
        "notes": "Before/after fix verification with verdicts: verified, not_verified, inconclusive",
    },
    "proof_of_mitigation": {
        "status": "implemented",
        "evidence": ["CertificateService", "ProofCertificate model", "POST /v1/verification-records/{id}/proof-of-mitigation"],
        "notes": "Issues signed certificates with claim, root_hash, signature; verification endpoint exists",
    },
    "scenario_library": {
        "status": "implemented",
        "evidence": ["ScenarioLibraryService", "Scenario model", "POST /v1/scenarios"],
        "notes": "Promotes VR to Scenario with expected outcome; immutable after creation",
    },
    "scenario_runs": {
        "status": "implemented",
        "evidence": ["ScenarioRunService", "ScenarioRun model", "POST /v1/scenario-runs"],
        "notes": "Runs scenarios against agent versions with optional fix_config; pass/fail result",
    },
    "readiness_policies": {
        "status": "implemented",
        "evidence": ["ReadinessService", "ReadinessPolicy model", "POST /v1/readiness-policies"],
        "notes": "Defines required scenario sets for release",
    },
    "readiness_checks": {
        "status": "implemented",
        "evidence": ["ReadinessService", "ReadinessCheck model", "POST /v1/readiness-checks"],
        "notes": "Executes scenario runs per policy; issues readiness certificate",
    },
    "release_gate": {
        "status": "implemented",
        "evidence": ["ReleaseGateService", "ReleaseGateResult model", "POST /v1/release-gate/checks"],
        "notes": "Evaluates readiness checks; pass/fail/error with evidence refs",
    },

    # ── Setup & Decision Discovery (WO-64) ────────────────────────────────
    "assurance_setup_plan": {
        "status": "implemented",
        "evidence": ["AssuranceSetupPlan model", "POST /v1/setup/plans"],
        "notes": "Top-level onboarding plan linking workflow, sources, rules",
    },
    "decision_workflow": {
        "status": "implemented",
        "evidence": ["DecisionWorkflow model", "POST /v1/setup/decision-workflows"],
        "notes": "Defines business decision family, expected safe outcome, common failure",
    },
    "workflow_evidence_sources": {
        "status": "implemented",
        "evidence": ["WorkflowEvidenceSource model", "POST /v1/setup/decision-workflows/{id}/evidence-sources"],
        "notes": "Records source connections (SDK, CSV, JSON, connector)",
    },
    "record_selection_rules": {
        "status": "implemented",
        "evidence": ["RecordSelectionRule model", "GET /v1/setup/decision-workflows/{id}/record-selection-rules"],
        "notes": "Heuristic filters for import preview (transitional — not assurance evaluators)",
    },
    "import_parse_preview": {
        "status": "partial",
        "evidence": ["POST /v1/setup/plans/{id}/imports/parse", "POST /v1/setup/plans/{id}/imports/preview"],
        "notes": "Parses CSV/JSON/JSONL; preview applies heuristic selection rules; transitional path",
    },
    "import_commit": {
        "status": "partial",
        "evidence": ["POST /v1/setup/plans/{id}/imports/commit"],
        "notes": "Creates VerificationRecord directly (legacy path); marked 'legacy_verification_record' in response",
    },
    "decision_discovery_ui": {
        "status": "implemented",
        "evidence": ["static/app/app.js Decision Discovery section", "tests/test_platform_static_app.py"],
        "notes": "Entry point in Setup SPA; will evolve into NSE surface",
    },

    # ── SDK & Capture ──────────────────────────────────────────────────────
    "python_sdk_capture": {
        "status": "implemented",
        "evidence": ["packages/notary-sdk-py/notary_sdk/capture.py", "RunCapture, DecisionSnapshot"],
        "notes": "HMAC chain, root_hash, offline verification; local .notary_captures storage",
    },
    "python_sdk_submission": {
        "status": "implemented",
        "evidence": ["packages/notary-sdk-py/notary_sdk/client.py", "snapshot.submit()"],
        "notes": "Posts to /v1/verification-records/from-snapshot",
    },
"typescript_sdk": {
            "status": "planned",
            "evidence": [],
            "notes": "WP-120: Parity with Python SDK after DEP mapping frozen",
        },

    # ── Storage ────────────────────────────────────────────────────────────
    "memory_storage": {
        "status": "implemented",
        "evidence": ["MemoryStorage class", "Default for local dev"],
        "notes": "In-memory dicts; full StorageBackend contract",
    },
    "shared_demo_file_storage": {
        "status": "implemented",
        "evidence": ["SharedDemoFileStorage class", "JSON file persistence"],
        "notes": "Survives process restart; demo profile",
    },
"postgres_s3_storage": {
            "status": "implemented",
            "evidence": ["PostgresS3Storage class", "NOTARY_USE_REMOTE_STORAGE"],
            "notes": (
                "Incidents + WO-28 objects (VR, labels, replay, mutation, proof, "
                "scenario, readiness, gate) + setup/platform objects (WO-64, Phase E) "
                "persist in PostgreSQL/S3; replay_execution_events persisted"
            ),
        },

    # ── DEP Protocol (Public) ──────────────────────────────────────────────
    "dep_schemas": {
        "status": "implemented",
        "evidence": ["schemas/dep/*.schema.json", "docs/dep/spec.md", "docs/dep/governance.md"],
        "notes": "13 schemas: observation, context-artifact, context-binding, assessment, finding, envelope, etc.",
    },
    "dep_spec": {
        "status": "implemented",
        "evidence": ["docs/dep/spec.md", "docs/dep/whitepaper.md", "docs/dep/README.md"],
        "notes": "Public specification v0.1 draft; vendor-neutral",
    },
    "dep_ingress": {
        "status": "planned",
        "evidence": [],
        "notes": "WP-030: POST /v1/dep/resources, /batches, /cloudevents; provider registry",
    },
    "dep_validation_runtime": {
        "status": "planned",
        "evidence": [],
        "notes": "WP-020: Schema registry, canonical JSON, digest, conformance CLI, fixtures",
    },

    # ── Notary Sweep Engine (NSE) — Proprietary ───────────────────────────
    "dep_ingress_gateway": {
        "status": "planned",
        "evidence": [],
        "notes": "WP-030: Immutable DEP resource intake, quarantine, integrity conflicts",
    },
    "source_profiler": {
        "status": "planned",
        "evidence": [],
        "notes": "WP-040: Field types, timestamps, identifiers, samples, join keys, sensitive fields",
    },
    "decision_identity_resolver": {
        "status": "planned",
        "evidence": [],
        "notes": "WP-050: Exact-ID precedence, namespace mapping, ambiguity handling",
    },
    "temporal_context_resolver": {
        "status": "planned",
        "evidence": [],
        "notes": "WP-050: Effective-time bindings, supersession, authority, conflict preservation",
    },
    "decision_evidence_record": {
        "status": "planned",
        "evidence": [],
        "notes": "WP-050: DER as logical graph of resource refs + typed relationships",
    },
    "evaluator_registry": {
        "status": "planned",
        "evidence": [],
        "notes": "WP-060: Versioned contracts, prerequisites, method class, authority",
    },
    "sweep_runtime": {
        "status": "planned",
        "evidence": [],
        "notes": "WP-060: Frozen manifests, durable jobs, budgets, resumability, deterministic rerun",
    },
    "missing_evidence_evaluator": {
        "status": "planned",
        "evidence": [],
        "notes": "WP-070: Evidence requirement vs observed coverage",
    },
    "expected_outcome_mismatch_evaluator": {
        "status": "planned",
        "evidence": [],
        "notes": "WP-070: Requires customer-confirmed/authoritative expected outcome",
    },
    "replayability_failure_evaluator": {
        "status": "planned",
        "evidence": [],
        "notes": "WP-070: Reuses canonical replayability predicates",
    },
    "evidence_sufficiency_service": {
        "status": "planned",
        "evidence": [],
        "notes": "WP-070: Deterministic E0–E4 from predicates, not scores",
    },
    "assurance_candidate": {
        "status": "planned",
        "evidence": [],
        "notes": "WP-080: Lifecycle: candidate -> needs_context|reviewable -> approved|dismissed|accepted_risk|suppressed",
    },
    "candidate_review_service": {
        "status": "planned",
        "evidence": [],
        "notes": "WP-080: Append-only reviews, authority, suppression, deterministic delegation",
    },
    "proof_bridge_service": {
        "status": "planned",
        "evidence": [],
        "notes": "WP-090: Approved candidate -> VR/Incident -> existing replay/mutation/proof/scenario/gate path",
    },
    "policy_mismatch_evaluator": {
        "status": "planned",
        "evidence": [],
        "notes": "WP-110: Structured policy, executable comparison, confirmed policy only",
    },
    "guardrail_violation_evaluator": {
        "status": "planned",
        "evidence": [],
        "notes": "WP-110: Guardrail definition, enforcement event, side-effect state",
    },
    "consistency_mismatch_evaluator": {
        "status": "planned",
        "evidence": [],
        "notes": "WP-110: Confirmed cohort, comparison fields, variance rule",
    },
    "sdk_dep_mapping": {
        "status": "planned",
        "evidence": [],
        "notes": "WP-120: SDK capture -> DEP Observation/EvidenceBundle resources",
    },
    "otlp_bridge": {
        "status": "planned",
        "evidence": [],
        "notes": "WP-120: OTLP -> DEP Observation deterministic mapping",
    },
    "langsmith_adapter": {
        "status": "planned",
        "evidence": [],
        "notes": "WP-120: First native trace adapter",
    },
    "outcome_policy_adapter": {
        "status": "planned",
        "evidence": [],
        "notes": "WP-120: One authoritative outcome/policy source (Salesforce, Zendesk, DB)",
    },

    # ── Governed Assistance & Learning ──────────────────────────────────────
    "assistance_provider_interface": {
        "status": "planned",
        "evidence": [],
        "notes": "WP-130: Optional LLM assistance for mapping, policy extraction, summary, clustering",
    },
    "feedback_event_service": {
        "status": "planned",
        "evidence": [],
        "notes": "WP-130: Append-only reviewer corrections, mapping edits, suppression decisions",
    },

    # ── Production Hardening ───────────────────────────────────────────────
    "durable_sweep_scheduling": {
        "status": "planned",
        "evidence": [],
        "notes": "WP-140: Cursors, checkpoints, retries, dead-letter, budgets",
    },
    "secrets_manager_integration": {
        "status": "planned",
        "evidence": [],
        "notes": "WP-140: Source credential storage and rotation",
    },
    "s3_object_lock_verification": {
        "status": "planned",
        "evidence": [],
        "notes": "WP-140: Immutable manifest verification",
    },
    "tenant_isolation_tests": {
        "status": "partial",
        "evidence": ["tests/test_storage_tenant_isolation.py (planned)"],
        "notes": "WP-140: Cross-tenant read/write must fail closed",
    },
    "failure_injection_tests": {
        "status": "planned",
        "evidence": [],
        "notes": "WP-140: Worker crash, S3 failure, DB transaction failure, duplicate job, schema drift",
    },

    # ── Scenario Compounding & DEP Export ──────────────────────────────────
    "scenario_promotion_lineage": {
        "status": "planned",
        "evidence": [],
        "notes": "WP-150: Candidate -> Incident -> VR -> replay -> mutation -> proof -> Scenario -> Gate lineage",
    },
    "dep_evidence_bundle_export": {
        "status": "planned",
        "evidence": [],
        "notes": "WP-150: Export verified bundles and claims as DEP resources",
    },
    "gate_coverage_reporting": {
        "status": "planned",
        "evidence": [],
        "notes": "WP-150: Coverage by decision family, source availability, evaluator eligibility, evidence level",
    },
}


# ── Tests ──────────────────────────────────────────────────────────────────

class TestCapabilityInventory:
    """Ensures capability inventory is complete and accurately categorized."""

    def test_inventory_has_no_unknown_statuses(self) -> None:
        valid: set[str] = {"implemented", "partial", "demo_only", "planned"}
        for name, data in CAPABILITIES.items():
            assert data["status"] in valid, f"{name}: invalid status {data['status']}"

    def test_implemented_capabilities_have_evidence(self) -> None:
        for name, data in CAPABILITIES.items():
            if data["status"] == "implemented":
                assert data["evidence"], f"{name}: implemented but no evidence listed"
                assert len(data["evidence"]) >= 1, f"{name}: implemented but empty evidence"

    def test_partial_capabilities_have_notes(self) -> None:
        for name, data in CAPABILITIES.items():
            if data["status"] == "partial":
                assert data["notes"], f"{name}: partial but no notes explaining limitation"

    def test_planned_capabilities_reference_work_package(self) -> None:
        for name, data in CAPABILITIES.items():
            if data["status"] == "planned":
                assert "WP-" in data["notes"], f"{name}: planned but no WP reference in notes"

    def test_no_capability_is_both_demo_only_and_implemented(self) -> None:
        # Sanity: nothing marked demo_only should also claim implemented evidence
        for name, data in CAPABILITIES.items():
            if data["status"] == "demo_only":
                assert not any("implemented" in e.lower() for e in data["evidence"]), \
                    f"{name}: demo_only but evidence mentions implemented"

    def test_summary_counts(self) -> None:
        """Prints a summary for CI visibility."""
        counts: dict[str, int] = {}
        for data in CAPABILITIES.values():
            counts[data["status"]] = counts.get(data["status"], 0) + 1
        print(f"\nCapability summary: {counts}")
        # At baseline: implemented ~18, partial ~4, planned ~30
        assert counts.get("implemented", 0) >= 15
        assert counts.get("planned", 0) >= 25


def generate_markdown_report() -> str:
    """Generates a markdown report for documentation."""
    lines = ["# Notary Platform Capability Inventory\n", "| Capability | Status | Evidence / Notes |", "|---|---|---|"]
    for name, data in sorted(CAPABILITIES.items()):
        evidence = "; ".join(data["evidence"]) if data["evidence"] else data["notes"]
        lines.append(f"| {name} | {data['status']} | {evidence} |")
    return "\n".join(lines)


if __name__ == "__main__":
    # Allow running as script to generate report
    print(generate_markdown_report())
