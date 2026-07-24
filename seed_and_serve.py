"""Seed WP-100 landscape fixtures into in-memory storage, then start uvicorn."""
import sys

import uvicorn

from notary_platform.api_server.main import app
from notary_platform.discovery.models import (
    AdvisorySuggestion,
    ContextBinding,
    DecisionEvidenceRecord,
    DecisionEvidenceResource,
    LinkAssertion,
)
from notary_platform.discovery.sources import (
    FieldMappingEntry,
    FieldMappingVersion,
    FieldProfile,
    SourceConnection,
    SourceProfile,
)
from notary_platform.storage import get_storage, reset_storage
from notary_platform.sweep.models import (
    AssuranceCandidate,
    EvaluatorContractRecord,
    SweepDefinition,
    SweepRun,
)

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
reset_storage()
s = get_storage()

# Sources
for name, stype, status, adapter in [
    ("CRM DB", "database", "connected", "postgresql"),
    ("Support API", "api", "profiled", "rest"),
    ("Compliance Feed", "file", "pending", "csv"),
]:
    sc = SourceConnection(org_id="demo-org", name=name, source_type=stype, status=status, adapter_type=adapter)
    s.create_source_connection(sc)

# Source profiles
for sc in [sc1 for sc1 in [SourceConnection(org_id="demo-org")]]:
    pass
sc_list = s.list_source_connections("demo-org")
for sc in sc_list:
    fields = ["decision_id", "amount", "customer_id"] if "CRM" in sc.name else ["ticket_id", "resolution"]
    s.create_source_profile(SourceProfile(source_id=sc.id, org_id="demo-org",
        field_profiles=[FieldProfile(field_name=f) for f in fields]))

# Field mappings
sc = sc_list[0]
mapping = FieldMappingVersion(source_id=sc.id, status="confirmed", mappings=[
    FieldMappingEntry(source_field="decision_id", dep_field="decision_id"),
    FieldMappingEntry(source_field="amount", dep_field="decision_amount"),
])
s.create_field_mapping_version(mapping)

# Resources
for i in range(1, 4):
    s.create_resource(DecisionEvidenceResource(
        resource_id=f"res-{i}", org_id="demo-org", environment_id="env:demo",
        envelope_id=f"env-{i}",
        resource_type=["loan_application", "support_ticket", "compliance_report"][i - 1],
        provider_id="provider:main", digest_algorithm="sha-256",
        digest_value=f"digest-{i}", payload_ref=f"payload-{i}",
    ))

# DERs
identities = ["lending/approval", "support/escalation", "compliance/review"]
for i in range(1, 4):
    s.create_decision_evidence_record(DecisionEvidenceRecord(
        id=f"der-{i}", org_id="demo-org", environment_id="env:demo",
        decision_identity=identities[i - 1], identity_method="exact_id",
        evidence_level=f"E{i % 4}", source_resource_ids=[f"res-{i}"], enriched=True,
    ))

# Context binding
s.create_context_binding(ContextBinding(
    org_id="demo-org", environment_id="env:demo",
    subject_scope="decision_family", subject_selector="lending/approval",
    binding_type="governed_by_policy", artifact_ref="policy:underwriting-v3",
    authority="customer_confirmed",
))

# Link assertions
s.create_link_assertion(LinkAssertion(org_id="demo-org",
    source_resource_id="res-1", target_resource_id="res-2",
    relationship="confirms", basis="exact_deployment_id", status="confirmed"))
s.create_link_assertion(LinkAssertion(org_id="demo-org",
    source_resource_id="res-2", target_resource_id="res-3",
    relationship="contradicts", basis="heuristic", status="inferred"))

# Evaluator
s.create_evaluator_contract(EvaluatorContractRecord(
    org_id="demo-org", name="Policy Mismatch", version="1.0.0",
    method_class="deterministic", trust_class="authoritative",
    required_prerequisites=["decision_id", "policy_version"],
))

# Candidates
for i in range(1, 4):
    s.create_assurance_candidate(AssuranceCandidate(
        id=f"candidate-{i}", org_id="demo-org", environment_id="env:demo",
        der_id=f"der-{i}", candidate_type="expected_outcome_mismatch",
        lifecycle_state="needs_context" if i == 1 else ("reviewable" if i == 2 else "approved_incident"),
        evidence_level=f"E{i % 4}",
        actual_outcome=["approved", "escalated", "flagged"][i - 1],
        expected_outcome=["denied", "escalate_to_human", "auto_approve"][i - 1],
        missing_prerequisites=["verified_replay_run"] if i == 3 else [],
    ))

# Advisory suggestion
s.create_advisory_suggestion(AdvisorySuggestion(
    org_id="demo-org", suggestion_type="systematic_issue",
    workflow_id="wf-demo",
    content={"cohort": "lending/approval", "method": "clustering",
             "time_window": "2026-07-01/2026-07-24",
             "evidence": ["res-1", "res-2"], "coverage": 0.6},
    basis="Advisory only, not authoritative",
))

# Sweep definition and run
sd = SweepDefinition(org_id="demo-org", name="Default Sweep", enabled=True, schedule="manual")
s.create_sweep_definition(sd)
s.create_sweep_run(SweepRun(org_id="demo-org", environment_id="env:demo",
    definition_id=sd.id, status="completed"))

print(f"Seeded: {len(s.list_decision_evidence_records('demo-org'))} DERs, "
      f"{len(s.list_resources('demo-org'))} resources, "
      f"{len(s.list_assurance_candidates('demo-org'))} candidates")

uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
