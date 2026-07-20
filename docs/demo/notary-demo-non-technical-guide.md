# Notary Living Demo Guide

Status: demo-ready, local/sandbox scope  
Primary audience: design partners, pilot customers, investors, compliance leaders, product leaders, and demo operators  
Current demo focus: platform + SDK + website  
Deferred for today: Command Center and shared/pilot infrastructure setup

## 1. The One-Sentence Version

Notary turns a real or realistic AI decision failure into sealed evidence, proves the failure can be replayed, verifies that a proposed fix changes the outcome, and then turns that failure into a release gate so the same mistake does not silently ship again.

## 2. What To Open First

Use these links as the current source of truth for the demo stack.

| Surface | Link | What it is for |
|---|---|---|
| Platform PR | https://github.com/notarydev/notary-platform/pull/13 | Current top platform branch with Harborline proof loop, preflight, evidence pack, and this guide. |
| SDK PR | https://github.com/notarydev/notary-sdk/pull/2 | SDK claim hardening: explicit capture, local sealing, local verification. |
| Website PR | https://github.com/notarydev/GetNotary.ai/pull/4 | Canonical current website/pilot copy stack. |
| Control-plane PR | https://github.com/notarydev/notary-viz/pull/1 | Execution history and autonomous work-order coordination. |
| Website | https://getnotary.ai | Public story; use if deployed copy is current. If not, use the website PR branch/source as the accurate copy. |

Important: for today's demo, treat `notary-platform` PR #13, `notary-sdk` PR #2, and `GetNotary.ai` PR #4 as the relevant surfaces. Command Center can wait.

## 3. The Demo Scenario

The demo uses a fictional but realistic organization: Harborline Credit Union.

Harborline has an AI-assisted personal-loan workflow. A thin-file applicant is denied, even though the safer expected behavior is to route the application to underwriting review because key bureau evidence is missing or borderline.

In normal software, a team might say, "we changed the logic, so this should be fixed." Notary is designed to answer a stronger question: can you prove the fix works against the exact scenario that failed?

The demo record is `HLCU-PL-0427`.

Expected behavior:

| Moment | Expected result | What it proves |
|---|---|---|
| Original decision | `DENY` | The AI produced the bad or risky outcome. |
| Replay | `DENY` | The failure is reproducible from captured evidence. |
| Expected corrected behavior | `UNDERWRITING_REVIEW` | Human-approved safer outcome for the scenario. |
| Before-fix Release Gate | `fail` | A release with the old behavior should be blocked. |
| After-fix Release Gate | `pass` | The fixed behavior passes this scenario. |
| Readiness certificate verification | `signature_valid: true` | The proof artifact can be verified for the demo scenario. |

## 4. The Product Story From Requirements And Blueprints

This section summarizes the project requirements and blueprints in plain language.

### 4.1 The problem

AI observability tools can tell a team what happened: a model was called, an API returned a response, a workflow produced an output. That is useful, but it does not answer the harder forensic questions:

- Why did the decision happen?
- Can we reproduce it?
- Can we prove a fix changed the outcome?
- Can we preserve that proof for future audit, release review, or dispute response?

Regulated teams need more than logs. They need evidence that can support remediation, recurrence prevention, and audit defensibility.

### 4.2 The active build horizon

The active build horizon stops at the Release Gate.

That means Notary's near-term job is to complete this loop:

1. Capture a consequential AI decision as evidence.
2. Seal enough of the decision context to make tampering detectable.
3. Ingest the record into the platform.
4. Replay the scenario from the captured cassette.
5. Verify that a proposed fix changes the outcome.
6. Promote the verified case into a Scenario.
7. Run the Scenario against a candidate release.
8. Return a pass/fail/error Release Gate result.
9. Attach proof and certificate references so the decision is reviewable.

Everything beyond that, including full GRC delivery, broad enterprise inventory, organization-wide policy management, and live compliance-system integrations, remains planned expansion. It should not be claimed as already live in today's demo.

### 4.3 The key product components

