# Demo Implementation Plan — AI Decision Assurance Panes

Work order scope: platform + SDK + website. Command Center deferred.
Goal: make the platform demo feel like a working AI Decision Assurance product.

---

## 1. Current State Audit (main SHAs: platform b0d1618, sdk 59280be, website 385d452)

### Already on main
| Capability | Status | Notes |
|------------|--------|-------|
| CI fixed | ✅ | Ruff I001 fixed, pytest 126 passed, SDK/website checks green. |
| Release manifest + dev/deploy framework | ✅ | `docs/demo/demo-release-manifest.md`, `docs/dev-deploy-framework.md`, `infra/deploy-api.sh`. |
| Investigation console UI | ✅ | Merged from `codex/incident-investigation-console`. Incident detail now shows: captured decision path, replay trace, before/after fix, proof section, scenario promotion, release-gate impact. |
| Live deploy | ✅ | `api.getnotary.ai` is on task-def `notary-dev-api:51`, `getnotary.ai` is current. |

### Missing / shallow on main
| Capability | Status | Gap |
|------------|--------|-----|
| Harborline seed reliability | ❌ P0 | Live seed 500s with `ModuleNotFoundError: No module named 'boto3'`. Production image built without `[cloud]` extra. |
| Setup guided flow | ⚠️ P1 | `renderSetup` exists but shows only API token + generic cards. No decision workflow, boundary, systems, capture method, test capture, or replay checklist. |
| Home golden path | ⚠️ P1 | `renderHome` has golden-path banner, but the bottom cards are not clickable and do not show concrete proof-journey state. |
| Incidents proof click | ⚠️ P1 | Certificates now return 409 for missing prereq, but production signing fails because boto3 missing. Once P0 is fixed, proof click should work. |
| Proofs page | ⚠️ P1 | `renderProofs` exists; needs verification after P0 fix. May need bounded-claim labels. |
| Verification Records depth | ⚠️ P2 | `renderVRs` exists; rows need to explain capture layer and be clickable. |
| Website alignment | ⚠️ P2 | Minor copy alignment if platform language changes. |
| Living guide | ⚠️ P2 | `notary-demo-non-technical-guide.md` needs updating to match new UI. |

### Relevant branches
- `codex/incident-investigation-console` — already merged to main (c0c15ea). No other pending branches are known to contain scoped demo UI improvements.
- No merge conflicts expected for Setup/Home/Proofs/VRs work; those pages are not under active development elsewhere.

### Deploy risks
- **P0 blocker:** Production image lacks `boto3`/`sqlalchemy`/`psycopg2` because the deploy script builds with `INSTALL_CLOUD=0` default. The ECS task sets `NOTARY_KMS_KEY_ARN` and DB secrets, so it expects cloud extras.
- Risk of scope creep: redesigning Command Center (`static/cc`) or broad platform refactors. Must stay on `static/app/app.js` only.
- Risk of product-claim expansion: language must remain bounded to AI Decision Assurance, not process mining.

---

## 2. P0: Fix Harborline Seed Failure — DONE ✅

### Root cause (confirmed from CloudWatch)
```
File "/app/src/notary_platform/services/services.py", line 930, in issue_proof_of_mitigation
  signed_dict = generate_certificate(...)
File "/app/src/notary_platform/certificates.py", line 54, in _sign
  import boto3
ModuleNotFoundError: No module named 'boto3'
```

The seed endpoint creates a proof-of-mitigation certificate. Signing in production requires `boto3` for KMS. The Dockerfile installs `[cloud]` only when `INSTALL_CLOUD=1`; the deploy script does not set that build arg.

### Fix
1. Update `infra/deploy-api.sh` to build with `--build-arg INSTALL_CLOUD=1`.
2. Re-run `bash infra/deploy-api.sh` (from clean origin/main).
3. Verify the seed now returns 200 (not 500) against `https://api.getnotary.ai/v1/demo/harborline-release-gate/seed` with a valid token.

