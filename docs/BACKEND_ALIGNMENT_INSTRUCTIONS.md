# Backend Alignment Instructions — make the API match the new frontend

**Audience:** the backend engineer/agent.
**Goal:** the `/app` SPA was rebuilt around a single narrative — **Northstar Air**, an airline
whose AI support bot invents a retroactive bereavement-refund policy (inspired by *Moffatt v.
Air Canada*, 2024). The backend already exposes nearly every endpoint the UI calls, but the
**seeded demo data is still the old lending story** and a couple of onboarding hooks are still
client-side. This doc tells you exactly what to change so the whole product tells one story.

> TL;DR: You mostly need to (1) re-theme the seed data from lending → Northstar support-bot,
> (2) expose a `POST /v1/demo/northstar/seed` (or re-point the existing seed), and (3) optionally
> wire two onboarding calls. No new architecture required.

---

## 1. How the app runs (unchanged)
- FastAPI package `notary_platform` serves the SPA at `/app` and the API at `/v1` on the **same
  origin**. Frontend calls are relative (`/v1/...`) — no CORS/base-URL config needed.
- Local dev: `make install && make run` → open `http://localhost:8000/app/`.
- Auth: when `NOTARY_API_AUTH_TOKEN` is unset, `/v1` auth is disabled. The SPA sends
  `Authorization: Bearer <token>` automatically when a token is set (Settings screen / `S.token`).
- Ignore `/frontend` and `/backend` at repo root — those were gitignored Emergent preview shims.

---

## 2. What the frontend now is (what you're matching)
Files: `static/app/index.html`, `app.js` (~3.6k lines), `components.js`, `styles.css`.

Navigation (left rail): **Home · Demo · Setup · Verification Records · Incidents · Proofs ·
Scenarios · Readiness · Governance · Evidence · Settings · About**.

Three things drive the current mismatch:

### (a) Home hero — Northstar story, no data dependency
`renderHome` / `renderHarborlineJourney` (function name is legacy; content is Northstar).
Shows the 6-step loop (Capture → Replay → Fix → Proof → Scenario → Gate) and CTAs
"Watch the full demo" (→ Demo view) and "Connect your systems" (→ Setup). The stat tiles + queues
DO read from `GET /v1/platform/home`.

### (b) Demo view — fully client-side narrative (no backend today)
`renderDemo` + `demo*` functions + constants `NORTHSTAR` and `NORTHSTAR_EVENTS` in `app.js`.
A 10-scene guided walkthrough. **This is the canonical data you should mirror in the backend.**

### (c) Setup view — system-first onboarding, partly simulated
`renderSetup` + `renderOnb*`. Steps: Register AI System → Evidence Sources → Instrument (SDK/API/
Webhook snippet) → Send First Record (live "waiting → received") → Replay Readiness.
`saveOnbSystem()` and `sendOnbTestRecord()` are **client-side stubs** (see §5).

---

## 3. Canonical Northstar dataset (mirror this exactly)
These values are hard-coded in `app.js` (`const NORTHSTAR`, `NORTHSTAR_EVENTS`). Seed the backend
so real objects use the same values — then the Demo and the list screens tell the identical story.

```
Company:            Northstar Air
Org id:             org:harborline-demo   (KEEP the id; display name is now "Northstar Air")
AI system:          Bereavement Support Bot
Buggy version:      support-bot-v42
Fixed version:      support-bot-v43
Model:              GPT-4o (Azure OpenAI)
Policy version:     bereavement-policy-v7
Source system:      Salesforce Service Cloud  (Case #50093821)
Release system:     GitHub Actions

Verification Record id:   vr-northstar-001
Proof of Mitigation id:   pom-northstar-7a3f
Proof of Readiness id:    por-northstar-91c2

Original decision:  OFFER_RETROACTIVE_REFUND   (wrong)
Expected outcome:   ESCALATE_TO_HUMAN          (human label / answer key)

Scenario name:      Bereavement refund policy misrepresentation
Readiness policy:   High-risk support policy gate   (3 required scenarios)
Release gate:       FAIL on support-bot-v42, PASS on support-bot-v43
```

