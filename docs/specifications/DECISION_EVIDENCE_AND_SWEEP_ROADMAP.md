# Decision Evidence and Sweep Roadmap

**Status:** Proposed execution roadmap
**Date:** July 2026
**Scope:** Independent DEP publication plus proprietary Notary Sweep Engine and platform integration
**Excluded:** Command Center, process mining, live observability, generalized GRC workflow, and autonomous remediation

## 1. Outcome

Deliver a low-friction discovery path that begins with evidence customers already possess, reconstructs decision-time context across systems, surfaces explainable Assurance Candidates, and moves accepted failures through Notary's existing replay, fix verification, proof, Scenario, and Release Gate workflow.

The program has two independent artifacts:

1. **Decision Evidence Protocol:** Public specification, schemas, examples, conformance fixtures, and independent verifier behavior.
2. **Notary Sweep Engine:** Proprietary platform implementation for profiling, identity resolution, temporal context resolution, evaluator planning, evidence sufficiency, clustering, prioritization, review, and proof-loop orchestration.

## 2. Product Invariants

* DEP never depends on Notary-specific resources, services, domains, or product workflows.
* NSE consumes and produces portable DEP resources at its external boundaries.
* Source evidence remains immutable and attributable; normalization never flattens ownership or silently upgrades authority.
* Sweep produces candidates by default. Incident promotion requires human authority or explicit deterministic delegation.
* Evaluators run only when declared prerequisites are satisfied.
* Evidence sufficiency is deterministic and independent from severity or ranking.
* Replay and fix verification use the existing Replay Engine; NSE does not implement a second execution path.
* Initial storage uses PostgreSQL and S3. No graph database or neural network is required for the first production release.
* Cross-customer learning is disabled by default.

## 3. Delivery Strategy

Build vertical slices that produce visible customer value. Do not build a connector catalog first. The first slice uses generic intake plus one trace source and one authoritative outcome or policy source, because context diversity matters more than connector count.

Recommended initial source set:

* Notary SDK cassettes;
* DEP HTTP and batch bundles;
* OpenTelemetry bridge;
* CSV/JSONL historical import;
* LangSmith as the first native observability adapter;
* one pilot-specific business outcome source, selected between Salesforce, Zendesk, ServiceNow, or a customer database export.

## 4. Phased Roadmap

### Phase 0: DEP Publication Foundation

**Duration:** 2 weeks
**Goal:** Freeze the independent protocol boundary before NSE implementation creates accidental product coupling.

**Deliverables:**

* Publish the DEP ecosystem whitepaper, normative specification, and implementation-neutral governance policy.
* Publish DEP terminology, roles, resource families, relationships, epistemic statuses, and evidence sufficiency levels in the normative specification.
* Define the Provider Card, CloudEvents envelope, HTTP profile, batch profile, and OTLP bridge profile.
* Publish JSON Schemas for the exchange envelope, Provider Card, Observation, ContextArtifact, ContextBinding, Assessment, Finding, ReviewDecision, EvidenceBundle, VerificationClaim, EvaluatorContract, and ProcessingManifest.
* Publish threat model, versioning rules, namespace rules, redaction behavior, integrity rules, and the public proposal process.
* Produce neutral lending and customer-support examples.
* Create conformance fixtures for valid resources, invalid resources, conflicts, redactions, idempotency, and independent claim verification.

**Exit criteria:**

* No schema or example contains a Notary identifier.
* A standalone validator can validate all fixtures.
* A third-party implementation can emit a valid Observation and validate a VerificationClaim using only public material.

### Phase 1: Evidence Foundation

**Duration:** 3 weeks
**Goal:** Store portable evidence safely before implementing discovery intelligence.

**Deliverables:**

* Implement #DEPIngressGateway with HTTP and batch ingestion.
* Add immutable `DecisionEvidenceResource` storage in S3 and PostgreSQL indexes.
* Implement tenant scope, digest validation, idempotency, quarantine, redaction lineage, and source provenance.
* Add Provider Card registration and connection health.
* Add basic source inventory and resource coverage API.
* Add contract tests using DEP conformance fixtures.

**Exit criteria:**

* Duplicate deliveries are idempotent.
* Identifier reuse with a changed digest creates an integrity conflict.
* Every normalized field can be traced to a source resource or recorded transformation.
* No cross-tenant query path exists in integration tests.

### Phase 2: Progressive Discovery Setup

**Duration:** 3 weeks
**Goal:** Replace heavy up-front setup with inspect, propose, confirm, and continue.

**Deliverables:**

* Implement SourceConnection, SourceProfile, FieldMapping, redaction policy, and source cursor models.
* Build #SourceProfiler for CSV, JSONL, generic HTTP, and OTLP inputs.
* Show schema, volume, sample records, identifiers, timestamps, candidate joins, sensitive fields, and available evidence types.
* Generate inferred mapping proposals with explicit confidence and source basis.
* Require confirmation only for mappings needed by the selected discovery objective.
* Show which evaluators each confirmed mapping unlocks.

**Exit criteria:**

