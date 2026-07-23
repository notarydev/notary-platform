# Notary Platform Coding Agent Execution Handoff

**Status:** Ready after `codex/setup-spine-unification` is merged to `main`

## Repository State to Preserve

The implementation agent must begin from `main` only after the following branch commits are present:

* `41b87fd` - unifies Decision Discovery with the active setup-plan flow;
* `5d6a3a4` - adds the public DEP package, schemas, and private Notary discovery architecture;
* `ceb7662` - replaces the high-level roadmap with an implementation-grade delivery sequence.

Do not recreate, revert, rename, or bypass this work. If the hashes change during squash merge, confirm the following files and behavior exist on `main` before coding:

* `docs/dep/README.md`, `whitepaper.md`, `spec.md`, and `governance.md`;
* `schemas/dep/*.schema.json`;
* `docs/specifications/NOTARY_PLATFORM_REQUIREMENTS.md`;
* `docs/specifications/NOTARY_PLATFORM_BLUEPRINTS.md`;
* `docs/specifications/DECISION_EVIDENCE_AND_SWEEP_ROADMAP.md`;
* Decision Discovery is part of the existing setup flow in `static/app/app.js`;
* setup/discovery static tests exist in `tests/test_platform_static_app.py`.

## Authority Order

When documents appear to conflict, use this order:

1. `docs/specifications/NOTARY_PLATFORM_REQUIREMENTS.md` defines required product behavior.
2. `docs/specifications/NOTARY_PLATFORM_BLUEPRINTS.md` defines containers, components, boundaries, contracts, and architecture decisions.
3. `docs/specifications/DECISION_EVIDENCE_AND_SWEEP_ROADMAP.md` defines implementation order, current repository status, package placement, APIs, tests, and exit criteria.
4. `docs/dep/spec.md` and `schemas/dep/` define the public interoperability boundary.
5. Existing code and tests show reusable implementation patterns but do not override the requirements or blueprints.

Ask for a product decision only if the requirements and blueprints truly leave a consequential choice unresolved. Resolve ordinary implementation details using existing repository conventions.

## Product Boundaries

Build Notary Platform and the Notary SDK only.

## Discovery-First Product Motion

Build toward this customer journey:

1. connect or import evidence the customer already has;
2. validate and preserve it through DEP;
3. generate an initial discovery map and honest findings or gaps;
4. ask the customer to confirm mappings, authority, and context only where needed;
5. turn confirmed discovery into continuous monitoring and the existing proof loop.

Do not build toward a setup-first experience where the customer must define the whole environment before seeing value.

In scope:

* progressive Decision Discovery setup;
* DEP ingestion and immutable evidence;
* source profiling and confirmed mapping;
* decision identity and decision-time context resolution;
* the proprietary Notary Sweep Engine;
* Assurance Candidates and governed review;
* the bridge into the existing replay, fix verification, proof, Scenario, Readiness, and Release Gate workflow;
* Python SDK evidence capture and DEP compatibility;
* production persistence, isolation, security, and operational hardening.

Out of scope:

* Command Center;
* process mining;
* real-time observability and alerting;
* generalized GRC workflow;
* autonomous remediation;
* a graph database;
* a custom neural network;
* a large native-connector catalog before the first vertical slice works.

## Existing Capabilities to Reuse

The repository already contains working or partially working implementations for:

* the FastAPI application and authenticated `/v1` routing;
* the setup-plan and Decision Workflow flow;
* JSON, JSONL, and CSV parsing, preview, and transitional import commit;
* Verification Record creation and replayability assessment;
* cassette replay and replay execution events;
* mutation/fix verification;
* Proof of Mitigation issuance and signature verification;
* Scenario promotion and execution;
* Readiness Policies, Readiness Checks, and Release Gate results;
* the static Platform SPA;
* Python SDK capture, HMAC chain, root hash, submission, and local verification;
* memory, shared-demo file, and partial PostgreSQL/S3 storage implementations.

Do not build parallel versions of these services. Discovery must enter the proof loop through `ProofBridgeService`, which reuses the current service layer.

Important distinctions:

* `AssuranceCandidate` is a potential concern produced by Sweep and awaiting review.
* `Incident` is an authorized investigation object.
* `ScenarioCandidate` is a post-investigation candidate for the Scenario Library.
* These are separate lifecycle objects and must not share one model merely because their names are similar.

## Known Transitional Behavior and Technical Debt

