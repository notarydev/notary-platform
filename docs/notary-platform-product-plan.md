# Notary Platform — Full Product Plan

Planning model: screen-by-screen specification against REQ-NP-001 through REQ-NP-014.

## Current `/app` weaknesses
- 11 sidebar entries, only Home has live data; rest are blank placeholders
- Agents, Systems, Capture are static `<table>` renders, no actions, no drawers, no filters
- Incidents, Proofs, Replay, Scenarios, Governance, Settings are filler text/cards
- No loading, empty, error, or disabled states anywhere
- No demo markings on seeded objects
- Built-vs-planned not distinguished in UI

---

## Cross-cutting states (applies to ALL modules)

Every module must honor these UI states:

| State | Behavior |
|---|---|
| **Loading** | Skeleton cards/rows with pulsing animation |
| **Empty** | Friendly message + link to next action or onboarding |
| **Error** | Red banner with error detail + retry button |
| **Disabled** | Grayed out button/action with tooltip explaining why |
| **Planned** | "Planned" badge, disabled action, honest description |
| **Demo** | "DEMO" badge on every seeded object, "Demo data — not production" banner |

Every feature/object must carry three labels:
- **Build State** — Built / In build / Backlog / Roadmap / Unknown
- **Demo State** — Live demo / Seeded demo / Preview only / Not demoable / Unknown
- **Customer Readiness** — Demo prototype / Beta / Production-ready / Internal only / Planned / Unknown

---

## 1. Home (WO-49)

**Purpose:** At-a-glance platform health. The first thing a customer sees when they log in.

**Personas:** Platform owner, compliance officer, operator

**Default state:** Shows seeded demo org (Acme Assurance Demo) with a visible DEMO badge and "Demo data — not production" banner across the top.

**Data shown:**
- Organization name + environment selector (demo/staging/production dropdown)
- Setup health card: SDK installed (check/x), systems connected (N/M), agents instrumented (N), incidents collected (N), proofs issued (N), scenarios created (N)
- Active queues bar: incidents needing replay (N), fixes needing verification (N), proofs ready to issue (N) — each count is clickable, navigates to that module filtered
- Recent proof activity (last 5 certificates issued, showing incident ID, agent name, status, date)
- Current blockers (from `/v1/topology` blockers list, each with label, status, and next action)
- Next action card: the single most impactful thing to do right now (context-aware: "Replay incident inc-000001" or "Issue proof for inc-000002" or "Install the SDK to begin")

**Primary actions:**
- Seed demo incident (hidden in production environments)

**Secondary actions:**
- View all incidents →
- View all proofs →
- View all agents →
- View all systems →

**Row actions:** None — summary cards and clickable counts only

**Detail panel:** None — clicking a queue count navigates to that module. Clicking a recent proof navigates to Proofs filtered to that certificate.

**Loading state:** Skeleton cards (pulsing gray rectangles matching card shapes). Environment selector shows spinner.

**Empty state:** "Welcome to Notary Platform. Your organization, Acme Assurance Demo, is ready to go. Install the SDK to begin capturing decisions." + prominent link to Onboarding + checklist progress indicator.

**Error state:** Red banner "Could not load platform data. Is the API running?" + retry button.

**Disabled/planned states:** "Production" and "Staging" environments show "No production data yet" or "This environment is configured but not yet in use." Cards still render but show placeholder values.

**Demo markings:**
- "DEMO" badge on org name
- "Demo data — not production" banner at top
- Every stat marked with subtle "demo" tooltip

**Backend data needed:**
- HomeStats model (exists, extend with recent_proofs, blockers, setup_health)
- Topology blockers list
- Incident list filtered by status

**Existing endpoints:**
- `GET /v1/platform/home` — exists, extend response

**New endpoints:**
- `GET /v1/platform/home/recent-proofs` — last 5 certificates
- `GET /v1/platform/home/setup-health` — SDK/system/agent completion booleans

**Related WOs:** WO-49 (Shell + Home overview)

**Open questions:**
- Should environment switching actually filter data, or is it placeholder for now?
- Should the next-action card use heuristics or be static for demo?

---

## 2. Onboarding (WO-50)

**Purpose:** Get a new organization from zero to first captured decision. Step-by-step guided checklist.

**Personas:** AI platform owner, engineer setting up SDK for the first time

**Default state:** Numbered checklist with step-by-step progress indicators. Each step has a checkmark when complete, a spinner when in progress, and a disabled state when previous step isn't done.

**Data shown:**
- Step 1 — Install SDK: Code snippet (`pip install notary-sdk`), copy button, status indicator (Not installed / Installed / Connected)
- Step 2 — Instrument an agent: Decorator example code, "Agent detected" check, agent name input
- Step 3 — Send test capture: "Run Test Capture" button, loading spinner, result preview (shows decision, elements count, root hash)
- Step 4 — Connect systems: Link to Systems page with systems count shown
- Step 5 — Create capture policy: Link to Capture page with policy count shown
- Step 6 — View first incident: Link to Incidents page with incident count shown

