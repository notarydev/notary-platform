<!--lint disable strong-marker-->

# Review Log: WO-090

**Work Order:** WO-090 — Proof Bridge review remediation
**Initialized At (UTC):** 2026-07-23T13:20:16Z

This file records review and verification rounds. Append new rounds; do not overwrite prior rounds.

---

## Round 1

### Requirements Alignment

**Blocking:** Candidate bridge identity collided for candidates sharing a DER; authority metadata was client-controlled; environment checks failed open; downstream gate lineage and E4 recalculation were incomplete.

**Advisory:** EvidenceBundle schema accepted undeclared top-level properties.

### Blueprint Alignment

**Blocking:** Remote EvidenceBundles were stored as mutable PostgreSQL rows without an immutable S3 manifest.

**Advisory:** None.

### Architecture And Conventions

**Blocking:** Read-then-create promotion could create duplicate proof-loop records under concurrent retry.

**Advisory:** None.

### Tests And Build

**Commands run:** 456 non-browser tests, 4 Playwright tests, Ruff, mypy, and diff checks before Round 1 review.

**Blocking:** Existing tests did not cover same-DER candidates, concurrent-stable identity, strict schema rejection, full gate lineage, or E4 propagation.

**Advisory:** None.

### User-Facing Verification

**Skipped:** no

**Evidence:** Four Playwright vertical tests passed outside the macOS sandbox.

**Blocking:** None beyond requirements findings above.

**Advisory:** None.

### Security, Privacy, And Data Safety

**Skipped:** no

**Blocking:** Tenant/environment and reviewer-authority findings above.

**Advisory:** None.

### Round 1 Verdict

- Total blocking: 6
- Total advisory: 1
- Files reviewed: full WP-090 working-tree diff
- **Verdict:** CHANGES_REQUESTED

---

## Round 2

### Requirements Alignment

**Blocking:** Reviewer principal remained generic; environment scope was absent on several lineage records; E4 was assigned rather than recalculated; full gate-lineage integration coverage was incomplete.

**Advisory:** A second delegation resolver had weaker checks.

### Blueprint Alignment

**Blocking:** Logical bundle IDs were not verified against manifest digests.

**Advisory:** None.

### Architecture And Conventions

**Blocking:** Delimiter-based bridge keys could collide.

**Advisory:** None.

### Tests And Build

**Commands run:** 458 non-browser tests, 4 Playwright tests, Ruff, mypy, and diff checks.

**Blocking:** Add gate-lineage and strict boundary regression coverage.

**Advisory:** None.

### User-Facing Verification

**Skipped:** no

**Evidence:** Four Playwright vertical tests passed.

**Blocking:** None beyond requirements findings above.

**Advisory:** None.

### Security, Privacy, And Data Safety

**Skipped:** no

**Blocking:** Reviewer identity and environment lineage findings above.

**Advisory:** None.

### Round 2 Verdict

- Total blocking: 6
- Total advisory: 1
- Files reviewed: full WP-090 working-tree diff
- **Verdict:** CHANGES_REQUESTED

---

<!-- Subsequent rounds: copy the structure above and increment the round number. -->
