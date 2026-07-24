# Decision Evidence Protocol Specification

## Version 0.1 Draft

**Status:** Public draft specification
**Protocol:** Decision Evidence Protocol (DEP)
**Version:** 0.1
**Date:** July 2026

Sections 1-5, 15-16, and 21 are informative. Sections 6-14 and 17-19 are normative. Section 20 delegates protocol stewardship to [DEP Governance](governance.md). The companion [whitepaper](whitepaper.md) explains the ecosystem problem and adoption model.

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED, MAY, and OPTIONAL are to be interpreted as described by BCP 14 when, and only when, they appear in all capitals.

## Abstract

Organizations already possess fragments of the evidence needed to understand AI decisions. Observability systems hold traces. Business applications hold outcomes. Governance platforms hold policies and controls. Guardrail products hold enforcement results. Model registries and deployment systems hold version history. Agent SDKs can capture prompts, retrievals, tool calls, and responses. None of these fragments alone establishes whether a particular AI decision was wrong, whether the available evidence is sufficient to reconstruct it, whether a proposed change fixed it, or whether the same failure can be prevented from returning.

This paper proposes the **Decision Evidence Protocol (DEP)**, an open, vendor-neutral protocol for exchanging observations, decision-time context, assessments, review decisions, evidence bundles, and bounded verification claims.

DEP does not replace observability, governance, evaluation, ticketing, policy, business, or agent platforms. It allows those systems to contribute independently owned evidence to a portable Decision Evidence Record while preserving provenance, authority, time, and uncertainty. Any conforming processor may use that record for investigation, evaluation, replay, remediation verification, audit, or release control.

DEP standardizes evidence, not judgment. It does not mandate how an implementation identifies anomalies, resolves ambiguous identities, ranks findings, determines business severity, or chooses remediation. Its central design principle is simple: **facts, context, assessments, and assurance claims must never be conflated**.

## 1. The Problem

AI systems make consequential decisions across multiple technical and organizational boundaries. A single decision may depend on:

- application input;
- conversation or case history;
- retrieved documents;
- model and prompt versions;
- agent memory;
- MCP tools or external APIs;
- policy and guardrail versions;
- human approvals or overrides;
- downstream business outcomes;
- the release that introduced or fixed the behavior.

These records rarely live in one system. Even when an organization has complete telemetry, telemetry answers only what was recorded. It does not automatically establish which policy applied, what outcome was expected, whether two cases are genuinely comparable, or whether the record is complete enough for replay.

This produces three recurring failures.

### 1.1 Collection without meaning

Trace and log systems can show what an agent did, but the business meaning of the action often lives elsewhere. A denial is not necessarily wrong. A policy result is not useful unless it can be linked to the policy version effective at the time of the decision.

### 1.2 Evaluation without evidentiary boundaries

Evaluators can assign scores and labels to production traces, but an evaluation result is an assessment produced by a particular evaluator. It is not an observed fact, and it does not prove that all relevant context was available.

### 1.3 Remediation without durable proof

Ticketing and governance systems can record that a remediation was completed. Evaluation systems can show that aggregate scores improved. Neither necessarily proves that a specific change corrected a specific production failure under the recorded conditions, or that the failure has become a permanent release test.

## 2. Market and Standards Context

DEP begins from the assumption that adjacent platforms are useful and should remain in place.