**Primary actions:**
- Run Test Capture (POSTs a demo snapshot for the selected agent, shows result inline)

**Secondary actions:**
- Skip to Home → navigates to Home
- Copy code snippets (each step has a copy button)

**Row actions:** None — checklist only

**Detail panel:** None

**Loading state:** Spinner on test capture button while running. Spinner on SDK status check on load.

**Empty state:** Fresh checklist — all 6 steps unchecked, all disabled except Step 1.

**Error state:** "SDK connection failed. Is the SDK installed and running on your agent?" with link to SDK docs. "Test capture failed — the agent may not be connected. Try checking agent status on the Agents page."

**Disabled/planned states:** Steps become enabled sequentially. Step N is disabled (grayed out with tooltip "Complete previous step first") until Step N-1 is completed. The checklist state persists per organization/environment.

**Demo markings:** "DEMO — use a real agent for production" banner. Test capture results show DEMO badge.

**Backend data needed:**
- Agent list with sdk_status, sdk_version (exists)
- Demo scenario for test capture (exists — lending-denial)

**Existing endpoints:**
- `GET /v1/platform/org/agents` — exists, filter by sdk_status

**New endpoints:**
- `POST /v1/platform/onboarding/test-capture` — creates a demo incident for the specified agent, returns incident ID + result summary

**Related WOs:** WO-50 (Onboarding + SDK status)

**Open questions:**
- Should the checklist be dismissible after completion, or always accessible?
- Should we track checklist completion per-user or per-org?

---

## 3. Agents (WO-50)

**Purpose:** Inventory of AI agents connected to Notary. Understand SDK health, capture status, and incident history per agent.

**Personas:** AI platform owner, engineer

**Default state:** Filterable table of agents. Each row shows compact info; clicking expands to a detail drawer.

**Data shown (table):**
- Agent name, risk tier (standard/high), SDK status (connected/stale/not_installed — with colored dot), SDK version, last seen (relative time), incident count, scenario count, capture policy count

**Primary actions:**
- Register Agent (opens form: name, risk tier, environment)

**Secondary actions:**
- Filter by SDK status (dropdown: All, Connected, Stale, Not installed)
- Filter by environment (dropdown: All, Demo, Staging, Production)
- Search by agent name

**Row actions (dropdown menu or detail drawer tabs):**
- View Agent — opens detail drawer
- Setup SDK — show install instructions snippet for this agent
- Send Test Capture — POST a demo snapshot, show result inline
- Troubleshoot Stale SDK — show last-heartbeat detail, connection diagnostic
- View Capture Policy — navigate to Capture filtered by this agent
- View Incidents — navigate to Incidents filtered by this agent
- View Scenarios — navigate to Scenarios filtered by this agent

**Detail drawer:**
- Full agent profile header: name, risk tier badge, SDK status dot + label
- SDK details: version, last seen timestamp, connection method
- Stats: incident count (clickable), scenario count (clickable), capture policy count (clickable)
- Linked incidents list (last 5, with status badges and links)
- Linked scenarios list (last 5)
- Linked capture policies (with coverage type)
- Data-handled summary (from topology lens metadata)
- Created date

**Loading state:** Table skeleton rows (5 rows of pulsing rectangles)

**Empty state:** "No agents registered yet. Install the Notary SDK in your agent runtime to get started." + prominent link to Onboarding (Step 2).

**Error state:** "Could not load agents. Check your API connection." + retry button.

**Disabled/planned states:** Actions grayed out if SDK not installed (e.g., "Send Test Capture" disabled with tooltip "SDK not installed for this agent"). "View Scenarios" disabled with tooltip "No scenarios linked to this agent."

**Demo markings:**
- DEMO badge on seeded agent rows
- "Seeded demo agent — not a real deployment" tooltip
- Detail drawer shows "Demo data" watermark

**Backend data needed:**
- Agent list (exists, extend with incident_count, system_count, scenario_count)
- Per-agent incident list (from storage)
- Per-agent scenario list (from seed data)

**Existing endpoints:**
- `GET /v1/platform/org/agents` — exists, extend response with linked counts

**New endpoints:**
- `POST /v1/platform/org/agents` — register a new agent
- `POST /v1/platform/agents/{id}/test-capture` — demo capture for a specific agent
- `GET /v1/platform/agents/{id}/details` — full agent profile with linked objects

**Related WOs:** WO-50 (Onboarding + Agents)

**Open questions:**
- Should agent registration auto-detect from SDK heartbeat, or always be manual?
- Should we show agent version history?

---

## 4. Systems (WO-51)

**Purpose:** Manage external system connections — source systems, sandboxes, GRC platforms, webhooks, CI/CD systems.

**Personas:** Platform owner, engineer, compliance officer

**Default state:** Filterable table of systems. Connected systems show green dot; planned show gray.

**Data shown (table):**
- System name, type (api/sdk/webhook/sandbox/grc/ci_cd), connection status (connected/disconnected/stale/planned — colored dot), last checked (relative time), capability summary

