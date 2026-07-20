# Platform Reconciliation — Implementation Plan

> Plan for the code agent. Compact/refine as you execute; keep the P0/P1/P2 order
> and the acceptance criteria. Each item lists the concrete files/lines found at
> platform HEAD `91727de`.

## Context & goal

The platform is "demoable with careful narration," not yet a solid working
platform. Several UI flows sit over simulated or contradictory state. The goal of
this work is to remove invented/contradictory state and make the UI reflect real
server state, so the interactive Harborline workflow (capture → replay → fix →
proof → release gate) is truthful when clicked through live.

**Guiding principle:** the server is the source of truth. The browser must never
hard-code an expected outcome, invent a root hash, fabricate replay execution
events, or present an action as available when the server has not said it is.

**Constraints**
- Do not regress the seeded golden path (backend preflight must keep passing).
- Keep proof claims scenario-scoped; do not introduce general-safety claims.
- Make minimal, focused changes; follow existing code style.
- Frontend is vanilla JS (`static/app/app.js` + `components.js`); backend is
  FastAPI (`src/notary_platform/**`). API base is the literal `/v1` prefix.

## Verification commands (run before finishing)

```
cd notary-platform
make install            # first time only (creates .venv, installs .[dev])
.venv/bin/ruff check .
.venv/bin/mypy src
.venv/bin/pytest -q --ignore=tests/test_ui_vertical.py
make topology           # CI also runs this
# Manual/API smoke of the changed flows (capture -> replay -> verify -> proof -> gate)
```

CI = `ruff check .` + `mypy src` + `make topology` + `pytest -q --ignore=tests/test_ui_vertical.py`.

---

## P0 — must fix before any serious demo

### P0-1. Remove hard-coded `APPROVE` expected outcome
The single highest-risk defect: it contradicts the Harborline demo
(`UNDERWRITING_REVIEW`) and can make the manual fix/proof path fail even though
the seeded preflight passes.

- Frontend callers hard-code the payload:
  - `static/app/app.js:1262-1267` (`runVRMutation`) → POST
    `/v1/verification-records/{id}/mutation-tests` with
    `expected_correct_behavior: "APPROVE"`.
  - `static/app/app.js:1477-1479` (`runIncidentVerify`) → POST
    `/v1/incidents/{id}/mutation-tests` with `expected_correct_behavior: "APPROVE"`.
  - `static/app/app.js:1147` Add-Label placeholder `"e.g. APPROVE"` (cosmetic;
    update to a realistic example, e.g. `UNDERWRITING_REVIEW`).
- Backend defaults that also say `APPROVE`:
  - `routers/certificates.py:34` (`MutationRequest.expected_correct_behavior` default).
  - `replay_engine/mutation.py:15` (`run_mutation(...)` default).
  - `routers/platform.py:309, 321`; `demo_catalog.py:519, 531`;
    `routers/dashboard.py:460`.
- Canonical correct value: `demo_scenarios.py:139`
  (`expected_correct_behavior="UNDERWRITING_REVIEW"` for `lending-denial`).

