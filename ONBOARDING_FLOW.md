# Customer Onboarding Flow

When a customer connects a system, here's where the data goes and how frontend ↔ backend interact.

---

## 1. Customer lands at the platform

```
Browser → GET / → 302 → /app/ → FastAPI serves static/app/index.html
```

The SPA loads `app.js` and calls `GET /v1/platform/home` to get org stats, environment list, setup health, and next-action hints. The environment selector now shows available environments (Demo, Staging, Production) loaded from the API response.

**Files:** `index.html`, `app.js` (init → `loadEnvironments()`), `main.py` (static mount), `routers/platform.py:110` (`get_home`)

---

## 2. Customer clicks "Setup" or "Connect your systems"

```
SPA nav('setup') → renders Setup view from renderSetup(step)
```

The setup wizard has steps:

| Step | Frontend | Backend |
|------|----------|---------|
| 1. SDK Install | Shows `pip install notary-sdk` code snippet, API token | `GET /v1/platform/keys` lists keys |
| 2. Connect systems | Renders available systems from `_SEED` + selection UI | `GET /v1/platform/org/systems` returns systems |
| 3. Capture method | Radio buttons (SDK .submit / Webhook / Manual) | — |
| 4. Workflow confirmation | Visual flow of data lifecycle | — |
| 5. Done | Redirects to Verification Records | — |

**Caveat:** The setup wizard is a demo facade — it doesn't actually install SDKs or connect real systems. It sets `setupSystems` and `setupCaptureMethod` in `S` (in-memory JS state) but doesn't persist. Real onboarding would POST to a backend endpoint.

**Files:** `app.js:510-660` (setup wizard functions), `routers/platform.py:60` (`get_systems`)

---

## 3. SDK captures a decision

The customer instruments their AI agent with the Python SDK:

```python
from notary_sdk import RunCapture

capture = RunCapture(token="ntry-demo-...")
capture.capture_input(text="Can I get a bereavement refund?")
capture.capture_tool(method="GET", url="/policy-api", response={"allowed": False})
capture.capture_decision(decision="OFFER_REFUND")
capture.finalize()  # calls POST /v1/verification-records/from-snapshot
```

### Data flow

```
SDK (customer's system)
  │  POST /v1/verification-records/from-snapshot
  │  Content-Type: application/json
  │  Body: { snapshot: { elements: [...], root_hash: "0x..." } }
  ▼
FastAPI (verification router)
  │  1. Verifies snapshot integrity
  │  2. Creates VerificationRecord in storage
  │  3. Records custody: "ingested from SDK"
  ▼
Storage (in-memory by default, Postgres+S3 if configured)
```

**File:** `routers/verification.py:72` (`from_snapshot`)

### What gets stored

```
VerificationRecord {
  id: "vr-abc123",
  org_id: "org:harborline-demo",
  environment_id: "env:demo",
  source_system_id: "customer-system",
  agent_id: "agent:bereavement-bot",
  replayability: "replayable",
  elements: [
    { kind: "input", payload: { ... } },
    { kind: "http", payload: { request, response } },
    { kind: "decision", payload: { decision: "OFFER_REFUND" } }
  ],
  custody: [
    { timestamp: "...", action: "ingested", actor: "SDK" }
  ]
}
```

**Caveat:** The VerficationRecord is the core forensic object. Every subsequent action (replay, mutation, proof) references it. Without a VR, nothing else works.

---

## 4. Customer browses Verification Records

### Flow

```
SPA nav('verification-records')
  │  GET /v1/verification-records?environment_id=env:demo
  ▼
FastAPI → storage.list_vrs() → returns list of VRs
  │  Response: [{ id, source_system_id, agent_id, replayability, ... }]
  ▼
SPA renders table with columns: VR ID, Source System, Agent, Replayability, Status, Actions
```

**File:** `app.js` (`renderVerificationRecords()`), `routers/verification.py:88` (`list_vrs`)

### Clicking a VR

```
SPA GET /v1/verification-records/{vr_id}
  → renders detail view with evidence elements, metadata, replayability
  → shows available actions based on eligibility:
    GET /v1/verification-records/{vr_id}/eligibility/replay
    GET /v1/verification-records/{vr_id}/eligibility/issue_proof
```

Eligibility is server-computed and tells the frontend what buttons to enable/disable with reasons.

**Files:** `routers/release_gate.py:106` (`eligibility_check`), `app.js` (`renderVRDetail()`)

---

## 5. Customer replays a VR

### Flow

```
SPA clicks "Run Replay"
  │  POST /v1/verification-records/{vr_id}/replay-runs
  ▼
FastAPI → ReplayRun created
  │  → DemoReplayRunner replays the cassette
  │  → compares replayed decisions against captured decisions
  │  → stores events (step-by-step execution trace)
  ▼
SPA polls: GET /v1/replay-runs/{run_id}/events
  → renders timeline with each event's status (pass/fail/error)
```

**Files:** `routers/release_gate.py:121` (`create_replay_run`), `services/services.py` (`ReplayService`)

### What gets created

```
ReplayRun {
  id: "rr-abc",
  vr_id: "vr-abc123",
  replay_status: "replayed",
  decision: "DENY",                    // what the AI decided
  events: [
    { step: "lookup_policy", status: "pass" },
    { step: "apply_decision", status: "pass", expected: "ESCALATE_TO_HUMAN", actual: "DENY" }
  ]
}
```