**Primary actions:**
- Add Connection (opens form: name, type selector, endpoint URL or config, credentials — masked on save)

**Secondary actions:**
- Filter by type (dropdown)
- Filter by status (dropdown: All, Connected, Disconnected, Stale, Planned)
- Search by name

**Row actions:**
- Test Connection — pings the endpoint, shows success/failure banner
- Configure — edit connection settings
- Review Data Scope — show what data flows through this system (from topology data_handled)
- View Related Incidents — navigate to Incidents filtered by system
- Disconnect — confirm dialog, sets status to disconnected

**Detail drawer:**
- System profile: name, type badge, status dot
- Connection details: endpoint (masked if contains credentials), last checked time, failure reason if disconnected
- Data scope: what data types flow through this connection
- Related incidents list (last 5, clickable)
- Configuration history (last modified, created date)

**Loading state:** Table skeleton rows

**Empty state:** "No systems connected. Connect a source system, sandbox, or GRC platform to get started." + Add Connection button.

**Error state:** "Could not load systems." + retry. "Connection test failed — endpoint unreachable. Check the URL and try again."

**Disabled/planned states:** "Planned" systems show informational card with "This integration is planned and not yet available." No actions enabled. "Test Connection" disabled if system is disconnected or planned.

**Demo markings:**
- DEMO badge on seeded system rows
- "Seeded demo connection — not a real integration" tooltip

**Backend data needed:**
- SystemConnection list (exists, extend with incident_count)
- SystemConnection detail (config — from seed data, not real credentials)

**Existing endpoints:**
- `GET /v1/platform/org/systems` — exists

**New endpoints:**
- `POST /v1/platform/org/systems` — add a new connection
- `POST /v1/platform/systems/{id}/test` — test connection (returns success/failure + detail)
- `PUT /v1/platform/systems/{id}` — update connection config

**Related WOs:** WO-51 (Systems + Capture)

**Open questions:**
- Should connection testing be real (actual HTTP ping) or seeded/demo for each system type?
- Should credentials be stored as reference-only (ARNs) or can we accept values for demo?

---

## 5. Capture (WO-51)

**Purpose:** Define what Notary captures, redacts, hashes, omits, or routes for each agent. Policies control evidence scope.

**Personas:** Compliance officer, engineer

**Default state:** Filterable table of capture policies. Each row shows agent assignment and coverage type.

**Data shown (table):**
- Policy name, coverage type (all/redacted/omitted/hashed), assigned agent (linked), status (active/inactive/inherited), last modified, created date

**Primary actions:**
- Create Policy (opens form: name, agent selector, field rules — for each field: capture/redact/omit/hash toggle)

**Secondary actions:**
- Filter by agent
- Filter by status

**Row actions:**
- Edit — opens policy form
- Preview Captured Fields — shows sample field list with capture/redact status (uses seed data for demo)
- Assign Policy — links to an agent
- Deactivate — sets status to inactive
- Delete — confirm dialog, archives policy

**Detail panel (or modal):**
- Policy name, agent, status
- Field rules table: field name | action (capture/redact/omit/hash) | description
- Assigned agents list
- Created/updated dates

**Loading state:** Table skeleton

**Empty state:** "No capture policies defined. Create a policy to control what Notary captures from your agents." + Create Policy button.

**Error state:** "Could not load capture policies." + retry.

**Disabled/planned states:** Inherited policies (from org default) show "inherited from organization default" + view-only mode. No edit/delete actions on inherited policies.

**Demo markings:**
- DEMO badge on seeded policies
- "Seeded demo policy — configure real policies for production" tooltip

**Backend data needed:**
- CapturePolicy list (exists)
- Field preview data (seeded demo)

**Existing endpoints:**
- `GET /v1/platform/org/policies` — exists

**New endpoints:**
- `POST /v1/platform/org/policies` — create policy
- `PUT /v1/platform/policies/{id}` — update policy
- `DELETE /v1/platform/policies/{id}` — archive policy
- `GET /v1/platform/policies/{id}/preview` — field preview with demo data

**Related WOs:** WO-51 (Capture)

**Open questions:**
- Should policies support regex-based field matching or only named fields?
- Should field preview use real agent data or only seed data for demo?

---

## 6. Incidents (WO-52)

**Purpose:** Queue of captured verification records and incidents needing action. Primary workflow surface.

**Personas:** Compliance officer, operator, AI engineer

**Default state:** Filterable, paginated table. Each row compact; click to expand inline detail or open Investigation module.

**Data shown (table):**
- Incident ID, source agent (name + icon), decision type (lending/support/prior-auth/hiring), status (ingested/replayed/mitigated/certified — colored badge), age (relative time), next action (human-readable: "Needs replay", "Ready for proof", etc.), owner (if assigned)

**Primary actions:**
- Open Incident — navigates to Incident Investigation module
- Seed demo incident (hidden in production envs)

