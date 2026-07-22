# Notary Decision Evidence and Sweep Implementation Roadmap

* **Status:** Active implementation roadmap
* **Revision:** July 2026, repository-aware execution edition
* **Repository baseline:** `notary-platform` at `5d6a3a4` on `codex/setup-spine-unification`
* **Requirements authority:** [Notary Platform Requirements](./NOTARY_PLATFORM_REQUIREMENTS.md)
* **Architecture authority:** [Notary Platform Blueprints](./NOTARY_PLATFORM_BLUEPRINTS.md)
* **Protocol authority:** [Decision Evidence Protocol](../dep/README.md)
* **Primary scope:** Notary Platform and Notary SDK
* **Explicitly excluded:** Command Center, process mining, generalized GRC workflow, real-time observability, autonomous remediation, and a custom neural network

## 1. Purpose and Required Outcome

This document is the implementation handoff for turning the currently working Notary proof loop and setup experience into a production-capable Decision Evidence Discovery and Sweep system.

The end state is one continuous customer journey:

1. A customer starts with evidence they already possess: an SDK cassette, JSON/JSONL/CSV export, DEP resource, OpenTelemetry trace, or supported source adapter.
2. Notary profiles the source before committing data or requiring a large setup questionnaire.
3. The customer confirms only the mappings and context needed for the discovery objective.
4. Notary preserves each source artifact, its provenance, authority, effective time, and epistemic status.
5. Notary links evidence into a contestable Decision Evidence Record (DER) without flattening source boundaries.
6. The Notary Sweep Engine (NSE) runs only evaluators whose declared prerequisites are satisfied.
7. NSE produces explainable Assurance Candidates, not automatic claims that an AI system failed.
8. An authorized human or an explicit deterministic delegation approves a candidate as an Incident.
9. The approved Incident enters the existing cassette replay, fix verification, certificate, Scenario, Readiness, and Release Gate path.
10. Reviewer decisions and verified outcomes improve future mapping, ranking, and evaluator coverage without changing historical evidence or silently creating new truth.

The implementation is successful when a non-technical buyer can follow one real decision from imported or captured evidence through context resolution, candidate discovery, review, replay, fix verification, proof issuance, Scenario promotion, and a passing Release Gate.

## 2. Non-Negotiable Product and Engineering Rules

Every coding agent must preserve these rules. A work package is incomplete if it violates any one of them.

1. **DEP is independent.** Public DEP schemas and documentation must not depend on Notary names, APIs, services, or proprietary algorithms.
2. **NSE is proprietary.** Identity resolution, temporal resolution, evaluator implementations, clustering, ranking, calibration, and feedback application remain internal Notary code.
3. **Evidence is immutable.** A correction creates a new resource, mapping version, binding, or superseding decision. It never rewrites source evidence or a completed Sweep Run.
4. **Provenance survives normalization.** Every normalized field must point to a source resource or a recorded transformation.
5. **Missing context is not failure.** Evaluators with missing or conflicted prerequisites are skipped or emit an Evidence Gap when that is their declared purpose.
6. **Candidates are not Incidents.** Promotion requires an authorized Review Decision or a versioned deterministic delegation rule.
7. **Probabilistic output is advisory.** LLM or statistical output cannot establish policy applicability, expected correctness, proof eligibility, Incident authority, or Release Gate outcome by itself.
8. **Evidence sufficiency is deterministic.** E0-E4 is calculated from explicit predicates and remains separate from severity, confidence, and priority.
9. **Replay has one implementation.** NSE never creates a second replay engine. Approved candidates bridge into the existing `ReplayService`, `MutationService`, `CertificateService`, `ScenarioLibraryService`, `ReadinessService`, and `ReleaseGateService` path.
10. **No production side effects during discovery.** Profiling and Sweep do not call customer production tools or replay side effects.
11. **Tenant scope is mandatory.** Every query and stored object is scoped by organization and environment. An identifier alone is never an authorization boundary.
12. **Setup is progressive.** The user may receive useful Evidence Gap or replayability results after one source. Optional enrichment cannot block the entire setup flow.
13. **No connector catalog before value.** Generic intake plus one trace source and one authoritative context or outcome source is the first vertical slice.
14. **No graph database initially.** PostgreSQL metadata and immutable S3 payloads are sufficient for the first production release.
15. **No custom neural network initially.** Improvement comes first from evaluator coverage, confirmed mappings, review feedback, better context bindings, ranking, deduplication, and Scenario promotion.

## 3. What Exists Today

The coding agent must inspect and reuse the current implementation. It must not rebuild working proof-loop capabilities under new names.

### 3.1 Implemented and reusable

| Capability | Current implementation | How it must be used |
| --- | --- | --- |
| Public DEP package | `docs/dep/` and `schemas/dep/` | Treat schemas as the external contract; add conformance fixtures and validators without Notary coupling. |
| Platform API | `src/notary_platform/api_server/main.py` and routers | Add discovery routes through a new router; preserve current `/v1` conventions and auth dependency. |
| Setup-plan spine | `AssuranceSetupPlan`, `DecisionWorkflow`, `WorkflowEvidenceSource`, and setup routes | Extend the active setup plan; do not create a second onboarding wizard. |
| Progressive historical import | `/v1/setup/plans/{plan_id}/imports/parse`, `/preview`, and `/commit` | Reuse parsing and preview UX. Replace the direct-to-VerificationRecord commit path in controlled steps. |
| Discovery UI entry point | Decision Discovery section in `static/app/app.js` | Evolve this surface into source profile, mapping, Sweep Run, and candidate views. |
| Verification Record ingestion | `IngestionService` and verification routes | Use as the proof-loop bridge target after candidate approval. Do not use it as the immutable DEP store. |
| Replayability assessment | `ReplayabilityService` | Reuse its known checks while extracting evaluator-compatible pure logic where needed. |
| Replay execution trace | `ReplayRun` and `ReplayExecutionEvent` | Preserve and link these records from accepted candidates. |
| Fix verification | `MutationService` and `MutationTest` | Remains the only before/after fix verification path. |
| Proof issuance | `CertificateService`, `ProofClaim`, and `ProofCertificate` | Reuse exact prerequisite and limitation behavior; extend lineage, not signing logic. |
| Scenario and gate loop | `ScenarioLibraryService`, `ScenarioRunService`, `ReadinessService`, `ReleaseGateService` | Preserve as the downstream recurrence-prevention path. |
| Python capture SDK | `packages/notary-sdk-py` | Extend capture-to-DEP mapping and metadata; preserve offline verification. |
| Local and demo persistence | `MemoryStorage` and `SharedDemoFileStorage` | Keep for local development and deterministic fixtures. |
| AWS storage path | `PostgresS3Storage` | Complete its stubs before claiming production persistence. |
| Automated tests | `tests/` plus SDK tests | Follow existing FastAPI `TestClient`, service, storage, UI, replay, and release-gate patterns. |

### 3.2 Partially implemented or transitional

