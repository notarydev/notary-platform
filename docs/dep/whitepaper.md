# Decision Evidence Protocol

## An Open Evidence Layer for AI Assurance

**Status:** Public design paper
**Version:** 0.1
**Date:** July 2026

## Abstract

AI decisions cross systems that were not designed to produce one coherent assurance record. Observability platforms record traces. Governance systems hold policies and controls. Guardrails record enforcement. Business systems reveal actual outcomes. Source control and deployment systems identify changes. Human reviewers supply authority. Each system sees a useful fragment, but no shared contract preserves how those fragments support, contradict, or limit a claim about one decision.

Decision Evidence Protocol (DEP) is an open, vendor-neutral protocol for exchanging those fragments as typed, attributable evidence. It defines portable observations, context artifacts and bindings, assessments, findings, review decisions, evidence bundles, and bounded verification claims. DEP enables independent systems to cooperate from investigation through remediation verification while retaining source ownership, decision-time applicability, uncertainty, and explicit limits.

DEP is not another observability or governance platform. It is the evidence layer between them.

## The Missing Layer

Modern AI systems already use interoperability layers for important boundaries. [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-06-18/architecture) standardizes access to tools and context. [Agent2Agent](https://github.com/a2aproject/A2A/blob/main/docs/specification.md) standardizes collaboration between agents. [OpenTelemetry](https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/) standardizes telemetry. [CloudEvents](https://github.com/cloudevents/spec) standardizes event envelopes. [in-toto attestations](https://github.com/in-toto/attestation/blob/main/spec/README.md) authenticate claims about immutable subjects.

AI assurance still lacks an equivalent boundary. A trace can show that a model returned `DENY`, but not whether the policy effective at that moment required `REVIEW`. A policy system can identify the rule, but may not possess the runtime inputs. A human outcome can establish that the case was corrected, but not which system version caused the original result. A signed certificate can prove who issued a claim, but a signature alone cannot prove the evidence was complete or the claim was appropriately bounded.

The missing layer is a common way to say:

```text
what was observed
+ what context applied at decision time
+ what was evaluated and by which method
+ what remains missing or conflicted
+ who authorized the disposition
+ what immutable change was verified
= a bounded assurance claim
```

## Protocol Thesis

DEP organizes evidence around a decision subject rather than around the product that collected it. Multiple providers can contribute without surrendering ownership or pretending to share the same authority.

DEP makes four distinctions durable:

1. Facts remain separate from assertions, inferences, and human confirmation.
2. Evidence integrity remains separate from evidence completeness.
3. A candidate concern remains separate from an authorized incident.
4. A verified, scoped result remains separate from a universal claim of safety or compliance.

These distinctions let organizations use automation aggressively without turning incomplete telemetry or probabilistic judgment into false certainty.

## Ecosystem Model

DEP participants adopt roles independently:

| Role | Contributes or performs | Receives |
| --- | --- | --- |
| Observation Provider | decisions, traces, retrievals, tool calls, outcomes, deployment events | capture-quality and disposition references |
| Context Provider | policies, expected outcomes, guardrails, manifests, evidence requirements | coverage and verification status |
| Evaluator | versioned assessments with declared prerequisites | immutable evidence and context bindings |
| Reviewer | authoritative approval, dismissal, suppression, or accepted risk | explainable findings and evidence gaps |
| Evidence Custodian | content-addressed evidence bundles and custody history | selected immutable resources |
| Verifier | bounded verification claims | evidence bundles, expected behavior, and immutable change identity |
| Gate Consumer | release or deployment decision | verified scenarios and claims |

No participant must implement every role. An observability vendor can emit Observations. A policy platform can emit ContextArtifacts. A laboratory can verify a claim. A regulator or auditor can consume the resulting bundle with an independent validator.

## Use Cases Beyond Any One Platform

### Cross-vendor incident investigation

A company combines a model trace from one vendor, a guardrail result from another, an effective policy from its governance repository, and a customer outcome from its CRM. DEP binds them to one decision while preserving each source and authority level. A review tool can explain why the case is actionable and which evidence is still missing.

### Portable evaluation

An evaluator publishes its required evidence and method. Any compatible processor can determine whether the evaluator is eligible to run. Results carry the exact resources, versions, limitations, and method class used, allowing the assessment to move between observability, governance, testing, and audit systems.

### Independent remediation verification

An evidence custodian seals the original decision inputs and dependencies. A verifier tests an identified code, prompt, policy, or model change and issues a bounded claim. The customer can validate its signature, subjects, method, expected result, and limitations without access to the verifier's internal database.

### Regulatory and audit evidence exchange

Organizations can export a compact evidence bundle that preserves provenance, redactions, decision-time policy applicability, reviewer authority, and verification scope. Auditors can verify integrity and identify gaps without requiring direct access to every operational system.

### Release assurance portability

A verified production failure can become a versioned test scenario. CI/CD systems consume the scenario and return a gate result linked to the original evidence and fix. The scenario survives changes in model, cloud, agent framework, or observability vendor.

### Assurance services and research

Independent assurance firms, benchmark maintainers, and academic teams can publish DEP-compatible evaluator contracts, assessment outputs, test fixtures, and verification claims. Their methods can remain proprietary or open while their protocol behavior remains testable.

## How Adoption Starts

DEP uses progressive conformance. Adoption does not require an enterprise to replace tools or complete a large integration project.

1. A provider publishes a capability card and emits one resource family.
2. A consumer validates schema, identity, provenance, and integrity.
3. Additional providers contribute context or outcomes for the same decision subject.
4. Evaluators declare prerequisites and emit inspectable assessments.
5. Reviewers and custodians add authority and immutable evidence.
6. Verifiers and gate consumers close the remediation and recurrence loop.

Generic HTTP, CloudEvents, batch JSONL, and OpenTelemetry bridge profiles reduce the need for native connectors. Native adapters remain useful where they preserve stronger identity, richer source semantics, or lower operational burden.

## Design Boundaries

DEP deliberately does not standardize source profiling, identity-resolution algorithms, context ranking, evaluator internals, candidate clustering, user experience, remediation workflows, or release policy. Those are areas where products and research should differentiate.

The protocol standardizes only what must cross a trust boundary:

- resource identity and version;
- source provenance and epistemic status;
- typed relationships and temporal applicability;
- evaluator prerequisites and reproducibility material;
- review authority and supersession;
- evidence manifests, integrity, and redaction lineage;
- verification subjects, methods, results, and limitations.

## Relationship to Existing Standards

DEP composes with existing work instead of replacing it:

- MCP and A2A describe interaction with tools, context, and agents; DEP describes evidence about decisions produced through those interactions.
- OpenTelemetry describes telemetry vocabulary and transport; DEP can reference or deterministically map telemetry into decision evidence.
- CloudEvents provides an exchange envelope; DEP defines the evidence payload and semantics.
- in-toto and DSSE provide attestation structures and authenticated envelopes; DEP defines predicates for decision evidence and bounded verification.
- Governance and observability systems remain systems of record for their domains; DEP preserves their claims as independently owned resources.

## Trust and Safety Model

DEP assumes that providers can be incomplete, mistaken, compromised, or mutually inconsistent. A valid signature proves origin and integrity, not truth or completeness. Consumers therefore evaluate trust by role, claim type, identity, authority, time, and declared scope.

Sensitive content can remain in customer-controlled storage. DEP supports digests, access-controlled references, explicit redaction lineage, and deletion tombstones. Replay is side-effect-free by default; external mutations require a separately authorized isolated policy.

## Open Standard, Competitive Implementations

Protocol openness does not require implementation sameness. Providers can compete on collection coverage, identity resolution, context discovery, evaluator quality, investigation experience, replay fidelity, cost, security, and operational reliability. They conform by producing portable resources and respecting observable safety invariants.

An open protocol becomes useful when independent parties can implement only the portion relevant to them, test that implementation, and exchange evidence without bilateral schema negotiation. DEP's publication package therefore includes a normative specification, JSON Schemas, examples, conformance fixtures, and governance rules.

## Conclusion

AI ecosystems have abundant telemetry and fragmented authority. DEP gives those fragments a shared evidentiary structure without granting any one vendor ownership of the assurance chain.

The intended outcome is straightforward: a real decision can be investigated across systems, unsupported conclusions remain visibly unsupported, remediation can be verified against immutable evidence, and the result can be carried forward as a durable release control.

The normative protocol is defined in the [DEP Specification](spec.md).