| Component | Plain-English role | Current demo interpretation |
|---|---|---|
| SDK | Captures selected decision evidence inside an AI workflow. | Explicit/manual capture, context manager capture, decorator capture, local HMAC/Merkle sealing, local verification. |
| Verification Record | The trusted case file for one captured decision. | Harborline record `HLCU-PL-0427`. |
| Response Cassette | Recorded external responses used for deterministic replay. | Lets the demo replay without making production/provider calls. |
| Replay Engine | Re-runs the captured scenario. | Reproduces the original `DENY`. |
| Mutation / Fix Verification | Tests the corrected logic against the same scenario. | Shows the corrected output becomes `UNDERWRITING_REVIEW`. |
| Proof of Mitigation | Scenario-scoped proof that the fix worked. | Used in the proof loop; do not describe as broad compliance certification. |
| Scenario Library | Stores verified failures as reusable regression scenarios. | Harborline becomes a scenario for future release checks. |
| Proof of Readiness | Certificate/result attached to a release candidate that passes required scenarios. | Passing gate includes a readiness certificate reference. |
| Release Gate | CI/CD-facing pass/fail/error decision. | Before fix fails; after fix passes. |
| Web Dashboard / Platform UI | Human surface for operating the proof loop. | Presenter uses the Harborline path in `/app/`. |
| Website | Public story and CTA. | Harborline + design-partner pilot positioning. |

### 4.4 The blueprint decisions that matter for the demo

- The API Server is Python/FastAPI and owns the proof workflow, organization scoping, certificates, and release-gate orchestration.
- Replay is cassette-first. That means the default replay uses captured responses, not live external provider calls.
- Sandbox/provider escalation is future or opt-in behavior when a fix changes external calls or a customer requires live validation.
- The dashboard should look like a proof workflow, not logs or APM.
- The platform should be honest about known limitations and claim scope.
- The SDK is the trust root for capture, but today's supported SDK boundary is explicit capture, not transparent capture of every runtime side effect.
- Production-grade storage and signing need real infrastructure such as remote storage, locked CORS/auth, and KMS before we claim shared/pilot or production deployment readiness.

## 5. What Notary Shows In The Demo

The demo walks through four proof moments.

### 5.1 Capture the decision

Notary records the important evidence around the AI decision: what the system saw, what it used, what it decided, and the final outcome. In the demo, the original outcome is `DENY`.

### 5.2 Replay the failure

Notary replays the recorded scenario from the captured cassette. The point is to show the failure is reproducible, not just a one-off log entry. In the demo, replay reproduces the original denial.

### 5.3 Verify the fix

Notary tests the corrected behavior against the same scenario. The expected corrected outcome is `UNDERWRITING_REVIEW`. If the fix changes the outcome as expected, Notary can issue scenario-scoped proof.

### 5.4 Gate the next release

The verified scenario becomes part of a Release Gate. Before the fix, the gate fails. After the fix, the gate passes and returns a Proof of Readiness certificate reference.

## 6. How To Run The Demo Locally

These commands are for the `notary-platform` repo on the top demo branch:

```bash
git checkout codex/prg-018-final-evidence-pack
```