### Status after fix
- Deployed main `024d3c2` → task-def `notary-dev-api:52`.
- Production image now built with `--build-arg INSTALL_CLOUD=1`.
- `boto3` present in image; live `demo_preflight` passes including `harborline_seed`.
- Repeated seed calls are idempotent: the same demo org data is overwritten/reset.

### Acceptance
- ✅ Seed does not 500.
- ✅ Repeated seed calls are idempotent (storage overwrites for the same demo org).
- ✅ If auth fails, UI shows 401 detail, not 500.

---

## 3. P1: Rebuild Setup as Guided AI Decision Setup Flow

Replace the shallow `renderSetup(c)` with a multi-step wizard:

1. **Choose decision workflow**: Harborline personal-loan adverse-action. Show business workflow, risk, original decision (DENY), expected outcome (UNDERWRITING_REVIEW).
2. **Define AI decision boundary**: explicit "In scope" vs "Out of scope" lists. Use the exact boundaries from the work order.
3. **Select evidence systems**: required/selected cards (Loan Origination, Credit Bureau, Underwriting Policy, AI Decision Agent) and optional/excluded cards. Each card answers: what Notary captures, why it's decision-relevant, what proof it enables, what it does not capture.
4. **Choose capture method**: SDK / API / Manual / Webhook cards with "Captures / Does not capture / Best for" and CTA.
5. **Send test capture**: visually create a sample packet (applicant ID, decision, expected, captured systems, root hash, replay status). Clicking it should lead to Verification Records.
6. **Replay readiness checklist**: checklist UI showing all items green.

Implementation: rewrite `renderSetup` in `static/app/app.js` and add CSS in `static/app/styles.css` for wizard steps.
Backend: no new routes needed unless test capture needs to actually call an API. Keep it client-side demo state for the setup wizard, or call the existing manual intake endpoint.

---

## 4. P1: Make Home Golden Path Visual and Clickable

Modify `renderHome(c, h)`:

1. Convert the right-side "ready to seed" step list into a visual proof journey with concrete data after seed.
2. After seed, each stage shows:
   - **Capture**: evidence packet with applicant, model/policy, decision, expected outcome, root hash.
   - **Replay**: original DENY, replayed DENY, "failure reproduced from cassette".
   - **Fix**: before DENY, after UNDERWRITING_REVIEW, reason: missing bureau evidence routes to underwriting.
   - **Proof**: certificate card with proof id, signature/seal, root hash, replay method.
   - **Scenario**: promoted to release gate regression library.
   - **Gate**: before FAIL, after PASS.
3. Make bottom cards clickable and route to the right sections:
   - SDK Installed → Setup
   - Agents → Setup/Systems
   - Systems → Setup evidence systems
   - Policies → Readiness
   - Need Label → VRs filtered label-needed
   - Proofs → Proofs
   - Need Replay → Incidents/VRs filtered replay-needed
   - Need Verification → Incidents filtered fix/proof-needed
   - Proofs Ready → Proofs filtered ready

Backend: no new routes. Filtering is client-side by passing query params to `nav()`.

---

## 5. P1: Rework Incidents into AI Failure Investigation Console

Current `renderIncidents` + `renderIncidentDetail` already has the investigation console merged. Enhancements still needed:

1. **Incident list columns**: add R/F/C badges (Replay, Fix, Certificate) with tooltips.
2. **Case summary**: show workflow, applicant/case id, original decision, expected outcome, risk, status.
3. **Captured decision path**: visual timeline (applicant → loan system → bureau cassette → policy → AI decision → expected outcome).
4. **Replay run detail**: table with columns Step | Source | Expected | Actual | Status.
   - Applicant facts | sealed input | match | match | pass
   - Bureau response | cassette | missing evidence | missing evidence | pass
   - Policy version | sealed metadata | v1.3 | v1.3 | pass
   - AI decision | replay | DENY | DENY | reproduced
   - Replay verdict | comparison | reproduce failure | reproduced | pass