**Secondary actions:**
- Filter by status (multi-select pills: Ingested, Replayed, Mitigated, Certified)
- Filter by agent (dropdown from agent list)
- Filter by decision type
- Search by incident ID
- Pagination (previous/next, showing "1–20 of N")

**Row actions (inline buttons or dropdown):**
- Replay — triggers POST replay, shows spinner, updates status badge
- Assign — opens owner selector (dropdown of seeded names)
- Add Expected Outcome — opens label form (text + reviewer name)
- Submit Fix — navigates to Replay & Verification module with this incident pre-selected
- Issue Proof — navigates to Proofs module (or triggers cert issuance directly if no config needed)
- Promote to Scenario — opens confirm dialog, POSTs (currently returns 501 "Planned")

**Detail panel (inline expand below row, or side drawer):**
- Incident metadata: ID, agent, decision type, status badge
- Evidence summary: number of elements, root hash (truncated), integrity status
- Workflow timeline: ingested → replayed (or not) → fix verified (or not) → certified (or not) — filled/gray step indicators
- Quick-actions bar: same actions as row actions, in a button bar

**Loading state:** Table skeleton. Spinner on replay/cert actions.

**Empty state:** "No incidents yet. Incidents appear when Notary captures a decision from an instrumented agent." + link to Onboarding (Step 6) + "Seed a demo incident" button (if in demo mode).

**Error state:** "Could not load incidents." + retry. "Replay failed — see ECS logs for details." on action failure.

**Disabled/planned states:** Row actions grayed out if prerequisite not met:
- "Replay" — disabled if already replayed
- "Submit Fix" — disabled if not yet replayed
- "Issue Proof" — disabled if not yet mitigated
- "Promote to Scenario" — always disabled with "Planned — coming in a future release"
- "Add Expected Outcome" — enabled only after replay

**Demo markings:**
- DEMO badge on seeded incidents
- "Seeded demo incident — not a real customer decision" watermark

**Backend data needed:**
- Incident list from storage (exists, extend response with agent_name, decision_type, next_action, assigned_owner)
- Incident counts by status (for filter pills)

**Existing endpoints:**
- `GET /v1/incidents` — exists, extend response
- `POST /v1/incidents/{id}/replay` — exists
- `POST /v1/incidents/{id}/mutation-tests` — exists
- `POST /v1/incidents/{id}/certificates` — exists

**New endpoints:**
- `POST /v1/incidents/{id}/assign` — set owner (metadata, no backend model change yet)
- `POST /v1/incidents/{id}/promote-to-scenario` — returns 501 (planned)

**Related WOs:** WO-52 (Incidents collection)

**Open questions:**
- Should assignment persist or be ephemeral (in-memory only for demo)?
- Should "Issue Proof" auto-navigate to Proofs or issue directly?

---

## 7. Incident Investigation (WO-52)

**Purpose:** Deep-dive into a single incident. Understand what was captured, replay result, fix verification, proof status, and custody chain. Replaces the old Forensic Control Center graph.

**Personas:** Compliance officer, AI engineer

**Default state:** Full-page view when clicking "Open Incident" from the queue. Shows incident ID in the top bar with a back arrow.

**Data shown (sections top to bottom):**

**Header:** Incident ID, agent name, decision type, status badge, age, assigned owner (if set)

**Workflow Timeline:** Horizontal step indicators — Captured → Integrity Verified → Replayed → Fix Verified → Certified — each filled or gray based on current state. Current step highlighted.

**Evidence Section:**
- Snapshot summary: schema version, timestamp, element count, root hash (truncated, with copy button)
- Element list: kind (http/decision/llm), payload summary (request method+URL, decision value, prompt snippet), element hash
- Integrity status: verified/not_verified with detail

**Replay Section:**
- Replay status: replayed/not replayed
- If replayed: decision value, replay method, cassette info, timestamp
- If not: "Replay not yet run" with Run Replay button
- Replay history if multiple replays done

**Fix Verification Section:**
- Original decision (from replay)
- Fix config (JSON or key-value display)
- Mutated decision
- Mitigated: yes/no (green check / red x)
- Expected correct behavior (from human label)
- Human label source (who approved the expected outcome)

**Proof Section:**
- If certified: certificate ID, signing algorithm, signature (truncated preview), signature valid (green check / red x), issued date, known limitations
- If not: "Proof not yet issued" with Issue Proof button

**Custody Chain:** Timestamped event log — created, ingested, evidence stored, replayed, mutation tested, certified. Each event shows action, actor, detail, timestamp.

**Primary actions:**
- Run Replay (if not yet replayed)
- Verify Fix (opens fix config input + expected outcome, runs mutation test)
- Issue Proof (POSTs certificate, shows result inline)
- Export Evidence (downloads full incident JSON)

**Secondary actions:**
- Promote to Scenario (disabled — planned)
- Assign Owner
- Close Incident (archives — sets status to closed, removes from active queue)

**Loading state:** Section skeletons — each section shows pulsing rectangles while data loads.

**Empty state:** "Select an incident from the queue to investigate." (if accessed without an incident ID)