**Change:** the expected outcome must come from the approved label / server
workflow, never from the browser.
- Frontend: stop sending `expected_correct_behavior` from `runVRMutation` and
  `runIncidentVerify`; let the server resolve it from the VR/incident's approved
  label (fall back to the workflow's canonical value).
- Backend: make the server derive the expected outcome from the approved label
  for the record/incident; only fall back to the scenario's canonical value
  (e.g. `UNDERWRITING_REVIEW` for `lending-denial`) when no label exists.
  Remove the bare `"APPROVE"` default in favor of label/workflow resolution.

**Acceptance**
- [ ] Manually clicking "Verify Fix" on the Harborline incident tests
      `UNDERWRITING_REVIEW`, not `APPROVE`, and passes after the fix.
- [ ] No `expected_correct_behavior: "APPROVE"` literal remains in frontend or in
      the Harborline/lending path.
- [ ] Existing preflight tests still pass (`tests/test_release_gate_vertical.py:211`).

### P0-2. Gate "Issue Proof" by server-side eligibility
- `static/app/app.js:1455` renders "Issue Proof" whenever `!cert.certificate_id`
  — even before fix verification succeeded.
- Server already enforces eligibility:
  - `routers/certificates.py:85-99` returns 409 with explanations.
  - `routers/release_gate.py:99-102` → `GET /v1/verification-records/{id}/eligibility/{action}`
    backed by `services/services.py:1373-1445` (`issue_proof` at 1414-1436
    returns `eligible/reason/next_action`).
  - `routers/incidents.py:109` workflow endpoint returns `can_issue_proof`.

**Change:** on the Incident detail page, query eligibility (workflow
`can_issue_proof` or the eligibility endpoint) and render the button
**disabled** until eligible, showing the missing prerequisite (`reason` /
`next_action`) beside it. Do not rely only on the 409 after the fact.

**Acceptance**
- [ ] "Issue Proof" is disabled with a visible prerequisite until the server
      reports eligible; enabled only when eligible.
- [ ] Triggering it when not eligible is not possible from the UI.

### P0-3. Replace fake root hash with server evidence (Test Capture)
- `static/app/app.js:688` builds `root_hash: "demo-harborline-root-" + Date.now()`
  and POSTs to legacy `/v1/incidents/ingest` (`app.js:690`), then displays it as
  a sealed root hash (`app.js:724, 735`). Same pattern in `sendSDKTestCapture()`
  (`app.js:864, 866`).
- Real endpoint: `routers/verification.py:72-85`
  `POST /v1/verification-records/from-snapshot` →
  `IngestionService.create_from_sdk_snapshot` (`services/services.py:187-216`)
  returns `vr.to_dict()` with real `id` and `root_hash`
  (`models.py:444-454`; `_compute_root_hash` in `snapshot.py:108`).

**Change:** Test Capture must POST to `/v1/verification-records/from-snapshot`,
display the **returned** `root_hash`, and link to the resulting Verification
Record. Remove the timestamp-string "seal." Apply to both Harborline and SDK
test-capture flows.

**Acceptance**
- [ ] Test Capture shows the server-returned root hash and links to the created VR.
- [ ] No `demo-...-root-`/Date.now() or `"demo-root-hash"` literal is presented as a seal.

### P0-4. Derive Setup readiness from real returned state
- `renderSetupReadinessStep()` `app.js:742-751` hard-codes all six checklist items
  `ok: true` even without a successful test capture.
- Setup otherwise saves nothing (see P1-1).

**Change:** readiness checklist items must reflect actual returned state (e.g.
test capture succeeded → VR id present; adapters reachable; label approved). At
minimum, the "test capture" item is green only after a real capture returns a VR
id; unmet items show as pending/blocked, not green.

**Acceptance**
- [ ] Readiness is not all-green on first load; it turns green only from real
      returned state.

### P0-5. Fix environment scoping or lock UI to Demo
- `apiGet` `app.js:42-55` appends `?environment_id=<S.env>`; `apiPost`
  (`app.js:57-74`), `apiPostForm` (`76-79`), `apiPatch` (`81-93`) do not.
- Selector `index.html:27-31` offers Demo/Staging/Production; backend POSTs fall
  back to `env:demo` default (`release_gate.py:293, 333, 388, 422`).

**Change (choose one, prefer A for this demo release):**
- **A.** Lock the UI to Demo: remove/disable Staging and Production until
  isolation is correct; make the selector read-only "Demo".
- **B.** Thread `environment_id` consistently through every POST/PATCH (body or
  query per backend contract) so mutations follow the selection.

**Acceptance**
- [ ] Either mutations honor the selected environment, or only Demo is selectable
      and clearly indicated.

### P0-6. Resolve Release Gate active/planned contradiction
- Settings shows `renderDisabledAction("CI/CD Release Gate", "Planned")`
  (`app.js:2086`) while Readiness provides an active Release Gate button
  (`app.js:1853`), trigger (`app.js:1934-1943`), result page
  (`app.js:1977-2010`), and backend (`release_gate.py:418-437`).

**Change:** make the capability status consistent. Release Gate is active in the
app — update Settings to reflect the actual state (and if the *CI/CD delivery*
piece specifically is planned, label that precisely rather than the whole
feature). Also fix the badge misuse in P1-6 while here.

**Acceptance**
- [ ] No screen labels an active feature "Planned" while another exposes it as active.

### P0-7. Align organization identity (Acme vs Harborline)
- `platform_data.py:18-19` → `Organization(id="org:acme-demo", name="Acme Assurance Demo")`,
  served by `GET /v1/platform/org` (`platform.py:36-39`) and Home stats (`platform.py:215`).
- Frontend Home `#org-name` from `h.org_id` (`app.js:285`); Settings hard-codes
  "Acme Assurance Demo" / "org:acme-demo" (`app.js:2079-2082`), while the demo
  workflow is Harborline (`app.js:385, 579`).

**Change:** pick one coherent identity for the demo org and use it everywhere.
Settings must render org name/id from `/v1/platform/org`, not hard-coded strings.
Decide whether the org is Harborline (and the workflow a Harborline workflow) or
a neutral "demo org" label; keep it consistent across Home, Settings, Proof.

**Acceptance**
- [ ] Home, Settings, and Proof show one consistent organization identity sourced
      from the server.

---

## P1 — make it feel like a working platform

### P1-1. Make Setup selections real and persistent
Largest product-depth gap. All in `static/app/app.js`:
- Workflow preselected/unchangeable: `renderSetupWorkflowStep()` `app.js:572-596`.
- Evidence-system cards not selectable: `renderSetupSystemsStep()` `app.js:632-652`.
- required/optional/excluded hard-coded: `SETUP_SYSTEMS` `app.js:443-514`.
- Capture method not persisted: `SETUP_CAPTURE_METHODS` `app.js:516-549`,
  `renderSetupCaptureStep()` `app.js:654-671`.
- "Next" always enabled: `renderSetupNav(step, canNext=true)` `app.js:564-570`,
  called without `canNext` at `app.js:790`.
- No org config saved; only call is `apiGet("/v1/platform/adapters")` (`app.js:795`).

**Change:** make selections interactive (click handlers), persist them (state `S`
and a backend POST so choices survive reload), gate "Next" on the current step
being satisfied, and derive tiers/status from real adapter data where possible.
If a backend setup/config endpoint does not exist, add a minimal one rather than
faking persistence in the browser.

**Acceptance**
- [ ] Workflow/systems/capture selections are selectable, persist across reload,
      and "Next" is disabled until the step is satisfied.

### P1-2. Persisted replay runs and execution events
- `runIncidentReplay()` `app.js:1467-1475` awaits POST then toasts "Replay
  completed" and reloads.
- Frontend-fabricated trace: `app.js:1383-1389`, `1403-1411`.
- Backend replay endpoints exist (`incidents.py:35-57`; `release_gate.py:114-137`;
  engine `replay_engine/replay.py:36-70`, `worker.py:11-21`) but `ReplayRun`
  (`models.py:696-728`) stores only status/decisions/missing_calls/limitations —
  **no per-step execution events and no run-state/events endpoint exists.**

**Change:** add persisted replay-run execution events (queued → loading sealed
cassette → restoring applicant input → matching recorded bureau request →
returning cassette response → loading policy version → reconstructing decision →
comparing original and replayed outcomes → reproduced/diverged/errored). Emit
them from the replay engine, persist on the run, expose via a run-status/events
endpoint (poll by run id), and render the trace from returned events — not
invented by the UI. (Streaming/websocket optional; polling is acceptable.)

**Acceptance**
- [ ] Replay shows a live run state and the trace rows come from persisted
      backend events, not from the presence of a replay result.

### P1-3. Render Verification Record evidence visually
- "Event Timeline" maps events to flat KV rows with
  `JSON.stringify(e.payload).substring(0, 120)` (`app.js:1064-1071`), despite
  events carrying `kind`, `order`, `source_system` (`models.py:453`).

**Change:** render a Decision Evidence Graph (typed nodes/edges by `kind`, ordered
by `order`, grouped by `source_system`), not truncated raw JSON.

**Acceptance**
- [ ] VR detail shows a structured evidence graph instead of truncated JSON blobs.

### P1-4. Make incident→scenario promotion an explicit action
- Detail-page "Promote to Scenario" just runs `nav('scenarios')`
  (`app.js:1456`, also `1450`).
- Real endpoints: `release_gate.py:225-232`
  (`POST /v1/scenario-candidates/{candidate_id}/promote`) and
  `release_gate.py:240-249` (`POST /v1/scenarios` with `vr_id` **query** param).
- Note a second bug: `promoteVRToScenario()` (`app.js:1285-1294`) sends `vr_id`
  in the JSON **body**, which the query-param endpoint ignores → would 400.

**Change:** wire promotion to the real endpoint, show a confirm + success/error
result, and fix the `vr_id` query-vs-body mismatch.

**Acceptance**
- [ ] Promoting executes the promotion call, reports the outcome, and the new
      scenario appears in the library.

### P1-5. Generalize Proof Detail from certificate data
- Hard-coded workflow string `app.js:1559` ("Harborline Credit Union
  personal-loan adverse-action") regardless of the certificate.
- Limitations default `"None documented"` (`app.js:1571`; PDF exporter also
  `certificates.py:251`).

**Change:** render decision workflow, parties, and limitations from the
certificate/VR data. Absence of returned limitations must NOT be presented as
evidence that none exist — show "Not documented" (or omit) rather than implying
"none."

**Acceptance**
- [ ] Proof Detail is driven by certificate/VR data; "None documented" is not
      shown as if it were verified fact.

### P1-6. Distinguish gate fail from system error; fix badges
- `triggerReleaseGate()` `app.js:1937` toasts `fail` as an error; same at
  `app.js:1926`. Backend distinguishes pass/fail/error with `error_code`/
  `retry_guidance` (`services.py:1315-1356`).
- Policy version uses `badge-planned` styling (`app.js:1846`).
- Home golden path mislabels certificate id as "Root hash" (`app.js:347`).

**Change:** render `fail` as a valid business verdict (distinct styling from
`error`); only `error` is a system error. Use active styling for an active policy
version. On Home, show the real root hash (from the VR, per P0-3) instead of the
certificate id, or relabel the field correctly.

**Acceptance**
- [ ] Gate `fail` and `error` are visually/semantically distinct; policy version
      is not styled "planned"; Home no longer labels a certificate id as a root hash.

---

## P2 — polish

### P2-1. Compress Incident Detail into staged sections
Convert the long page into a sticky top workflow with sections/tabs:
**Evidence → Replay → Fix → Proof → Release Gate.** The top summary always shows:
workflow, original decision, expected outcome, current stage, next available
action, exact blocker. (`app.js:1357+`.)

### P2-2. Golden-path status coloring
Home golden-path panel uses green borders for every seeded stage. Use state
colors: blue captured/running; red failure reproduced/gate blocked; amber
review/prerequisite required; green fix verified/proof issued/gate passed; grey
not started.

### P2-3. Replace mixed emoji/text nav icons with the icon set or consistent text.

### P2-4. Mask API tokens
Tokens stored in localStorage (`app.js:15, 166-172, 2096-2103`) and shown in
plaintext (`app.js:159, 803, 2066, 848`). Mask by default with Copy/Reveal
controls.

### P2-5. Banner text
`index.html:36` and `app.js:303` say "design partner preview." Change to:
**"Fictional demo data — no production or customer data."**

### P2-6. Update living guide + release manifest after behavior is fixed
- `docs/demo/demo-release-manifest.md` claims canonical but lists platform main
  `a3fcb10` (current `91727de`) at line 14, stale website/live status at
  lines 16 & 96-104, against its own procedure (lines 147-155).
- Reconcile SHAs and live status **after** the behavior changes land.

---

## Out of scope
- New product features beyond the listed reconciliation.
- Real production GRC integrations (remain "planned").
- Website (`GetNotary.ai`) changes — handled by a separate work order.

## Open questions for the code agent to resolve
1. Expected-outcome resolution order (P0-1): approved label → scenario canonical
   value → error if neither? Confirm intended precedence.
2. Setup persistence (P1-1): is there an existing org-config/setup endpoint to
   reuse, or should a minimal one be added?
3. Replay events (P1-2): polling by run id acceptable for this release, or is
   streaming required?
4. Environment (P0-5): lock to Demo now (recommended) vs. threading
   `environment_id` through mutations — confirm which for this release.
5. Org identity (P0-7): Harborline-as-org vs. neutral demo org label — confirm
   the single identity to standardize on.
