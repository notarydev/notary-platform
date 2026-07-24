<!--lint disable no-undefined-references strong-marker-->

# Work Order Execution Checklist: WO-100

**Work Order Number:** WO-100
**Work Order Title:** Decision Landscape UX
**Initialized At (UTC):** 2026-07-24T01:20:00Z

## Phase 1: Start / Context Gathering

### Required Steps

- [x] Review work order description
- [x] Identify linked requirements and blueprints
- [x] Review every connected requirements document
- [x] Review every connected blueprint document
- [x] Follow `@...` mentions and links to other blueprints in linked documents
- [x] Review every referenced blueprint
- [x] Extract acceptance criteria from requirements
- [x] Identify architecture path from blueprints
- [x] Confirm foundation WP-000–090 contracts merged in main (`e129300`)
- [x] Create `codex/wp-100-discovery-ux-v2` from merged main

## Phase 2: Implementation

### Decision Landscape Overview

- [x] Scaffold `renderDecisionLandscape()` in `static/app/app.js`
- [x] Fetch landscape data from `GET /v1/discovery/landscape`
- [x] Display source count, decision families, evaluator status
- [x] Display evidence gaps with advisory signals

### Assurance Candidate Queue

- [x] Scaffold `renderLandscapeCandidates()` in `static/app/app.js`
- [x] Fetch candidates from `GET /v1/discovery/candidates`
- [x] Display candidate list with type, severity, evidence level, lifecycle state
- [x] Add review action buttons (approve_incident/dismiss/request_context)
- [x] Scaffold `openCandidateDetail()` for single-candidate view + Proof Bridge promote
  - [x] E0–E4 evidence sufficiency visual indicator
  - [x] DER detail with identity, method, environment, version, context bindings, source resources
  - [x] Resolution trace link from DER detail
  - [x] Proof eligibility status with failures, next actions, authority
  - [x] Review history
  - [x] Outcome comparison (expected vs actual)
  - [x] Business summary display
  - [x] Action buttons per lifecycle state
- [x] Resolution Trace explorer — DER drill-down with context bindings

### Sweep Definitions

- [x] Scaffold `renderLandscapeSweep()` in `static/app/app.js`
- [x] Fetch sweep definitions from `GET /v1/discovery/sweep-definitions`
- [x] Display table of definitions with Run action
- [x] Implement `runSweep()` to trigger a sweep run

### Navigation And Styling

- [x] Update `static/app/index.html` navigation with "Decision Landscape" link
- [x] Wire up state management (`S.viewParams.tab` for tab navigation)
  - [x] Add CSS classes to `static/app/styles.css` (using existing components)

## Phase 3: Testing

- [x] Update `tests/test_platform_static_app.py` — landscape view registration test
- [x] Create `tests/test_landscape_api.py` — 14 API contract tests
- [x] Expand `tests/test_ui_vertical.py` with Playwright browser coverage — 34 tests covering landscape journey, families, candidates, DER detail, resolution trace, evidence gaps, signals safety, state coverage, responsive, authority safety, sweep, tab navigation
- [x] Run browser tests: `pytest tests/test_ui_vertical.py` — 34 passed
- [x] Run all tests: `pytest tests/test_ui_vertical.py tests/test_landscape_api.py tests/test_platform_static_app.py` — 55 passed
- [x] `ruff check .` passes
- [x] `mypy src` passes
- [x] `make topology` succeeds

## Phase 4: Review And Merge

- [x] Create PR against main
- [ ] Request independent review
