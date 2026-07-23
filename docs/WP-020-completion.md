# WP-020: DEP Runtime Validation and Conformance Harness — Completion Record

**Status:** Accepted  
**Committed:** `17de78c` on `feat/w000-baseline-guardrails`  
**Date:** 2026-07-22  
**Review:** Code review passed — WP-000 through WP-020.

## Deliverables

| Artifact | Path | Count |
|---|---|---|
| JSON Schemas | `schemas/dep/*.schema.json` | 13 |
| Runtime package | `src/notary_platform/dep/` | 6 files |
| Documentation | `docs/dep/` | 4 files |
| Valid fixtures | `tests/fixtures/dep/valid/` | 12 envelopes |
| Invalid fixtures | `tests/fixtures/dep/invalid/` | 9 envelopes |
| Conformance tests | `tests/test_dep_conformance.py` | 28 tests |

## Exit Criteria

- **All published schemas have valid and invalid fixtures** ✅ — 12 valid, 9 invalid
- **Validation is deterministic and offline** ✅ — `jsonschema` with `FormatChecker`, no network calls
- **No public schema, fixture, or error contract contains proprietary NSE fields** ✅ — vendor-neutral

## Verification

```
ruff check:  All checks passed
mypy:        Success: no issues found in 7 source files
pytest:      247 passed, 0 failed (excludes 2 pre-existing UI/replay failures)
```

## Non-Blocking Technical Debt

- `jsonschema.RefResolver` deprecated as of v4.18.0 in favor of `referencing` — resolve before adding cross-schema `$ref`
- Full resource payload validation against type-specific schemas deferred due to naming conflict on `type` (routing vs event)