| Area | Current limitation | Required correction |
| --- | --- | --- |
| Discovery import | Preview applies heuristic selection rules and commit creates `VerificationRecord` objects directly. | Introduce immutable evidence intake, Source Profile, confirmed mapping, DER, Sweep Run, and Assurance Candidate stages before any proof-loop bridge. |
| Discovery findings | Existing findings contain trigger, reason, replayability, and a Scenario-candidate boolean. | Replace with typed Assessments and Assurance Candidates containing evidence links, context trace, evaluator version, evidence level, limitations, and lifecycle state. |
| Setup persistence | Several `PostgresS3Storage` setup methods return empty values or no-op. | Implement remote persistence for setup plans, workflows, connectors, mappings, rules, and discovery objects. |
| Replay runner | Demo replay works; a non-demo customer replay runner is not generally configured. | Make replay eligibility honest and support a pluggable customer runner or explicit sandbox requirement. |
| TypeScript SDK | `packages/notary-sdk-ts` is a placeholder. | Keep out of the critical path until Python SDK and DEP mapping are stable; then implement parity as a separate work package. |
| Schema validation | DEP schemas exist, but runtime validation and complete conformance fixtures do not. | Add a schema registry, local `$ref` resolution, deterministic validation errors, and positive/negative fixtures. |
| Source adapters | Generic manual/webhook/import paths exist; native adapters do not meet production adapter contracts. | Build only the adapters required by the first design partner after generic DEP/file/OTLP paths work. |
| Sweep runtime | Blueprint components exist only in documentation. | Implement durable jobs, frozen manifests, evaluator planning, results, and resumability. |
| LLM assistance | Label suggestion is heuristic and no governed model-assistance boundary exists. | Add optional, versioned, advisory assistance only after deterministic engine contracts are stable. |

### 3.3 Not implemented

The following named components from the blueprint still require implementation:

* `DEPIngressGateway`
* `SourceAdapterPort`
* `DiscoverySetupService`
* production `SourceProfiler`
* `DecisionIdentityResolver`
* `TemporalContextResolver`
* `EvaluatorRegistry`
* `SweepPlanner`
* `EvidenceSufficiencyService`
* `CandidateAssembler`
* `CandidateReviewService`
* `ProofBridgeService`
* durable Sweep Worker and job lifecycle
* context conflicts, resolution traces, review decisions, suppressions, and deterministic promotion delegation
* a governed learning loop based on reviewer feedback and verified outcomes

## 4. Target Architecture and Data Flow

```text
SDK / DEP / File / OTLP / Native Adapter
                  |
                  v
        DEP Ingress + Quarantine
                  |
                  v
 Immutable Resource Store + Source Index
                  |
          Source Profile + Mapping
                  |
                  v
 Decision Identity + Temporal Context Resolution
                  |
                  v
       Decision Evidence Record (DER)
                  |
                  v
  Sweep Planner -> Evaluator Registry -> Assessments
                  |
                  v
       Evidence Sufficiency + Candidate Assembly
                  |
                  v
       Human Review / Deterministic Delegation
                  |
                  v
    Proof Bridge -> existing Verification Record / Incident
                  |
                  v
 Replay -> Fix Verification -> Proof -> Scenario -> Release Gate
                  |
                  v
     Governed Feedback Events and Coverage Improvements
```

### 4.1 Storage model

Use PostgreSQL for identity, indexing, configuration, relationships, run state, review state, and queryable metadata. Use S3 for immutable DEP payloads, source snapshots, frozen manifests, evidence bundles, and exported claims.

The initial implementation must use two persistence patterns deliberately:

* A dedicated `decision_evidence_resources` table enforces resource identity and digest conflicts.
* Versioned discovery metadata may use typed objects serialized to PostgreSQL JSONB while the model is evolving, but it must include indexed `org_id`, `environment_id`, `kind`, `id`, `version`, and lifecycle fields.

Do not put source payloads, secrets, or large trace bodies in query-oriented JSONB rows. Do not add Neo4j or another graph database. DER is a logical graph built from relational edges and immutable resource references.

### 4.2 Current-to-target object mapping

| Current object | Target relationship |
| --- | --- |
| `AssuranceSetupPlan` | Owns selected sources, discovery objective, mapping versions, and initial Sweep Definition reference. |
| `DecisionWorkflow` | Supplies business decision-family scope and optional customer-confirmed expected behavior. |
| `WorkflowEvidenceSource` | Becomes or references a versioned `SourceConnection`; existing values must migrate without loss. |
| `RecordSelectionRule` | Becomes a pre-ingestion selection/sampling rule; it is not an assurance evaluator. |
| `VerificationRecord` | Remains the proof-loop record created or linked by `ProofBridgeService` after candidate approval. |
| `ScenarioCandidate` | Remains a candidate for Scenario promotion after proof. It must not be reused as `AssuranceCandidate`. |
| `EvidenceArtifact` | Remains a proof-loop artifact. DEP source resources use a separate immutable resource model. |
| `HumanLabel` | May supply expected-outcome context when its authority and effective scope are explicit. |
| `ReplayabilityService` | Supplies logic to the replayability evaluator and downstream proof eligibility, with one canonical predicate set. |
| `KnownLimitation` | Continues into proof claims; discovery limitations link to it through the Proof Bridge. |

### 4.3 Required new domain objects

Implement the blueprint fields and constraints for these objects. Each object must expose `to_dict`/`from_dict` behavior consistent with current repository conventions until a typed validation migration is intentionally performed.

* `ProviderRegistration`
* `SourceConnection`
* `SourceCursor`
* `SourceProfile`
* `FieldMappingVersion`
* `DecisionEvidenceResource`
* `IntegrityConflict`
* `LinkAssertion`
* `ContextBinding`
* `ContextConflict`
* `ResolutionTrace`
* `DecisionEvidenceRecord`
* `EvaluatorContractRecord`
* `SweepDefinition`
* `SweepRun`
* `EvaluationExecution`
* `AssessmentRecord`
* `EvidenceSufficiencyResult`
* `AssuranceCandidate`
* `ReviewDecisionRecord`
* `SuppressionRule`
* `PromotionDelegation`
* `ProofBridgeResult`
* `FeedbackEvent`

Do not place all new classes in the already-large `models.py`. Create `src/notary_platform/discovery/models.py` and export only stable public types from `src/notary_platform/discovery/__init__.py`.

## 5. LLM and Continuous-Improvement Policy

The platform warrants optional LLM assistance. It does not warrant a custom neural network or an LLM in the assurance authority path.

### 5.1 Deterministic core

The following must be deterministic, versioned, testable without network access, and reproducible from a frozen manifest:

* schema and digest validation;
* tenant and environment enforcement;
* idempotency and integrity-conflict detection;
* exact identifier matching;
* effective-time and explicit-supersession resolution;
* evaluator prerequisite checks;
* policy evaluation when the policy is executable or customer-confirmed structured data;
* missing-evidence and replayability checks;
* E0-E4 evidence sufficiency;
* candidate lifecycle transitions;
* promotion authority;
* replay and fix-verification eligibility;
* proof and certificate eligibility;
* Scenario and Release Gate pass/fail behavior.

### 5.2 Permitted model-assisted functions

Model assistance may be added behind an internal `AssistanceProvider` interface for:

* suggesting source-field mappings;
* extracting a draft structured policy from a document;
* drafting a buyer-readable candidate summary;
* suggesting candidate clusters or duplicate groups;
* suggesting evaluator configuration from plain-language customer intent;
* ranking the next context source likely to unlock the most evaluator coverage.

Every model-assisted output must include provider, model, prompt/template version, input resource references, generation time, confidence where available, and status `inferred`. It remains inactive until confirmed when used for identity, policy, expected outcome, or applicability.