5. **Fix verification**: before/after with changed item.
6. **Proof section**: already partially done. After P0 fix, ensure "Issue Proof" succeeds and shows proof id, status, root hash, replay method, expected outcome provenance, limitations. If not eligible, show exact missing prerequisite (409 handled in certificates.py).
7. **Scenario candidate**: show scenario id, expected outcome, release gate membership, last gate result.

Backend: `/v1/incidents/{id}/snapshot` already exists. The replay table is client-side rendering using existing `replay_result` data. No new backend needed unless the current payload lacks a field.

---

## 6. P1: Proofs Page

Modify `renderProofs(c, proofs)`:

1. Ensure clicking a proof opens detail (proof click path works after P0 fix).
2. Proof detail shows: proof id, incident id, decision workflow, original decision, verified fixed outcome, replay method (cassette/sandbox), root hash, signature/seal status, claim boundary/limitations.
3. If PDF export is not implemented, use JSON/HTML display. No false PDF claims.

Backend: no new routes needed.

---

## 7. P2: Verification Records, Website, Living Guide

### Verification Records
- Enhance `renderVRs` rows to show: source, decision type, captured systems, label status, replayability status, links to incident/scenario/proof.
- Make rows clickable.

### Website
- If platform language changes in Setup/Home, update `GetNotary.ai` copy to match.
- Run `npm run check:site-sync` if changed.

### Living Guide
- Update `docs/demo/notary-demo-non-technical-guide.md` with:
  - Demo URL assumptions
  - How to seed Harborline
  - Setup flow walkthrough
  - Systems selection rationale
  - VR → Incident flow
  - Replay table explanation
  - Proof open/issue steps
  - Release gate result
  - Known limitations
  - Technical appendix

---

## 8. Verification & Deploy

### Local checks
- `ruff check .`
- `mypy src`
- `pytest -q --ignore=tests/test_ui_vertical.py`
- `PYTHONPATH=src python3 -m notary_platform.demo_preflight`

### SDK / Website
- `PYTHONPATH=src python3 -m pytest tests` (SDK)
- `npm ci && npm run check:site-sync && npx wrangler deploy --dry-run` (website)

### Live deploy
- `bash infra/deploy-api.sh` (platform) — must include `INSTALL_CLOUD=1`.
- `npx wrangler deploy` (website) — only if copy changed.

### Live smoke tests
- `curl -s https://api.getnotary.ai/health`
- `curl -s https://api.getnotary.ai/app/app.js | grep -E "Harborline|Captured AI Decision Path|Replay Execution Trace|Proof"`
- Seed Harborline with valid token → 200, not 500.
- Browser: open `api.getnotary.ai/app/`, seed, navigate Setup/Home/Incidents/Proofs, verify proof click opens.

---

## 9. Stop Conditions

- P0 cannot be resolved without touching production secrets/KMS/deploy settings → stop and report.
- Any P1 UI redesign starts touching `static/cc` (Command Center) → stop.
- Product claims drift toward process mining/SLA analytics → stop.
- Tests fail, scope becomes messy, or merge conflicts arise → stop.

---

## 10. Next Actions (recommended order)

1. ✅ **P0 blocker fix** (deploy script `INSTALL_CLOUD=1`) and redeploy.
2. ✅ Verify seed works live.
3. ✅ **P1: Setup wizard.**
4. ✅ **P1: Home golden path + clickable cards.**
5. ✅ **P1: Incidents replay table + proof path verification.**
6. ✅ **P1: Proofs page verification.**
7. ✅ **P2: VRs + living guide.** (Website intentionally excluded per scope.)
8. ✅ **Final live QA:** `/health` ok, all UI markers present, `demo_preflight` passes against `api.getnotary.ai`.