Observability and evaluation platforms already capture traces, run online evaluators, create datasets, and support CI/CD quality checks. LangSmith provides production tracing, online and offline evaluation, automation rules, annotation workflows, datasets, and quality-gate patterns. Langfuse organizes generations, tool calls, retrieval steps, traces, sessions, and human or automated scores. Arize AX runs evaluations over spans, traces, sessions, and experiments and supports deployment gating. Braintrust scores production traces, turns selected traces into versioned datasets, and runs evaluations in CI/CD. These are meaningful capabilities that DEP can connect without replacing. See [LangSmith Evaluation](https://docs.langchain.com/langsmith/evaluation), [Langfuse Observability](https://langfuse.com/docs/observability/overview), [Arize AX](https://arize.com/docs/ax), and [Braintrust Evaluation](https://www.braintrust.dev/docs/evaluate).

Governance and guardrail systems also hold valuable context. WhyLabs manages versioned guardrail policies and actions. Credo AI describes a governance knowledge layer connecting regulations, risks, controls, systems, and business context. Microsoft Purview discovers AI applications and agents, collects interaction and policy signals, and assesses data security posture. See [WhyLabs Secure Policy](https://docs.whylabs.ai/docs/secure/whylabs-policy/), [Credo AI Platform](https://www.credo.ai/product), and [Microsoft Purview DSPM](https://learn.microsoft.com/en-us/purview/data-security-posture-management-learn-about).

Several open standards provide foundations that DEP should reuse:

- The [Model Context Protocol](https://modelcontextprotocol.io/docs/learn/architecture) defines how AI applications discover and invoke tools, resources, and prompts.
- The [Agent2Agent Protocol](https://github.com/a2aproject/A2A/blob/main/docs/specification.md) defines capability discovery and task collaboration between independent agents.
- [CloudEvents](https://www.cncf.io/projects/cloudevents/) standardizes interoperable event metadata and transport bindings.
- [OpenTelemetry GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/) describe model, agent, retrieval, and tool telemetry.
- The [in-toto Attestation Framework](https://github.com/in-toto/attestation/blob/main/spec/README.md) defines statements, predicates, envelopes, and bundles for authenticated claims about immutable subjects.

These standards solve transport, agent interaction, telemetry vocabulary, and attestation structure. They do not define how heterogeneous AI decision evidence is bound to the business context effective at decision time, how evidence sufficiency controls which evaluations may run, or how a production finding is connected to a verified fix and recurrence gate.

Emerging evidence protocols reinforce the need for this layer while addressing narrower boundaries. The [Verifiable Evidence Interchange Protocol](https://veraxis.io/) describes a pre-commit evidence pack for consequential institutional actions. The [VeritasChain Protocol](https://veritaschain.org/) defines cryptographic decision trails for algorithmic and AI-driven trading. DEP differs in scope: it defines a general, cross-provider record that can be assembled progressively before or after a decision, carries explicit decision-time context and epistemic status, and supports investigation through bounded remediation verification without prescribing an execution gateway or industry domain.

As of this paper's publication, the reviewed official specifications and product documentation do not describe a single vendor-neutral contract combining all of the following:

- cross-provider AI decision evidence;
- temporal context applicability;
- explicit epistemic status;
- prerequisite-aware evaluation;
- human incident promotion;
- sealed reconstruction;
- fix-specific before-and-after verification;
- bounded assurance claims; and
- recurrence prevention derived from the verified incident.

DEP is designed around that combination. This is a statement about the architecture described in reviewed public materials, not a claim that no private or unpublished implementation could exist.

## 3. The Thesis

AI assurance requires an interoperability layer organized around the decision under review.

```text
Observed decision
  + context effective at decision time
  + evaluator prerequisites
  + source provenance
  + human review authority
  + reconstruction evidence
  + change identity
= bounded assurance claim
```

DEP makes these pieces portable. It permits independent providers, processors, evaluators, custodians, reviewers, and verifiers to participate without requiring one vendor to own the entire evidence chain.

## 4. Design Principles

### 4.1 Vendor neutrality

DEP identifies provider roles and resource types, not preferred vendors. A trace may come from an observability platform, OpenTelemetry, an application database, or an instrumented SDK. A policy may come from a governance platform, guardrail system, source repository, policy engine, or uploaded document.

### 4.2 Evidence honesty

The system must distinguish what was observed from what was asserted, derived, inferred, confirmed, or missing. Integrity does not imply completeness, and authenticity does not imply applicability.

### 4.3 Progressive completeness

A Decision Evidence Record may begin with one observation and accumulate context over time. Conforming consumers expose what is available, what is missing, and which operations the current evidence can support. DEP does not require comprehensive integration before evidence can be exchanged.

### 4.4 Explicit authority

Authority is represented as evidence, not assumed from system behavior. Deterministic rules, provider assertions, human decisions, and model-generated assessments remain distinguishable. AI-generated mappings or conclusions remain `inferred` until an authorized actor or deterministic procedure confirms them.

### 4.5 Reuse before invention

DEP uses CloudEvents-compatible exchange envelopes, OpenTelemetry-compatible telemetry references, URI-addressed schemas, and in-toto/DSSE-compatible signed attestations. It defines new semantics only where existing standards do not.

### 4.6 Bounded claims

Every verification claim identifies its subject, evidence, method, prerequisites, limitations, and result. No certificate may imply that unobserved behavior was captured or that a provider's assertion was independently proven when it was merely imported.

## 5. Protocol Architecture

```text
Providers
  Observability | Governance | Guardrails | Business Outcomes | SDK | CI/CD
       |
       v
DEP Exchange Layer
  Provider discovery | envelopes | schemas | provenance | integrity
       |
       v
DEP Consumers and Processors
  Normalize | link | evaluate | review | preserve
       |
       v
DEP Evidence Operations
  Bundle | replay | verify | attest | export
       |
       v
Independent Consumers
  Audit | remediation | release control | regulatory examination
```

The architecture separates evidence responsibilities so no single implementation must perform every role.

### 5.1 Acquisition plane

Source adapters receive files, database rows, object-store exports, OTLP telemetry, webhooks, SDK cassettes, policy artifacts, labels, and system manifests. Adapters handle transport and source authentication. They do not decide what a record means.

### 5.2 Normalization plane

Normalizers convert provider-specific payloads into DEP resources while retaining the original payload or a content-addressed reference. Every transformation is recorded so a consumer can trace a normalized field back to its source.

### 5.3 Linking plane

A processor may link observations to policies, expected outcomes, guardrails, evidence requirements, system identities, and deployments. Context bindings include subject scope, effective time, provenance, precedence, and confirmation status. DEP specifies the representation of a binding, not the algorithm used to propose it.

### 5.4 Assessment plane

Evaluators declare their prerequisites and emit versioned Assessments. A processor records which checks executed, skipped, or failed. Findings identify their supporting evidence, unavailable context, method, and authority. DEP does not prescribe evaluator implementation or ranking behavior.

### 5.5 Verification plane

Authorized review may promote a candidate to an incident. Evidence custodians may seal selected resources into bundles. Verifiers may replay or otherwise test immutable subjects and issue bounded claims. Downstream consumers decide how those claims affect audit, remediation, scenarios, or release gates.

## 6. Decision Evidence Protocol

DEP is a semantic protocol with multiple transport profiles. It defines resources, relationships, lifecycle rules, provenance, integrity, and capability discovery. It does not require a specific message broker, database, cloud, or programming language.

Normative protocol requirements begin in this section. Implementations claim only the conformance profiles they support.

### 6.1 Provider roles

A DEP provider advertises one or more roles:

- **Observation Provider:** supplies decisions, traces, spans, tool activity, retrievals, inputs, outputs, or downstream effects.
- **Context Provider:** supplies policies, guardrails, expected outcomes, evidence requirements, system manifests, or deployments.
- **Evaluator:** evaluates declared inputs and emits assessments.
- **Reviewer:** records an authoritative disposition of a candidate.
- **Evidence Custodian:** preserves and seals evidence bundles.
- **Verifier:** validates integrity and produces bounded verification claims.
- **Gate Consumer:** consumes verified scenarios or claims for a release decision.

A provider role states capability, not trust. Consumers independently decide which identities and signatures they trust for each claim type.

### 6.2 Capability discovery

HTTP-capable providers SHOULD publish a DEP Provider Card at:

```text
/.well-known/dep.json
```

The card identifies:

```json
{
  "protocol_versions": ["0.1"],
  "provider_id": "urn:provider:example-observability",
  "roles": ["observation_provider", "evaluator"],
  "resource_types": [
    "org.dep.observation.trace.v1",
    "org.dep.assessment.v1"
  ],
  "transports": ["https", "cloudevents-http", "batch-jsonl"],
  "auth": ["oauth2-client-credentials"],
  "integrity": ["sha-256", "dsse-ed25519"],
  "limits": {"max_batch_items": 1000, "max_inline_bytes": 1048576}
}
```

Capability discovery borrows the useful pattern of MCP initialization and A2A Agent Cards without adopting their task or tool semantics.

### 6.3 Exchange envelope

DEP exchange messages use a CloudEvents-compatible envelope:

```json
{
  "specversion": "1.0",
  "id": "01JAV2R4QW8ZQPFYVQ7H7NQY2A",
  "type": "org.dep.observation.decision.v1",
  "source": "urn:langfuse:project:customer-support",
  "subject": "urn:decision:CASE-1042",
  "time": "2026-07-22T14:31:00Z",
  "datacontenttype": "application/json",
  "dataschema": "urn:dep:schema:observation-decision:v1",
  "deporg": "urn:org:customer",
  "depenvironment": "production",
  "data": {
    "actual_outcome": "DENY",
    "agent_ref": "urn:agent:lending:v7",
    "evidence_refs": ["urn:trace:8f21"]
  },
  "provenance": {
    "epistemic_status": "observed",
    "provider_object_id": "trace-8f21",
    "collected_at": "2026-07-22T14:35:00Z",
    "transformations": []
  },
  "integrity": {
    "algorithm": "sha-256",
    "digest": "..."
  },
  "relationships": []
}
```

CloudEvents extension attributes remain scalar. DEP-specific structured metadata is carried in the event data according to the referenced DEP schema.

### 6.4 Resource identity

Every resource MUST have a stable URI or URN. Identity is independent of storage location. Providers SHOULD preserve their native identifier in provenance while assigning or accepting a globally scoped DEP subject identifier.

Two resources with different identifiers MUST NOT be treated as identical solely because selected fields match. Deduplication is an explicit, reversible assessment.

### 6.5 Core resource families

#### Observation

An `Observation` represents something recorded as having occurred. Types include:

- decision;
- input;
- model interaction;
- retrieval;
- tool request;
- tool response;
- policy-engine result;
- guardrail result;
- human action;
- downstream business effect;
- deployment event.

An Observation does not claim completeness or correctness.

#### ContextArtifact

A `ContextArtifact` represents information used to interpret observations. Types include:

- policy;
- guardrail;
- expected outcome;
- evidence requirement;
- system manifest;
- model, prompt, or agent version;
- decision-family definition;
- cohort definition;
- evaluator definition;
- approved suppression.

Artifacts are versioned and immutable once referenced by digest. A mutable external document may produce multiple artifact versions.

#### ContextBinding

A `ContextBinding` states that a context artifact applies to a subject under specified conditions:

```json
{
  "subject_ref": "urn:decision:CASE-1042",
  "context_ref": "urn:policy:lending:3.2",
  "relationship": "governed-by",
  "effective_from": "2026-06-01T00:00:00Z",
  "effective_until": null,
  "selector": {"jurisdiction": "CA", "product": "personal-loan"},
  "basis": "customer_confirmed",
  "precedence": 100
}
```

The binding is a claim about applicability and has its own provenance. It is not inferred from physical proximity in a trace.

#### Assessment

An `Assessment` is the output of an evaluator. It MUST identify:

- evaluator identity and version;
- inputs and context used;
- rule, prompt, or method;
- output label or score;
- deterministic or probabilistic method;
- execution time;
- limitations and errors.

LLM-as-judge output is always an Assessment with `epistemic_status: inferred` unless a human confirms it.

#### Finding

A `Finding` is a candidate assurance concern assembled from one or more observations, bindings, and assessments. It includes:

- finding type;
- affected decision or decision family;
- basis references;
- missing prerequisites;
- evidence grade;
- severity and business impact, when provided;
- current lifecycle state;
- deduplication or cluster membership;
- available next actions.

A Finding is not an Incident until an authorized ReviewDecision promotes it.

#### ReviewDecision

A `ReviewDecision` records an authorized human or configured authority action:

- approve as incident;
- dismiss with reason;
- request context;
- suppress under defined conditions;
- mark accepted risk;
- instrument the next occurrence.

Review decisions are append-only. Corrections supersede prior decisions without deleting them.

#### EvidenceBundle

An `EvidenceBundle` is a manifest of immutable or content-addressed subjects selected for investigation or verification. The bundle includes source references, digests, bindings, transformations, redactions, custody events, and declared omissions.

An EvidenceBundle may be carried as an in-toto bundle. Signed DEP claims SHOULD use an in-toto Statement with a DEP predicate and a DSSE-compatible envelope. This separates transport metadata from authenticated claim content.

#### VerificationClaim

A `VerificationClaim` describes what was tested or verified. It includes:

- immutable subjects;
- original and candidate system versions;
- replay or verification method;
- expected and observed behavior;
- result;
- evaluator versions;
- evidence grade;
- scope limitations;
- signature and verifier identity.

Verification claims MUST NOT use unbounded language such as "safe," "compliant," or "correct" without a separately defined and supported claim scope.

### 6.6 Epistemic status

DEP defines the following statuses:

- `observed`: directly recorded by an identified source;
- `asserted_by_provider`: claimed by an external provider but not independently established;
- `customer_confirmed`: explicitly confirmed by an authorized customer actor;
- `derived`: produced through a deterministic, recorded transformation;
- `inferred`: generated through heuristic, statistical, or model-based reasoning;
- `missing`: required for a proposed operation but unavailable;
- `conflicted`: two or more applicable sources disagree without a resolved precedence.

Consumers MUST preserve epistemic status through transformations. A derived value cannot silently become observed, and a signed inference does not become a fact merely because its signature is valid.

### 6.7 Relationship vocabulary

DEP v0.1 defines:

```text
describes          resource describes subject
derived-from       resource was transformed from another resource
governed-by        policy or control applies to subject
expected-by        expected outcome applies to subject
constrained-by     guardrail applies to subject
produced-by        system or version produced observation
corroborates       independent resource supports another
contradicts        resource materially disagrees with another
supersedes         resource replaces an earlier version or decision
included-in        resource is part of an evidence bundle
evaluated-by       assessment was produced by evaluator
reviewed-by        finding was dispositioned by reviewer
verified-by        claim was produced by verifier
remediated-by      finding is connected to a proposed change
prevents           scenario or gate is intended to prevent recurrence
```

Extension relationships MUST use URI-qualified names.

### 6.8 Transport profiles

DEP v0.1 defines four profiles:

1. **HTTP exchange:** individual resources and queryable manifests.
2. **CloudEvents push:** asynchronous event delivery over supported CloudEvents bindings.
3. **Batch bundle:** JSONL or archive manifests for exports and air-gapped transfer.
4. **OTLP bridge:** deterministic mapping from OpenTelemetry traces and attributes into DEP Observations.

SDK capture is an Observation Provider profile, not a separate evidence ontology.

### 6.9 Redaction and external references

Sensitive or large payloads SHOULD be referenced rather than embedded:

```json
{
  "uri": "s3://customer-evidence/trace-8f21.json",
  "media_type": "application/json",
  "digest": {"sha256": "..."},
  "access_class": "restricted",
  "redactions": ["customer.ssn", "prompt.free_text"]
}
```

A redacted artifact is a distinct representation with its own digest and a relationship to the source artifact. Redaction MUST NOT be invisible.

### 6.10 Idempotency and ordering

Providers MUST use stable event identifiers. Consumers MUST treat re-delivery of the same identifier and digest as idempotent. Reuse of an identifier with a different digest is an integrity conflict.

DEP does not assume global ordering. Relationships and source sequence numbers establish local ordering. Reproducible processing manifests freeze the exact resource versions and bindings used.

## 7. The Decision Evidence Record

A **Decision Evidence Record (DER)** is the portable logical record for one decision or decision family. It consists of DEP resources and typed relationships. It is not a required storage format and does not require a graph database.

Graph nodes are DEP resources. Edges are typed relationships and ContextBindings. The graph is temporal: a processor evaluates applicability at the decision timestamp, not merely at the current time.

A DER MAY be incomplete. Completeness is always evaluated relative to a declared purpose, such as investigation, policy evaluation, deterministic replay, or remediation verification. A producer MUST NOT claim that a record is complete without identifying the completeness profile and evidence requirements used.

### 7.1 Resolution hierarchy

Context is resolved using the following precedence:

1. exact decision binding;
2. case or session binding;
3. decision-family binding;
4. system or agent-version binding;
5. environment binding;
6. organization default.

Within the same scope, explicit customer confirmation outranks provider assertion, which outranks inference. Effective time and selector conditions must also match.

A conforming processor MUST NOT silently choose between equally authoritative conflicting artifacts. It emits a context conflict and prevents evaluators requiring that context from making an authoritative determination. DEP specifies this safety invariant but does not prescribe a resolver algorithm beyond the explicit applicability and authority fields carried by bindings.

### 7.2 Context sources

The graph can incorporate:

- traces and evaluations from observability providers;
- policy and control artifacts from governance platforms;
- guardrail definitions and enforcement results;
- human labels and downstream business outcomes;
- source-control commits and deployment versions;
- model, prompt, tool, and agent manifests;
- SDK cassettes and application logs;
- customer-confirmed mappings and decisions.

The record preserves source ownership. Importing context into another system does not transfer authorship or authority to that system.

## 8. Evidence Sufficiency Levels

DEP defines evidence sufficiency levels that communicate which operations a Decision Evidence Record may support. A sufficiency level is not an opaque confidence score and does not certify that a decision was correct.

| Grade | Meaning | Permitted interpretation |
|---|---|---|
| E0 | Observation only | Pattern or anomaly signal |
| E1 | Context linked | Candidate finding with identified basis |
| E2 | Authoritative context or corroborated outcome | Reviewable incident candidate |
| E3 | Sealed reconstruction material available | Replay and investigation eligible |
| E4 | Before-and-after fix verification completed | Bounded proof and scenario eligible |

Evidence grade is not severity. A catastrophic-looking outcome may remain E0 if context is missing. A low-severity issue may be E4 if fully reconstructed and verified.

Each evaluator declares a minimum evidence level and specific prerequisites. A conforming processor calculates the level from available resources and relationships; it MUST NOT estimate sufficiency with a probabilistic model. Implementations MAY define stricter profiles but MUST NOT weaken the meanings above.

## 9. Processing Model

DEP permits different products and organizations to process the same evidence differently while preserving interoperable inputs and outputs. A conforming processing flow may contain the following operations.

### 9.1 Receive and validate

The consumer validates envelope shape, schema version, resource identity, tenant scope, digest, signature when present, and declared provenance. Invalid resources are rejected or quarantined with a machine-readable reason.

### 9.2 Normalize without erasure

Provider-specific payloads may be transformed into DEP resources. The original payload or a content-addressed reference and the complete transformation history remain attached. Normalization MUST NOT silently upgrade authority or epistemic status.

### 9.3 Link identity and context

Processors may propose that resources concern the same decision, case, session, system, agent, or deployment. Ambiguous matches remain explicit assertions with provenance and confidence. Context applicability is represented with ContextBindings and effective-time fields.

### 9.4 Evaluate declared prerequisites

Before invoking an evaluator, a processor compares available resources with the evaluator contract. Missing prerequisites produce a recorded skip or evidence-gap Assessment, not a guessed authoritative result.

### 9.5 Emit explainable outputs

Assessments and Findings identify their input resources, context bindings, evaluator identity and version, method class, limitations, missing evidence, and authority. A consumer must be able to inspect the basis of an individual output even when the producing algorithm is proprietary.

### 9.6 Preserve reproducibility

A `ProcessingManifest` identifies the frozen inputs, context bindings, evaluator versions, parameters, start and completion times, and executed, skipped, failed, or suppressed operations. Re-running the same manifest MUST reproduce deterministic outputs. Probabilistic methods record sufficient configuration to characterize, but not promise, repeatability.

### 9.7 Review and supersede

Authorized actors may approve, dismiss, enrich, suppress, accept risk, or request additional evidence. Review decisions are append-only resources. Corrections supersede earlier decisions rather than deleting history.

DEP does not specify source profiling, identity-resolution algorithms, context-ranking rules, evaluator implementations, candidate clustering, prioritization, user experience, or remediation workflow. Those remain implementation choices.

## 10. Evaluator Contracts

Every evaluator publishes a machine-readable contract:

```json
{
  "evaluator_id": "urn:dep:evaluator:expected-outcome-mismatch:v1",
  "method": "deterministic",
  "requires": [
    "observation.decision.actual_outcome",
    "context.expected_outcome.value",
    "binding.expected-by"
  ],
  "minimum_evidence_grade": "E1",
  "produces": "assessment.expected-outcome-mismatch",
  "authority": "candidate_only"
}
```

### 10.1 Policy mismatch

**Requires:** observed decision, applicable structured policy rule, policy-relevant inputs, and decision-time binding.

**Produces:** expected and actual outcome, rule identifier, policy version, evaluation trace, and missing inputs.

A policy document parsed by AI becomes a draft ContextArtifact. It cannot support an authoritative mismatch until confirmed or supplied in an executable form.

### 10.2 Expected-outcome mismatch

**Requires:** observed decision and authoritative or customer-confirmed expected outcome linked to the same subject.

**Produces:** normalized expected and actual values plus source provenance.

### 10.3 Missing evidence

**Requires:** an applicable EvidenceRequirement and the observed evidence manifest.

**Produces:** present, missing, redacted, and unverifiable fields. This evaluator can create a supported finding even when the underlying decision cannot be judged.

### 10.4 Guardrail violation

**Requires:** observed action or guardrail result, applicable GuardrailArtifact, and relevant threshold or permission inputs.

**Produces:** rule, action, limit, enforcement result, and side-effect status.

### 10.5 Consistency mismatch

**Requires:** a customer-confirmed cohort definition, visible comparison fields, outcome normalization, and an allowed-variance rule.

**Produces:** cohort membership, differences, outcome divergence, and hidden-context warnings.

Without a confirmed cohort definition, a processor may produce a similarity signal but not a consistency violation.

### 10.6 Replayability failure

**Requires:** applicable ReplayRequirement and observed evidence manifest.

**Produces:** replayability level, missing cassette elements, mutable dependencies, unsupported tools, and recommended capture action.

## 11. Portable Finding Lifecycle

```text
signal
  -> candidate
  -> needs_context | reviewable
  -> approved_incident | dismissed | accepted_risk | suppressed
  -> evidence_sealed
  -> replayed
  -> fix_verified
  -> proof_issued
  -> scenario_active
  -> gate_enforced
```

Automated systems MAY create signals and candidates. Formal incident promotion requires an authorized ReviewDecision unless the governing organization has explicitly delegated that authority to a deterministic rule. Delegated automation must be visible and revocable.

Dismissal is valuable context. A dismissal records why the case was acceptable and which future records the explanation may cover. A processor must not generalize a dismissal beyond its declared scope.

## 12. Evidence Bundling and Verification

DEP defines the portable boundary between a reviewed finding and a verification claim. It does not mandate a particular replay or remediation product.

It performs five checks:

1. Is there an authorized incident decision?
2. Are the evidence subjects identified and immutable?
3. Is the reconstruction method supportable?
4. Is the proposed change identified by immutable version or digest?
5. Is the expected corrected behavior explicit?

If the checks pass, a custodian may create a sealed EvidenceBundle and a verifier may create a VerificationClaim. If they do not, the processor returns exact prerequisites rather than a generic failure.

Historical evidence that cannot reconstruct the original conditions must not be presented as deterministic replay. The allowed paths are:

- enrich with recoverable evidence;
- run a clearly labeled isolated reproduction;
- instrument the decision family and capture the next occurrence; or
- retain the finding as non-proof-eligible.

Re-running an agent against current live APIs is not equivalent to reconstructing a historical decision. Mutable data and side effects make live reproduction a separate claim type.

## 13. Interoperability Model

DEP treats existing systems as puzzle-piece providers and result consumers.

| Provider category | DEP input | DEP output returned |
|---|---|---|
| Observability | traces, spans, tool calls, evals | incident disposition, proof reference, scenario reference |
| Governance | policies, controls, inventory, risk context | verified claim, remediation evidence, coverage status |
| Guardrails | rules, thresholds, enforcement results | verified violation or false-positive disposition |
| Business systems | human outcomes, case resolution, side effects | investigation and remediation status |
| Source control and CI | commit, build, deployment identity | scenario and release-gate result |
| SDK and OTLP | detailed runtime evidence | replayability and capture-quality feedback |

DEP favors broad compatibility through OTLP, CloudEvents, webhooks, batch bundles, and generic APIs. Implementations may add native integrations when they provide unique evidence, stronger identity guarantees, or better preservation of source semantics.

## 14. Security and Privacy

### 14.1 Data minimization

Providers should disclose metadata and content references separately. Raw prompts, retrieved documents, tool results, and customer data are not required when a digest and controlled retrieval reference can satisfy the operation.

### 14.2 Tenant isolation

Organization and environment scope are mandatory. Cross-tenant context resolution is forbidden unless an explicit federation policy authorizes it.

### 14.3 Authentication and authorization

Transport profiles must use established mechanisms such as OAuth 2.0, mutual TLS, workload identity, or signed batch bundles. Credentials never appear inside DEP resources.

Authorization is resource- and role-aware. Permission to submit an Observation does not imply permission to approve an Incident or issue a VerificationClaim.

### 14.4 Integrity

Every material resource should carry a digest. Signed claims use an authenticated envelope. Verification checks the signature, subject digest, predicate type, issuer trust, expiry, revocation status, and declared scope.

### 14.5 Replay safety

Replay is side-effect-free by default. Tool calls use sealed cassette responses or explicit mocks. Network access, writes, payments, notifications, and external mutations require isolated sandbox policy and affirmative authorization.

### 14.6 Retention and deletion

DEP preserves provenance when content is deleted. A tombstone may retain identifier, digest, deletion authority, timestamp, and reason without retaining the sensitive payload.

## 15. What Is Novel

The Decision Evidence Layer does not claim novelty for traces, evaluators, datasets, policy registries, event envelopes, cryptographic signatures, or CI gates individually.

Its distinctive architecture is the combination of:

1. **A decision-centric interchange protocol:** heterogeneous providers contribute independently owned evidence to one decision subject.
2. **Temporal context bindings:** policies, guardrails, outcomes, and versions are resolved according to their applicability at decision time.
3. **Epistemic typing:** observed, asserted, confirmed, derived, inferred, missing, and conflicted information remain distinguishable throughout the lifecycle.
4. **Prerequisite-aware evaluation:** processors evaluate only what available context can support and expose skipped checks as first-class results.
5. **Evidence grades tied to permitted operations:** anomaly detection, incident review, replay, and proof have explicit sufficiency boundaries.
6. **Human authority as protocol data:** approval, dismissal, suppression, and accepted risk are portable, versioned assurance resources.
7. **Fix-specific lineage:** a production failure is connected to an immutable proposed change, before-and-after verification, and a bounded claim.
8. **Recurrence conversion:** the verified incident becomes a durable scenario and future gate input.
9. **Vendor-neutral portability:** the assurance chain survives changes in observability, governance, model, cloud, or agent vendors.

The protocol contribution is not another log format. It is a portable model for preserving the meaning and evidentiary boundaries of a real decision from observation through verification.

## 16. Example: Lending Decision

### 16.1 Provider inputs

```text
Langfuse trace
  decision: DENY
  bureau tool result: evidence unavailable
  agent version: lending-agent-v7

Governance policy
  missing bureau evidence -> UNDERWRITING_REVIEW
  version: lending-policy-3.2

Loan operations outcome
  human resolution: UNDERWRITING_REVIEW

GitHub deployment
  candidate fix: commit abc123
```

### 16.2 Context resolution

The processor binds policy 3.2 to the decision because its effective dates, product, jurisdiction, and system selectors match. The operations outcome corroborates the policy expectation. The trace supplies the actual decision and bureau response.

### 16.3 Processor result

```text
Finding: expected-outcome and policy mismatch
Actual: DENY
Expected: UNDERWRITING_REVIEW
Evidence grade: E2
Replayability: partial
Missing: sealed model response and prompt configuration
Available actions: review, enrich, instrument next occurrence
```

### 16.4 Enrichment and proof

An SDK cassette supplies the missing model response and configuration. The EvidenceBundle reaches E3. A reviewer approves the candidate as an incident. A conforming verifier replays the original cassette against the original version, applies commit `abc123`, verifies the corrected outcome, and issues an E4 VerificationClaim.

### 16.5 Recurrence prevention

The incident becomes a scenario pinned to the evidence bundle and expected behavior. Future agent releases run the scenario. Gate results reference the original incident, verified fix, and current candidate version.

## 17. Initial Conformance Suite

A DEP implementation should pass at least these scenarios:

1. Trace, policy, outcome, and deployment come from four providers and resolve to one decision.
2. Two applicable policy versions conflict and the processor refuses an authoritative policy mismatch result.
3. An evaluator score is signed but its required input is missing; the signature verifies while the assessment remains insufficient.
4. A redacted artifact retains verifiable lineage to its source without exposing removed content.
5. Re-delivery of an identical resource is idempotent; reuse of its identifier with a new digest raises an integrity conflict.
6. A probabilistic evaluator produces a candidate but cannot automatically issue an incident or proof.
7. A dismissed finding creates a scoped suppression that does not hide unrelated future decisions.
8. A historical record without replay evidence is routed to enrichment or future instrumentation.
9. A fix verification claim identifies original version, candidate version, evidence bundle, method, expected result, and limitations.
10. A verifier can validate the claim without access to the issuer's internal database.

## 18. Conformance Profiles

Conformance is capability-based. An implementation claims only the profiles it supports.

The machine-readable schemas for this draft are published in [`schemas/dep`](../../schemas/dep/). Schema validation is necessary but not sufficient for conformance; implementations must also satisfy the behavioral requirements for the profiles they claim.

### 18.1 Provider profile

A conforming provider publishes a Provider Card, emits schema-valid resources, uses stable identifiers, preserves source provenance, and implements at least one transport profile.

### 18.2 Processor profile

A conforming processor preserves immutable source lineage, does not silently upgrade epistemic status, records context conflicts, checks evaluator prerequisites, and emits a ProcessingManifest for reproducible operations.

### 18.3 Evaluator profile

A conforming evaluator publishes an Evaluator Contract and emits Assessments identifying its frozen inputs, method class, version, result, limitations, and errors.

### 18.4 Custodian profile

A conforming custodian produces content-addressed EvidenceBundles, records transformations and redactions, preserves custody events, and exposes integrity material required by authorized verifiers.

### 18.5 Verifier profile

A conforming verifier validates subject digests, signatures, issuer identity, claim scope, method, limitations, expiry, and revocation status. Verification MUST be possible without trusting undocumented issuer behavior.

### 18.6 Full-chain profile

A full-chain conformance test combines resources from multiple providers, resolves them to one Decision Evidence Record, records conflicts and missing prerequisites, produces an authorized review decision, seals an EvidenceBundle, and validates a bounded VerificationClaim with an independent verifier.

## 19. Explicit Non-Goals

DEP is not:

- an agent orchestration protocol;
- a replacement for MCP or A2A;
- a telemetry backend;
- a universal policy language;
- an LLM evaluation marketplace;
- a GRC system of record;
- a guarantee that every relevant event was captured;
- an automatic declaration of legal or regulatory compliance;
- permission to replay production side effects.

## 20. Open Governance

DEP is an open, implementation-neutral specification. Its schemas, examples, validation rules, test vectors, and verifier behavior are publicly inspectable. No vendor owns evidence produced by another conforming participant merely by processing or transporting it.

The public change process, decision authority, versioning rules, namespace policy, conformance policy, and transition to multi-stakeholder stewardship are defined in [DEP Governance](governance.md). Conformance does not require publication of source code, evaluator logic, ranking algorithms, or internal data structures. It requires interoperable resources, observable safety invariants, portable claims, and independently testable behavior at the protocol boundary.

## 21. Conclusion

The AI ecosystem does not lack logs, traces, evaluators, policies, or dashboards. It lacks a common assurance contract that preserves what each source actually knows, determines what context applied to a specific decision, prevents unsupported evaluations from becoming false incidents, and connects a supported production failure to a verified fix and durable recurrence gate.

DEP addresses that gap by making observations, context, assessments, review decisions, evidence bundles, and verification claims interoperable without collapsing their trust boundaries.

The resulting protocol does not compete with observability, governance, guardrail, business, or agent platforms. It gives their data a shared evidentiary purpose:

```text
Find what matters.
Show what is known.
Expose what is missing.
Verify the fix.
Prevent recurrence.
```