### 5.3 Prohibited model behavior

An LLM must never:

* mutate source evidence;
* invent missing evidence or context;
* silently convert inferred data into observed or customer-confirmed data;
* make final Incident promotion decisions;
* issue or approve proof;
* determine Release Gate pass/fail;
* train across customer evidence by default;
* hide the deterministic reason an evaluator ran or was skipped.

### 5.4 Continuous improvement without model training

Implement improvement as governed product data before considering training:

1. Record reviewer corrections, dismissals, approvals, context requests, mapping edits, and suppression decisions as append-only `FeedbackEvent` records.
2. Record whether a candidate reached replay, reproduced, verified, received proof, and became a Scenario.
3. Calculate evaluator yield, dismissal rate, context-block rate, proof-conversion rate, and duplicate rate by evaluator version and decision family.
4. Improve rules, mappings, ranking weights, prompts, and coverage only in new versions.
5. Validate every new version against frozen organization-specific fixtures before activation.
6. Keep cross-customer aggregation disabled unless explicit governance and opt-in requirements are implemented.

A custom neural model may be reconsidered only after there is a large, lawful, representative, explicitly governed labeled dataset and a measured task where rules, retrieval, and off-the-shelf model assistance are insufficient. That is not part of this roadmap.

## 6. Delivery Sequence

Work packages are ordered by dependency. Coding agents must complete them in order unless a package explicitly says it may run in parallel. Each package must leave the repository passing tests and must not expose non-working UI controls.

### WP-000: Baseline, contract inventory, and execution guardrails

**Goal:** Freeze the current behavior before changing discovery persistence or routing.

**Required work:**

* Run and record `pytest`, `ruff check`, `ruff format --check`, and `mypy` results.
* Add a machine-readable build-status test or fixture that distinguishes implemented, partial, demo-only, and planned capabilities.
* Inventory every existing setup, import, Verification Record, replay, mutation, certificate, Scenario, readiness, and gate endpoint.
* Add golden-path integration coverage for the existing flow: import or SDK snapshot -> Verification Record -> label -> Incident -> replay -> mutation -> proof -> Scenario -> readiness -> release gate.
* Add a regression assertion that a non-demo record without a configured replay runner cannot report successful replay.
* Document the transitional direct-import behavior in API response metadata as `processing_path: legacy_verification_record` until WP-090 replaces it with the reviewed Proof Bridge path.

**Primary files:**

* `tests/test_customer_record_golden_path.py`
* `tests/test_setup_engine_fixes.py`
* `tests/test_release_gate_vertical.py`
* `src/notary_platform/api_server/routers/setup.py`
* `src/notary_platform/api_server/routers/platform.py`

**Exit criteria:**

* Existing proof-loop behavior has an end-to-end regression test.
* Demo-only behavior is explicit in API data and tests.
* Baseline commands pass before feature work begins.

### WP-010: Complete production persistence foundations

**Goal:** Ensure current setup and proof-loop state survives process restart in the remote backend before adding discovery state.

**Required work:**

* Replace all `PostgresS3Storage` no-op setup/platform methods with real PostgreSQL persistence.
* Persist `Organization`, `Environment`, `Agent`, `SystemConnection`, `CapturePolicy`, `AISystem`, `CaptureConnector`, `FieldHandlingRule`, `CaptureValidationRun`, `DecisionFamilyCandidate`, `DecisionWorkflow`, `WorkflowEvidenceSource`, `RecordSelectionRule`, and `AssuranceSetupPlan`.
* Persist `ReplayExecutionEvent`; remove the process-local remote-backend dictionary.
* Fix list methods that currently attempt organization-empty reads when retrieving labels, replay runs, or mutation tests. Queries must receive organization scope or perform a tenant-safe join.
* Introduce schema migration files or an idempotent versioned migration runner. Do not continue growing one unversioned `_ensure_schema` method.
* Add uniqueness and tenant indexes for all object identifiers and parent references.
* Preserve `MemoryStorage` and `SharedDemoFileStorage` behavior.

**Primary files and additions:**

* `src/notary_platform/storage.py`
* `src/notary_platform/persistence/migrations.py`
* `src/notary_platform/persistence/schema/`
* `tests/test_remote_storage_contract.py`
* `tests/test_storage_tenant_isolation.py`

**Tests:**

* Run one shared storage contract suite against memory and a disposable PostgreSQL/S3-compatible test fixture.
* Verify create/get/list/update for every persisted type.
* Restart storage and verify setup plans, replay traces, and proof-loop records remain available.
* Verify organization A cannot fetch or list organization B objects by guessed identifier.

**Exit criteria:**

* Remote storage contains no setup/discovery-related no-op implementation.
* Replay execution events survive restart.
* Tenant-isolation tests fail closed.

### WP-020: DEP runtime validation and conformance harness

**Goal:** Convert the published DEP schemas into an executable platform boundary.

**Required work:**

* Implement a schema registry that loads `schemas/dep/*.schema.json` once and resolves local references without network access.
* Validate envelope version, resource type, stable resource ID, provider identity, subject reference, provenance, timestamps, digest format, and declared signature metadata.
* Define canonical JSON bytes and digest computation. One function must be used by HTTP, batch, tests, and SDK mapping.
* Add positive fixtures for every resource type and negative fixtures for missing identity, malformed time, invalid epistemic status, unknown schema version, invalid digest, cross-resource reference error, and redaction lineage error.
* Add a standalone validation command usable by SDK and third-party implementers.
* Keep validation errors machine-readable: `code`, `resource_id`, `json_pointer`, `message`, and `retryable`.

**Target package:**

```text
src/notary_platform/dep/
  __init__.py
  canonical.py
  registry.py
  validation.py
  errors.py
  cli.py
tests/fixtures/dep/valid/
tests/fixtures/dep/invalid/
tests/test_dep_conformance.py
```

**Exit criteria:**

* All published schemas have valid and invalid fixtures.
* Validation is deterministic and offline.
* No public schema, fixture, or error contract contains proprietary NSE fields.

### WP-030: Immutable DEP ingress and source inventory

**Goal:** Accept portable evidence safely before implementing discovery intelligence.

**Required models:** `ProviderRegistration`, `DecisionEvidenceResource`, `IntegrityConflict`, and `IngestionReceipt`.

**Required APIs:**

* `POST /v1/dep/resources` for one DEP envelope.
* `POST /v1/dep/batches` for a bounded batch or JSONL bundle.
* `POST /v1/dep/cloudevents` for the DEP CloudEvents profile.
* `GET /v1/dep/resources/{resource_id}` for metadata and authorized payload retrieval.
* `GET /v1/discovery/sources` for provider/source inventory and coverage.
* `POST /v1/discovery/providers` and `GET /v1/discovery/providers/{provider_id}`.

**Required behavior:**

* Authentication determines organization; payload organization claims must match or be rejected.
* Compute digest server-side and compare any supplied digest.
* Same organization + resource ID + digest returns idempotent success.
* Same organization + resource ID + different digest creates `IntegrityConflict` and quarantines the new payload.
* Store accepted payload bytes in immutable evidence storage before marking the index accepted.
* Preserve provider object ID, source reference, event time, collection time, epistemic status, and transformation references.
* Return per-resource `accepted`, `duplicate`, `rejected`, or `quarantined` state.
* Bound request and batch sizes and reject decompression bombs or excessive nesting.