**Error state:** "Incident not found" (invalid ID). "Access denied" (cross-org). "Replay failed — cassette may be incomplete." (action failure).

**Disabled/planned states:**
- Issue Proof disabled until mitigated
- Verify Fix disabled until replayed
- Promote to Scenario disabled (planned)
- Export Evidence always available if incident exists

**Demo markings:**
- DEMO badge in header
- "Demo incident" watermark on evidence

**Backend data needed:**
- Full incident object: snapshot_summary, replay_result, mutation_result, certificate, custody
- Snapshot detail (elements + hashes)

**Existing endpoints:**
- `GET /v1/incidents/{id}` — exists
- `GET /v1/incidents/{id}/snapshot` — exists
- `POST /v1/incidents/{id}/replay` — exists
- `GET /v1/incidents/{id}/replay` — exists
- `POST /v1/incidents/{id}/mutation-tests` — exists
- `GET /v1/incidents/{id}/mutation-tests` — exists
- `POST /v1/incidents/{id}/certificates` — exists
- `GET /v1/incidents/{id}/certificates/pom-cert-v1` — exists
- `GET /v1/incidents/{id}/certificates/pom-cert-v1/verify` — exists
- `GET /v1/incidents/{id}/certificates/pom-cert-v1/download` — exists

**New endpoints:**
- None needed — all data and actions exist. Frontend needs to compose the responses into the Investigation view.

**Related WOs:** WO-52 (Incident Investigation)

**Open questions:**
- Should the incident detail auto-refresh after actions (replay, fix), or require manual refresh?
- Should custody events be expandable or always visible?

---

## 8. Replay & Verification (WO-53)

**Purpose:** Dedicated workflow view for replay → fix → verify. Focused screen with minimal distraction.

**Personas:** AI engineer, compliance officer

**Default state:** Shows either the currently selected incident or an incident selector dropdown if none selected.

**Data shown:**
- Incident selector (dropdown, searchable by ID)
- Replay section: readiness indicator (green/yellow/red), cassette completeness % (N/N elements captured), deterministic conditions check (✓/✗), sandbox requirement (planned/available), replay history (list of past runs with decision and timestamp)
- Fix Verification section: fix reference input (text area or JSON editor), expected outcome label (Human Label — text input + reviewer name), original decision display, mutated decision display (updates after running), mitigated result (yes/no with color)
- Limitations: known caveats about the replay (from certificate limitations field)

**Primary actions:**
- Run Replay (if ready — POSTs replay, shows result inline, enables Fix section)
- Submit Fix + Verify (POSTs mutation test, shows original vs mutated vs mitigated result)
- View Proof → navigates to Proofs module filtered to this incident's certificate

**Secondary actions:**
- View Incident → navigates to Investigation module
- View Scenario → navigates to Scenarios (if promoted)

**Row actions:** None — this is a workflow view, not a data table.

**Detail panel:** This IS the module — the entire screen is the workflow.

**Loading state:** Spinner on Replay Run button while executing. Skeleton on section load. "Verifying fix..." spinner on Submit Fix action.

**Empty state:** "Select an incident to begin replay and verification." + incident selector dropdown prominently displayed.

**Error state:** "Replay failed — cassette may be incomplete. The incident was captured with M of N elements. Try recording a more complete capture." "Fix verification failed — could not apply the fix config. Check the config format."

**Disabled/planned states:**
- Fix Verification section entirely disabled (grayed out with tooltip "Replay required before fix verification") until replay completes
- Issue Proof button disabled until mitigated
- Sandbox mode toggle disabled with "Planned — sandbox replay coming in a future release"

**Demo markings:**
- DEMO badge on incident selector
- "Demo replay — production replays may vary" note

**Backend data needed:**
- Incident replay_result, mutation_result (exists)
- Cassette completeness info (from snapshot element count)
- Sandbox availability flag (from topology)

**Existing endpoints:**
- Same as Investigation, plus:
- `GET /v1/incidents/{id}/incidents` — for dropdown

**New endpoints:**
- `GET /v1/incidents/{id}/replay-readiness` — cassette completeness, deterministic conditions, sandbox required

**Related WOs:** WO-53 (Replay + Fix Verification)

**Open questions:**
- Should the fix config be free-form text, JSON, or structured key-value pairs?
- Should replay history accumulate or only show the latest?

---

## 9. Proofs (WO-53)

**Purpose:** Certificate and proof management. View issued proofs, verify signatures, download certificates, and prepare export bundles (planned).

**Personas:** Legal, compliance officer, auditor

**Default state:** Filterable table of issued proofs. Each row shows certificate status.

**Data shown (table):**
- Certificate ID (pom-cert-v1), incident ID (linked), agent name, signing algorithm, signature valid (green check / red x / not verified), issued date, claim scope summary

**Primary actions:**
- Issue Proof (if an incident is mitigated but not yet certified — opens confirmation dialog, POSTs certificate)

**Secondary actions:**
- Filter by signature status (valid/invalid/unverified)
- Filter by agent