* A user can upload one source and obtain a source profile without completing an organization questionnaire.
* Required mapping errors and optional enrichment are visually distinct.
* Preview performs no Incident creation and no authoritative evaluation.

### Phase 3: Decision Identity and Context Graph

**Duration:** 4 weeks
**Goal:** Construct contestable Decision Evidence Records and resolve historical context safely.

**Deliverables:**

* Implement #DecisionIdentityResolver and LinkAssertion history.
* Implement `DecisionEvidenceRecord` as a logical graph over immutable resources.
* Implement `ContextBinding`, applicability selectors, effective intervals, authority, and explicit supersession.
* Implement #TemporalContextResolver and human-readable ResolutionTrace.
* Support exact decision, case/session, family, system/version, environment, and organization scopes.
* Add context-conflict workflow and correction history.

**Exit criteria:**

* Exact IDs outrank inferred similarity.
* An ambiguous join remains unconfirmed and cannot support authoritative evaluation.
* Historical decisions use the artifact effective at decision time.
* Equal-authority disagreement blocks dependent evaluators and is visible to reviewers.

### Phase 4: Sweep MVP

**Duration:** 4 weeks
**Goal:** Produce the first trustworthy, explainable Assurance Candidates.

**Deliverables:**

* Deploy the Sweep Worker and durable job lifecycle.
* Implement versioned SweepDefinition and immutable SweepRun manifests.
* Implement #EvaluatorRegistry, #SweepPlanner, and prerequisite checking.
* Implement deterministic missing-evidence, expected-outcome-mismatch, and replayability-failure evaluators.
* Implement #EvidenceSufficiencyService for E0 through E3; E4 remains supplied by completed fix verification.
* Implement #CandidateAssembler with evidence links, context trace, missing prerequisites, business summary, and available actions.
* Add candidate list and detail views to the dashboard.

**Exit criteria:**

* Every evaluator is recorded as executed, skipped, failed, or suppressed.
* Missing prerequisites never become guessed results.
* A non-technical reviewer can identify what happened, why it was flagged, what is known, and what is missing.
* Re-running a deterministic manifest produces identical assessments.

### Phase 5: Review and Proof Bridge

**Duration:** 3 weeks
**Goal:** Connect discovery to the existing proof loop without weakening incident authority.

**Deliverables:**

* Implement #CandidateReviewService and append-only ReviewDecision resources.
* Support approve, dismiss, request context, accept risk, scoped suppression, and instrument-next-occurrence.
* Implement optional deterministic incident-promotion rules with visible delegation and revocation.
* Implement #ProofBridgeService and exact prerequisite reporting.
* Link candidate, DER, Sweep Run, review decision, Incident, replay, fix verification, certificate, Scenario, and gate lineage.
* Update Incident Detail to show discovery origin and evidence sufficiency progression.

**Exit criteria:**

* A probabilistic assessment cannot promote itself.
* An approved E3 candidate enters the existing replay path with no duplicate execution implementation.
* An ineligible candidate receives an exact missing prerequisite, not a generic proof failure.
* A completed fix advances the record to E4 and preserves full lineage.

### Phase 6: Evaluator Depth

**Duration:** 4 weeks
**Goal:** Add the context-heavy checks that create differentiated assurance value.

**Deliverables:**

* Add structured policy-mismatch evaluator with rule trace.
* Add guardrail-violation evaluator with enforcement and side-effect state.
* Add consistency-mismatch evaluator requiring confirmed cohort and variance definitions.
* Implement Notary-certified, customer-defined, and third-party evaluator classes.
* Add evaluator certification state and proof-eligibility enforcement.
* Add customer rule testing against sample DERs before activation.

**Exit criteria:**

* A policy document parsed by AI remains draft until confirmed or supplied in executable form.
* Similar cases without a confirmed cohort cannot be labeled a consistency violation.
* Customer evaluators can produce useful candidates without being represented as Notary-certified.

### Phase 7: Native Pilot Adapters

**Duration:** 4 weeks
**Goal:** Reduce setup effort for the systems used by design partners.

**Deliverables:**

* Build LangSmith adapter with authentication, cursoring, pagination, retries, rate limits, schema drift handling, deletion state, provenance, and fixtures.
* Build one pilot-specific business outcome adapter.
* Add source-to-source identity mapping UI and coverage diagnostics.
* Return Incident, proof, and Scenario references to providers where supported.
* Document least-privilege scopes and data minimization for every adapter.

**Exit criteria:**

* Both adapters survive replayed pagination, throttling, schema-change, duplicate, and deletion fixtures.
* The pilot workflow links trace evidence to at least one authoritative business outcome or policy source.
* The customer can disconnect an adapter without losing previously retained evidence lineage.

### Phase 8: Production Hardening

**Duration:** 4 weeks
**Goal:** Make scheduled discovery reliable, bounded, secure, and operable.

**Deliverables:**

* Add run scheduling, cursor checkpoints, cancellation, retry, backoff, dead-letter handling, and resumability.
* Add per-organization concurrency, evidence-volume, evaluator, and cost budgets.
* Add operational metrics for ingestion rejection, mapping coverage, resolver conflict, skipped checks, candidate yield, review outcomes, and proof conversion.
* Add retention, deletion tombstones, key rotation, custody, audit, and disaster-recovery tests.
* Complete threat modeling, tenant-isolation testing, penetration testing, and failure injection.
* Add support tooling that exposes run diagnostics without exposing customer evidence across tenants.

