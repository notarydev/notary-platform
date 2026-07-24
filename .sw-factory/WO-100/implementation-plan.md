<!--lint disable no-undefined-references strong-marker-->

# Implementation Plan: WO-100

**Work Order:** WO-100 — Decision Landscape UX
**Created At (UTC):** 2026-07-24T01:20:00Z

## Summary

Build the graph-first Decision Landscape UX on top of the merged WP-000–090 foundation. This work is a clean rebuild against the actual merged contracts — no cherry-picking from the old WP-100 branch.

## Code Reuse And Package Structure

Reuse the existing SPA patterns in `static/app/app.js`, `static/app/components.js`, `static/app/styles.css`. All backend contracts are available through the merged WP-000–090 API routers:

- `GET /v1/discovery/landscape` — aggregated landscape data
- `GET /v1/discovery/context` — context bindings and resolution traces
- `GET /v1/discovery/sources` — source inventory
- `GET /v1/discovery/profiling` — source profiles
- `GET /v1/candidates/` — Assurance Candidate queue
- `GET /v1/sweep/runs` — Sweep run history
- `POST /v1/sweep/bridge/promote` — Proof Bridge promotion

Do not create a graph database, real-time monitoring, or a second proof path.

## Components And Flow

1. **Landscape overview** — aggregate view of sources, decision families, evaluators, coverage, gaps
2. **Candidate queue** — list/detail for Assurance Candidates with review/suppress/delegate actions
3. **Resolution trace explorer** — follow DERs and context bindings through the decision graph
4. **Sweep run history** — table of completed/in-progress sweeps with evaluator results
5. **Navigation** — integrate new views into the existing SPA navigation

## Implementation Order

1. Scaffold new view functions in `static/app/app.js` (renderDecisionLandscape, renderCandidateQueue, renderResolutionTrace, renderSweepHistory)
2. Implement Decision Landscape view against `GET /v1/discovery/landscape`
3. Implement Assurance Candidate queue with review actions against `/v1/candidates/`
4. Implement Resolution Trace explorer against `/v1/discovery/context`
5. Implement Sweep run history against `/v1/sweep/runs`
6. Update navigation in `static/app/index.html`
7. Add CSS for new components to `static/app/styles.css`
8. Write tests: `tests/test_platform_static_app.py` updates, `tests/test_landscape_api.py`, browser test expansion in `tests/test_ui_vertical.py`
