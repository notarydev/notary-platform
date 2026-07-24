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
- [ ] Resolution Trace explorer — DER drill-down with context bindings

### Sweep Definitions

- [x] Scaffold `renderLandscapeSweep()` in `static/app/app.js`
- [x] Fetch sweep definitions from `GET /v1/discovery/sweep-definitions`
- [x] Display table of definitions with Run action
- [x] Implement `runSweep()` to trigger a sweep run

### Navigation And Styling

- [x] Update `static/app/index.html` navigation with "Decision Landscape" link
- [x] Wire up state management (`S.viewParams.tab` for tab navigation)
- [ ] Add CSS classes to `static/app/styles.css` (using existing components)

## Phase 3: Testing

- [x] Update `tests/test_platform_static_app.py` — landscape view registration test
- [x] Create `tests/test_landscape_api.py` — 14 API contract tests
- [ ] Expand `tests/test_ui_vertical.py` with Playwright browser coverage
- [x] Run full test suite: `pytest -q --ignore=tests/test_ui_vertical.py` — 480 passed
- [x] Run browser tests: `pytest tests/test_ui_vertical.py` — 4 passed
- [x] `ruff check .` passes
- [x] `mypy src` passes
- [x] `make topology` succeeds

## Phase 4: Review And Merge

- [ ] Create PR against main
- [ ] Request independent review
