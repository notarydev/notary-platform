# DEP: Making AI Decisions Auditable

## The problem

AI systems make consequential decisions every day — approving loans, triaging support tickets, generating medical notes, moderating content. When one of these decisions is wrong, harmful, or non-compliant, the operator needs to answer three questions:

1. **What happened?** What did the system observe, retrieve, and decide?
2. **Why was that wrong?** What policy, expectation, or context made this particular outcome a failure?
3. **Can we prove we fixed it?** Can we replay, verify, and attest that the corrected system now behaves as expected?

Current observability tools capture raw logs but cannot answer these questions with verifiable certainty. Logs can be altered, timestamps can be wrong, and there is no standard way to link an AI decision to the policy that should have governed it.

## The solution

DEP defines a portable evidence format that preserves:

- **Immutable observations** — each trace element is captured with a digest that can be independently verified.
- **Decision-time context** — policies and configurations are tied to the exact moment a decision was made, not when an investigation starts.
- **Deterministic verification** — the same evidence, evaluated with the same contracts, always produces the same result.

DEP is not a monitoring tool, an observability platform, or a logging standard. It is a packaging and verification protocol that sits between evidence sources and assurance systems.

## Key design decisions

- **Digest-first**: Every envelope carries a content digest computed from canonical JSON. Anyone can verify integrity without trusting the source.
- **Typed resources**: Different kinds of evidence (observations, policies, assessments) have distinct schemas but share the same envelope and verification machinery.
- **Context at decision time**: Bindings between decisions and context artifacts record which policies were effective when the decision was made, preventing retroactive policy changes from distorting evaluations.
- **Vendor-neutral**: DEP schemas contain no proprietary fields. Any assurance platform can consume DEP resources.

## Use cases

| Use case | How DEP helps |
|---|---|
| Incident investigation | Immutable evidence preserves what happened before any system change. |
| Regulatory compliance | Verifiable context bindings show which policies governed each decision. |
| Fix verification | Proof claims attest that a corrected system produces the expected outcome. |
| Continuous assurance | Evidence bundles freeze a snapshot of evidence for recurring evaluation. |

## Status

DEP is an early draft (v0.1). It is under active development and not yet recommended for production use without careful evaluation.