**Sealed cassette events (the replay), in order:**
```
1. input   Customer message  — "My grandmother passed away. I already booked.
                                 Can I still get a bereavement fare refund?"
2. http    Policy lookup      — Bereavement Policy API →
                                 { retroactive_refund_allowed: false,
                                   human_review_required: true,
                                   policy_version: "bereavement-policy-v7" }
3. llm     Model call         — GPT-4o · prompt support-policy-prompt-v42 · temp 0 · seed 12345
4. decision Bot response      — "Yes, you can submit a refund request within 90 days."
5. decision Final decision    — OFFER_RETROACTIVE_REFUND
```

**Fix config (applied for v43):**
```json
{ "require_policy_match_for_refund_claims": true,
  "escalate_when_policy_requires_human_review": true }
```
Replay of the SAME cassette after the fix must yield `ESCALATE_TO_HUMAN`.

---

## 4. Endpoint status — what to change (the main work)
The frontend calls the endpoints below. **All already exist** in
`src/notary_platform/api_server/routers/`. The fix is the **data** they return.

### 4.1 Re-theme the seed data (highest priority)
The lending/Harborline story lives in these files:
- `src/notary_platform/platform_data.py`  (org, systems, agents, policies, home stats, queues)
- `src/notary_platform/demo_scenarios.py`  (the golden-path incident/replay/fix/proof/scenario)
- `src/notary_platform/demo_catalog.py`    (catalog seed used by `/v1/demo/catalog/seed`)
- `src/notary_platform/evidence_pack.py`   (rehearsal artifacts + calls preflight)
- `src/notary_platform/demo_preflight.py`  (preflight anchors — already points at "Northstar Air")

**Action:** replace the lending domain objects with the Northstar dataset from §3:
- `platform_data.py`: org display name is already "Northstar Air". Change the seeded **systems**
  from Loan Origination / Credit Bureau / Underwriting Policy / AI Decision Agent to:
  **Customer Support System (Salesforce Service Cloud), Policy Knowledge Source (Bereavement Policy
  API), Prompt/Policy Config, AI Support Agent (Bereavement Support Bot)**. Update agents/policies/
  home stat labels accordingly.
- `demo_scenarios.py`: rebuild the golden-path objects (Verification Record, replay run, mutation/
  fix test, Proof of Mitigation, Scenario, Release Gate before/after) using §3 values and the
  5-event cassette. Keep the SAME object relationships the UI already renders (see shapes in §6).

### 4.2 Seed endpoint naming
Frontend currently references `POST /v1/demo/harborline-release-gate/seed` (from the legacy
`seedHarborlineGoldenPath()` — still defined but not wired to a Home button anymore) and
`POST /v1/demo/catalog/seed`.

**Action (pick one):**
- **Preferred:** add `POST /v1/demo/northstar/seed` that seeds the full Northstar golden path
  (VR, incident, replay, proof, scenario, readiness policy, release-gate FAIL+PASS) and returns:
  ```json
  { "verification_record_id": "vr-northstar-001",
    "incident_id": "...", "scenario_id": "...",
    "proof_of_mitigation_certificate_id": "pom-northstar-7a3f",
    "release_gate_before_fix_id": "...", "release_gate_before_fix_status": "fail",
    "release_gate_after_fix_id": "...",  "release_gate_after_fix_status": "pass" }
  ```
  Then I (frontend) will re-point `seedHarborlineGoldenPath()` to it and re-add a "Load demo data"
  button. Tell me the final route name.
