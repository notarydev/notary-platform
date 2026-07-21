# Notary Platform — Frontend Overhaul

## Problem statement
Live product on api.getnotary.ai. Backend (FastAPI, Python pkg `notary_platform`) is OK.
Fix the frontend: the `/app` vanilla-JS SPA "feels like static HTML, no depth, no proper
workflow/screen flows — like a rock." Setup felt unrealistic. Rename Harborline → generic
demo company. Build the workflow first; backend fit figured out later. Destination: GitHub
(NOT Emergent) — keep the repo's native run model (FastAPI serves `/app` + `/v1`).

## Architecture
- Backend: FastAPI at `/v1`, serves SPAs at `/app` (target) and `/cc` (ignored). In-memory
  storage by default; auth disabled when NOTARY_API_AUTH_TOKEN unset.
- Frontend under fix: `static/app/` = vanilla HTML/CSS/JS (index.html, app.js ~3100 lines,
  components.js, styles.css). No build step.
- Preview-only shim (gitignored): `/app/frontend/package.json` runs uvicorn on :3000 so the
  Emergent ingress can reach it. Not part of the real repo.

## Done (this session — 2026-07-21)
- Full visual-system overhaul (styles.css rewrite): Chivo/IBM Plex Sans/JetBrains Mono,
  layered grey surfaces + blueprint-blue accent, depth/shadows, glass topbar, staggered
  entrance animations, hover lifts, refined forensic tables & monospace pill badges.
- Fixed bug: overlapping Reveal/Copy buttons in code blocks (now a toolbar).
- Golden-path hero enriched (grid texture, outcome tiles fill dead space, colored steps).
- Renamed Harborline → "Meridian Credit Union" across all visible UI + backend demo org
  name + demo_preflight anchor. (Internal fn/id names + `/v1/demo/harborline-release-gate/seed`
  endpoint path kept.)
- Rebuilt Setup into a two-pane enterprise onboarding: vertical progress tracker w/ completion
  checkmarks + live progress bar, per-step guidance, pinned API token, bordered content pane,
  clickable visited steps, Finish → Verification Records.
- Verified: all 12 views render, 0 JS errors, demo seed flow works (gate FAIL→PASS, 6/6 steps).

## Backlog / Next
- P1: Deepen per-screen flows (Verification Record detail → replay → mutation → proof as one
  guided journey; Incidents; Scenarios; Readiness/Release Gate) with the same depth.
- P1: Replace remaining unicode/emoji glyphs (system-type icons in Integrations detail, nav)
  with SVGs per design guidelines.
- P2: Build the standalone "demo" experience (shelve/replace old one) — self-contained
  guided tour with a generic company.
- P2 (deferred per user): backend test fit — 4 `test_ui_vertical` errors are pre-existing
  (pytest-playwright `page` fixture not installed). 2 static-app + preflight tests updated to
  new naming/breakpoint.
- Consider real org display name from backend `/v1/platform/home` (currently mapped client-side).