The current Decision Discovery UI is a useful starting point, not the completed NSE.

* Import preview uses heuristic record-selection rules.
* Import commit currently creates `VerificationRecord` objects directly.
* Existing preview findings are shallow and are not typed Assessments or Assurance Candidates.
* `PostgresS3Storage` still contains no-op setup/platform methods.
* Remote replay execution events are process-local.
* Non-demo replay does not have a generally configured customer replay runner.
* Runtime DEP schema validation and conformance fixtures are not implemented.
* The TypeScript SDK remains a placeholder.
* At this handoff, 189 non-browser tests pass, `ruff check .` passes, and `mypy src` passes.
* The Playwright suite requires permission to launch Chromium outside the local sandbox; CI or an authorized local run must provide the authoritative browser result.
* Repository-wide `ruff format --check .` reports 39 pre-existing files that would be reformatted. Do not mix repository-wide formatting churn into a functional work package. Changed Python files must pass Ruff formatting; normalize the existing repository only in a separate mechanical change.

Do not represent any of these areas as production-complete.

## First Execution Queue

Execute the roadmap by work package. Do not start with connectors, LLM assistance, or UI redesign. The first customer-visible vertical slice is DEP intake plus discovery map, not a broad onboarding questionnaire.

### Work Order 1: WP-000 Baseline and Guardrails

#### Summary

Freeze and verify the current end-to-end proof loop before changing discovery storage or routing. Make demo-only and transitional behavior explicit so later work cannot accidentally convert a demo shortcut into a production contract.

#### In Scope

* Run the complete test, lint, formatting, and type-check baseline.
* Add or strengthen the existing import/SDK -> Verification Record -> label -> Incident -> replay -> mutation -> proof -> Scenario -> readiness -> Release Gate integration test.
* Verify non-demo records without a configured replay runner fail honestly.
* Add `processing_path: legacy_verification_record` to the transitional discovery import response until WP-090 replaces it.
* Record baseline failures and fix only failures caused by the branch or required to establish a green baseline.

#### Out of Scope

* New DEP ingress.
* New persistence architecture.
* Sweep Worker or evaluators.
* Connector work.
* LLM assistance.
* Command Center.

#### Requirements

* `NOTARY_PLATFORM_REQUIREMENTS.md`: `REQ-FP-DES-001`, `REQ-FP-DES-011`, and `REQ-FP-DES-015` only where needed to preserve the existing lifecycle boundary.

#### Blueprints

* `NOTARY_PLATFORM_BLUEPRINTS.md` - API Server, Web Dashboard, Replay Engine, and Decision Evidence Discovery integration contracts.

#### Acceptance

* `pytest` passes.
* `ruff check .` passes.
* Every Python file changed by WP-000 passes `ruff format --check <changed-files>`.
* The pre-existing repository-wide Ruff formatting baseline is recorded without unrelated mass formatting.
* `mypy src` passes.
* The golden-path integration test proves the current loop.
* The non-demo replay boundary has a regression test.
* No production-shaped API returns hard-coded demo success.

### Work Order 2: WP-010 Production Persistence

Begin only after WP-000 is green. Complete the remote-storage foundation exactly as specified in the roadmap. This work may run in parallel with WP-020 only if agents use separate branches or worktrees and avoid overlapping files.

Required outcome:

* all existing setup/platform domain objects persist in PostgreSQL;
* replay execution events persist across restart;
* no remote setup method is a no-op;
* migrations are versioned;
* storage contract and tenant-isolation tests run against memory and a disposable remote fixture.

Do not add discovery domain models to the old giant `models.py` as part of this work.

### Work Order 3: WP-020 DEP Runtime Conformance

Begin only after WP-000 is green. This work may run in parallel with WP-010.

Required outcome:

* schemas load locally with complete `$ref` resolution;
* canonical JSON and digest behavior are defined once;
* every DEP resource has positive and negative fixtures;
* validation errors are stable and machine-readable;
* a standalone offline validation command passes the fixture suite;
* public fixtures contain no Notary or NSE implementation fields.

WP-030 DEP ingress starts only after WP-010 and WP-020 are complete. WP-030 is the first customer-visible discovery surface, and WP-040 converts that surface into guided confirmation rather than blank-slate setup.

## Deterministic and Model-Assisted Boundary

Do not add an LLM to the core execution path.

Deterministic and authoritative:

* validation, digests, idempotency, tenant scope, identity rules, effective-time resolution, evaluator prerequisites, E0-E4 evidence sufficiency, promotion authority, replay eligibility, proof eligibility, and Release Gate verdicts.

Optional and advisory in later work:

* source-field mapping suggestions;
* draft policy extraction;
* candidate summaries;
* duplicate/cluster suggestions;
* suggestions about which context source to connect next.

Every model-assisted result stays `inferred`, retains model/prompt/input provenance, and requires confirmation when used for identity, policy, expected outcome, or applicability.

## Required Working Method

For each work package:

1. Create a new branch from updated `main` using the `codex/` prefix.
2. Read the complete requirement and blueprint sections connected to that package.
3. Inspect all current files named in the roadmap before proposing changes.
4. Write a short implementation plan naming reused code, new files, interfaces, flow, migrations, and tests.
5. Add or update tests before or with the implementation.
6. Implement only the package's scope.
7. Run focused tests and then the full required verification commands. Run Ruff formatting checks on changed Python files; do not mass-format unrelated files inside a functional work package.
8. Review the diff for unrelated files, secrets, generated asset churn, and Command Center changes.
9. Update the roadmap completion table only when all exit criteria pass.
10. Commit and push the package branch; do not merge with failing checks.

Do not stop merely because usage visibility is unavailable. Report `Usage visibility: not available` and continue. Stop for missing credentials, production/destructive actions requiring authorization, an actual access blocker, contradictory requirements, or a consequential unresolved product decision.

## Required Worker Report

Return this exact structure after each work package:

```markdown
# Worker Report: WP-XXX

## Outcome
Complete | Partial | Blocked

## Implemented
* Concrete behavior delivered

## Reused
* Existing services/components reused instead of duplicated

## Files Changed
* Path - reason

## Data and API Changes
* Models, migrations, endpoints, compatibility notes

## Verification
* Command - result
* Acceptance criterion - evidence

## Security and Tenant Isolation
* Relevant checks and results

## Known Limitations
* Honest remaining limitations; write `None` if none

## Decisions Needed
* Only genuine product/access decisions; write `None` if none

## Next Work Package
* Exact next unblocked package and dependency status

## Usage Visibility
Available: NN% remaining | Not available
```

## Paste-Ready Agent Instruction

Use the following prompt after this branch is merged to `main`:

```text
You are the implementation worker for Notary Platform and SDK.

Start from updated main. Before editing, verify that main contains the content introduced by commits 41b87fd, 5d6a3a4, and ceb7662, even if they were squash-merged under different hashes.

Read these files in full and use them in this authority order:
1. docs/specifications/NOTARY_PLATFORM_REQUIREMENTS.md
2. docs/specifications/NOTARY_PLATFORM_BLUEPRINTS.md
3. docs/specifications/DECISION_EVIDENCE_AND_SWEEP_ROADMAP.md
4. docs/specifications/CODING_AGENT_EXECUTION_HANDOFF.md
5. docs/dep/spec.md and schemas/dep/*.schema.json for public DEP contracts

Inspect the existing implementation before coding. Reuse the setup-plan flow, IngestionService, ReplayabilityService, ReplayService, MutationService, CertificateService, ScenarioLibraryService, ReadinessService, ReleaseGateService, storage abstractions, Platform SPA, and Python SDK. Do not create parallel proof-loop services.

Execute WP-000 only. Do not begin WP-010 or WP-020 in the same change. Follow the exact scope, exclusions, acceptance criteria, and verification commands in the handoff and roadmap.

Product boundaries:
- Platform and SDK only; no Command Center.
- DEP is public and vendor-neutral; NSE internals remain private.
- Candidates are not Incidents.
- AssuranceCandidate and ScenarioCandidate are distinct.
- No LLM authority, custom neural network, graph database, process mining, real-time observability, autonomous remediation, or connector catalog.
- The existing replay/fix/proof/Scenario/Release Gate path is the only proof path.
- Missing context causes a skip or Evidence Gap, never a guessed failure.
- Preserve immutable evidence, provenance, temporal applicability, tenant scope, and append-only history.

Create a codex/ branch from main, implement WP-000 end to end, run all required checks, commit, push, and return the Required Worker Report. Continue when usage visibility is unavailable. Stop only for a real access/security/production/destructive-action blocker, contradictory requirements, or a consequential unresolved product decision.
```