If dependencies are not installed yet, use the repo's normal Python setup. Depending on the environment, that may be one of:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
```

or the repo's existing install command if it has one.

### 6.1 Run the automated preflight

Run this before every rehearsal:

```bash
PYTHONPATH=src python3 -m notary_platform.demo_preflight
```

Machine-readable version:

```bash
PYTHONPATH=src python3 -m notary_platform.demo_preflight --json
```

Expected behavior:

- overall status is `PASS` or JSON `status: pass`;
- API health check passes;
- Harborline seed endpoint completes;
- scenario contract is `harborline-personal-loan-adverse-action`;
- Verification Record exists and is replayable;
- replay reproduces `DENY`;
- mutation/fix verification produces `UNDERWRITING_REVIEW`;
- before-fix Release Gate is `fail`;
- after-fix Release Gate is `pass`;
- passing gate has evidence refs and a certificate id;
- readiness certificate verification has `signature_valid: true`;
- presenter UI contains Harborline, Blocked Gate, and Passing Gate copy.

If this preflight fails, do not improvise. Use the troubleshooting section below.

### 6.2 Build the final evidence pack

Run:

```bash
PYTHONPATH=src python3 -m notary_platform.evidence_pack --output-dir artifacts/final-evidence-pack
```

Expected files:

- `harborline-preflight.json`
- `security-readiness.json`
- `blocked-gate.json`
- `passing-gate.json`
- `readiness-certificate.json`
- `readiness-certificate-verification.json`
- `architecture-summary.json`
- `limitations.json`
- `rehearsal-manifest.json`

Expected behavior:

- `harborline-preflight.json` has `status: pass`;
- `blocked-gate.json` has `status: fail`;
- `passing-gate.json` has `status: pass`;
- `readiness-certificate-verification.json` has `signature_valid: true`;
- `security-readiness.json` may be `blocked` in local demo mode. That is acceptable for today's demo if you clearly say shared/pilot infrastructure is not being claimed.

### 6.3 Start the platform app

Run the platform locally. Common command:

```bash
make run
```

If `make run` is unavailable, use the repo's FastAPI start command. A typical fallback is:

```bash
PYTHONPATH=src uvicorn notary_platform.api_server.main:app --reload --host 0.0.0.0 --port 8000
```

Open:

```text
http://localhost:8000/app/
```

Expected behavior in the app:

1. You see the platform home screen.
2. You see a Harborline path or Harborline demo band.
3. Click `Seed Harborline Path`.
4. The UI gives links or cards for the source Verification Record, Blocked Gate, and Passing Gate.
5. The source Verification Record shows Harborline data, original `DENY`, replayability, and label/expected behavior context.
6. Blocked Gate shows a failed gate for the before-fix behavior.
7. Passing Gate shows a passed gate for the fixed behavior, evidence refs, scenario result, and certificate reference.

## 7. Demo Operator Runbook

Use this sequence when training someone else.

### 7.1 Five-minute prep

1. Pull or open the latest platform branch: `codex/prg-018-final-evidence-pack`.
2. Run `PYTHONPATH=src python3 -m notary_platform.demo_preflight`.
3. If it passes, start the app.
4. Open `http://localhost:8000/app/`.
5. Open the website or website PR preview/source.
6. Keep this guide open.

### 7.2 Ten-minute demo flow

1. Start with the problem.

   Say: "Logs tell you what happened. Notary proves why a decision happened, whether a fix works, and whether a known failure can ship again."

2. Introduce Harborline.

   Say: "Harborline Credit Union has an AI-assisted personal-loan workflow. A thin-file applicant was denied. The expected safer behavior was underwriting review."

3. Seed the demo.

   In the platform UI, click `Seed Harborline Path`.

   Expected behavior: the app creates or reveals the Verification Record, replay, fix verification, scenario, blocked gate, passing gate, and certificate path.

4. Show the Verification Record.

   Say: "This is the case file. It captures the decision evidence and gives us something stronger than a log."

   Expected behavior: record references `HLCU-PL-0427`, original outcome `DENY`, and replayability.

5. Show replay.

   Say: "Replay proves the failure is reproducible from captured evidence. We are not just staring at a log line."

   Expected behavior: replayed decision is also `DENY`.

6. Show fix verification.

   Say: "Now we test the corrected behavior against the same scenario. The expected outcome is underwriting review."

   Expected behavior: fixed/mutated decision is `UNDERWRITING_REVIEW`.

7. Show Blocked Gate.

   Say: "Before the fix, this release should not ship. The gate fails because the old behavior repeats the known failure."

   Expected behavior: status is `fail`, with the Harborline scenario listed as failing.

8. Show Passing Gate.

   Say: "After the fix, the same scenario passes and produces readiness evidence. This is recurrence prevention."

   Expected behavior: status is `pass`, evidence refs exist, and certificate id/reference exists.

9. Show the website.

   Say: "The public story is intentionally narrow: one high-risk workflow, one known failure pattern, one reviewer-approved expected outcome, one release-gate proof loop."

10. End with the ask.

   Say: "For a design partner, we need one regulated decision workflow, one known failure or dispute pattern, one expected outcome, and one release review context."

## 8. Screenshot And Recording Checklist

Capture these for the demo evidence pack or follow-up email:

- platform home screen with Harborline path;
- seed action or seeded state;
- Verification Record for `HLCU-PL-0427`;
- replay showing original/replayed `DENY`;
- fix verification or mutation showing `UNDERWRITING_REVIEW`;
- before-fix Release Gate showing `fail`;
- after-fix Release Gate showing `pass`;
- readiness certificate id or verification result;
- website Harborline flagship section;
- website design-partner pilot section;
- final evidence-pack folder listing if useful.

## 9. What To Say

Use this framing:

- "This is AI Decision Assurance."
- "We turn failures, overrides, disputes, or denials into replayable scenarios."
- "The proof is bounded to the tested scenario."
- "The release gate stops a known failure from silently shipping again."
- "The first pilot is intentionally narrow: one workflow, one known failure pattern, one expected outcome, one release-gate proof loop."
- "Notary is not trying to replace observability. It starts where observability stops: proof and recurrence prevention."

## 10. What Not To Claim

Do not claim:

- Notary certifies general AI safety.
- Notary guarantees fairness across all applicants.
- Notary is already connected to live GRC systems.
- Notary automatically captures every OpenAI, Anthropic, framework, browser, or HTTP call.
- The local demo is production deployment evidence.
- Shared-demo JSON storage is immutable custody storage.
- The SDK is published on PyPI/npm unless package publishing is separately verified.
- TypeScript SDK parity is implemented beyond the current placeholder.

The accurate claim is narrower and stronger: Notary proves what happened and whether the fix works for a recorded, replayable, tested scenario.

## 11. Website Guide

The website should reinforce the same story as the platform demo.

Current canonical website PR: https://github.com/notarydev/GetNotary.ai/pull/4

Website messages to check:

- Harborline is the flagship story.
- The CTA is design partner / pilot access.
- The pilot offer is narrow and realistic.
- GRC exports and broader enterprise workflows are future-facing, not current live-production claims.
- The buyer should understand the value in one sentence: every known AI failure can become a release gate.

Suggested website walkthrough:

1. Open the hero.
2. Point to the phrase about stopping repeated AI failures.
3. Open the Harborline section.
4. Explain before-fix blocked gate and after-fix passing gate.
5. Open the pilot section.
6. Explain what a design partner provides and what Notary returns.
7. Mention out-of-scope boundaries: no broad certification, no hidden production data, no live GRC promise.

## 12. SDK Guide In Plain English

Current SDK PR: https://github.com/notarydev/notary-sdk/pull/2

The SDK is the capture tool. It lets a developer explicitly record selected AI calls, tool calls, HTTP calls, and decision points.

Today, the SDK supports explicit capture through:

- manual `RunCapture` calls;
- a `capture_run` context manager;
- an `@instrument` decorator;
- local HMAC-SHA256 sealing;
- Merkle root generation;
- local verification.

Today, it does not prove that every possible runtime side effect was captured automatically. Transparent capture of every OpenAI, Anthropic, framework, browser, or HTTP call is future work unless and until implemented and tested.

If someone asks why this is enough for the demo, say:

"For the first pilot, explicit capture is acceptable because the demo is about proving the end-to-end proof loop: capture, replay, verify, scenario, release gate. Transparent capture is valuable later, but it should not block the Harborline proof loop."

## 13. Troubleshooting

### 13.1 Preflight fails

Run:

```bash
PYTHONPATH=src python3 -m notary_platform.demo_preflight --json
```

Look for the first failed check.

Common causes:

| Failed area | Likely cause | What to do |
|---|---|---|
| import error | dependencies missing | install repo dev dependencies, activate venv, confirm `PYTHONPATH=src`. |
| API health | app import/runtime issue | run targeted tests or start FastAPI manually to see error. |
| Harborline seed | branch is wrong or route missing | confirm branch is `codex/prg-018-final-evidence-pack`. |
| replay or mutation | platform proof loop regression | do not demo; ask engineering to inspect release-gate vertical test. |
| presenter UI | static app not updated | confirm PRG-012 changes are in the branch. |
| certificate verification | certificate/signature regression | do not claim readiness proof until fixed. |

### 13.2 App does not start

Try:

```bash
PYTHONPATH=src python3 -m compileall -q src
```

Then try:

```bash
PYTHONPATH=src uvicorn notary_platform.api_server.main:app --reload --host 0.0.0.0 --port 8000
```

If `uvicorn` is missing, install dev dependencies in the active virtual environment.

### 13.3 The website does not match the story

Use the canonical website PR #4 as the source of truth. Older website PRs may be superseded.

Do not use stale deployed copy if it has not been updated.

### 13.4 Cloudflare or production deploy fails

Do not spend demo time debugging Cloudflare unless the demo depends on a live deployed website. For today's scoped demo, local platform proof plus website PR/source is enough.

Shared/pilot infrastructure is a separate decision. It needs auth, CORS, remote storage, KMS, and deployment verification before shared/pilot claims.

## 14. Common Non-Technical Questions

### Is this a monitoring tool?

No. Monitoring tells you something happened. Notary is focused on proof: replay the decision, verify the fix, and prevent recurrence through a release gate.

### Is this an eval platform?

Not exactly. Evals often start with synthetic test cases. Notary starts from real or realistic decision failures, overrides, disputes, and reviewer-approved outcomes, then turns them into replayable release-gate scenarios.

### Is this a compliance certification product?

Not yet, and not as a broad claim. Notary creates evidence that can support compliance workflows. It does not certify general AI compliance or safety.

### What is the design-partner pilot?

A four-week narrow pilot:

- Week 1: choose the workflow, failure pattern, expected outcome, and safe data boundary.
- Week 2: instrument capture and produce the first sealed Verification Record.
- Week 3: replay the scenario and verify the fix.
- Week 4: promote the scenario and rehearse the release gate with evidence references.

### What is the investor takeaway?

The wedge is recurrence prevention for AI decisions. Notary converts failures into proof-backed release gates. That creates a recurring reason to use the product: every future release can be checked against known failure scenarios.

### Why is Harborline fictional?

Because the demo needs to be safe, repeatable, and free of real customer data. The scenario is realistic enough to show the product workflow without creating privacy, regulatory, or customer-access risk.

### What makes this defensible?

The defensibility comes from replayability, scoped expected outcomes, captured evidence refs, certificate verification, and explicit limitations. The demo does not hide what is local, sandboxed, or future work.

## 15. Pilot Qualification Checklist

A good design partner has:

- a regulated or high-risk decision workflow;
- repeated AI-assisted denials, escalations, overrides, disputes, or policy exceptions;
- an owner in product, compliance, QA, model risk, or legal;
- a reviewer who can approve expected outcomes;
- willingness to start in sandbox or non-production data;
- a release review context where a scenario gate would matter.

A weak design partner has:

- no known failure/dispute pattern;
- no reviewer who can define the expected outcome;
- only generic interest in AI safety;
- a need for broad GRC integrations before seeing the proof loop;
- a requirement to use production data before security readiness is configured.

## 16. Demo Close

Use this close:

"Notary does not ask you to trust that the AI fix worked. It replays the failure, verifies the fix, and turns that proof into a gate for the next release."

Then ask:

"Do you have one AI decision workflow where a denial, dispute, override, or escalation has already shown you a failure pattern worth preventing from recurring?"

## 17. Technical Appendix

This appendix is for engineers or technical reviewers.

### 17.1 Main local commands

```bash
git checkout codex/prg-018-final-evidence-pack
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
PYTHONPATH=src python3 -m notary_platform.demo_preflight
PYTHONPATH=src python3 -m notary_platform.evidence_pack --output-dir artifacts/final-evidence-pack
make run
```

Fallback app command:

```bash
PYTHONPATH=src uvicorn notary_platform.api_server.main:app --reload --host 0.0.0.0 --port 8000
```

### 17.2 Targeted verification commands

Platform commands reported by workers:

```bash
PYTHONPATH=src python3 -m pytest tests/test_evidence_pack.py tests/test_demo_preflight.py tests/test_security_readiness.py
python3 -m ruff check src tests
python3 -m mypy src
PYTHONPATH=src python3 -m pytest tests/test_auth.py tests/test_certificates.py tests/test_demo_preflight.py tests/test_evidence_pack.py tests/test_ingestion.py tests/test_live_status.py tests/test_platform_static_app.py tests/test_release_gate_cli.py tests/test_release_gate_vertical.py tests/test_replay.py tests/test_security_readiness.py tests/test_shared_demo_storage.py tests/test_verification.py tests/test_viz.py
```

Known limitation: full `pytest tests` may still be blocked in some worker environments by missing Playwright browser dependencies for UI vertical tests.

SDK commands reported by workers:

```bash
PYTHONPATH=src python3 -m pytest tests
```

Website commands reported by workers:

```bash
npx wrangler deploy --dry-run
```

This validates the Worker bundle without deploying.

### 17.3 Key platform files

| File | Purpose |
|---|---|
| `src/notary_platform/demo_preflight.py` | Runs the Harborline proof loop through the FastAPI app in-process. |
| `src/notary_platform/evidence_pack.py` | Writes the final local evidence-pack JSON files. |
| `src/notary_platform/security_readiness.py` | Checks whether shared/pilot deployment posture is ready. |
| `src/notary_platform/demo_scenarios.py` | Contains the Harborline scenario contract. |
| `src/notary_platform/demo_catalog.py` | Builds the deterministic demo path. |
| `src/notary_platform/api_server/routers/release_gate.py` | Release Gate API surface. |
| `src/notary_platform/release_gate_cli.py` | CI-style Release Gate result evaluator. |
| `static/app/app.js` | Local platform presenter UI. |
| `docs/final-evidence-pack.md` | Evidence-pack runbook. |
| `docs/security-deployment-readiness.md` | Shared/pilot readiness checklist. |

### 17.4 Security readiness interpretation

`security-readiness.json` may be blocked in local demo mode. That is expected unless all shared/pilot controls are configured.

Shared/pilot readiness requires:

- API auth token;
- Command Center auth token before exposing status endpoints;
- exact non-localhost CORS origins;
- remote storage enabled with database URL and evidence bucket;
- S3 Object Lock/WORM evidence storage before immutable-custody claims;
- KMS signing key before production-grade certificate sealing claims.

If these are not configured, say:

"Today's demo is local/sandbox proof-loop evidence. Shared pilot deployment is a separate readiness step."

### 17.5 Claim boundary matrix

| Claim | Can we say today? | Safe wording |
|---|---:|---|
| Replay recorded AI failure | Yes | "Replays the Harborline recorded scenario from captured evidence." |
| Verify scenario-specific fix | Yes | "Verifies the fix changes this scenario from DENY to UNDERWRITING_REVIEW." |
| Release Gate pass/fail | Yes | "Before fix fails; after fix passes for this scenario." |
| Proof of Readiness certificate reference | Yes | "Passing gate includes readiness certificate evidence." |
| General AI safety certification | No | "Proof is bounded to tested scenarios." |
| Fairness guarantee | No | "This does not guarantee fairness across all applicants." |
| Live GRC integrations | No | "GRC exports/integrations are planned consumers of proof artifacts." |
| Transparent capture of every provider/API call | No | "SDK supports explicit capture today; transparent capture is planned work." |
| Production/shared deployment readiness | Not unless PRG-017 passes | "Local/sandbox demo unless shared readiness is configured and verified." |

### 17.6 Why cassette-first matters

Cassette-first replay is central to the product wedge. It means Notary can replay from captured responses rather than depending on a live provider sandbox. This makes the proof more durable and repeatable. Live sandbox escalation can be added when needed, but it is not required for the Harborline demo.

### 17.7 Why the Release Gate matters commercially

The Release Gate is the recurring product motion. An incident or disputed decision is not just resolved once; it becomes a scenario that can check future releases. That turns a painful failure into durable regression coverage and creates an ongoing reason to run Notary.

## 18. Change Log

- 2026-07-20: Expanded from plain-English explainer into living demo/operator guide with links, run commands, expected behavior, requirements/blueprint summary, training flow, troubleshooting, and technical appendix.
- 2026-07-20: Scoped today's demo to platform, SDK, and website; Command Center and shared/pilot infrastructure deferred.