**Row actions:**
- View Certificate — opens detail panel with full JSON content, pretty-printed
- Verify Signature — runs `/verify` endpoint, shows result banner (green/red)
- Download — triggers browser download of the certificate JSON
- Export Bundle — disabled, tooltip: "Defensibility bundles are planned and not yet available"
- View Incident — navigates to Investigation

**Detail panel:**
- Certificate ID, certificate type, incident ID, timestamp
- Signing algorithm, signing public key (if asymmetric — displayed as truncated base64 with copy button)
- Signature (truncated preview with copy button)
- Claim scope and known limitations
- Original decision, mutated decision, fix config (from certificate payload)
- Verified outcome (true/false)
- Full JSON toggle (expands raw cert JSON)

**Loading state:** Table skeleton

**Empty state:** "No proofs issued yet. Run replay and fix verification on an incident to issue a proof of mitigation." + link to Incidents.

**Error state:** "Could not load proofs." + retry. "Signature verification failed — the certificate may be tampered." (specific error from verify endpoint). "Could not issue proof — incident must be in mitigated state."

**Disabled/planned states:**
- Export Bundle always disabled with "Planned" tooltip
- Verify Signature grayed out if no KMS key is configured
- Issue Proof disabled if no incident is ready (shows how many are ready)

**Demo markings:**
- DEMO badge on seeded certificates
- "Demo certificate — not a production proof. Production certificates are independently verifiable."

**Backend data needed:**
- Certificate list from storage (filter incidents by certified status)
- Per-certificate verification result

**Existing endpoints:**
- `GET /v1/incidents` (filter by certified) — exists
- `POST /v1/incidents/{id}/certificates` — exists
- `GET /v1/incidents/{id}/certificates/pom-cert-v1` — exists
- `GET /v1/incidents/{id}/certificates/pom-cert-v1/verify` — exists
- `GET /v1/incidents/{id}/certificates/pom-cert-v1/download` — exists

**New endpoints:**
- None — all needed endpoints exist

**Related WOs:** WO-53 (Proofs)

**Open questions:**
- Should certificates from deleted incidents still appear in the proofs list?
- Should we show certificate revocation status (planned feature)?

---

## 10. Scenarios (WO-54)

**Purpose:** Scenario Library for release-gate testing. Map captured failures to repeatable test cases that prevent recurrence. Currently a planned scaffold.

**Personas:** AI platform owner, engineer

**Default state:** Honest planned scaffold. Shows informational cards explaining what Scenarios will do, with seed demo data for illustration.

**Data shown:**
- Banner: "Scenario testing is planned and not yet available. Scenarios will let you promote verified incidents into repeatable regression tests."
- If demo scenarios exist (seeded): table with name, source incident (linked), expected outcome, last run (empty for demo), release-gate membership
- Feature preview card: "When Scenarios are live, you'll be able to: Run replay against multiple scenarios simultaneously, Gate agent releases based on scenario results, Receive alerts when a scenario fails in CI/CD"

**Primary actions:** None enabled — Promote Incident to Scenario button is visible but disabled

**Secondary actions:** None

**Row actions (demo view):**
- View Scenario Detail — shows metadata card with name, source incident, expected outcome, replayability status, last run (empty), release gate status
- View Source Incident — navigates to Investigation

**Detail panel:** Scenario detail card — name, source incident link, expected outcome, label source, replayability status, last run result (empty), release gate membership, owner

**Loading state:** None — this is mostly static + seeded data

**Empty state:** "No scenarios yet. When scenario testing is available, you'll be able to promote incidents to scenarios here." — This IS the default state.

**Error state:** "Could not load scenario data." + retry.

**Disabled/planned states:** Entire module is a planned scaffold:
- "Run Scenario" button visible but disabled: "Planned capability — not yet built"
- "Create Release Gate" button visible but disabled: "Planned capability — not yet built"
- "Promote Incident to Scenario" disabled with same messaging
- Every feature described as "Planned"

**Demo markings:**
- DEMO badge on seeded scenarios
- "Scenario testing is not yet available. This is a preview of planned functionality."
- "Planned" badges on every action

**Backend data needed:**
- Seeded demo scenarios (from topology demo_scenarios or new seed data)

**Existing endpoints:** None for scenarios

**New endpoints:**
- `GET /v1/platform/scenarios` — returns seeded demo scenarios
- `POST /v1/incidents/{id}/promote-to-scenario` — returns 501 (planned)

**Related WOs:** WO-54 (Scenarios)

**Open questions:**
- Should seeded scenarios map 1:1 to existing demo_scenarios from the API, or be separate?
- When Scenarios go live, should they use the same data model as demo_scenarios.py?

---

## 11. Governance (WO-54)

**Purpose:** Labels, claim scope, regulatory mappings, retention policies, audit trail. Honest scaffold — everything is planned.

**Personas:** Compliance officer, legal, auditor

**Default state:** Informational cards explaining what governance will cover. No active functionality.