**Exit criteria:**

* Failed workers resume without duplicate candidates or corrupted manifests.
* Scheduled runs cannot starve interactive API traffic.
* Tenant isolation and deletion behavior pass security review.
* Service objectives and alert thresholds are defined from measured pilot behavior.

### Phase 9: Scenario and Gate Compounding

**Duration:** 3 weeks
**Goal:** Convert verified discovery findings into recurring release assurance.

**Deliverables:**

* Recommend Scenario promotion only for human-labeled, reproducible, verified Incidents.
* Preserve candidate-to-Incident-to-Scenario lineage and evidence-grade history.
* Add release impact summaries showing which discovered failure a gate prevents.
* Add coverage reporting by decision family, evaluator eligibility, Scenario status, and missing context.
* Add verified-finding exports using DEP EvidenceBundle and VerificationClaim resources.

**Exit criteria:**

* A buyer can follow one case from imported evidence to candidate, Incident, replay, fix, certificate, Scenario, and passing gate.
* A gate never implies coverage for an untested decision family or missing evidence scope.

## 5. Parallel Workstreams

### Protocol and SDK

* Maintain DEP schemas, examples, validators, and conformance fixtures.
* Map SDK cassette capture to DEP Observations and EvidenceBundles.
* Keep local SDK verification offline and independent from platform availability.

### Platform Backend

* Build ingress, storage, graph repositories, workers, evaluators, review, and Proof Bridge.
* Keep all engine-specific code behind internal ports with contract tests at DEP boundaries.

### Platform Experience

* Build progressive setup, source coverage, conflict resolution, Sweep Runs, candidate detail, and review.
* Extend Incident Detail and release impact rather than creating a separate discovery product shell.

### Security and Assurance

* Threat-model provider impersonation, resource substitution, replay attacks, cross-tenant joins, unsafe replay, malicious evaluator payloads, and authority escalation.
* Publish verifier behavior and claim limitations while keeping managed key custody operational controls internal.

## 6. Recommended Team

The minimum credible team is four dedicated engineers plus fractional product/design/security support:

* one protocol and SDK engineer;
* two backend/platform engineers;
* one full-stack product engineer;
* fractional product designer or TPM;
* fractional security and infrastructure reviewer.

With this team, Phases 0 through 5 are approximately 19 weeks sequentially. Protocol, product experience, and backend work can overlap to target a design-partner vertical slice in 12 to 14 weeks, provided the pilot sources are selected in Phase 0 and existing proof-loop APIs remain stable.

## 7. Demo Milestones

### Milestone A: Evidence arrives

Import trace and outcome data, show provider provenance, source coverage, mapping preview, and a partial DER.

### Milestone B: Context changes meaning

Attach the historical policy, resolve its effective version, and show an evaluator moving from skipped to eligible.

### Milestone C: Candidate is explainable

Run Sweep and show actual versus expected outcome, source evidence, decision-time context, evidence level, and missing replay prerequisite.

### Milestone D: Proof loop closes

Approve the candidate, enrich the cassette, replay the original, verify the fix, issue the certificate, promote the Scenario, and pass the Release Gate.

## 8. Risks and Controls

| Risk | Control |
| --- | --- |
| Connector work consumes the roadmap | Generic DEP, file, HTTP, and OTLP first; native adapters only for pilot demand |
| False positives damage trust | Prerequisite-aware evaluators, candidates before Incidents, explicit missing context |
| Current policy applied to historical decisions | Effective-time bindings, explicit supersession, conflict preservation |
| Proprietary logic leaks into DEP | Public conformance tests at the boundary; separate repositories and terminology |
| Closed algorithms become unchallengeable | Explain every individual output with inputs, context, method class, and limitations |
| Customer rules dilute certification | Evaluator trust classes and proof-eligibility checks |
| Scheduled Sweep becomes observability | Bounded runs, no live telemetry dashboard, no real-time operational alerting |
| Cross-customer learning creates privacy risk | Tenant-isolated default; opt-in governed aggregates only |
| Evidence retention conflicts with privacy | Redaction lineage, reference-only fields, tombstones, scoped retention |

## 9. First Build Cut

The first implementation increment should contain only:

1. DEP Observation, ContextArtifact, ContextBinding, Assessment, EvaluatorContract, and ProcessingManifest schemas.
2. HTTP and JSONL intake with immutable storage and provenance.
3. CSV/JSONL profiling and confirmed field mapping.
4. Exact-ID Decision Evidence Record construction.
5. Effective-time context binding without inferred identity.
6. Missing-evidence and expected-outcome evaluators.
7. E0 through E2 sufficiency calculation.
8. Assurance Candidate list, detail, and approve/dismiss review.
9. Proof Bridge eligibility report using the existing Incident API.

This cut demonstrates the core thesis without requiring a neural network, a graph database, five native connectors, or a second replay engine.
