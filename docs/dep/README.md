# Decision Evidence Protocol

Decision Evidence Protocol (DEP) is an open, vendor-neutral interchange protocol for evidence about consequential AI decisions. It lets observability systems, governance tools, guardrails, business applications, evaluators, evidence custodians, and independent verifiers contribute to and consume one portable evidence chain without requiring a shared platform.

DEP standardizes evidence boundaries, not the algorithm used to judge a decision.

## Documents

- [Whitepaper](whitepaper.md): problem, thesis, ecosystem roles, use cases, and adoption path.
- [Specification](spec.md): normative resources, relationships, transport profiles, processing rules, and conformance profiles.
- [Governance](governance.md): versioning, change process, neutrality, security, and conformance policy.
- [JSON Schemas](../../schemas/dep/): machine-readable contracts for the protocol resource families.

## Start Here

A producer can adopt DEP by publishing a Provider Card and emitting one valid Observation. A consumer can adopt DEP by validating envelopes, preserving provenance, and importing the resource without silently changing its epistemic status. Full-chain support is not required.

The smallest useful exchange is:

```text
Observation Provider -> DEP Observation -> Evidence Consumer
```

A complete assurance chain can grow into:

```text
Observations + Context Bindings + Assessments
  -> Finding -> Review Decision -> Evidence Bundle
  -> Verification Claim
```

## Independence

DEP does not require a particular AI framework, model vendor, cloud, database, governance system, observability platform, evaluator, replay engine, or assurance product. Conformance applies only to observable behavior at the protocol boundary.

## Status

Version 0.1 is a public design draft. Implementers should expect additive changes until the first release candidate. Breaking changes require a new protocol version under the rules in [Governance](governance.md).