**Target package:**

```text
src/notary_platform/discovery/models.py
src/notary_platform/discovery/repositories.py
src/notary_platform/discovery/ingress.py
src/notary_platform/api_server/routers/discovery.py
tests/test_dep_ingress.py
tests/test_dep_ingress_tenant_isolation.py
```

**Exit criteria:**

* Ingress passes all DEP conformance fixtures.
* Every accepted resource has an immutable payload reference and queryable provenance.
* Duplicate delivery is safe and changed-content identifier reuse is visible.

### WP-040: Progressive source profiling and confirmed mapping

**Goal:** Turn the existing import preview into a truthful inspect-propose-confirm flow.

**Required models:** `SourceConnection`, `SourceCursor`, `SourceProfile`, and `FieldMappingVersion`.

**Required APIs:**

* `POST /v1/discovery/sources` creates a source connection without credentials in response data.
* `POST /v1/discovery/sources/{source_id}/profile` queues or executes a bounded profile.
* `GET /v1/discovery/sources/{source_id}/profiles/{profile_id}` returns profile status and results.
* `POST /v1/discovery/sources/{source_id}/mappings/propose` returns inferred mappings.
* `POST /v1/discovery/sources/{source_id}/mappings` confirms a new mapping version.
* `GET /v1/discovery/sources/{source_id}/coverage` reports available evidence and unlocked evaluators.

**Required profile output:**

* field names and types;
* candidate timestamps and identifier fields;
* null and redaction rates;
* bounded representative samples;
* record count or estimate;
* outcome distributions when safely computable;
* candidate join keys and their basis;
* sensitive-field classification and configured handling;
* available DEP resource types;
* mappings required for decision identity;
* optional mappings and the evaluator each would unlock.

**Implementation instructions:**

* Reuse `parse_discovery_input` and `ImportPreviewService` only as parsing and sampling helpers.
* Move path access and field-normalization logic into pure tested utilities.
* A heuristic or LLM proposal is always `inferred`; it cannot support authoritative evaluation until confirmed.
* Mapping edits create a new version. Existing previews and Sweep Runs remain pinned to their original version.
* Profiling must not create `VerificationRecord`, `Incident`, `Assessment`, or `AssuranceCandidate` objects.
* Update the setup-plan object with source and mapping references rather than embedding unversioned JSON strings.

**UI changes:**

* Keep Decision Discovery inside the current Setup plan.
* Show source status, profile coverage, required corrections, optional enrichment, mapping confidence/basis, sensitive-field handling, and unlocked evaluators.
* Keep Preview and Commit separate.

**Tests and exit criteria:**

* CSV, JSON, and JSONL produce stable profiles.
* Empty, malformed, oversized, nested, and mixed-type sources fail with actionable errors.
* A user can profile one source without answering an organization-wide questionnaire.
* No profile operation creates proof-loop records.

### WP-050: Decision identity and temporal context resolution

**Goal:** Construct contestable DERs and apply the context that was effective when each decision occurred.

**Required packages:**

```text
src/notary_platform/discovery/identity.py
src/notary_platform/discovery/context.py
src/notary_platform/discovery/evidence_records.py
tests/test_decision_identity_resolver.py
tests/test_temporal_context_resolver.py
tests/test_decision_evidence_record.py
```

**Decision identity precedence:**

1. Exact decision ID from a confirmed mapping.
2. Explicit DEP relationship supplied by an authorized provider.
3. Exact case/session/source record ID under a confirmed namespace mapping.
4. Exact system/version/environment plus configured deterministic composite key.
5. Human-confirmed link assertion.
6. Similarity proposal, retained only as ambiguous/inferred until confirmed.

Never merge evidence solely because timestamps are close, text is similar, or an LLM says two records appear related.

**Context resolution order:**

1. Select bindings whose subject scope and selector match the DER.
2. Evaluate `effective_from <= decision_time < effective_until`, where the end is optional.
3. Apply explicit supersession.
4. Apply configured authority.
5. Preserve equally authoritative material disagreement as `ContextConflict`.
6. Return a `ResolutionTrace` listing included, excluded, superseded, missing, stale, redacted, and conflicted artifacts with reasons.

**Supported context relationships for MVP:**

* `governed_by_policy`
* `expected_outcome`
* `guarded_by`
* `evidence_required_by`
* `executed_by_deployment`
* `human_override`
* `business_outcome`

**Required APIs:**

* `POST /v1/discovery/context-artifacts`
* `POST /v1/discovery/context-bindings`
* `POST /v1/discovery/link-assertions/{assertion_id}/confirm`
* `POST /v1/discovery/link-assertions/{assertion_id}/reject`
* `GET /v1/discovery/records/{der_id}`
* `GET /v1/discovery/records/{der_id}/resolution-trace`
* `POST /v1/discovery/context-conflicts/{conflict_id}/resolve`

**Exit criteria:**

* Exact identifiers outrank similarity.
* Ambiguous joins remain visible and cannot support authoritative evaluators.
* Historical decisions resolve the policy effective at decision time, not the currently collected policy.
* Equal-authority conflict blocks dependent evaluators.
* Every DER is a set of resource and relationship references, not copied flattened source data.

### WP-060: Sweep runtime, manifests, and evaluator contracts

**Goal:** Create the reproducible execution spine before implementing many checks.

**Required packages:**

```text
src/notary_platform/sweep/
  __init__.py
  jobs.py
  registry.py
  planner.py
  runner.py
  manifests.py
  budgets.py
  errors.py
src/notary_platform/sweep_worker/main.py
tests/test_sweep_planner.py
tests/test_sweep_runs.py
tests/test_sweep_reproducibility.py
```

**Required states:**

* Job: `queued`, `claimed`, `running`, `retry_wait`, `completed`, `failed`, `cancelled`.
* Sweep Run: `queued`, `profiling`, `resolving`, `evaluating`, `assembling`, `completed`, `completed_with_errors`, `failed`, `cancelled`.
* Evaluation: `planned`, `executed`, `skipped`, `failed`, `suppressed`.

**Required APIs:**

* `POST /v1/discovery/sweep-definitions`
* `POST /v1/discovery/sweep-definitions/{definition_id}/runs`
* `GET /v1/discovery/sweep-runs/{run_id}`
* `POST /v1/discovery/sweep-runs/{run_id}/cancel`
* `POST /v1/discovery/sweep-runs/{run_id}/rerun`
* `GET /v1/discovery/evaluators`
* `GET /v1/discovery/evaluators/{evaluator_id}/versions/{version}`

**Frozen manifest content:**

* organization and environment;
* Sweep Definition ID and version;
* source cursors and time window;
* mapping versions;
* DER versions and resource digests;
* Resolution Trace references;
* evaluator IDs, versions, contracts, and parameters;
* suppressions and delegation rules;
* run budgets and sample limits;
* code build identifier;
* start/end timestamps and terminal status.

**Execution rules:**

* Planner checks prerequisites before loading an evaluator implementation.
* Each skip records exact missing or conflicted inputs.
* Each failure records stable error code, retryability, and affected DER/evaluator.
* One failed evaluator does not corrupt completed evaluations; terminal state becomes `completed_with_errors` when safe.
* Deterministic rerun compares assessment digests and reports the first divergent input or implementation version.
* Initial jobs may use a PostgreSQL queue with `FOR UPDATE SKIP LOCKED`; do not use an in-memory queue for a production profile.
* All jobs have organization concurrency, record-count, evaluator-count, elapsed-time, and retry budgets.

