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

## Iteration 2 — System-first onboarding + Replay player (2026-07-21)
Research-backed (Sentry/Datadog/Arize/Langfuse/Fiddler): onboarding is system-first, SDK-driven,
with a live "first event" state; demo is a shortcut, not a separate product.

Built (skeleton + flow, placeholder data; backend fit deferred per user):
- Rebuilt Setup into ONE unified system-first onboarding (removed "select workflow"):
  1) Register AI System (name/type/env → issues ingest token) 2) Select Evidence Sources
  3) Instrument & Collect (SDK/API/Webhook with token-prefilled snippet) 4) Send First Record
  (live "waiting → received" radar animation + Send test record) 5) Replay Readiness.
- Merged Integrations + Demo nav into single "Setup"; removed the demo/non-demo fork.
- Demo decoupled → global "Load sample data" button in topbar (seeds catalog, refreshes).
- Replay Player (drawer): autoplay step-through of sealed cassette events (input→llm→http→policy
  →decision) with Play/Pause/Step/Restart, progress bar, and Original-vs-Replayed verdict.
  Opened from Send-step "Watch it replay" and Readiness step.
- Verified full flow via Playwright: register→sources→instrument→send→received→replay, 0 JS errors.

## Next
- Wire onboarding to real /v1 endpoints (register system, real from-snapshot capture, poll for
  first record) — currently simulated client-side.
- Attach Replay Player to real Verification Record / Incident detail (use record's actual events).
- Reconsider always-on DEMO banner now that demo is decoupled (currently backend home is_demo=true).
- Then: layer the Meridian demo tour on top of the real skeleton.

## Iteration 3 — Guided demo: Northstar Air (2026-07-21)
Per user spec (inspired by Moffatt v. Air Canada, 2024): support bot invents a retroactive
bereavement-refund policy. Built a dedicated guided "Demo" view (new nav item + topbar "Run demo").
10 chaptered scenes, clickable chip progress, Back/Next:
Setup → The failure (VR + decision evidence graph + policy/bot contradiction) → Replay (autoplay
player, reproduces OFFER_RETROACTIVE_REFUND) → Answer key (human label ESCALATE_TO_HUMAN) →
Verify fix (before/after) → Proof of Mitigation cert → Promote to Scenario → Gate blocked (v42 FAIL)
→ Gate passed (v43 PASS + Proof of Readiness + CI curl) → Assured end-state (6 green tiles + CTA).
Generalized the replay player to play any scenario (events + verdict). Client-side/self-contained
(no backend), kept minimal per user's "don't show" list. Verified full walkthrough, 0 JS errors.

## Next
- Wire demo artifacts to real /v1 (or a seeded Northstar dataset) so VRs/Proofs/Scenarios/Gate
  screens show the same Northstar story when opened from nav.
- Update onboarding Setup examples to the support-bot systems (Salesforce/Bereavement Policy API/
  GitHub Actions) so Setup and Demo tell one coherent story.
- Optionally retire/rework the Meridian lending golden-path on Home in favor of Northstar.
