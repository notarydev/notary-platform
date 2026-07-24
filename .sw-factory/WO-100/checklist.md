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

- [ ] Scaffold `renderDecisionLandscape()` in `static/app/app.js`
- [ ] Fetch landscape data from `GET /v1/discovery/landscape`
- [ ] Display source count, decision families, coverage %, evaluator status
- [ ] Display evidence gaps with advisory signals

### Assurance Candidate Queue

- [ ] Scaffold `renderCandidateQueue()` in `static/app/app.js`
- [ ] Fetch candidates from `GET /v1/candidates/`
- [ ] Display candidate list with status, priority, evidence bundle ref
- [ ] Add review action buttons (approve/reject/suppress/delegate)
- [ ] Scaffold `renderCandidateDetail()` for single-candidate view

### Resolution Trace Explorer

- [ ] Scaffold `renderResolutionTrace()` in `static/app/app.js`
- [ ] Fetch context bindings from `GET /v1/discovery/context`
- [ ] Display DER chain with timestamps and identities
- [ ] Support drill-down to individual DER

### Sweep Run History

- [ ] Scaffold `renderSweepHistory()` in `static/app/app.js`
- [ ] Fetch sweep runs from `GET /v1/sweep/runs`
- [ ] Display table of runs with status, evaluator results, timestamps

### Navigation And Styling

- [ ] Update `static/app/index.html` navigation with new view links
- [ ] Add CSS classes to `static/app/styles.css`
- [ ] Wire up state management for new views

## Phase 3: Testing

- [ ] Update `tests/test_platform_static_app.py` for new views
- [ ] Create `tests/test_landscape_api.py` for landscape endpoint contract
- [ ] Expand `tests/test_ui_vertical.py` with Playwright browser coverage
- [ ] Run full test suite: `pytest -q --ignore=tests/test_ui_vertical.py`
- [ ] Run browser tests: `pytest tests/test_ui_vertical.py`

## Phase 4: Review And Merge

- [ ] `ruff check .` passes
- [ ] `mypy src` passes
- [ ] `make topology` succeeds
- [ ] `git diff --check origin/main...HEAD` passes
- [ ] Create PR against main
- [ ] Request independent review