**Exit criteria:**

* A frozen run can be rerun deterministically.
* Every enabled evaluator is accounted for as executed, skipped, failed, or suppressed.
* Worker restart resumes or safely retries without duplicate Assessments or Candidates.

### WP-070: Deterministic evaluator MVP and evidence sufficiency

**Goal:** Produce trustworthy value from incomplete evidence before adding complex policy interpretation.

**Implement first:**

1. `missing_evidence`
2. `expected_outcome_mismatch`
3. `replayability_failure`

**Evaluator interface:**

```python
class Evaluator(Protocol):
    contract: EvaluatorContractRecord

    def evaluate(
        self,
        record: FrozenDecisionEvidenceRecord,
        context: ResolvedContext,
        parameters: Mapping[str, Any],
    ) -> AssessmentRecord: ...
```

Implementations receive frozen inputs and cannot fetch arbitrary source data, mutate records, call production systems, or promote candidates.

**MVP evaluator semantics:**

* `missing_evidence`: compare observed resource/field coverage to a versioned evidence requirement; enumerate missing, redacted, stale, conflicted, or unverifiable items.
* `expected_outcome_mismatch`: require observed actual outcome plus customer-confirmed or authoritative expected outcome applicable at decision time; compare normalized values under a versioned comparison rule.
* `replayability_failure`: reuse canonical replayability predicates to identify missing cassette calls, mutable dependencies, unsupported tools, missing seed/configuration, unavailable runner, and required instrumentation action.

**Evidence levels:**

* `E0`: at least one attributable Observation representing a decision or execution event.
* `E1`: E0 plus at least one applicable Context Binding with no blocking identity ambiguity.
* `E2`: E1 plus authoritative or independently corroborated context needed for the executed finding.
* `E3`: E2 plus integrity-verified sealed evidence sufficient for the declared replay method and an available replay path.
* `E4`: E3 plus successful original replay, customer-authorized expected outcome, verified before/after fix result, and retained evidence references.

The service must return current level, satisfied predicates, failed predicates, and exact requirements for the next level. It must not return an opaque numeric score.

**Target files:**

```text
src/notary_platform/sweep/evaluators/base.py
src/notary_platform/sweep/evaluators/missing_evidence.py
src/notary_platform/sweep/evaluators/expected_outcome.py
src/notary_platform/sweep/evaluators/replayability.py
src/notary_platform/sweep/sufficiency.py
tests/test_initial_evaluators.py
tests/test_evidence_sufficiency.py
```

**Exit criteria:**

* Missing prerequisites yield skip or Evidence Gap according to the evaluator contract.
* Expected-outcome mismatch cannot run on an inferred, unconfirmed label.
* Replayability findings identify a concrete capture or sandbox action.
* E0-E3 are deterministic; E4 consumes the existing verified mutation result.

### WP-080: Assurance Candidate assembly and review

**Goal:** Turn assessments into an understandable, governable review queue.

**Candidate required fields:**

* candidate ID, organization, environment, DER and Sweep Run references;
* candidate type and lifecycle state;
* actual and expected outcome where supported;
* buyer-readable business summary;
* evaluator ID, version, method class, trust class, and assessment references;
* supporting source resources and applied Context Bindings;
* Resolution Trace reference;
* evidence level and next-level requirements;
* missing/conflicted/redacted/stale prerequisites;
* severity, confidence, and priority as separate fields;
* available review and proof-loop actions;
* cluster reference without losing individual disposition.

**Review actions:**

* approve as Incident;
* dismiss with reason;
* request context;
* accept risk;
* create scoped suppression;
* instrument next occurrence;
* supersede a prior review decision.

**Required APIs:**

* `GET /v1/discovery/candidates`
* `GET /v1/discovery/candidates/{candidate_id}`
* `POST /v1/discovery/candidates/{candidate_id}/reviews`
* `GET /v1/discovery/candidates/{candidate_id}/reviews`
* `POST /v1/discovery/suppressions`
* `GET /v1/discovery/suppressions`
* `POST /v1/discovery/promotion-delegations`

**Authority rules:**

* Review decisions are append-only and identify actor, role, basis, scope, effective period, and superseded decision.
* Dismissal does not delete the candidate.
* Suppression applies only to matching future evaluations and is still recorded as `suppressed` in a Sweep Run.
* Probabilistic assessments cannot satisfy delegation.
* Delegation rules are versioned, scoped, revocable, and recorded on every promoted Incident.

**Exit criteria:**

* A non-technical reviewer can answer: what happened, why it was flagged, what evidence supports it, what context applied, what is missing, and what action is available.
* Review history is complete and corrections apply prospectively.
* Candidate and existing `ScenarioCandidate` types remain distinct.

### WP-090: Proof Bridge into the existing proof loop

**Goal:** Connect approved discovery findings to existing product value without duplicating execution.

**Required behavior:**

1. Accept one approved `AssuranceCandidate` and its active Review Decision.
2. Verify organization/environment scope and promotion authority.
3. Freeze supporting resource digests, context, expected behavior, evaluator lineage, and known limitations into an Evidence Bundle manifest.
4. Create or link exactly one `VerificationRecord` using an idempotent bridge key.
5. Create or classify exactly one Incident when the existing workflow requires it.
6. Preserve candidate, DER, Sweep Run, review, Verification Record, Incident, replay, mutation, certificate, Scenario, and gate lineage.
7. Return replay state: `fully_replayable`, `partially_replayable`, `requires_sandbox`, `not_replayable`, or `missing_evidence`.
8. Return exact prerequisites and next actions for every blocked state.

**Required APIs:**

* `POST /v1/discovery/candidates/{candidate_id}/promote`
* `GET /v1/discovery/candidates/{candidate_id}/proof-eligibility`
* `GET /v1/discovery/candidates/{candidate_id}/lineage`

**Implementation rules:**

* Call `IngestionService` or a narrowly extracted factory to create the proof-loop record. Do not duplicate snapshot-to-VerificationRecord mapping.
* Call existing eligibility, replay, mutation, certificate, Scenario, readiness, and gate services.
* Extend those objects with lineage references only through backward-compatible fields or dedicated relationships.
* Idempotent retry returns the same bridge result.
* Proof eligibility error responses use stable codes and concrete remediation, never only `400 Proof failed`.

**Exit criteria:**

* One accepted E3 candidate can run through the current proof loop.
* One E0-E2 candidate receives an exact enrichment or instrumentation path.
* Completing fix verification recalculates the linked evidence record to E4 without rewriting the original Sweep Run.

### WP-100: Discovery and investigation user experience

**Goal:** Make the new engine legible while preserving the current Setup and Incident investigation surfaces.

**Required Setup views:**

* source inventory and connection health;
* source profile with field coverage and samples;
* required mappings versus optional enrichment;
* context source and effective-time coverage;
* evaluators unlocked, skipped, or blocked;
* Sweep Definition summary and run action.

**Required Discovery views:**