- **Or:** keep `POST /v1/demo/harborline-release-gate/seed` but make it seed Northstar data. The
  route string can stay (it's internal); only the payload/theme changes.

### 4.3 List endpoints must return the seeded Northstar objects
After seeding, these must return the Northstar records so the nav screens match the Demo:
```
GET /v1/verification-records            → [vr-northstar-001, ...]
GET /v1/verification-records/{id}       → full record (see §6.1)
GET /v1/incidents , /v1/incidents/{id}  → the bereavement incident + workflow
GET /v1/proofs , /v1/proofs/{id}        → pom-northstar-7a3f
GET /v1/scenarios , /v1/scenarios/{id}  → "Bereavement refund policy misrepresentation"
GET /v1/scenario-runs                   → fail on v42, pass on v43
GET /v1/readiness-policies , /readiness-checks → "High-risk support policy gate"
GET /v1/release-gate/checks/{id}        → FAIL (v42) and PASS (v43) results
GET /v1/replay-runs/{id} , /replay-runs/{id}/events → the 5-event cassette
GET /v1/platform/home                   → stat tiles + queues themed to support bot
```
No shape changes needed if you reuse the existing serializers — only the seeded values change.

---

## 5. Onboarding hooks still client-side (optional wiring)
In `app.js`, the Setup "Register" and "Send first record" steps are simulated. Backend endpoints
already exist; when you're ready, tell me and I'll switch the frontend from stub → real call.

| Frontend stub (app.js) | Currently does | Real endpoint to use |
|---|---|---|
| `saveOnbSystem()` | pushes an in-memory system + fake `ntry-…` token | `POST /v1/setup/ai-systems` → return `{system_id, ingest_token, endpoint}` |
| `sendOnbTestRecord()` | `setTimeout` then fakes a received VR | `POST /v1/verification-records/from-snapshot` (exists) + a poll on `GET /v1/verification-records` for "first record received" |

Ensure `POST /v1/setup/ai-systems` returns an **ingest token** and **endpoint** in its response so
the Instrument step can show a token-prefilled snippet. If it doesn't today, add those fields.

---

## 6. Data shapes the UI expects (so you don't guess)
These are the fields the current renderers read. Keep them present (extra fields are fine).

### 6.1 `GET /v1/verification-records/{id}`
```
id, root_hash, replayability ("replayable" | "pending"...), agent_id, business_function,
source_system_id, source_record_id, original_decision, expected_outcome, environment,
policy_version, created_at, events[] (kind: input|llm|http|policy|decision, payload{...})
```

### 6.2 `GET /v1/platform/home`
```
org_id, is_demo (bool), environment_id,
setup_health { sdk_installed, agent_count, system_count, ... },
stats/queues used by the tiles + "active queues" chips, next_action, recent_proofs[]
```
(The frontend maps `org_id` → "Northstar Air" via `friendlyOrg()`, so `org_id` can stay
`org:harborline-demo`.)

### 6.3 Release gate result `GET /v1/release-gate/checks/{id}`
```
result_id, release (e.g. "support-bot-v42"), verdict ("pass"|"fail"),
policy_name, required_scenarios[], passed, failed, errored,
failed_scenario, expected, actual, certificate_id (Proof of Readiness on pass)
```

### 6.4 Proof `GET /v1/proofs/{id}`
```
id (pom-…), scenario, source (case), replay_method ("sealed cassette"),
original_decision, fixed_decision, expected_outcome, fix_reference (support-bot-v43),
claim_scope, known_limitations, signature/seal
```

---

## 7. Naming notes
- Visible "Harborline"/"Meridian" have been replaced by "Northstar Air" in the UI. Backend org id
  stays `org:harborline-demo`; only the display name changed (already "Northstar Air" in
  `platform_data.py`).
- `demo_preflight.py` presenter anchor now checks the app.js contains `"Northstar Air"`,
  `"From AI failure to release gate"`, `"ESCALATE_TO_HUMAN"`. Keep these strings if you edit the UI.
- Legacy, now-unreachable frontend functions (`renderSetupWorkflowStep`, `sendHarborlineTestCapture`,
  the seeded lending branch in `renderHarborlineJourney`) still contain "Meridian"/lending strings.
  Safe to ignore; they don't render. I can prune them on request.

---

## 8. Tests
- `tests/test_platform_static_app.py` — updated to assert Northstar strings. Keep green.
- `tests/test_demo_preflight.py`, `tests/test_evidence_pack.py` — will need their expected values
  updated when you re-theme the seed data to Northstar.
- `tests/test_ui_vertical.py` — needs `pytest-playwright` + a running server (pre-existing env gap;
  4 errors are unrelated to these changes).
Run: `python -m pytest -q`.

---

## 9. Suggested order of work
1. Re-theme `platform_data.py` systems/agents/policies/home to the support-bot domain (§4.1).
2. Rebuild `demo_scenarios.py` golden path to Northstar using §3 values + the 5-event cassette.
3. Expose `POST /v1/demo/northstar/seed` (or re-theme the harborline seed) returning §4.2 shape.
4. Verify list endpoints return the seeded Northstar objects (§4.3).
5. Update `demo_preflight` / `evidence_pack` expected values; fix tests (§8).
6. (Optional) Tell frontend to wire `saveOnbSystem` / `sendOnbTestRecord` to real endpoints (§5).
7. Ping me with final seed route name + confirmation, and I'll flip the frontend hooks and re-add
   the "Load demo data" affordance so nav screens light up with the Northstar story.
