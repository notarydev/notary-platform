# Notary Demo Guide For Non-Technical Reviewers

Status: demo-ready, local/sandbox scope

This guide explains the Harborline demo in plain language. It is for design partners, investors, compliance leaders, and business reviewers who need to understand what Notary proves without reading code.

## The One-Sentence Version

Notary turns a real or realistic AI decision failure into sealed evidence, proves the failure can be replayed, verifies that a proposed fix changes the outcome, and then turns that failure into a release gate so the same mistake does not silently ship again.

## The Demo Scenario

The demo uses a fictional but realistic organization: Harborline Credit Union.

Harborline has an AI-assisted personal-loan workflow. A thin-file applicant is denied, even though the safer expected behavior is to route the application to underwriting review because key bureau evidence is missing or borderline.

In normal software, a team might say, "we changed the logic, so this should be fixed." Notary is designed to answer a stronger question: can you prove the fix works against the exact scenario that failed?

## What Notary Shows

The demo walks through four proof moments.

1. Capture the decision

   Notary records the important evidence around the AI decision: what the system saw, what it used, what it decided, and the final outcome. In the demo, the original outcome is `DENY`.

2. Replay the failure

   Notary replays the recorded scenario from the captured cassette. The point is to show the failure is reproducible, not just a one-off log entry. In the demo, replay reproduces the original denial.

3. Verify the fix

   Notary tests the corrected behavior against the same scenario. The expected corrected outcome is `UNDERWRITING_REVIEW`. If the fix changes the outcome as expected, Notary can issue scenario-scoped proof.

4. Gate the next release

   The verified scenario becomes part of a Release Gate. Before the fix, the gate fails. After the fix, the gate passes and returns a Proof of Readiness certificate reference.

## What To Say In The Demo

Use this framing:

- "This is AI Decision Assurance."
- "We turn failures, overrides, disputes, or denials into replayable scenarios."
- "The proof is bounded to the tested scenario."
- "The release gate stops a known failure from silently shipping again."
- "The first pilot is intentionally narrow: one workflow, one known failure pattern, one expected outcome, one release-gate proof loop."

## What Not To Claim

Do not claim:

- Notary certifies general AI safety.
- Notary guarantees fairness across all applicants.
- Notary is already connected to live GRC systems.
- Notary automatically captures every OpenAI, Anthropic, framework, browser, or HTTP call.
- The local demo is production deployment evidence.
- Shared-demo JSON storage is immutable custody storage.

The accurate claim is narrower and stronger: Notary proves what happened and whether the fix works for a recorded, replayable, tested scenario.

## What The Website Should Reinforce

The website should send the same message as the platform demo:

- Harborline is the flagship story.
- The CTA is design partner / pilot access.
- The pilot offer is narrow and realistic.
- GRC exports and broader enterprise workflows are future-facing, not the current proof claim.
- The buyer should understand the value in one sentence: every known AI failure can become a release gate.

## What The SDK Means In Plain English

The SDK is the capture tool. It lets a developer explicitly record selected AI calls, tool calls, HTTP calls, and decision points.

Today, the SDK supports explicit capture through manual calls, a context manager, or a decorator. It seals the captured evidence locally with HMAC and Merkle hashing so tampering can be detected.

Today, it does not prove that every possible runtime side effect was captured automatically. That broader transparent interception story is future work unless and until it is implemented and tested.

## The Demo Flow To Show Today

1. Open the platform app.
2. Seed the Harborline demo path.
3. Show the Verification Record for `HLCU-PL-0427`.
4. Show that the original replayed outcome is `DENY`.
5. Show the before-fix Release Gate failing.
6. Show the after-fix Release Gate passing.
7. Show the readiness certificate reference or verification result.
8. Open the website and show the Harborline + pilot sections.
9. End with the pilot ask: one regulated decision workflow, one known failure or dispute pattern, one reviewer-approved expected outcome, and one release review context.

## Questions A Non-Technical Reviewer May Ask

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

## Today's Scope

For today's demo, focus only on:

- Platform: Harborline proof loop and Release Gate.
- SDK: honest explicit-capture boundary.
- Website: design-partner / pilot story.

Command Center can wait. Shared/pilot infrastructure can wait unless auth, CORS, remote storage, KMS, and deployment are explicitly configured and verified.

## Final Demo Line

"Notary does not ask you to trust that the AI fix worked. It replays the failure, verifies the fix, and turns that proof into a gate for the next release."