**Caveat:** Demo VRs use `DemoReplayRunner` which knows the expected outcomes. Production replay requires a custom `ReplayRunner` implementation registered via `ServiceRegistry`.

---

## 6. Customer verifies a fix (Mutation Test)

### Flow

```
SPA clicks "Verify Fix"
  │  POST /v1/verification-records/{vr_id}/mutation-tests
  │  Body: { fix_config: { ... }, expected_correct_behavior: "UNDERWRITING_REVIEW" }
  ▼
FastAPI → MutationTest created
  │  → applies fix_config to the replay
  │  → checks if mutated decision matches expected_correct_behavior
  ▼
SPA re-renders detail with before/after comparison
  → shows "Blocked before fix: DENY → Pass after fix: UNDERWRITING_REVIEW"
```

**Files:** `routers/release_gate.py:157` (`create_mutation_test`)

### What gets created

```
MutationTest {
  vr_id: "vr-abc123",
  original_decision: "DENY",
  mutated_decision: "UNDERWRITING_REVIEW",
  expected_correct_behavior: "UNDERWRITING_REVIEW",
  mitigated: true,
  verdict: "verified",
  fix_config: { "require_bureau_evidence": true }
}
```

**Caveat:** Mutation tests use the same `DemoReplayRunner` in demo mode. The `fix_config` is scenario-specific and must match what the runner understands. Currently only `threshold` (for lending) and `require_policy_match_for_refund_claims` (for bereavement) are supported.

---

## 7. Customer issues a Proof of Mitigation

### Flow

```
SPA clicks "Issue Proof"
  │  POST /v1/verification-records/{vr_id}/proof-of-mitigation
  ▼
FastAPI → Certificate generated
  │  → signed with HMAC-SHA256 (dev) or KMS (prod)
  │  → includes: incident_id, original decision, mutated decision, root hash
  │  → stores: certificate_id, replay_method, claim_scope, limitations
  ▼
SPA shows proof with Download JSON/PDF buttons
  → can verify signature: GET /v1/incidents/{id}/certificates/{cert_id}/verify
```

**Files:** `routers/release_gate.py:188` (`proof_of_mitigation`), `certificates.py`

### What gets created

```
Certificate {
  certificate_id: "cert-abc",
  schema_version: "pom-v1",
  incident_id: "inc-abc",
  root_hash: "0xabcd...",
  replay_method: "sealed cassette replay",
  claim_scope: "Verified fix for this tested scenario under recorded conditions...",
  known_limitations: "Does not certify general AI safety",
  signature: "0x...",
  signing_algorithm: "HMAC-SHA256"
}
```

**Caveat:** Dev signatures use HMAC-SHA256 (symmetric, not independently verifiable). Prod uses KMS `ENCRYPT_DECRYPT` (still server-verifiable only). Neither is a public-key signature. The certificate is tamper-evident but cannot be verified by third parties without access to the same key.

---

## 8. Customer promotes to Scenario

### Flow

```
SPA clicks "Promote to Scenario"
  │  POST /v1/scenarios?vr_id={vr_id}
  ▼
FastAPI → promotes VR + certificate to a reusable Scenario
  │  → stored in scenario library
  │  → can be executed against any agent version
```

**Files:** `routers/release_gate.py:247` (`create_scenario`)

---

## 9. Customer runs a Release Gate

### Flow

```
1. Create Readiness Policy: POST /v1/readiness-policies
   Body: { name: "Lending Gate", required_scenario_ids: ["sc-abc"] }

2. Run Readiness Check: POST /v1/readiness-checks
   Body: { policy_id: "pol-abc", agent_version: "1.2.0" }

3. Run Release Gate: POST /v1/release-gate/checks
   Body: { policy_id: "pol-abc", agent_version: "1.2.0" }
```

The release gate aggregates scenario run results and returns pass/fail. If all required scenarios pass against the agent version, the gate passes.

**Files:** `routers/release_gate.py:346-449` (policies, checks, gate)

---

## End-to-end data relationship

```
SDK Capture ──→ VerificationRecord ──→ ReplayRun ──→ MutationTest ──→ Certificate
                      │                                                    │
                      │                                                    ▼
                      │                                              Proof of Mitigation
                      │                                                    │
                      ▼                                                    ▼
                 Promote ──→ Scenario ──→ ScenarioRun
                                            │
                                            ▼
                                   ReadinessPolicy ←─── ReadinessCheck
                                            │
                                            ▼
                                     ReleaseGateResult
```

## All API calls from frontend

All 23 API endpoints used by the frontend have matching backend routes.

## Key caveats

| Area | Caveat |
|------|--------|
| Demo data | Demo VRs are marked `is_demo=True`. Their replayability may be force-set for storytelling. Computed replayability is separate. |
| Replay runner | Demo mode uses `DemoReplayRunner`. Custom runners needed for real data. |
| Mutation fix_config | Currently only supports `threshold` (lending) and `require_policy_match_for_refund_claims` (bereavement). |
| Certificate signing | HMAC-SHA256 locally, KMS in prod. Neither is public-key — not independently verifiable. |
| Storage | In-memory by default. Postgres+S3 requires `NOTARY_USE_REMOTE_STORAGE`. |
| Setup wizard | Demo facade — doesn't actually connect real systems. |
| Environment switching | Changes `environment_id` query param on API calls. Only affects API data scoping, not auth. |