**Data shown (static cards):**
- Labels: "Human Labels track approved expected outcomes for replay and fix verification. When governance is enabled, you'll be able to review, approve, and audit labels assigned to incidents."
- Claim Scope: "Every proof is scoped to the tested scenario and approved expected outcome. Notary does not claim general AI safety beyond the tested conditions."
- Regulatory Mappings: "Planned — maps evidence to NAIC AI governance, EU AI Act (Article 10), HIPAA, FCRA, GLBA, ADA, and SEC disclosure requirements."
- Retention: "Planned — evidence lifecycle management, legal hold, and archival policies."
- Audit Events: "Planned — administration and access audit trail. All user actions (login, incident access, replay, proof issuance) will be logged."
- GRC Push Status: "Planned — push proofs and evidence bundles to ServiceNow, OneTrust, AuditBoard, and other GRC platforms."

**Primary actions:** None

**Secondary actions:** None

**Row actions:** None

**Detail panel:** None

**Loading state:** None — static content

**Empty state:** This IS the default state — informational cards

**Error state:** None — static content

**Disabled/planned states:** Every card carries a "Planned" badge. No actions. All feature descriptions use future tense.

**Demo markings:** "Governance features are planned and not yet available."

**Backend data needed:** None

**Existing endpoints:** None

**New endpoints:** None — static content

**Related WOs:** WO-54 (Governance)

**Open questions:**
- When governance goes live, should it be a separate module or integrated into each existing module?
- Should label management be part of Governance, or should labels appear inline in Incident Investigation?

---

## 12. Settings (WO-54)

**Purpose:** Organization administration — users, roles, API keys, environments, integrations, entitlements. Mostly planned scaffold with read-only org info live.

**Personas:** Organization administrator

**Default state:** Section cards. Organization info is live; everything else is planned.

**Data shown (section cards):**
- Organization (live): name, ID, environments list (demo/staging/production), created date. Copy Org ID button works.
- Users & Roles: "Planned — user management for multi-user organizations. Invite team members, assign roles, and manage permissions."
- API Keys: "Planned — manage SDK and API keys. Rotate, revoke, and audit key usage."
- Environments: Shows environment list (demo/staging/production) with status (active/configured/placeholder). No edit capability yet.
- Integrations: "Planned — configure GRC connectors, CI/CD webhooks, sandbox providers, and ticketing system integrations."
- Entitlements: "Planned — manage usage limits, feature gates, and plan upgrades."

**Primary actions:**
- Copy Org ID (copies to clipboard, shows toast confirmation)

**Secondary actions:** None enabled

**Row actions:** None

**Detail panel:** None

**Loading state:** Spinner on org info card while loading

**Empty state:** N/A — org always exists

**Error state:** "Could not load organization settings." + retry (org info card only)

**Disabled/planned states:** All cards except Organization are "Planned" with disabled actions. Environment list is read-only.

**Demo markings:** "Demo organization — production settings available after upgrade"

**Backend data needed:**
- Organization data (exists)
- Environment list (exists)

**Existing endpoints:**
- `GET /v1/platform/org` — exists
- `GET /v1/platform/org/environments` — exists

**New endpoints:** None — existing endpoints serve the live data

**Related WOs:** WO-54 (Settings)

**Open questions:**
- Should user management be the first Settings feature to go live, or API keys?
- Should environments be editable (add/remove) or fixed to demo/staging/production?

---

## 13. Demo Organization (WO-48)

**Purpose:** Pre-seeded Acme Assurance Demo org so the platform has realistic data without connecting real customer systems. Every seeded object must be visibly marked.

**Seed data (already exists):**
- Organization: Acme Assurance Demo (id: org:acme-demo)
- Environments: demo (env:demo), staging (env:staging), production (env:production)
- 4 Agents: Lending Decision (connected, high risk), Support Handoff (connected, medium), Prior Authorization (stale, high), Hiring Screen (not installed, medium)
- 7 Systems: Notary SDK, Notary API, Credit Bureau API, Support Ticketing, AWS KMS, S3 Evidence Store, GRC System (planned)
- 2 Capture Policies: Default Capture Policy (active, all), Lending Agent Policy (active, all)

**Seed incidents needed (not yet implemented):** 5 demo incidents that flow through the full replay→mutation→cert proof-loop so every module has data:

1. **inc-000001** — lending-denial: qualified borrower denied → replayed (DENY) → fix verified (APPROVE, mitigated) → certified (pom-cert-v1, signature valid)
2. **inc-000002** — support-handoff: customer handoff failed → replayed → fix verified (mitigated) → certified
3. **inc-000003** — prior-auth: auto-denied → replayed → not yet fix-verified
4. **inc-000004** — hiring-screen: rejection captured → replayed → no fix yet
5. **inc-000005** — complaint-escalation: missing escalation → captured, needs replay

**Every seeded object must carry:**
- `is_demo: true` flag in the response
- Visible DEMO badge in the UI
- "Seeded demo [object] — not a real [object]" tooltip

**Backend data needed:** Seed script to create 5 demo incidents programmatically