* Sweep Run list/detail with frozen inputs and counts by executed/skipped/failed/suppressed;
* Assurance Candidate queue with filters for type, state, evidence level, severity, evaluator, source, and decision family;
* Candidate detail with business summary, evidence, applied context, Resolution Trace, evaluator explanation, evidence level, limitations, and review actions;
* conflict-resolution surface for ambiguous identity and context conflicts.

**Required proof-loop integration:**

* Incident Detail shows discovery origin and full lineage when applicable.
* Existing captured decision path, replay execution trace, original/replayed comparison, before/after fix verification, proof panel, Scenario promotion, and Release Gate impact remain visible.
* Every button is backed by an API or disabled with the exact server-provided reason.

**Frontend constraints:**

* Continue the current static SPA for this roadmap; do not introduce a frontend migration as a hidden dependency.
* Add view modules/functions in `static/app/app.js` and reusable rendering helpers in `static/app/components.js`.
* Do not put assurance business rules in JavaScript.
* Render loading, empty, partial, blocked, error, cancelled, and completed-with-errors states.
* Keep Command Center code out of scope.

**Tests:**

* Add static registration tests for every view and route.
* Add Playwright flows for profile -> mapping -> Sweep -> candidate review -> proof eligibility.
* Test mobile and desktop widths and verify tables/drawers do not overlap.

**Exit criteria:**

* A buyer can explain the proof loop by following one candidate.
* No UI reports a candidate as an Incident or proof as eligible before server authority exists.

### WP-110: Context-heavy evaluator depth

**Goal:** Add differentiated checks after the deterministic MVP is trusted.

Implement in this order:

1. **Structured policy mismatch**
   Requires observed outcome, applicable structured policy, relevant inputs, decision-time binding, and executable comparison logic. AI-parsed policy remains draft until confirmed.
2. **Guardrail violation**
   Requires guardrail definition/version, applicable binding, evaluation or enforcement event, and side-effect state. Distinguish `guardrail_flagged`, `guardrail_blocked`, and `side_effect_occurred`.
3. **Consistency mismatch**
   Requires confirmed cohort definition, comparison fields, normalized outcomes, minimum sample size, and allowed-variance rule. Similarity alone never establishes a violation.
4. **Customer-defined evaluators**
   Run in a bounded sandbox with declared input/output schema, author, version, and authority `candidate_only` by default.
5. **Third-party evaluators**
   Use the same contract and retain provider/version provenance. They cannot inherit Notary-certified status.

**Required safety and tests:**

* Evaluator code has no credentials or unrestricted network access.
* Time, memory, output-size, and record-count budgets are enforced.
* Malformed or malicious evaluator output fails only that evaluation.
* Certification state changes are prospective.
* Golden fixtures cover boundary values, historical policy versions, equal-authority conflicts, guardrail side effects, and cohort variance.

**Exit criteria:**

* All six initial candidate types exist with explicit prerequisites.
* Every output exposes method and authority.
* No natural-language policy is represented as executable truth without confirmation.

### WP-120: SDK and provider integration

**Goal:** Make evidence acquisition practical without requiring a connector for every customer system.

**Python SDK work:**

* Map SDK captures to DEP Observation and Evidence Bundle resources.
* Add stable run, decision, session, agent, deployment, and source-record identifiers.
* Capture LLM, tool/MCP, retrieval/memory, guardrail, human action, final decision, model configuration, policy reference, and timestamps as separate attributable elements.
* Preserve HMAC chain and root hash behavior and provide offline verification.
* Add configurable redaction and field handling before submission.
* Add buffered batch submission, retry, idempotency key, and local failure reporting.
* Do not claim transparent capture of every framework/provider call; expose explicit supported integrations and manual capture APIs.

**Provider/adapters work:**

1. Generic DEP HTTP and batch.
2. CSV/JSON/JSONL import.
3. OTLP bridge.
4. LangSmith adapter as the first native trace adapter.
5. One design-partner authoritative outcome or policy source: Salesforce, Zendesk, ServiceNow, or database export.

Each native adapter must implement auth, least privilege, cursoring, pagination, retry/backoff, rate-limit response, schema drift, deletion/tombstone behavior, provenance, data minimization, and replayable fixtures.

**TypeScript SDK:**

Implement only after the Python DEP payload and verifier behavior are frozen. Require fixture parity between Python and TypeScript canonicalization, hashes, and resource payloads.

**Exit criteria:**

* One trace source and one authoritative context/outcome source produce linked DERs.
* Disconnecting a source stops future collection without erasing retained lineage.
* SDK evidence validates with the standalone DEP conformance tool.

### WP-130: Governed assistance and learning loop

**Goal:** Improve setup and triage using feedback while keeping assurance authority deterministic.

**Implement only after WP-080 feedback data exists.**

**Required components:**

* `AssistanceProvider` interface with an offline-disabled default.
* `MappingSuggestionService`.
* `PolicyExtractionDraftService`.
* `CandidateSummaryService`.
* `CandidateClusterSuggestionService`.
* `FeedbackEventService`.
* version evaluation and rollback tooling.

**Required controls:**

* Per-organization enablement and data-use policy.
* Redacted/minimized prompts by default.
* Provider, model, prompt version, input references, output digest, latency, and cost metadata.
* No source payload logging outside the governed evidence store.
* Human confirmation for mappings, identity, policy, expected outcome, and applicability.
* Deterministic fallback for every customer-critical path.
* Frozen test sets split by organization; no customer data used across tenants by default.

**Metrics:**

* mapping acceptance and correction rate;
* policy extraction confirmation rate;
* unsupported-summary claim rate;
* candidate duplicate reduction;
* reviewer time to disposition;
* evaluator dismissal and proof-conversion rates;
* context source recommendation usefulness.

**Exit criteria:**

* Disabling model assistance leaves ingestion, Sweep, review, proof, and gates operational.
* Every generated statement in a candidate summary is traceable to evidence or clearly labeled interpretation.
* Version rollback does not rewrite prior suggestions or decisions.

### WP-140: Production hardening and operations

**Goal:** Make scheduled discovery secure, bounded, resumable, and supportable.

**Required work:**

* durable scheduling, cursor checkpoints, cancellation, retries, exponential backoff, dead-letter state, and resumability;
* per-organization worker concurrency and evidence/evaluator/cost budgets;
* source credential storage in Secrets Manager and rotation paths;
* S3 Object Lock/versioning checks and immutable-manifest verification;
* retention, tombstones, deletion requests, key rotation, and custody events;
* structured logs and metrics that exclude customer payloads;
* metrics for ingestion rejection, mapping coverage, identity ambiguity, context conflict, skipped evaluators, candidate yield, review outcomes, proof conversion, and gate conversion;
* failure injection for worker crash, S3 failure, database transaction failure, duplicate job, schema drift, provider throttling, and partial batch acceptance;
* tenant-isolation, authorization, malicious payload, decompression, evaluator sandbox, and cross-resource substitution tests;
* runbooks for quarantined evidence, stuck jobs, context conflicts, bad evaluator versions, and key/provider outage.

**Exit criteria:**

* Worker failure resumes without duplicate completed outputs.
* Scheduled Sweep cannot starve interactive APIs.
* Support diagnostics expose state and stable error codes without exposing another tenant's evidence.
* Security review and recovery rehearsal pass with measured service objectives.

### WP-150: Scenario and Release Gate compounding

**Goal:** Turn verified discovery findings into recurring release assurance and measurable customer value.

