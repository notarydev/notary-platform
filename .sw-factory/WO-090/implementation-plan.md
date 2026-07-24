<!--lint disable no-undefined-references strong-marker-->

# Implementation Plan: WO-090

**Work Order:** WO-090 — Proof Bridge review remediation
**Created At (UTC):** 2026-07-23T13:20:16Z

## Summary

Resolve the blocking findings from the cumulative WP-000 through WP-090 review, with WP-090 Proof Bridge correctness as the primary scope. The implementation will preserve the existing proof loop, make promotion authority and persistence tenant-safe and idempotent, emit standards-conformant frozen evidence, and restore the DEP ingress contract and required quality gates exposed by the full review.

## Code Reuse And Package Structure

Reuse `IngestionService`, `ReplayabilityService`, the existing `VerificationRecord`/Incident workflow, DEP resource storage, and repository `to_dict`/`from_dict` conventions. Do not create a discovery-specific replay implementation. Reuse canonical digest data from `DecisionEvidenceResource` and the published DEP schemas rather than hashing identifiers.

Intentional change areas:

- Proof Bridge and review authority: `src/notary_platform/sweep/bridge.py`, `src/notary_platform/sweep/candidates.py`, and `src/notary_platform/api_server/routers/candidates.py`.
- Backward-compatible lineage and frozen-bundle models: `src/notary_platform/models.py` and the applicable sweep/incident models.
- Tenant-safe persistence: `src/notary_platform/storage.py`.
- DEP envelope compatibility: `src/notary_platform/dep/registry.py`, `src/notary_platform/dep/validation.py`, and schemas/fixtures only where needed to distinguish the inner DEP resource envelope from the outer CloudEvents transport.
- Regression coverage: `tests/test_proof_bridge.py`, remote-storage contract tests, DEP conformance/ingress tests, and API authorization tests.

## Components And Flow

`CandidateReviewService` establishes the effective append-only human decision or deterministic delegation. `ProofBridgeService` validates candidate, DER, Sweep Run, evidence resources, organization/environment scope, and current authority; freezes one deterministic EvidenceBundle keyed to the bridge operation; calls `IngestionService` to create exactly one `VerificationRecord`; and uses the existing Incident and replay services.

Promotion flow:

1. Resolve the candidate and all linked records within the authenticated organization and environment.
2. Resolve the latest effective, non-superseded review decision or matching active deterministic delegation.
3. Return stable prerequisite-specific error codes and remediation for E0-E2, missing resources, authority, context, or replay inputs.
4. Build a canonical manifest from stored resource digests, expected behavior, evaluator lineage, limitations, and authority; persist it under a deterministic identity.
5. Create or retrieve the bridge `VerificationRecord` and Incident through existing services.
6. Map internal replayability states to the public five-state WP-090 contract.
7. Return and query complete downstream lineage without modifying immutable Sweep outputs.

DEP ingress keeps the product's inner DEP envelope contract distinct from the CloudEvents transport envelope. The schema registry must resolve both explicitly and validate each payload at the correct boundary.

## Steps

1. **Lock regression behavior** - add failing tests for delegated-only promotion, stale/superseded review decisions, cross-tenant/environment links, deterministic bundle/Incident retries, remote bundle persistence, schema conformance, replay-state mapping, and exact remediation.
2. **Repair authority and scope resolution** - centralize effective review/delegation resolution and enforce organization/environment boundaries before any write.
3. **Repair evidence freezing and persistence** - introduce a backward-compatible EvidenceBundle representation with canonical IDs, DEP fields, stored content digests, deterministic manifest identity, and tenant-safe remote storage.
4. **Reuse the proof loop** - require `IngestionService`, remove duplicated fallback mapping, create exactly one VR/Incident, expose public replay states, and attach auditable lineage references.
5. **Restore DEP ingress compatibility** - separate inner DEP and CloudEvents schema identities/resolution and make existing valid fixtures, digest checks, batches, and tenant-isolated discovery pass again.
6. **Close quality gates** - resolve changed-path lint/type/format findings, run targeted and full suites, then perform a fresh delegated review and address every blocking finding.

## Testing

Automated verification:

- `.venv/bin/pytest -q tests/test_proof_bridge.py`
- `.venv/bin/pytest -q tests/test_dep_conformance.py tests/test_dep_ingress.py tests/test_dep_ingress_tenant_isolation.py`
- `.venv/bin/pytest -q tests/test_remote_storage_contract.py tests/test_postgres_s3_storage.py`
- `.venv/bin/pytest -q`
- `.venv/bin/ruff check .`
- `.venv/bin/ruff format --check` on every changed Python file
- `.venv/bin/mypy src`

Manual/exploratory verification:

- Exercise eligibility, promotion retry, and lineage through the FastAPI test client using human-review and delegated paths.
- Run the browser vertical suite outside the sandbox and verify that the proof action remains disabled until mutation verification succeeds.