**New endpoints:**
- `POST /v1/platform/seed-demo` — creates or refreshes 5 demo incidents via the proof-loop

**Related WOs:** WO-48 (IA + demo org)

---

## 14. API summary

### Existing endpoints (usable as-is)
| Endpoint | Method | Used by |
|---|---|---|
| `/v1/incidents` | GET | Incidents, Proofs |
| `/v1/incidents/{id}` | GET | Investigation |
| `/v1/incidents/{id}/snapshot` | GET | Investigation |
| `/v1/incidents/{id}/replay` | GET, POST | Investigation, Replay |
| `/v1/incidents/{id}/mutation-tests` | GET, POST | Investigation, Replay |
| `/v1/incidents/{id}/certificates` | POST | Investigation, Proofs |
| `/v1/incidents/{id}/certificates/pom-cert-v1` | GET | Proofs, Investigation |
| `/v1/incidents/{id}/certificates/pom-cert-v1/verify` | GET | Proofs |
| `/v1/incidents/{id}/certificates/pom-cert-v1/download` | GET | Proofs |
| `/v1/platform/org` | GET | Home, Settings |
| `/v1/platform/org/environments` | GET | Home, Settings |
| `/v1/platform/org/agents` | GET | Agents, Home, Onboarding |
| `/v1/platform/org/systems` | GET | Systems, Home |
| `/v1/platform/org/policies` | GET | Capture |
| `/v1/platform/home` | GET | Home |

### New endpoints needed
| Endpoint | Method | Purpose | Module |
|---|---|---|---|
| `/v1/platform/home/recent-proofs` | GET | Last 5 certificates | Home |
| `/v1/platform/home/setup-health` | GET | SDK/system/agent booleans | Home |
| `/v1/platform/onboarding/test-capture` | POST | Demo snapshot | Onboarding |
| `/v1/platform/org/agents` | POST | Register agent | Agents |
| `/v1/platform/agents/{id}/test-capture` | POST | Agent-specific capture | Agents |
| `/v1/platform/agents/{id}/details` | GET | Agent profile + links | Agents |
| `/v1/platform/org/systems` | POST | Add connection | Systems |
| `/v1/platform/systems/{id}/test` | POST | Test connection | Systems |
| `/v1/platform/systems/{id}` | PUT | Update connection | Systems |
| `/v1/platform/org/policies` | POST | Create policy | Capture |
| `/v1/platform/policies/{id}` | PUT | Update policy | Capture |
| `/v1/platform/policies/{id}` | DELETE | Archive policy | Capture |
| `/v1/platform/policies/{id}/preview` | GET | Field preview | Capture |
| `/v1/incidents/{id}/assign` | POST | Set owner | Incidents |
| `/v1/incidents/{id}/replay-readiness` | GET | Cassette/sandbox info | Replay |
| `/v1/incidents/{id}/promote-to-scenario` | POST | → 501 planned | Incidents, Scenarios |
| `/v1/platform/scenarios` | GET | Seeded scenarios | Scenarios |
| `/v1/platform/seed-demo` | POST | Create 5 demo incidents | Demo org |

---

## 15. Build plan

### Batch 1: Home + Demo org (first to build)
- Extend `/v1/platform/home` endpoint with recent proofs, blockers, setup health
- Add `POST /v1/platform/seed-demo` to create 5 demo incidents via proof-loop
- Rebuild Home UI with setup health card, active queues, recent proofs list, blockers, next action
- Add DEMO badge and "Demo data — not production" banner
- All cross-cutting states (loading/empty/error/disabled)

### Batch 2: Incidents + Investigation (highest user value)
- Extend `/v1/incidents` response with agent_name, decision_type, next_action
- Build Incidents queue with filters, pagination, inline actions, expandable detail
- Build Investigation module: timeline, evidence, replay, fix verification, proof, custody chain
- Leverage all existing proof-loop endpoints

### Batch 3: Agents + Onboarding
- Extend agent endpoints with linked counts
- Build Agents table with detail drawer, filters, row actions
- Build Onboarding checklist with test capture

### Batch 4: Proofs + Replay & Verification
- Build Proofs table with certificate detail panel, verify, download
- Build Replay & Verification workflow screen

### Batch 5: Systems + Capture
- Build Systems table with detail drawer, Test Connection
- Build Capture policies with create/edit/preview

### Batch 6: Scenarios + Governance + Settings (scaffolds)
- Scenarios: seeded table + planned banner
- Governance: static informational cards
- Settings: org live + planned cards

---

## 16. WO mapping

| WO | Module | Batch | Status |
|---|---|---|---|
| 48 | IA, object model, demo org | 1 | In progress |
| 49 | Shell + Home | 1 | In progress |
| 50 | Onboarding + Agents | 3 | Not started |
| 51 | Systems + Capture | 5 | Not started |
| 52 | Incidents + Investigation | 2 | Not started |
| 53 | Replay + Proofs | 4 | Not started |
| 54 | Scenarios, Governance, Settings | 6 | Not started |