**Required work:**

* Recommend Scenario promotion only for human-labeled, reproducible, fix-verified Incidents.
* Preserve candidate -> Incident -> Verification Record -> replay -> mutation -> proof -> Scenario -> Scenario Run -> Readiness -> Release Gate lineage.
* Add release-impact summaries showing which real discovered failure each gate Scenario prevents.
* Report coverage by decision family, source availability, evaluator eligibility, evidence level, Scenario status, and missing context.
* Export verified Evidence Bundles and Verification Claims using DEP resources.
* Keep claim language bounded to tested scenarios, versions, conditions, and known limitations.

**Exit criteria:**

* One design-partner case completes the full lifecycle with no manual database changes.
* A gate never implies coverage for an untested decision family or missing evidence scope.
* The platform can show how accumulated verified Incidents increase release coverage over time.

## 7. First Vertical Slice

The first design-partner slice is complete only when all of the following work together. This is the priority before native connector breadth or LLM assistance.

1. Import JSONL containing AI trace/decision data and a stable business record ID.
2. Import or submit authoritative expected outcomes keyed by the same confirmed ID.
3. Profile both sources and confirm mappings.
4. Store source records as immutable DEP resources with provenance.
5. Build exact-ID DERs.
6. Bind expected outcome by effective time.
7. Run missing-evidence, expected-outcome-mismatch, and replayability evaluators.
8. Calculate E0-E3 and show exact next-level requirements.
9. Produce an Assurance Candidate with evidence and context trace.
10. Approve the candidate and bridge it to one existing Verification Record and Incident.
11. Replay from cassette, verify a fix, issue proof, promote a Scenario, and pass a Release Gate.
12. Show complete lineage and known limitations in the platform UI.

This slice proves the differentiated thesis: logs are one evidence source; decision-time context gives them meaning; deterministic replay and proof turn a reviewed finding into recurrence prevention.

## 8. Demo Scenario: Harborline Support Escalation

Use one stable scenario across implementation and demos so every work package can be verified end to end.

* **Observed decision:** A support agent continued FAQ responses after the customer asked for a human three times.
* **Trace source:** SDK cassette or LangSmith export includes messages, retrieval, tool responses, guardrail events, and final `CONTINUE_SELF_SERVICE` decision.
* **Business source:** Zendesk or CSV case record shows a later human escalation and complaint.
* **Context source:** Versioned escalation policy states that two human requests or negative sentiment requires `ESCALATE_TO_HUMAN`.
* **Decision identity:** Exact ticket ID shared by trace and business record.
* **Decision-time resolution:** Policy version effective at the original timestamp is selected.
* **Expected evaluator result:** `expected_outcome_mismatch`; policy evaluator runs only after structured policy confirmation.
* **Evidence limitation:** If a tool response is absent, replayability evaluator identifies the missing cassette element and E3 is blocked.
* **Review:** Compliance reviewer approves the candidate as an Incident.
* **Proof loop:** Original replay reproduces `CONTINUE_SELF_SERVICE`; fixed policy produces `ESCALATE_TO_HUMAN`; proof is issued with root hash, replay method, signature status, and scope limitations.
* **Compounding:** The verified Incident becomes a Scenario required by the Harborline support-agent Release Gate.

Required fixtures must include:

* exact-ID successful linkage;
* ambiguous linkage that remains unconfirmed;
* old and current policy versions;
* equal-authority policy conflict;
* missing tool response;
* inferred expected outcome rejected for authoritative evaluation;
* verified fix and E4 transition;
* future agent regression causing gate failure.

## 9. API and Error Contract Rules

All new endpoints must follow these conventions:

* Authentication supplies organization identity; never trust an unrestricted body `org_id`.
* Every response object includes its stable ID, organization-safe references, lifecycle state, `created_at`, and version where applicable.
* Collection endpoints support bounded pagination and deterministic sort order.
* Long-running commands return `202` plus job/run ID; synchronous local mode may complete immediately but returns the same shape.
* Idempotent commands accept or derive an operation key.
* Errors use `{code, message, details, retryable, remediation}`.
* `404` is returned for absent or cross-tenant objects to avoid existence leakage.
* Validation failures use `422`; integrity conflicts use `409`; unauthorized lifecycle transitions use `409` or `403` according to authority.
* UI-visible action eligibility is returned by the server and includes exact missing prerequisites.

Minimum stable error codes:

* `dep_schema_invalid`
* `dep_version_unsupported`
* `resource_digest_mismatch`
* `resource_identity_conflict`
* `source_profile_failed`
* `mapping_confirmation_required`
* `decision_identity_ambiguous`
* `decision_timestamp_missing`
* `context_conflict`
* `evaluator_prerequisite_missing`
* `evaluator_execution_failed`
* `sweep_budget_exceeded`
* `candidate_review_required`
* `promotion_authority_missing`
* `proof_bridge_not_replayable`
* `proof_prerequisite_missing`

## 10. Verification Matrix

| Layer | Mandatory verification |
| --- | --- |
| DEP | Schema fixtures, canonicalization vectors, digest vectors, invalid-resource errors, standalone validator. |
| Ingress | Idempotency, changed-digest conflict, quarantine, partial batch, size limits, tenant isolation. |
| Profiling | File formats, type inference, null/redaction rates, mapping versions, no side effects. |
| Identity | Exact-ID precedence, namespace handling, ambiguity, human confirmation, supersession. |
| Context | Effective intervals, selectors, authority, supersession, conflict, trace explanation. |
| Sweep | Job recovery, manifest freeze, prerequisite plan, all terminal evaluation states, deterministic rerun. |
| Evaluators | Golden inputs/outputs, boundary conditions, missing/conflicted prerequisites, version pinning. |
| Sufficiency | Predicate tests for every E0-E4 transition and downgrade/block reason. |
| Candidates | Evidence lineage, summary grounding, ranking independence, lifecycle transition table. |
| Review | Authorization, append-only history, scoped suppression, delegation and revocation. |
| Proof Bridge | Idempotency, exact prerequisite errors, single VR/Incident creation, full lineage. |
| Existing proof loop | Replay trace, before/after verification, signature verification, Scenario promotion, gate pass/fail/error. |
| Assistance | Tenant opt-in, prompt provenance, unsupported-claim detection, confirmation requirement, deterministic fallback. |
| UI | API-backed controls, loading/empty/error/blocked states, desktop/mobile Playwright screenshots. |
| Production | PostgreSQL/S3 integration, restart recovery, failure injection, tenant isolation, retention and key rotation. |

Before each merge, run at minimum:

```bash
pytest
ruff check .
mypy src
```

Run `ruff format --check` against every changed Python file. Repository-wide formatting normalization must be a separate mechanical change when the existing baseline is not clean. Run browser tests for any API response shape or UI change. Run remote-storage integration tests for any repository, persistence, migration, or worker change.

## 11. Coding-Agent Execution Rules

The receiving coding agent must follow this checklist for every work package:

1. Read the linked requirements and blueprint component contracts before editing code.
2. Inspect the named current files and reuse existing service behavior where specified.
3. Write or update tests that demonstrate the current failure or missing behavior.
4. Define typed models, repository interfaces, API request/response shape, and stable errors before implementing route bodies.
5. Implement the smallest complete vertical behavior for the work package.
6. Keep organization/environment scope explicit through route, service, repository, and query layers.
7. Run focused tests during implementation, then the full verification commands.
8. Inspect the diff for accidental Command Center, generated asset, secret, or unrelated changes.
9. Update this roadmap's completion table and any affected requirements/blueprints only when behavior or architecture changed.
10. Report files changed, commands run, test results, limitations, migrations, and the next unblocked work package.

The coding agent must not:

* mark a package complete because classes or routes exist without persisted behavior and tests;
* return hard-coded demo success from production-shaped endpoints;
* add a second replay or certificate path;
* overload `ScenarioCandidate` to represent an assurance finding;
* call model-generated output customer-confirmed;
* silently catch persistence, evaluator, or proof errors and return an empty successful result;
* add a native connector before generic intake and the first vertical slice work;
* place secrets, customer payloads, or tokens in logs, fixtures, commits, or model prompts;
* claim AWS production readiness while remote storage methods remain stubs.

## 12. Completion Tracking

Update this table only after implementation, automated verification, and applicable UI verification are complete.

| Work package | Status | Dependency | Completion evidence |
| --- | --- | --- | --- |
| WP-000 Baseline and guardrails | Not started | None | Test and lint report plus golden-path test |
| WP-010 Production persistence | Not started | WP-000 | Remote storage contract and restart tests |
| WP-020 DEP conformance runtime | Not started | WP-000 | Valid/invalid fixtures and validator command |
| WP-030 DEP ingress | Not started | WP-010, WP-020 | Ingress API and idempotency/integrity tests |
| WP-040 Source profiling/mapping | Not started | WP-010, WP-030 | Profile/mapping APIs and setup UI flow |
| WP-050 Identity/context | Not started | WP-030, WP-040 | Resolver golden fixtures and trace API |
| WP-060 Sweep runtime | Not started | WP-010, WP-050 | Durable run and reproducibility tests |
| WP-070 Evaluator MVP/sufficiency | Not started | WP-050, WP-060 | Three evaluator suites and E0-E4 tests |
| WP-080 Candidates/review | Not started | WP-070 | Candidate lifecycle and authority tests |
| WP-090 Proof Bridge | Not started | WP-080 | Full candidate-to-proof-loop integration test |
| WP-100 Platform UX | Not started | WP-040, WP-060, WP-080, WP-090 | Playwright desktop/mobile proof-loop flow |
| WP-110 Evaluator depth | Not started | WP-070, WP-080 | Six evaluator types and sandbox tests |
| WP-120 SDK/providers | Not started | WP-020, WP-030 | DEP-compatible SDK and two-source pilot |
| WP-130 Assistance/learning | Not started | WP-080, WP-110 | Governed opt-in assistance evaluation |
| WP-140 Production hardening | Not started | WP-010 through WP-120 | Security, failure, recovery, and SLO evidence |
| WP-150 Scenario/gate compounding | Not started | WP-090, WP-100, WP-140 | Full design-partner lifecycle demonstration |

## 13. Milestones and Decision Gates

### Milestone A: Evidence arrives safely

Complete WP-000 through WP-040. Demonstrate source profile, mapping confirmation, immutable resource provenance, duplicate handling, and source coverage without creating an Incident.

### Milestone B: Context changes meaning

Complete WP-050. Demonstrate the same observation evaluated against the policy effective at decision time, plus a conflict that correctly blocks evaluation.

### Milestone C: Sweep produces a trustworthy candidate

Complete WP-060 through WP-080. Demonstrate a frozen run, prerequisite-aware evaluator, evidence sufficiency, grounded candidate explanation, and append-only review.

### Milestone D: The proof loop closes

Complete WP-090 and WP-100. Demonstrate candidate approval, exact replay eligibility, original replay, fix verification, certificate, Scenario promotion, and Release Gate impact.

### Milestone E: Acquisition and intelligence deepen

Complete WP-110 through WP-130. Demonstrate context-heavy evaluators, Python SDK DEP output, two-source design-partner acquisition, and optional governed assistance.

### Milestone F: Pilot production readiness

Complete WP-140 and WP-150. Demonstrate recovery, isolation, bounded scheduled Sweep, operational diagnostics, and the full design-partner lifecycle under production storage.

## 14. Product Success Metrics

Measure whether discovery creates trusted proof-loop throughput, not whether it creates the most alerts.

Primary metrics:

* time from first source connection to first useful profile;
* percentage of DERs with exact confirmed identity;
* percentage of candidate evaluations skipped due to missing context, by prerequisite;
* percentage of candidates dismissed, approved, or awaiting context;
* median reviewer time to disposition;
* candidate-to-Incident conversion;
* Incident-to-reproduced-replay conversion;
* replay-to-verified-fix conversion;
* verified-fix-to-proof and Scenario conversion;
* decision-family coverage in Release Gates;
* recurrence caught by a Scenario before release;
* mapping correction and evaluator false-positive rates by version.

Do not optimize for raw candidate volume. A lower-volume system with explicit prerequisites, strong provenance, and high proof conversion is the desired product.

## 15. Risks and Controls

| Risk | Required control |
| --- | --- |
| Connector work consumes the roadmap | Generic DEP, file, HTTP, and OTLP first; one native trace and one authoritative source only after the vertical slice. |
| Existing preview is mistaken for NSE | Mark it transitional, add typed engine stages, and stop direct proof-loop creation after migration. |
| Remote deployment loses setup state | WP-010 blocks production claims and later durable Sweep work. |
| False positives damage trust | Prerequisite-aware evaluators, candidates before Incidents, explicit missing context, reviewer feedback metrics. |
| Current policy is applied historically | Effective-time bindings, explicit supersession, authority and conflict preservation. |
| LLM output becomes hidden authority | Inferred status, provenance, human confirmation, deterministic fallback, prohibited authority actions. |
| Proprietary logic leaks into DEP | Keep public resource contracts separate from internal implementation, ranking, and calibration fields. |
| Closed algorithms become unchallengeable | Explain each result with inputs, context, contract, method class, limitations, and version. |
| Customer evaluator dilutes certification | Trust classes and proof-eligibility enforcement. |
| Sweep becomes observability | Bounded jobs and historical discovery; no live telemetry dashboard or real-time alerting. |
| Cross-customer learning creates privacy risk | Tenant-isolated default and no aggregate learning without explicit opt-in governance. |
| Evidence retention conflicts with privacy | Redaction lineage, reference-only options, tombstones, scoped retention, and documented key-destruction behavior. |
| Duplicate systems emerge | Reuse the current proof services and bridge to them through stable IDs and lineage. |

## 16. Definition of Platform Completion

For this roadmap, the Decision Evidence and Sweep platform is complete only when:

* a customer can start with one source and see honest value without a full integration program;
* multiple heterogeneous evidence and context sources can be linked without flattening provenance;
* the system can state exactly which checks ran, which did not, and why;
* every candidate is explainable and governed before becoming an Incident;
* accepted candidates use the existing replay, fix, proof, Scenario, and Release Gate system;
* evidence and run state persist correctly in the production storage profile;
* optional model assistance can be disabled without breaking assurance behavior;
* the platform does not need a neural network, graph database, Command Center, process-mining product, or connector for every customer system to deliver the first design-partner value.

The immediate next work package is **WP-000**, followed by **WP-010 and WP-020 in parallel** once the baseline is green.
