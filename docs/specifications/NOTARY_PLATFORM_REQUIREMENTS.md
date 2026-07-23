# Notary Platform Requirements

**Revision:** Decision Evidence Protocol and Notary Sweep Engine integration, July 2026
**Source baseline:** `Test_Project_-_Copy_Combined_Requirements-3.md`
**Protocol reference:** [Decision Evidence Protocol](../dep/README.md)

## Table of Contents

### Overview Documents
- [Business Problem](#business-problem)
- [Current State](#current-state)
- [Product Description](#product-description)
- [Personas](#personas)
- [Success Metrics](#success-metrics)
- [Technical Requirements](#technical-requirements)
- [Competitive Landscape](#competitive-landscape)
- [Product Direction and Phases](#product-direction-and-phases)
- [Positioning and Messaging](#positioning-and-messaging)

### Feature Requirements
- [Forensic Agent Logger SDK](#forensic-agent-logger-sdk)
  - [Decision Evidence Graph Capture](#decision-evidence-graph-capture)
  - [Decision Context and Risk Metadata](#decision-context-and-risk-metadata)
- [Forensics Platform](#forensics-platform)
  - [Deterministic Replay](#deterministic-replay)
  - [Mutation Testing](#mutation-testing)
  - [Proof of Mitigation Certificates](#proof-of-mitigation-certificates)
  - [Compliance Reporting](#compliance-reporting)
  - [Branching and Experiments](#branching-and-experiments)
  - [Automated Incident Replay](#automated-incident-replay)
  - [Scenario Library](#scenario-library)
    - [Testing Playground](#testing-playground)
    - [Evidence Export](#evidence-export)
    - [Scenario Intelligence](#scenario-intelligence)
  - [Capture Rules and Decision Triggers](#capture-rules-and-decision-triggers)
    - [Manual Submission and Source-System Connectors](#manual-submission-and-source-system-connectors)
  - [Proof of Readiness](#proof-of-readiness)
  - [Data Lifecycle and Retention](#data-lifecycle-and-retention)
  - [Proof Claim Scope and Label Provenance](#proof-claim-scope-and-label-provenance)
- [GRC Integrations](#grc-integrations)
- [Web Dashboard](#web-dashboard)
- [Tiers and Entitlements](#tiers-and-entitlements)
- [Decision Evidence Discovery and Sweep](#decision-evidence-discovery-and-sweep)

---

# Overview Documents

## Business Problem

## The Regulatory Forensics Gap

Enterprises increasingly deploy autonomous AI agents in high-stakes, regulated domains: lending decisions, insurance claims processing, healthcare prior authorizations, and supply chain vendor selection. When these agents fail in production—denying a qualified loan applicant, misclassifying fraud, selecting the wrong vendor—the consequences are severe: regulatory fines ranging from $5M to $500M, litigation liability, and direct customer harm.

Today, compliance teams can see *what* happened through observability platforms, but they cannot prove *why* it happened or demonstrate that a fix will prevent recurrence. This is the regulatory forensics gap. Observability platforms such as Datadog, LangSmith, and Langfuse produce event logs: an error occurred, a particular model was invoked, an API was called, a response was returned. This is essential for operational monitoring, but it does not answer the forensic question regulators and courts demand: why did the agent's logic diverge, and how do we verify a fix works?

## The Compliance Liability Problem

Regulators are creating requirements that observability cannot satisfy. The EU AI Act (Regulation EU 2024/1689, Article 10) mandates detailed records of high-risk AI decisions and demonstrable human oversight. The NIST AI Risk Management Framework requires documented decisions and audit trails. Proposed SEC AI disclosure rules require public companies to disclose material AI failures and demonstrate remediation. OCC guidance requires banks to have mechanisms addressing model defects, bias, and errors.

The enforcement gap is concrete: enterprises can show regulators what happened, but cannot provide forensic proof that a specific logic error caused the failure (not a transient glitch or external factor), that the fix will prevent recurrence (which requires deterministic testing, not assumptions), and that no tampering occurred between incident and remediation (which requires cryptographic proof). The result is that regulatory investigations drag on for 8 to 12 weeks, fines are larger due to a lack of evidence of good-faith remediation, and customer litigation proceeds without defensible proof.

## Anatomy of the Gap: Four Things Enterprises Cannot Prove Today

The phrase "forensics gap" is easy to say and easy to underestimate. Concretely, when a production AI decision is challenged, four distinct claims must each be provable, and today's tooling supports none of them end to end.

**Causation, not correlation.** Observability shows that an error occurred alongside a particular model call and API response, but correlation in a log timeline is not proof that the agent's logic — rather than a transient network fault, a stale cache, or an upstream data error — produced the wrong decision. Proving causation requires re-executing the exact decision and observing it recur; a log cannot do this.

**Remediation, not intention.** Deploying a fix demonstrates intent to remediate, not that the remediation works. "We changed the threshold and believe it is resolved" is an assertion. Proving remediation requires running the proposed fix against the exact conditions that produced the failure and showing the outcome changes — something no logging or monitoring system does, because monitoring observes production, it does not re-run counterfactuals.

**Integrity, not trust.** An evidence record is only defensible if its recipient does not have to trust the party that produced it. A log file an enterprise hands to a regulator can, in principle, have been edited; absent cryptographic sealing, the enterprise is asking the regulator to take its word. Proving integrity requires tamper-evidence that a third party can verify independently, without trusting the vendor or the enterprise.

**Durability, not freshness.** Observability is optimized for the recent past — hours or days — because its job is operational monitoring. Regulatory and litigation timelines run for years. An audit letter can arrive long after the incident, when the engineer who built the agent has left, the model version has been deprecated, and the surrounding systems have changed. Proving what happened years later requires evidence that is self-contained and reproducible independent of the environment that produced it. Retention of logs is not the same as reproducibility of a decision. This has a sharp architectural consequence: re-running a decision against a live provider test environment does not satisfy durability, because the provider can change or retire that test environment at any time, breaking reproducibility through no fault of the enterprise. Evidence must instead carry its own sealed record of the external responses it depended on — so the decision can be replayed from that record years later, whether or not the provider's systems still exist in the form they did at incident time.

Each of these is a different technical problem, and a tool built for one does not incidentally solve the others. This is why the gap has persisted despite a crowded observability and logging market: those tools were built to answer "what is happening now," and defensibility asks "prove what happened then, prove why, and prove the fix — to someone who does not trust you, years from now."

## Why This Cannot Be Retrofitted

The most common objection is that existing logging can be extended to close the gap. It cannot, for a structural reason: evidence produced as a byproduct of monitoring is telemetry, not audit material. Telemetry is sampled, mutable, schema-flexible, and retained on operational timescales — all appropriate for debugging and dashboards, and all disqualifying for defensible evidence. Audit-grade evidence has the opposite properties: it must be complete rather than sampled, immutable rather than editable, sealed at the moment of the decision rather than assembled afterward, and enduring rather than rotated out. These properties have to be designed into the capture path from the first line of instrumentation; they cannot be bolted on when the audit letter arrives, because the decisive moment — the instant the decision was made — has already passed and cannot be re-sealed after the fact.

This mirrors the data-integrity bar that mature regulated industries already enforce. In pharmaceutical and clinical systems, evidence is expected to be attributable, contemporaneous, original, accurate, and enduring — recorded at the time by an identified actor, in unaltered form, and preserved for the long term. AI governance is converging on the same bar for consequential automated decisions. An architecture that seals each decision at write time, chains it so any later alteration is detectable, and can reproduce it on demand satisfies that standard by construction; a logging pipeline that was never designed for it does not, no matter how much retention is added.

The remaining gap is sharpest at the remediation step. A wave of new entrants now produces signed, replayable evidence of what a system decided — the causation and integrity claims above are increasingly contested. But re-deriving the original verdict proves only what happened; it does not run a corrected agent against the real failing conditions to prove the fix resolves it. That remediation-proof loop — capture the incident, replay it against the real external system, apply the fix, and certify the corrected outcome — is the part of the gap that remains genuinely unaddressed, and it is where this product is differentiated (the Competitive Landscape document develops this in detail).

## Why This Matters Now

The cost of the gap is measurable. In a 2023 lending AI failure, one major bank incorrectly denied qualified applicants; the regulatory investigation took six months and produced a $250M fine, with industry estimates attributing $100-125M of that to the absence of forensic evidence proving root cause and effective remediation. With purpose-built forensics, that proof could be generated within days, investigation time cut to two to three weeks, and fine severity reduced by an estimated 30-50% through documented good-faith remediation.

Unlike prior regulatory waves that were served by consultants and workflow tools, AI governance requires purpose-built forensics infrastructure. The regulatory tailwind is real, but its timing has shifted, and the runway is longer than a single deadline. The EU AI Act's high-risk obligations under Annex III — covering exactly these domains: credit decisions, insurance pricing, employment, and essential services — were formally deferred by the Digital Omnibus (adopted by the Council on June 29, 2026) from August 2, 2026 to December 2, 2027. Article 50 transparency duties and enforcement start dates remain on the August 2, 2026 schedule, but the record-keeping and tamper-evident logging obligations most relevant here now apply in December 2027. The demand is durable rather than a panic-buying spike, and it is compounded by NIST AI RMF, OCC guidance, and proposed SEC disclosure rules that do not depend on the EU timeline.

The longer runway changes the shape of demand rather than removing it, and it favors the shift-left extension of the same capability. Today the acute pain is reactive: proving why a decision failed after the fact. But the EU AI Act and NIST AI RMF are moving from "explain the failure" toward "prove the system was tested before it made a consequential decision," and the deferral gives enterprises time to adopt pre-deployment certification rather than only scrambling post-incident. The infrastructure that can deterministically prove a fix works is the same infrastructure that can certify an agent before deployment. Forensics is the entry point; pre-deployment certification is the same engine shifted left as demand expands. This sequencing matters: the ability to prove what happened is what earns the right to certify what will happen.

## Current State

## The Current AI Tooling Landscape

The AI tooling market is structured in layers, each solving a distinct part of the AI lifecycle but none addressing incident forensics:

* **Pre-deployment testing** (Pome, Confident AI, Armalo): Tests and scores agents before production to catch issues early. These tools operate before an incident ever occurs.
* **Observability and monitoring** (LangSmith, Langfuse, Laminar, Braintrust): Logs events and traces to show what happened during production runs. These tools capture data but do not prove causation or verify fixes.
* **Runtime governance** (Zenity, Modulos): Guards agent behavior in real time and enforces policies, but does not investigate failures after the fact.
* **Compliance and GRC** (OneTrust, ServiceNow, Sprinto, Drata): Manages compliance workflows and evidence, but consumes forensic evidence rather than generating it.

## The Gap Between Observability and Compliance

The layer between observability ("what happened?") and compliance ("prove it to regulators") is uncontested. No existing product owns AI incident forensics. This is structurally different from the crowded observability market (Datadog, New Relic, Splunk) or the crowded GRC market (OneTrust, ServiceNow), and the gap persists for concrete reasons:

* Traditional digital forensics companies (Exterro, Magnet) analyze static files and hard drives; they do not understand neural network logic or cloud API interactions.
* Observability companies optimize for real-time monitoring speed; forensics requires cryptographic proof, which is a fundamentally different architecture.
* Compliance tools manage workflows; they do not generate evidence.

## How Enterprises Cope Today

Without purpose-built forensics, compliance teams assemble evidence manually from observability logs, engineering assumptions, and consultant reports. Fixes are deployed based on "we think this works" rather than proof against the real incident scenario. Logs can be challenged as tampered with, because there is no cryptographic chain of custody. Investigations stretch across weeks or months, fines are inflated by the absence of defensible evidence, and litigation proceeds without admissible proof of root cause or remediation. This manual, assumption-driven process is the state that Notary replaces.

## Product Description

## What Notary Is

Notary is an **AI Decision Assurance** platform. It captures real AI decisions, human overrides, disputes, and incidents as sealed replayable evidence; verifies fixes against the same recorded conditions; and turns resolved failures into regression scenarios that gate future releases. Customers buy two outcomes: defensible proof for compliance and recurrence prevention for the business. Cryptography is why the proof is defensible, but the product is the replay-and-verification loop that shows what failed, what fixed it, and whether the next release would repeat it.

The closest analogy is version control for agent execution: capture is a commit, replay is a checkout, experimenting with a fix is a branch, comparing runs is a diff, and the scenario library is the regression suite built from real production failures. Notary sits between observability, governance, evaluation, and process intelligence: observability shows traces, governance documents policy, eval tools test planned cases, and process mining shows broad workflow drift. Notary turns decision failures and human overrides into sealed, replayable scenarios and proof that remediation worked under the tested conditions.

## The Decision-Assurance Model

Notary treats every important agent run as a recorded, replayable decision rather than a stream of logs, and layers forensic guarantees on top. Four capabilities turn a production failure or override into defensible evidence and recurring business value:

**Capture (commit) with cryptographic sealing.** The SDK records the decision-relevant workflow as a Decision Evidence Graph: model invocation, prompt and policy context, RAG retrieval, MCP and connector calls, guardrails, human overrides, business side effects, and final decision where those elements affect the outcome. Each captured element is sealed with HMAC-SHA256 and chained into a root hash, making later alteration detectable.

**Replay (checkout) from the sealed cassette.** Notary replays the captured scenario from the sealed cassette — the exact recorded inputs and responses the agent saw at decision time — rather than calling production again. This proves the failure is reproducible under the recorded conditions and keeps verification independent of the provider's current state. If a fix introduces a new external call the cassette cannot answer, Notary marks sandbox validation as required rather than pretending the scenario is fully verified.

**Verify the fix under the same conditions.** A customer developer supplies a fix: code, prompt, policy, model configuration, or release version. Notary runs the fixed agent against the same recorded scenario and checks whether it produces the customer-approved expected outcome. This is a bounded claim: Notary verifies remediation for the tested scenario, not general AI safety.

**Promote the verified scenario into the release gate.** Once a failure or override is labeled, reproducible, and verified, it becomes a Scenario. Future agent releases run against the Scenario Library so the same failure cannot silently ship again. This is the recurring business loop: one failure becomes permanent recurrence prevention.

## Concrete Example: A Failed Customer-Service Handoff

A support AI handles a billing dispute. The customer asks for a human three times, sentiment is negative, and the escalation policy requires handoff after two human requests or negative sentiment. The AI continues responding with FAQ content instead of escalating. A human agent later overrides the AI and escalates the case.

Notary captures the conversation, policy version, model version, intent, sentiment, human-request count, routing decision, and human override as a sealed Decision Evidence Graph. Replay reproduces the original failure from the cassette: the bot continues instead of escalating. The support team updates the escalation policy. Notary replays the same recorded conversation against the fixed version, verifies the output is the customer-approved expected behavior (`ESCALATE_TO_HUMAN`), and promotes the case into the Scenario Library. Every future support-agent release must pass that scenario before shipping.

## Concrete Example: A Lending Denial

A lending agent denies a qualified applicant with a credit score of 650 against a threshold of 700. Notary replays the captured scenario from the sealed cassette and reproduces the denial. A developer changes the approval threshold or policy logic to approve scores of 620 or higher. Notary re-runs the fixed version against the same recorded score and verifies the customer-approved expected outcome (`APPROVE`). The Proof of Mitigation certificate captures the original decision, fix reference, replay method, expected outcome label, verification result, root hash, and known limitations.

## Scenario Intelligence and Shift-Left Assurance

The same engine that proves a fix works after an incident can prove a future release does not repeat known failures. Scenario Intelligence mines an organization's historical AI decisions — overrides, escalations, denials, complaints, and high-risk outcomes — for candidate failure patterns. Notary clusters records by intent, outcome, policy, and override pattern, identifies policy gaps, maps candidates to regulatory obligations where applicable, and tests replayability. A human reviewer labels the expected correct outcome before any candidate becomes a Scenario.

This turns the customer's history into a growing release-assurance asset. Before a high-risk agent reaches production, Notary runs the candidate version against the Scenario Library and reports pass, fail, or errored results for the tested set. When the agent passes, Notary can issue a Proof of Readiness for the tested scenarios, documenting the scenario set, agent version, replay method, expected outcome labels, and limitations. The claim is deliberately bounded: the release did not repeat the covered known failure modes; Notary does not certify that the AI system is safe in general.

Delivered as a release gate, this fits how engineering teams already work with policy-as-code and CI/CD gates. In the first production versions, Notary may flag failed scenarios for manual release review; automated blocking in CI/CD is the next step as integrations mature. This positions Notary to play offense where competitors play defense: audit-defensibility and governance tools prove what already happened, whereas Notary compounds real failures into a replay suite that reduces recurrence.

## From Forensic Tool to Enterprise Platform

Forensics is how Notary wins its first deployment; the Release Gate is how Notary becomes recurring infrastructure. The active product horizon stops when the same evidence engine can gate a release: capture a real decision, replay it from the sealed cassette, verify the fix, save the case as a Scenario, run an agent version against the Scenario Library, and return a pass/fail readiness result. Once that loop is trusted, the same execution records become the foundation for broader platform-wide capabilities.

Those broader capabilities remain planned until the Release Gate is working. Enterprise AI Inventory would catalog agents, frameworks, models, owners, risk level, business unit, last execution, and last incident. Organization Policies would let platform teams configure policy sets once and apply them across agents. First-class integrations would connect capture-side frameworks and model providers with consumption-side enterprise systems. Enterprise operations tooling would give platform teams CLI and workflow support across many developers.

The long-term destination — the five-year vision, not today's positioning — is that Notary becomes the operational trust layer for enterprise AI: because every important AI execution can flow through it, it becomes the standard operational record every enterprise AI platform team relies on, regardless of framework, cloud, or model provider. That destination is earned by winning the forensic wedge and release-gate workflow first, not by leading with the platform claim.

## How Notary Is Delivered

Notary uses a hybrid model. A Python-first open source SDK lets developers instrument agents to record decision evidence with a few lines of code; being open source makes the sealing logic auditable and builds regulator trust. Source-system connectors and generic APIs let business users send overrides, complaints, denials, claims, tickets, or other cases to Notary from existing systems using a "Send to Notary" action where native SDK capture is not available.

The managed cloud platform now starts with a discovery-first onboarding motion. A customer can connect one evidence source first — for example SDK traffic, logs in object storage, database exports, or DEP resources from an existing tool — and receive an initial decision map, evidence-quality findings, and replayability findings before they complete every context integration. Setup becomes a confirmation and enrichment workflow after that first map exists: the platform identifies what it can already see, what context is missing, which evaluators are enabled, and what additional sources would unlock stronger assurance or continuous monitoring. After confirmation, the same platform runs bounded Sweep jobs, promotes accepted findings into the existing proof loop, manages the Scenario Library, and generates bounded Proof of Mitigation and Proof of Readiness certificates.

Planned GRC integrations will later push generated evidence into enterprise systems such as ServiceNow, OneTrust, and AuditBoard, but they are consumers of the proof loop rather than prerequisites for the Release Gate. Notary is not a better log file — it is the discovery, replay, and proof layer that turns real AI failures and assurance gaps into recurrence prevention.

## Personas

## Overview

Notary serves audiences that meet at the point of an AI incident: the compliance and legal leaders who bear regulatory and litigation risk, the developers who instrument agents and implement fixes, and — as an account matures — the platform teams who standardize Notary across the organization. The primary economic buyers are compliance-side leaders, not engineering managers; developers are the entry point for organic adoption through the open source SDK; AI platform teams are the expansion buyer who standardizes Notary org-wide once repeated incident value is proven. Understanding what each persona needs, and why, shapes both the product and the go-to-market motion.

## Primary Buyer Personas

**Chief Information Security Officer (CISO).** Owns the security and safety posture of mission-critical AI systems. The CISO needs forensic proof that deployed AI is safe, compliant, and fixable, with mathematical evidence ready before regulators audit or breaches occur. Their motivation is risk reduction and audit readiness across the AI portfolio.

**Compliance Officer.** Responds to regulatory investigations triggered by AI incidents. Today an investigation can take eight weeks; the compliance officer needs to cut that to two by generating forensic evidence regulators trust, avoiding inflated fines and reducing audit costs. Their motivation is faster, cheaper, defensible investigation outcomes.

**General Counsel.** Defends the enterprise when an AI failure leads to litigation. The general counsel needs admissible evidence—cryptographically sealed chain of custody, documented root cause, and proof of mitigation—that courts accept, enabling a defensible litigation strategy. Their motivation is liability protection through evidence courts trust.

## Adoption Persona

**Developer / AI Engineer.** Instruments production agents and implements fixes when incidents occur. The developer needs to debug production AI failures faster—deterministically replaying the exact incident, testing a fix against the real API, and getting proof it works—with minimal integration effort (a few lines of code). Developers adopt the open source SDK and free cloud tier organically; when they hit usage limits, a compliance officer approves the upgrade. Their motivation is faster, verifiable debugging without heavy setup.

## Expansion Persona

**AI Platform Team.** Owns the enterprise's AI infrastructure standards — the head of AI platform, GenAI platform engineering, ML platform, or enterprise AI engineering function that defines tooling for hundreds of developers. This persona enters after Notary has proven repeated value on individual incidents: they standardize the SDK across every agent regardless of framework, cloud, or model provider, configure organization-wide policies once so every agent inherits them, and treat Notary as the consistent operational record for the entire AI portfolio. Their motivation is organization-wide consistency, an enterprise AI inventory, and operational trust at scale. They are the strategic buyer over time, but they expand an existing footprint rather than initiating the first purchase.

## How the Personas Interact

The buying motion follows the personas' relationship to an incident, and unfolds in three stages. First, a developer self-serves with the free SDK and cloud tier, generating organic adoption with no sales cycle. Second, when an incident escalates into regulatory or litigation exposure, the compliance officer, CISO, or general counsel becomes the economic buyer, approving the upgrade to a paid tier. Third, once the organization has seen repeated value across multiple incidents, the AI platform team standardizes Notary across all agents, converting a departmental footprint into an enterprise-wide deployment. Messaging is tailored per persona: regulatory defense and liability shielding for the compliance side, faster verifiable debugging for developers, and organization-wide consistency and operational trust for platform teams. This land-and-expand lifecycle — developer lands, compliance buys, platform team standardizes — preserves the incident-driven willingness to pay while opening a path to enterprise-wide expansion.

## Success Metrics

## Overview

Notary's success is measured across three connected dimensions: developer adoption of the open source SDK (the top of the organic funnel), platform adoption converting free users into paying customers, and financial growth in recurring revenue. Because the go-to-market motion is land-and-expand—developers adopt freely, then compliance buyers approve upgrades—early developer metrics are leading indicators of later financial outcomes.

## Developer Adoption Metrics

These measure organic traction and the health of the top of the funnel:

* GitHub stars: 1,000 to 2,000 by end of Month 3.
* PyPI and NPM installs: 5,000 to 10,000 by end of Month 1.
* Active SDK users: 500 to 1,000 developer teams by Month 3.

## Platform Adoption Metrics

These measure conversion from free usage into paying customers across the three tiers (Free, Professional, Enterprise):

* Free tier signups: 50 to 100 by Month 2.
* Professional customers: 2 to 3 by Month 2, growing to 25 by end of Year 1.
* Enterprise customers: 1 by Month 9, growing to 2 by end of Year 1.

## Financial Metrics

These measure the core business outcome and unit-economic health:

* Monthly recurring revenue: $50K by Month 3, $170K by Month 12.
* Annual recurring revenue: $600K by Month 3, $2M by Month 12, with a path to $5M+ by end of Year 2.
* Customer acquisition cost: $0 for the organic free-to-paid path; $50-100K per sales-driven enterprise deal.
* Customer lifetime value: $600-900K for a Professional customer and $2-5M for Enterprise, yielding an LTV/CAC ratio of 50-100x on the organic path. Exact per-tier pricing is TBD (see the Tiers and Entitlements feature).

## Operational Outcome Metrics

Beyond adoption and revenue, Notary's value to customers is measured by the outcomes it produces during incidents: reducing regulatory investigation time from roughly eight weeks to two, and reducing fine severity by an estimated 30-50% through documented good-faith remediation. These customer outcomes underpin the ROI narrative that drives conversion and expansion.

## Forensic Defensibility Metrics

Notary should also measure whether its evidence would survive scrutiny from the same perspective traditional digital forensics applies to disk, endpoint, mobile, and cloud evidence: custody, integrity, repeatability, reproducibility, tool validation, and independent verification. These are product-health metrics, not adoption metrics; they show whether Notary is producing defensible evidence rather than only convenient investigation artifacts.

Core defensibility metrics:

* Custody completeness: 100% of accepted evidence records should carry the required provenance fields for the captured run, ingestion, replay, mutation test, certificate, and export.
* Evidence integrity pass rate: 100% of accepted Forensic Snapshots should pass integrity verification or explicitly document the BYOK custody mode that prevents server-side recomputation.
* Replay reproducibility rate: the percentage of incidents that produce a deterministic Reproducibility Result from sealed evidence.
* Certificate yield: the percentage of captured incidents that reach a signed Proof of Mitigation Certificate rather than stopping at non-deterministic, unsupported, or unverified states.
* Non-determinism rate: the percentage of runs blocked by uncaptured LLM output, unseeded randomness, unsupported providers, missing cassette data, or other sources that prevent certification.
* Provider and sandbox coverage: the percentage of external calls covered by cassette replay or a supported sandbox adapter.
* Independent verification success: the percentage of exported evidence bundles that can be verified outside Notary using the included hashes, signatures, public keys, tool versions, and method description.
* Tool validation coverage: the percentage of SDK, replay, mutation, signing, and export components with recorded version, test-suite result, and known-limitation statements available in the evidence package.
* Time to evidence package: elapsed time from incident ingestion to a regulator-ready certificate or report.
* Reviewer verification completeness: 100% of generated reports and certificates intended for external submission should carry explicit human approval before submission.

These metrics should be visible internally from the start and selectively surfaced externally once measured reliably. The external version should avoid a vague "defensibility score" unless the component metrics are also shown; courts and auditors trust concrete custody and verification facts more than an opaque composite.

## Timeline Assumptions and Competitive Risk

The adoption and financial targets above assume a largely uncontested, frictionless developer-to-compliance motion. As of mid-2026 that assumption no longer holds, and the targets should be treated as optimistic rather than base-case:

* The forensics and compliance-evidence lane is contested. Acipta launched Public Early Access in July 2026 with a lower-friction, lower-priced, CTO-oriented motion, and Drata (8,500+ organizations) launched AI Agent Governance in June 2026. Market attention is split, and organic adoption competes with incumbents' existing buyer relationships, so the Month 1–3 developer and early-customer targets are likely to take longer to reach.
* The regulatory forcing function softened. The EU AI Act high-risk deadline moved from August 2026 to December 2027, reducing near-term panic buying and lengthening the compliance sales cycle.

The practical implication is to plan for a longer, more contested expansion cycle (on the order of 9–12 months rather than 3) and to treat GRC integrations as table-stakes proof points rather than later expansion features. These figures should be revalidated against actual pipeline before they anchor planning, and the pre-deployment certification path should be developed as a hedge against the deferred deadline.

## Sandbox Coverage as a Product Metric

The value proposition only fully lands when a captured incident can produce a certificate, and that depends on a real provider sandbox existing for every external API the agent called. An agent that calls a provider Notary has no adapter for, or that uses an unseeded custom randomness source, degrades to "non-deterministic, no certificate." Sandbox and adapter coverage is therefore not only a competitive metric (adapter velocity versus rivals) but a product-coverage metric that caps the share of real incidents Notary can certify. Today that coverage is Stripe, GitHub, and Salesforce; every additional adapter widens the set of certifiable incidents. Track provider coverage — and the percentage of captured incidents that reach a signed certificate versus falling back to non-deterministic — as a core product health measure alongside adoption and revenue.

Coverage should also be surfaced externally as demonstrated momentum, not only tracked internally. To an evaluator, "certified incident coverage: Stripe, GitHub, Salesforce — expanding to the next providers on a published cadence" reads as a moving product with velocity, which lands very differently than a static feature list and converts the adapter race into visible progress. One caveat governs how it is published: a coverage list also advertises what is not covered, so a prospect whose provider is absent sees a gap. Present coverage as current set plus expansion trajectory rather than a fixed list, so the story is momentum toward broad coverage rather than a checklist a prospect can fail against. The same figure that is an internal gating metric becomes, framed this way, external evidence of execution speed against competitors.

## Technical Requirements

## Overview

This document captures the high-level technical constraints and building blocks that shape Notary. Detailed architecture, data models, and interface contracts belong in blueprints; this document establishes the technical context that requirements and blueprints must respect. Notary's active build horizon consists of an open source Forensic Agent Logger SDK, a cloud Forensics Platform, a Scenario Library, and a Release Gate that returns readiness verdicts for CI/CD. GRC integrations, evidence datasets, enterprise inventory, and broader operational-trust tooling remain planned after the Release Gate.

## Component 1: Forensic Agent Logger (Open Source SDK)

The SDK wraps AI agents and captures decision evidence with minimal integration effort. It records the decision-relevant workflow as a Decision Evidence Graph: model calls, prompts and policy context, retrieval, MCP or connector calls, guardrails, human overrides, business side effects, and the final decision where those elements affect replay, explanation, verification, or proof. Each captured element is sealed with HMAC-SHA256 and chained into a Merkle tree so that any alteration or reordering breaks the root hash.

Constraints: The active SDK implementation is Python-first, using decorators and context managers for explicit instrumentation and adapter seams. TypeScript remains planned rather than a release-gate blocker. Cryptography uses Python's `hmac` and `hashlib` (SHA256) with an in-house Merkle tree. The SDK must operate with zero dependency on cloud infrastructure so capture and local verification work offline, and developers must be able to validate evidence locally without sending data to the cloud.

## Component 2: Forensics Platform (Cloud Application)

The managed SaaS platform receives sealed decision records, validates cryptographic integrity where possible, persists immutable evidence, replays incidents, verifies fixes, manages Scenarios, and produces proof artifacts. Its active-release-gate services are:

* **Incident Ingestion Service**: Receives forensic snapshots or normalized Verification Records, validates cryptographic integrity where the required key material is available, and stores evidence in a tamper-proof, append-only immutable log.
* **Cassette Replay Engine**: Replays recorded external responses from the sealed Response Cassette by default, preserving reproducibility even when providers change or retire their test environments.
* **Sandbox Orchestrator**: Escalates to clean real-provider sandboxes only when the cassette cannot answer a changed external call or when customer-approved live validation is required.
* **Mutation Testing Service**: Accepts a customer-supplied fix reference and re-runs the captured scenario with modified agent logic to verify that the fix resolves the incident under the tested conditions.
* **Certificate Generator**: Produces cryptographically signed Proof of Mitigation certificates and Proof of Readiness certificates with bounded claim scope and known limitations.
* **Scenario Library Service**: Saves reproduced or verified cases as reusable Scenarios and runs Scenario sets against an agent version.
* **Release Gate**: Exposes the CI/CD-facing pass/fail/error contract that lets a pipeline block deployment when required Scenarios fail or cannot be evaluated.

Technology constraints: Backend in Python with FastAPI; the deployed product surface may use a pragmatic static or server-rendered client while the longer-term frontend target remains React/TypeScript; storage uses AWS S3 for immutable logs, RDS PostgreSQL for metadata, and AWS Secrets Manager/KMS for managed keys and signing custody; replay and verification execution run through isolated replay components that can scale toward concurrent runs.

## Component 3: Planned Enterprise Integrations and Platform Expansion

GRC integrations, framework-specific compliance reports, evidence export datasets, enterprise AI inventory, organization-wide policy management, and broad enterprise operations tooling are planned after the Release Gate. These capabilities consume proof artifacts and accumulated execution records; they do not define the first committed product horizon. ServiceNow, OneTrust, and AuditBoard remain the target GRC systems, but their connection, retry, and framework-mapping workflows should not block the capture-replay-verify-release-gate loop.

## Cross-Cutting Constraints

* **Cryptographic integrity**: HMAC-SHA256 sealing with Merkle-chained hashes must allow independent verification at any later time given the snapshot and root hash. Without the secret key, no party can forge a valid hash.
* **Cassette-first replay**: Replay shall use the sealed Response Cassette by default so evidence remains reproducible years later independent of provider availability or sandbox drift.
* **Real sandbox escalation**: Real provider sandboxes are the escalation path for changed external calls or customer-requested live validation. They must never replace cassette replay as the default durable proof path.
* **Bounded proof language**: Proof artifacts shall state the tested scenario conditions, agent version or fix reference, expected outcome provenance, replay method, and known limitations. They shall not imply general AI safety.
* **Immutability and auditability**: Forensic logs are append-only and immutable; the open source SDK ensures the sealing logic is transparent and auditable by regulators.

## Competitive Landscape

## Overview

Notary is the platform that closes the loop between an AI decision failing and proving the failure is fixed. It captures an autonomous agent's production run as sealed, tamper-evident evidence; deterministically reproduces the decision to prove *why* it diverged; lets a developer apply a fix and re-run it under the exact recorded conditions; and issues cryptographically signed proof that the fix resolves the incident — evidence built to survive a regulator's or court's scrutiny years later. It complements the Business Problem document, which establishes the regulatory forensics gap this addresses.

This document maps where Notary sits against a crowded field and, more importantly, where it stands apart. As of mid-2026 the surrounding lanes — observability, governance, tamper-evident logging, and even signed replayable evidence — are contested or commoditizing. The next section states plainly what Notary does that no competitor found does; the competitor detail and strategic risk that follow are there to support that claim, not to lead with the crowd.

## What Notary Does and Where It Stands Out

Notary is built from four capabilities. Three of them — signed evidence, deterministic replay, and root-cause reproduction — are individually strong but increasingly matched by competitors. The fourth is the one that is not matched anywhere, and it is the reason the other three are worth building:

**The standout: deterministic fix-verification.** Notary does not stop at proving what a decision *was*. It runs a corrected agent — a real git commit — against the exact recorded conditions that produced the failure, diffs the result, and issues a signed Proof of Mitigation only when the corrected run demonstrably resolves the incident. Every competitor found stops at re-deriving or logging the original decision. None runs a patched codebase against the real failing scenario and certifies the outcome. That specific loop — *prove this fix resolves it, tested against the real system* — is Notary's uncontested wedge, and everything else in the product exists to make that proof defensible.

The following matrix shows where each capability stands versus the competitor classes detailed later. It is the fastest way to see what is shared and what is singular.

| Capability | Notary | Acipta (defensibility) | Governance / MRM (Drata, ValidMind, Credo) | Observability (Datadog, LangSmith) | Audit-log vendors |
| --- | --- | --- | --- | --- | --- |
| Tamper-evident signed evidence | Yes | Yes | Emerging | No | Yes |
| Deterministic replay of a decision | Yes | Yes (re-derives verdict) | No | Trace re-run (debug) | No |
| Root-cause reproduction (causation) | Yes | Partial | No | No | No |
| **Fix-verification: patch + re-run + certify** | **Yes — singular** | **No (scoped out)** | **No** | **No** | **No** |
| Real-condition fidelity (sealed cassette + sandbox escalation) | Yes | Recording only | No | No | No |
| Open-source, auditable capture (BYOK) | Yes | No (closed cloud) | No | No | Partial |

Two capabilities under the standout are worth naming because they make the fix-verification claim survive scrutiny rather than being a slogan. First, **sealed, portable cassettes with fix-aware sandbox escalation** — the concrete edge that also names Notary's durability guarantee: because replay runs against the sealed cassette recorded at decision time, an incident is **reproducible independent of the provider's current state**, verifiable years later whether or not Stripe, GitHub, or Salesforce still behave as they did or even still offer the same test environment. This is the structural answer to "did you test against a stale recording or the real system, and will it still verify years from now?" and it is a guarantee competitors who replay against live provider environments cannot make in the same form. Second, **open-source, auditable capture** ("here is the code that sealed this evidence; audit it yourself"). Both are detailed in Differentiation and Positioning below.

## The Agent Lifecycle and Where the Whitespace Is

The capability matrix above compares features head-to-head. This one follows the life of a regulated AI agent — from building it, through testing and deploying, to finding a bad decision and proving it fixed — and asks at each stage who serves the need and where open ground remains. The pattern it reveals is the strategic point: competitors cluster densely at the front of the lifecycle (build, test, observe) and at the pure-evidence step (certify what happened), but the middle-to-late stages — reproducing *why* a decision diverged, proving a *fix* resolves it, and turning that into permanent recurrence prevention — are largely open. Notary is built to own exactly that open stretch.

| Lifecycle stage | Who serves it today | Notary's role | Whitespace |
| --- | --- | --- | --- |
| \\1. Build the agent | Agent frameworks (LangGraph, PydanticAI, ADK) | None — deliberately out of scope | Owned by others |
| \\2. Test before deploy | Eval tools (LangSmith, Braintrust, Patronus) | Pre-deployment certification against real recorded scenarios through Proof of Readiness | Contested, but real-condition certification is open |
| \\3. Deploy / gate release | Cloud providers, CI/CD | Release Gate result backed by Scenario Runs and Proof of Readiness | Partially open |
| \\4. Observe in production | Datadog, LangSmith, Langfuse (owned) | None — deliberately not here | Owned by others |
| \\5. Capture a consequential decision as sealed evidence | Audit-log vendors, Acipta | Sealed, tamper-evident capture via open-source SDK | Contested / commoditizing |
| \\6. Triage the set of decisions worth proving ("incidents") | No focused owner | Incident record spanning failed, overridden, disputed, and sampled decisions | Largely open |
| \\7. Reproduce *why* the decision diverged (causation) | Observability offers debug re-run only | Deterministic reproduction against sealed conditions | **Open — Notary-led** |
| \\8. Fix and verify the fix resolves it | No competitor found | Patch + re-run under recorded conditions + signed Proof of Mitigation | **Open — Notary only** |
| \\9. Certify evidence for regulators / courts | Acipta, governance, audit-log vendors | Signed certificates and compliance reports | Contested |
| \\10. Prevent recurrence | Eval tools offer generic regression | Accumulating Scenario Library re-run on every change | **Largely open — Notary-led** |

Read top to bottom, the whitespace concentrates at stages 6–8 and 10: the arc from "a decision is worth investigating" through "the fix is proven" to "it can never silently recur." That arc is the fix-verification loop plus the accumulating scenario library, and it is where Notary faces the least competition. The front of the lifecycle (stages 1–5) is where Notary either stays deliberately out (build, observe) or competes on commoditizing ground (capture, certify) — which is why positioning leads from the middle of the lifecycle, not its edges.

## Who Owns What

The AI tooling market has clear category owners:

* **Engineering productivity** is owned by LangSmith.
* **Observability** is owned by Datadog (and the broader LangSmith/Langfuse/Arize field).
* **Prevention and runtime security** are owned by Protect AI and Lakera.
* **Governance** is owned by the GRC vendors (OneTrust, ServiceNow, Sprinto, Drata).
* **Deployment** is owned by the cloud providers.

The space Notary occupies — **AI incident investigation, reproducible evidence, and proof of remediation** — is a contested but still underserved lane: direct forensics competitors (Acipta) and governance incumbents (Drata) generate evidence here too. Notary's defensible position within that lane is the fix-verification loop, not forensics generically. This is a stronger wedge than a broad "operational trust layer" claim that would place Notary adjacent to the crowded categories above.

## Competitor Categories

### Direct forensics and defensibility competitors

These competitors have entered the evidence-and-replay lane directly and are the sharpest threat to a generic "forensics" positioning.

* **Acipta**: An agent-based defensibility platform (Public Early Access July 2026) that produces cryptographically signed (Ed25519, RFC-3161 timestamped, Merkle-anchored), byte-identically replayable per-decision evidence, mapped to many regulatory frameworks. Its replay re-derives the *original* verdict to prove what was decided; it does not apply a code fix and re-run it, and does not test against real provider sandboxes. Acipta positions itself as "Layer 2" audit-defensible evidence and explicitly scopes out remediation verification, mutation testing, and sandbox re-execution. It lands low-friction at a low monthly price with a build-time, CI/CD-native motion aimed at the CTO — a lower-friction entry than Notary's incident-triggered motion, which is a real go-to-market threat on the evidence layer even though it does not close the fix-verification loop.
* **agent-forensics and similar open-source capture/replay tools**: One-line hooks into common agent frameworks that produce immutable event logs, EU AI Act Article 12 reports, and replay-with-diff. They lower the perceived novelty of capture and replay but do not close the loop to proving a specific code fix passes against a real external API.

### AI Governance, Supervision, and Model Risk platforms

These platforms already sell into compliance, risk, product, and model-validation teams in lending, insurance, healthcare, and customer operations, and several are extending toward agent auditing and pre-deployment assurance. They are the most direct enterprise threat because they own buyer relationships and can frame agent assurance as a governance workflow rather than a forensic proof loop.

* **Drata**: A GRC incumbent (8,500+ organizations) that declared AI Agent Governance a new category and offers agent discovery, real-time policy enforcement, drift detection, and tamper-evident logging that produces auditor-grade proof of agent decisions. It is the clearest case of incumbent encroachment: a vendor that owns the compliance buyer relationship now generating agent-decision evidence. Drata does runtime prevention and evidence, not post-incident fix-verification.
* **Swept AI**: An AI agent supervision and interrogation platform that positions around adversarial evaluation, pre-deployment verification, continuous production supervision, audit trails, and compliance evidence for autonomous systems. Swept overlaps most with Notary's Proof of Readiness, Release Gate, and broader assurance narrative: it helps teams decide whether agents are safe and compliant to deploy. Its center of gravity is supervision and governance; Notary's wedge remains narrower and more forensic — sealed records, cassette replay, customer-supplied fix verification, Proof of Mitigation, and converting real failures into release-gate Scenarios.
* **ValidMind**: Offers immutable audit trails, reasoning-trace capture, policy-as-code, and a model-risk-management heritage aimed at regulated banking and insurance. Governs and documents decisions but does not provide deterministic replay to prove a fix prevents recurrence.
* **Credo AI**: Responsible-AI suite with bias audit, adverse-action explainability aligned to CFPB and OCC guidance, continuous agent-trace monitoring, and regulatory mapping. Produces governance artifacts and runtime monitoring rather than forensic root-cause proof.
* **Dataiku, Trustible (SolasAI), Sprinto**: Broad governance suites covering AI inventory, bias testing, risk scoring, and exportable evidence packs. Forensics depth is shallow relative to Notary's focus.

### Audit-trail and compliance-logging vendors

Vendors such as SupraWall, DeepInspect, Collibra, and Vouched (Identiclaw) sell EU AI Act Article 12 tamper-proof logging with hash-chaining and cryptographic proof. This is the part of Notary's stack that is commoditizing fastest. They answer *what happened* immutably, but not *why the logic diverged* or *whether the fix works*.

### Observability platforms

LangSmith, Langfuse, Datadog, Arize, and Traceloop capture execution traces and offer trace re-run for debugging. The Business Problem document already frames these as the incumbents Notary differentiates against: they support operational monitoring, not defensible forensic proof or regulatory evidence.

### Deterministic replay tooling

LangGraph Time Travel, OpenTelemetry-based trace stores, and replay-stub patterns are open-source building blocks rather than competing products. They lower the moat around Notary's replay capability because anyone can assemble the primitives, but none package replay as regulatory evidence.

### Process mining and process intelligence platforms

Celonis and related process-mining tools discover how business processes actually run, where exceptions occur, and where work gets stuck. They are useful analogies but not direct competitors. Celonis optimizes broad business processes such as order-to-cash, procure-to-pay, support operations, or claims handling; Notary verifies specific AI decision paths, human overrides, and remediation outcomes. The safe analogy is: process mining reveals process deviations, while Notary turns AI decision deviations into replayable proof and release gates. Notary should not position as "Celonis for AI" externally because that invites a broad process-optimization comparison and dilutes the fix-verification wedge.

### Contact-center QA and analytics platforms

Zendesk QA, NICE, Infovista/VistaCX, Cyara, ASAPP, and similar contact-center tooling score interactions, measure quality, test scripted flows, surface recurring issues, and support agent coaching. They are adjacent to the contact-center wedge, not products Notary should replace. Notary's role is narrower: when an AI support agent fails to hand off, is overridden by a human, or mishandles a regulated topic, Notary seals that interaction, replays it, verifies the fix, and turns it into a release-gate scenario. Contact-center platforms measure and route; Notary proves recurrence prevention.

## Differentiation and Positioning

Forensics is not uncontested white space. Acipta contests signed, replayable evidence; Drata and other governance incumbents contest auditor-grade decision proof; open-source tools contest capture and replay. Notary's differentiation therefore leads with the one capability none of them offers, not with forensics generically.

* **Deterministic fix-verification and recurrence prevention** is the still-uncontested wedge. The specific loop — capture an incident or override, replay it deterministically, apply a fix as a git commit or release configuration, re-run the fixed version under the same recorded conditions, and issue a signed proof only when the re-run produces the customer-approved expected outcome — is not replicated by any competitor found. Acipta's replay re-derives the original verdict but does not run a patched codebase; governance incumbents enforce and log but do not verify fixes; observability shows what happened but not whether a fix resolves it. Scenario Intelligence extends this wedge by mining historical overrides, escalations, denials, and complaints for candidate failure patterns that can become replayable release-gate scenarios. This is Notary's strongest and sharpest differentiator, and positioning should lead with it — not with the mechanism (cassette or sandbox) underneath it.
* **Sealed, portable cassettes with fix-aware sandbox escalation are the concrete edge under the fix-verification loop — and the honest answer to the mock-drift question.** Replay defaults to a sealed `ResponseCassette`: the provider responses recorded at incident time, replayed deterministically in milliseconds. This is not the weak "we use mocks" position, because the cassette is cryptographically sealed, replayed bit-for-bit, and remains reproducible years later even if the provider changes or retires its test mode — directly serving the durability requirement a live sandbox fails. The regulator's follow-up, "did you test against a stale recording or the real system?", is answered by escalation: when a fix changes which external calls fire, the cassette cannot answer the novel call, so the platform detects the divergence and validates against a real provider sandbox (Stripe test mode, GitHub test org, Salesforce sandbox); customers can also opt into live validation for a high-stakes submission. The moat is therefore not "we use real APIs" and not "we use recordings" — it is the combination competitors cannot easily assemble: **cryptographic sealing + deterministic replay + fix-aware escalation that knows when a recording suffices and when live validation is required.** Real-sandbox coverage remains a race (per-provider adapters: Stripe, GitHub, Salesforce, then AWS, Slack, Twilio, SendGrid; generic infra like E2B, Modal, Northflank lets others assemble a similar workflow by hand), so adapter velocity should be tracked as a competitive metric — but it is now the escalation path, not the headline, so a single provider retiring its sandbox no longer threatens the core claim.
* **Execution-graph branching for exploratory debugging** — forking a reproduced run at a chosen node, applying a change, and diffing against the original at the node level — is genuinely novel: no competitor found offers what-if branching, only replay of what actually happened. It is a power-user capability for the technical investigator (principal engineers running post-mortems), positioned as "version control for agent execution," rather than a compliance-buyer driver. Lead with it for engineering teams, not for general counsel.
* **Open-source, auditable capture separated from the cloud platform** — an SDK that captures and seals evidence offline with bring-your-own-key custody, so regulators and a customer's internal audit team can inspect the sealing logic directly — is defensible against Acipta (closed-source cloud) and the SaaS governance vendors. It should be positioned as audit-ready capture for regulatory defense: "here is the open-source code that sealed this evidence; audit it yourself" is a stronger chain-of-custody answer than "we use HMAC-SHA256, trust us." This only holds with genuine open-source governance (third-party security audits, responsiveness to security reports, transparent roadmap); half-open will not convince security and compliance reviewers. One caveat must not be oversold: in BYOK mode, when a customer withholds their symmetric key, the server cannot recompute and verify the `RootHash` on ingestion, and Notary's own chain of custody falls back to the asymmetric notarization signature (see the Cryptographic Evidence Sealing blueprint, ADR-002/ADR-003). This is a sound design, but sales and compliance messaging should present BYOK with that tradeoff rather than implying full server-side integrity checking in all modes.
* **Root-cause proof** and **tamper-evident evidence** are contested (Acipta, Drata) and commoditizing; express them as customer outcomes that support the fix-verification story rather than as the headline claim.

The defensible position is the fix-verification and recurrence-prevention loop delivered as forensic evidence that survives a regulator's follow-up question — not "prove what happened," which competitors now also address, but "prove this fix resolved the tested failure and that future releases did not repeat covered scenarios." That specific answer to the remediation-proof demand, combined with auditable open-source capture and scenario intelligence, is what remains differentiated. The claim is intentionally bounded: Notary verifies customer-approved expected outcomes under recorded scenario conditions; it does not certify general AI safety.

**What Notary explicitly does not contest.** Positioning discipline requires conceding ground as clearly as claiming it. Notary does not compete on tamper-evident logging breadth against the audit-log vendors (SupraWall, DeepInspect, Collibra, Vouched), on governance breadth against Drata and the broad GRC suites, or on observability against Datadog and LangSmith. Those capabilities are either commoditizing or owned by incumbents, and trying to out-feature them dilutes the one claim that is genuinely Notary's. Where a buyer needs those, Notary integrates with or sits beside them rather than replacing them — tamper-evident capture is table stakes it meets, not a battle it fights. Conceding this explicitly keeps the narrative on fix-verification, where the field is open, instead of on ground already contested by better-resourced players.

## Strategic Risk

Incumbent encroachment is the primary risk. Drata, a GRC vendor that owns the compliance buyer relationship, generates auditor-grade agent-decision proof, and ValidMind and Credo AI extend audit trails and runtime monitoring toward the same territory. Separately, Acipta competes directly on defensibility with a lower-friction, lower-priced, CTO-oriented land motion that could win the evidence layer broadly even though it does not close the fix-verification loop.

Two risks follow. First, the window is compressed and contested: Acipta and the governance incumbents' existing buyer relationships split market attention, so organic developer-to-compliance adoption is slower and noisier than an uncontested runway would allow — a gap the Success Metrics targets should account for. Second, the EU AI Act high-risk deadline sits at December 2027 rather than August 2026, softening the panic-buying spike and lengthening the sales cycle.

The mitigation is positioning discipline: lead with deterministic fix-verification through real sandboxes rather than with "forensics," position open-source capture as regulatory-grade chain of custody, treat GRC integrations as table stakes rather than expansion features, and use the longer regulatory runway to develop the pre-deployment certification hedge. Revisit this assessment as Acipta reaches general availability and as governance incumbents expand their agent-auditing roadmaps.

## Product Direction and Phases

## Overview

This document sets Notary's product direction and separates the active build horizon from planned expansion. The product framing remains **AI Decision Assurance**: Notary turns real AI decisions, human overrides, disputes, and incidents into sealed, replayable evidence; verifies fixes against the same recorded conditions; and converts resolved failures into regression scenarios that prevent recurrence. The active build now begins one step earlier, with **discovery-first onboarding**: connect available evidence, build an initial decision map, surface assurance candidates and evidence gaps, confirm context and mappings, and then carry accepted findings through the proof loop and into the **Release Gate**.

That horizon is intentionally narrower than the full platform vision. Notary should not try to build the whole operational trust layer before the proof loop is trusted. The near-term product must prove one compounding workflow: a consequential AI decision becomes attributable evidence, attributable evidence becomes an explainable assurance candidate, an accepted candidate becomes sealed proof-loop evidence, sealed evidence becomes a replayable Scenario, the Scenario verifies a fix, and the same Scenario gates the next release. Everything beyond that — GRC delivery, evidence datasets, enterprise inventory, organization-wide policy management, broad connector coverage, and trust-layer platform tooling — remains planned until the Release Gate is credible with design partners.

The core evidence object behind the engine is the **Decision Evidence Graph**: the sealed graph of decision-relevant workflow elements for one AI run. It includes the user input, prompt and policy context, exact model invocation, retrieval, memory state, MCP tool calls, connector/API calls, guardrail results, human overrides, business side effects, final decision, and release context where those elements affect the decision or its remediation. The platform stores that graph as a **Verification Record**, with Incident remaining the failure-triggered case. This expands Notary beyond a simple "LLM + API + decision" recorder without turning it into observability: Notary captures only what is needed to replay, explain, verify, and prove decision outcomes.

The strategic gap Notary fills sits between compliance and business operations. Compliance and legal teams need defensible evidence: what happened, whether it was tampered with, why it happened, and whether remediation worked. Business owners need recurrence prevention: the same bad AI decision, failed handoff, or human override should not ship again after the next prompt, model, policy, or code release. Notary connects those needs with one engine: capture, seal, replay, verify, and gate future releases against real past failures.

## Active Build Horizon — Discovery Through the Release Gate

The active build horizon ends when Notary can serve as a release gate for known failure modes, starting from incomplete customer evidence rather than assuming a fully assembled Incident. That means the product can ingest DEP resources, SDK evidence, logs, or selected source exports; build an initial decision map; show source coverage, missing context, and eligible evaluators; run bounded Sweep analysis; preserve accepted findings as sealed proof-loop evidence; replay from the sealed cassette by default; verify a customer-supplied fix or agent version; save the verified case as a Scenario; run a Scenario set against a release candidate; and return a readiness verdict suitable for CI/CD.

This horizon includes the customer-facing surfaces needed to make the loop understandable and operable: discovery setup, source profiling, initial decision mapping, candidate review, verification record review, incident investigation, proof state, Scenario Library, Scenario Runs, readiness history, claim scope, and known limitations. It does not include every future enterprise surface. Planned items should remain visible in the roadmap, but they should not be treated as blockers for proving the discovery-to-release-gate loop.

## Phase 0 — Discover: Initial Map Before Full Setup

Notary should show value before demanding a full integration project. Phase 0 is the discovery wedge: a customer connects available evidence sources and receives an initial decision map, evidence sufficiency, replayability gaps, and candidate assurance findings. This is intentionally useful even when only logs or partial SDK data are present, but it does not overclaim correctness or policy applicability where context is still missing.

Core capabilities in this phase:

* DEP, SDK, API, file, object-store, and selected source ingestion without requiring every context system up front.
* Source profiling that previews identifiers, timestamps, schemas, candidate joins, sensitive fields, and likely decision counts.
* Progressive setup that separates required corrections from optional enrichment.
* Initial evaluators focused on what the evidence can actually support, especially missing evidence, expected-outcome mismatch, and replayability failure.
* Candidate review, suppression, and promotion into the existing proof loop rather than a parallel workflow.
* Confirmation of continuous monitoring only after the customer has reviewed the initial map and approved the source and policy shape.

## Phase 1 — Land: Proof of Remediation for Real AI Failures

Notary enters the market as the platform that proves an AI failure or high-risk override was reproduced and fixed. In regulated domains, that appears as AI incident investigation, reproducible evidence, and Proof of Mitigation. In high-volume operational domains such as contact centers, the same engine appears as **Escalation Replay**: turn human overrides, failed handoffs, customer complaints, and policy breaches into replayable scenarios that verify the next AI support-agent release does not repeat the same failure.

Core capabilities in this phase:

* Decision Evidence Graph capture through the SDK and manual or source-system intake paths where automatic capture is not yet available.
* Chain of custody through tamper-evident, cryptographically verifiable records.
* Cassette-first deterministic replay using the sealed responses captured at decision time.
* Sandbox escalation where the cassette cannot answer a changed external call or where the customer needs live provider confirmation.
* Fix verification against the same recorded conditions.
* Proof of Mitigation: cryptographically signed verification that a fix resolves the captured failure under the tested conditions.
* An investigation surface that shows the captured decision path, replay trace, fix-verification state, certificate state, claim scope, and known limitations.

Cryptographic integrity remains a core differentiator throughout, expressed as a customer outcome — trustworthy, defensible evidence — rather than led with as an algorithmic claim. Customers buy trustworthy evidence and recurrence prevention; cryptography is why the evidence is defensible.

## Phase 2 — Build: Scenario Library, Proof of Readiness, and Release Gate

Phase 2 turns the Phase 1 proof loop into a recurring release-assurance workflow. Once a failure, override, dispute, or high-risk decision has been reproduced and labeled, Notary can promote it into the Scenario Library. Future agent versions run against that Scenario Library before release. A passing run can produce Proof of Readiness; a failing run blocks or flags deployment.

Core capabilities in this phase:

* Scenario persistence from reproduced incidents and verified fixes.
* Scenario Runs against a specified agent version, with pass/fail/errored results per Scenario.
* Library browsing, curation, and run history so teams understand their accumulated coverage.
* Proof Claim Scope and Label Provenance so certificates and readiness reports never overclaim beyond the tested conditions and human-approved expected outcomes.
* Scenario Intelligence as managed library expansion: surface candidate scenarios from overrides, escalations, denials, complaints, policy breaches, and high-risk outcomes, while requiring human approval before any candidate becomes certificate-grade evidence.
* Proof of Readiness: a signed certificate that a specific agent version passed the required Scenario set.
* Release Gate: the CI/CD-facing pass/fail/error contract that lets a pipeline block deployment when required Scenarios fail or cannot be evaluated.

This is the stop line for the active build plan. When Phase 2 is complete, Notary has a defensible wedge and a recurring reason to run: every captured failure can become a permanent release gate.

## Planned After the Release Gate

The following capabilities remain planned and should not be treated as part of the active build horizon unless explicitly pulled forward:

* **Compliance Reporting and GRC delivery.** Framework-specific reports, ServiceNow, OneTrust, AuditBoard, retry handling, and control mappings are enterprise credibility items, but they consume proof artifacts rather than creating the release-gate loop.
* **Evidence Export and Improvement Dataset.** Provenance-carrying export sets and standing datasets are valuable after customers have accumulated scenarios, but they should follow the Release Gate rather than block it.
* **Enterprise AI Inventory and organization policies.** These become natural expansions once many agents emit execution records, but they move Notary into contested AI-operations territory and should remain planned until the wedge has traction.
* **Enterprise operations tooling.** Broad CLI workflows, org-wide SDK standardization, and full operational records are platform expansion items.
* **Broad connector and provider coverage.** Additional sandbox providers, source-system connectors, model providers, and framework adapters should be sequenced by customer demand rather than treated as launch prerequisites.
* **Industry policy packs and governance accelerators.** Starter packs for domains such as lending, insurance, customer support, and healthcare should accelerate setup and review, but they must remain editable customer-confirmed guidance rather than turnkey legal truth.
* **Transparency logs and advanced trust infrastructure.** Public append-only certificate logs and other long-horizon trust systems deepen defensibility but are later trust infrastructure, not wedge proof.

## Widening the Trigger: From Incident to Verification Event

Notary's original unit of work is the incident — a production failure someone noticed. That is the right first wedge, but it is too rare to carry the subscription model alone. The broader unit is a **Verification Event**: any agent decision worth proving because it failed, was overridden, was disputed, crossed a risk threshold, was sampled for assurance, or is being tested before deployment.

The intended sequencing is a volume ladder, each rung using the same capture-replay-verify engine: failures first; then overrides, disputes, and threshold crossings; then selected production decisions; then pre-deployment certification on every release. The Release Gate is the first committed expression of that ladder because it turns past failures into recurring pre-deployment checks without crossing into live monitoring.

**Boundary discipline: this is not observability.** A Verification Event is a discrete recorded run that is captured, sealed, replayed, and verified to produce defensible evidence. Notary does not watch production continuously, stream telemetry, alert on anomalies, or dashboard live agent behavior. If a future capability produces on-demand replayable evidence of a discrete decision, it stays in lane; if it watches the live system, it should be rejected or redesigned.

## Relationship to Other Documents

The Business Problem document establishes the forensic gap that anchors Phase 1. The Product Description details the capture-replay-verify model and the release-gate expansion. The Competitive Landscape document explains why Notary should lead with fix verification and recurrence prevention rather than a broad platform claim. The Requirements and Blueprints should treat the Release Gate as the active build horizon and keep post-gate enterprise expansion explicitly planned.

## Positioning and Messaging

## Overview

This document defines how Notary is positioned and described to the market. It translates the strategy captured in the Product Description, Competitive Landscape, and Product Direction and Phases documents into the message the product leads with, the language it uses per buyer, and the vocabulary it deliberately avoids. It exists because Notary operates in a lane that is easy to describe in ways that either invite the wrong competitors or undersell the one thing that is genuinely differentiated. Getting the words right is a competitive act, not a cosmetic one.

The central positioning problem is that Notary's original framing — forensic evidence produced after an AI decision fails — sells a product no one wants to need, and it invites the customer to pay continuously for something they perceive using only a handful of times a year. The reframe from incident to verification event (see Product Direction and Phases) changes what Notary sells: not a panic button for a crisis, but a continuous posture of provable, defensible AI decisions. The messaging must express that posture without drifting into the vocabulary of adjacent categories that Notary must not be confused with.

## The Core Message

Notary leads with **AI Decision Assurance**: turn real AI decisions, human overrides, disputes, and incidents into sealed, replayable evidence; verify fixes against the same recorded conditions; and use those verified failures as release-gate scenarios so they do not recur. The headline outcome remains deterministic fix-verification — prove a fix resolves a captured failure, tested against the real recorded conditions, with evidence a regulator, court, or business owner can trust — but the recurring value is broader: every high-risk decision or override can become part of the customer's assurance library.

The message shift, stated plainly, is from "forensic evidence when an AI decision fails" to "proof and recurrence prevention for AI decisions — every override, every dispute, every release." The reusable analogy that carries this is "version control for agent decisions": it frames Notary as something a team uses on every change, not only in a crisis, and it markets continuous use rather than crisis use. For contact centers, the sharpest version is: **turn every human override into a regression test for your AI support agent.** For carriers, lenders, and health plans, the broader version is: **your decision history is a scenario mine; Notary finds candidate failure patterns, verifies replayability, records the human-labeled expected outcome, and compounds the release gate.**

The second named line, which supports the fix-verification headline and answers the durability objection directly, is: **evidence that is reproducible independent of the provider's current state.** Replay runs against the sealed cassette recorded at the moment of the decision, so an incident stays reproducible years later whether or not Stripe, GitHub, or Salesforce still behave as they did — and whether or not their test environments still exist. This is the structural answer to the question every diligence-minded regulator or buyer eventually asks — "did you test against a stale recording or the real system, and will this still verify years from now?" — and it is a durability guarantee competitors who replay against live provider environments cannot make in the same form. Use it as a repeatable positioning line, not as a buried implementation detail.

## What to Lead With, and What Not To

Positioning discipline matters because the surrounding categories are crowded and several competitors are actively contesting the parts of Notary's stack that are commoditizing.

* **Lead with the fix-verification and recurrence-prevention loop.** "Prove the fix works, tested against the same recorded conditions, and prevent the failure from shipping again" is the sharpest differentiator. It is the door into the room.
* **Do not lead with "forensics" generically.** Direct competitors (Acipta) and governance incumbents (Drata) now contest signed, replayable evidence; leading with forensics puts Notary in a fight on contested ground.
* **Do not lead with cryptography as the headline.** Cryptographic sealing is why the evidence is defensible, not what the customer buys. Express it as a customer outcome — trustworthy, defensible evidence — and keep the algorithm as the supporting reason, not the pitch.
* **Treat GRC integrations as table stakes.** ServiceNow, OneTrust, and AuditBoard connections are proof of enterprise credibility, not headline expansion features.
* **Position open-source, auditable capture as chain-of-custody strength.** "Here is the open-source code that sealed this evidence; audit it yourself" is a stronger trust claim than any closed-source assurance, and it is defensible against closed-source cloud competitors.

## Per-Persona Messaging

Messaging is tailored to each buyer's relationship to an AI incident, consistent with the land-and-expand motion in the Personas document.

* **Compliance Officer, CISO, and General Counsel (the economic buyers).** Message: do not wait for the audit letter. Every consequential decision your agents make is captured, sealed, and provable on demand, so you are audit-ready continuously and can demonstrate good-faith remediation with evidence courts and regulators trust. This sells readiness and durability — a subscription-shaped value — rather than a one-time incident response.
* **Business Operations Leaders (contact-center/CX, claims, lending operations).** Message: stop repeating the same AI failure. Human overrides, failed handoffs, complaints, and high-risk decisions become replayable scenarios; every new bot or agent release is tested against those real failures before it ships. This sells recurrence prevention, release safety, and fewer repeated human interventions.
* **Developer and AI Engineer (the adoption motion).** Message: prove your fix works, and prove your release did not regress — on every deploy, tested against the real conditions your agent actually faced. This is the fix-verification loop and the Testing Playground story, and it is the reason a developer opens Notary weekly rather than once a quarter.
* **AI Platform Team (the expansion buyer).** Message: one consistent, provable operational record for every agent, regardless of framework, cloud, or model provider. This is the standardization and switching-cost story, and per Product Direction it is a genuine second sale, not an automatic upsell.

## Vocabulary Boundary: Not Observability

The "continuous" and "every decision" language required to sell the reframe sits dangerously close to the vocabulary of observability — the category owned by Datadog, LangSmith, and Langfuse — which the Business Problem and Competitive Landscape documents are explicit Notary must not enter. Blurring into that category invites the wrong competitors and dilutes the differentiated claim.

The discipline is a vocabulary rule: always attach continuous language to proof, evidence, scenario discovery, and release assurance, and never to monitoring, visibility, insight, dashboards, or real-time signals. Notary proves discrete past decisions on demand; it does not watch production continuously. "Continuously audit-ready" and "continuously expanding scenario library" are in-lane; "continuous monitoring of your agents" is not. Any marketing claim should be tested against this line: if it describes producing replayable evidence, discovering candidate scenarios, verifying fixes, or gating releases against known failures, it is Notary's message; if it describes watching the live system or surfacing operational signals, it belongs to observability and must be rejected or rewritten.

A second vocabulary rule governs proof language: Notary verifies that a customer-supplied fix or release produced the customer-approved expected outcome under recorded scenario conditions. It must not claim to independently determine the correct answer or certify that an AI system is safe in general. Use "verified against the tested scenario" rather than "certified safe."

## Relationship to Other Documents

The Product Description defines the capabilities this messaging sells. The Competitive Landscape document supplies the differentiation discipline — what to lead with and why leading with forensics or the platform vision would place Notary in crowded markets. The Product Direction and Phases document defines the incident-to-verification-event reframe that this messaging expresses, and owns the same observability boundary applied here to product scope. The Personas document defines the buyers each message is tailored to.

# Feature Requirements

## Forensic Agent Logger SDK

## Overview

The Forensic Agent Logger is an open source SDK that wraps any AI agent and transparently captures forensic data—LLM prompts and responses, outbound API calls, and the agent's final decision—with minimal integration effort. Each captured element is sealed with a cryptographic hash and chained together so that any later alteration or reordering is mathematically detectable. The SDK is the foundation of Notary: it produces the tamper-evident forensic snapshot that the cloud platform later ingests, replays, and certifies.

The SDK solves the first half of the regulatory forensics gap. Without trustworthy capture at the moment an agent runs, no downstream replay or certificate can be trusted. Because the SDK is open source and can validate its own output locally, regulators and courts can audit the sealing logic directly rather than trusting a vendor's claims. It must work offline with no dependency on cloud infrastructure, so that capture and local verification are always available.

## Terminology

* **Forensic Snapshot**: The structured record produced by the SDK for a single agent run, containing the captured elements, their individual hashes, the Merkle chain, and the root hash. This is the unit later ingested by the Forensics Platform.
* **Captured Element**: A single piece of forensic data recorded during an agent run—an LLM prompt, an LLM response, an outbound API request, an API response, or the agent's final decision.
* **Response Cassette**: The set of outbound call/response pairs captured during the run, indexed by call signature, so a later replay can answer each external call from the recording or detect a call with no recorded answer. Sealed as part of the Forensic Snapshot; defined formally in the Sandbox Orchestration and Replay blueprint.
* **Agent Decision**: The final output or choice produced by the wrapped agent for a given run (for example, "DENY").
* **Seal**: The act of computing an HMAC-SHA256 hash of a captured element using the secret key, producing a tamper-evident hash for that element.
* **Merkle Chain**: The tree of hashes that combines individual element hashes into intermediate hashes and finally a single root hash representing the entire snapshot.
* **Root Hash**: The single top-level hash of the Merkle chain that represents an entire Forensic Snapshot; any change to any element changes the root hash.
* **Secret Key**: The key used in HMAC-SHA256 sealing; possession of the key is required to produce or verify valid HMAC hashes. Custody is hybrid: by default Notary manages a per-organization key, and optionally a customer supplies and retains their own key (bring-your-own-key), which they may withhold from Notary and use for local verification.
* **Local Verification**: Recomputing hashes from a Forensic Snapshot and comparing them to the stored hashes, performed entirely on the developer's machine without contacting the cloud.
* **Interception**: The mechanism by which the SDK transparently captures LLM and API traffic without requiring changes to the agent's core logic.

## Requirements

### REQ-FAL-001: Wrap an Agent for Forensic Capture

**User Story:** As a developer, I want to wrap my existing agent with the SDK using minimal code, so that forensic capture begins without restructuring my agent.

**Acceptance Criteria:**

* **AC-FAL-001.1:** When the developer initializes the SDK with a secret key, the SDK shall begin capturing elements for subsequent agent runs without requiring changes to the agent's core logic.
* **AC-FAL-001.2:** The SDK shall provide a Python integration using decorators and context managers.
* **AC-FAL-001.3:** The SDK shall provide a TypeScript integration using proxy objects and middleware for Node.js environments.
* **AC-FAL-001.4:** If the SDK is initialized without a secret key, then the SDK shall raise an initialization error and shall not begin capture.
* **AC-FAL-001.5:** While no secret key rotation or override is supplied, the SDK shall use the key provided at initialization for all sealing in that run.
* **AC-FAL-001.6:** Where the customer supplies their own secret key (bring-your-own-key), the SDK shall use it for sealing and shall not transmit it to the cloud.

### REQ-FAL-002: Capture LLM Interactions

**User Story:** As a developer, I want the SDK to capture LLM prompts and responses automatically, so that the reasoning inputs and outputs of my agent are part of the forensic record.

**Acceptance Criteria:**

* **AC-FAL-002.1:** When the agent sends a prompt to a supported LLM provider, the SDK shall capture the full prompt as a Captured Element.
* **AC-FAL-002.2:** When the LLM returns a response, the SDK shall capture the full response and its associated metadata as Captured Elements.
* **AC-FAL-002.3:** The SDK shall support interception of Anthropic and OpenAI LLM calls.
* **AC-FAL-002.4:** If an LLM call raises an error, then the SDK shall capture the error outcome as part of the record rather than discarding the interaction.

### REQ-FAL-003: Capture Outbound API Calls

**User Story:** As a developer, I want the SDK to capture the outbound API calls my agent makes, so that external interactions that influenced a decision are preserved.

**Acceptance Criteria:**

* **AC-FAL-003.1:** When the agent issues an outbound HTTP/REST API call, the SDK shall capture the request body as a Captured Element.
* **AC-FAL-003.2:** When the API responds, the SDK shall capture the response body and status as Captured Elements.
* If the agent uses randomness, the SDK shall capture the seed used for the run as a Captured Element, so it can be replayed identically.
* If the agent checks the wall-clock time, the SDK shall capture the timestamp used for the run as a Captured Element, so it can be replayed identically.
* **AC-FAL-003.3:** When the SDK captures an outbound call and its response, it shall record them as a Response Cassette entry indexed by a call signature derived from the call, so a later replay can look up the recorded response or detect that a call has no recorded answer.
* **AC-FAL-003.4:** If the agent uses randomness, the SDK shall capture the seed used for the run as a Captured Element, so it can be replayed identically.
* **AC-FAL-003.5:** If the agent checks the wall-clock time, the SDK shall capture the timestamp used for the run as a Captured Element, so it can be replayed identically.

### REQ-FAL-004: Capture the Agent Decision

**User Story:** As a developer, I want the SDK to record my agent's final decision, so that the outcome under investigation is anchored in the forensic record.

**Acceptance Criteria:**

* **AC-FAL-004.1:** When the agent produces its final output for a run, the SDK shall capture it as the Agent Decision element.
* **AC-FAL-004.2:** The SDK shall associate the Agent Decision with the LLM and API elements captured during the same run within a single Forensic Snapshot.

### REQ-FAL-005: Seal Captured Elements Cryptographically

**User Story:** As a compliance officer, I want each captured element sealed cryptographically, so that any tampering with an individual element is detectable.

**Acceptance Criteria:**

* **AC-FAL-005.1:** When an element is captured, the SDK shall seal it by computing an HMAC-SHA256 hash of the element using the secret key.
* **AC-FAL-005.2:** The SDK shall produce a distinct hash for each Captured Element in the snapshot.
* **AC-FAL-005.3:** The SDK shall use SHA256 as the hashing algorithm for all seals.

### REQ-FAL-006: Chain Element Hashes into a Merkle Root

**User Story:** As a compliance officer, I want element hashes chained into a single root hash, so that reordering or altering any element breaks the proof for the whole snapshot.

**Acceptance Criteria:**

* **AC-FAL-006.1:** When all elements for a run are sealed, the SDK shall combine their hashes into a Merkle Chain and compute a single Root Hash for the Forensic Snapshot.
* **AC-FAL-006.2:** When any Captured Element changes, the SDK shall produce a different Root Hash on recomputation.
* **AC-FAL-006.3:** When the order of elements changes, the SDK shall produce a different Root Hash on recomputation.

### REQ-FAL-007: Export the Forensic Snapshot

**User Story:** As a developer, I want to export the forensic snapshot in portable formats, so that it can be stored, shared, or ingested by the Forensics Platform.

**Acceptance Criteria:**

* **AC-FAL-007.1:** When a run completes, the SDK shall produce a Forensic Snapshot containing all Captured Elements, their individual hashes, the Merkle Chain, and the Root Hash.
* **AC-FAL-007.2:** The SDK shall support exporting the Forensic Snapshot as JSON.
* **AC-FAL-007.3:** Where cloud export is configured, the SDK shall support exporting the Forensic Snapshot to S3 or the Notary cloud.
* **AC-FAL-007.4:** The default export format shall be JSON when no export target is configured.

### REQ-FAL-008: Verify Snapshot Integrity Locally

**User Story:** As a developer, I want to verify a snapshot's integrity on my own machine, so that I can confirm authenticity without sending data to the cloud.

**Acceptance Criteria:**

* **AC-FAL-008.1:** When the developer runs Local Verification with the correct secret key, the SDK shall recompute the Root Hash from the snapshot and confirm authenticity when it matches the stored Root Hash.
* **AC-FAL-008.2:** If the recomputed Root Hash does not match the stored Root Hash, then the SDK shall report that tampering was detected.
* **AC-FAL-008.3:** The SDK shall perform Local Verification without any network connection to cloud infrastructure.
* **AC-FAL-008.4:** If Local Verification is attempted without the correct secret key, then the SDK shall report that verification could not be completed.

### REQ-FAL-009: Operate Offline

**User Story:** As a developer, I want the SDK to work entirely offline, so that capture and verification never depend on cloud availability.

**Acceptance Criteria:**

* **AC-FAL-009.1:** While no network connection is available, the SDK shall continue to capture, seal, chain, and export Forensic Snapshots locally.
* **AC-FAL-009.2:** The SDK shall not require any cloud service to perform capture, sealing, chaining, or Local Verification.

### Decision Evidence Graph Capture

## Overview

Decision Evidence Graph Capture extends the Forensic Agent Logger SDK from a basic recorder of LLM calls, outbound API calls, and final decisions into a structured evidence graph for real AI workflows. Modern agents do not fail only at the model call. They fail across retrieval, memory, MCP tool use, connector calls, policy evaluation, guardrails, human handoff, side effects, and release configuration. This feature defines the decision-relevant workflow elements the SDK must be able to capture so Notary can replay, explain, verify, and turn failures into future release-gate scenarios.

The purpose is not to become observability or process mining. Notary captures only the workflow elements that affect a decision, explain a failure, or verify a fix. Each captured element should help answer one of four questions: what did the agent see, what did it use, what did it do, and what outcome did that produce? This evidence graph becomes the source for replay, fix verification, Scenario creation, certificates, Proof of Readiness, and Release Gate checks.

## Terminology

* **Decision Evidence Graph**: The sealed graph of decision-relevant workflow elements for one AI run, including model calls, retrieval context, tool calls, connectors, policy/guardrail evaluations, human actions, side effects, and the final decision.
* **Workflow Element**: Any captured node in the Decision Evidence Graph that can affect, explain, or verify an AI decision.
* **Model Invocation**: A call to a model provider, including provider, model name/version, parameters, input messages, output, and tool-call proposals.
* **Prompt and Policy Context**: The system prompt, policy text, policy version, rule configuration, or prompt reference used by the agent when making a decision.
* **Retrieval Event**: A RAG or search step that retrieves context for the agent, including query, embedding model, index/version, filters, retrieved document/chunk IDs, scores, and selected context.
* **Memory State**: Decision-relevant session, conversation, or long-term memory used by the agent.
* **MCP Tool Call**: A tool invocation made through the Model Context Protocol, including server, tool name, tool version, input arguments, permission scope, response, and error state.
* **Connector Call**: A call to a non-MCP external system or SaaS connector, including endpoint/tool name, request, response, status, and side-effect metadata.
* **Guardrail Result**: A safety, policy, or compliance check applied to a model output or tool action, including score, threshold, and allow/block/escalate decision.
* **Human Action**: A human review, approval, rejection, override, escalation, QA label, or expected-outcome label associated with the run.
* **Business Side Effect**: A real-world action caused or proposed by the agent, such as closing a ticket, denying a claim, sending a message, issuing a refund, creating a case, or triggering escalation.
* **Release Context**: The version context for an agent run, including agent version, git commit, prompt version, policy version, model version, RAG index version, connector version, feature flags, and environment.

## Requirements

### REQ-FAL-DEG-001: Capture the Decision Evidence Graph

**User Story:** As a compliance officer, I want the SDK to capture the workflow elements that affected an AI decision, so that Notary can reconstruct why the decision happened.

**Acceptance Criteria:**

* **AC-FAL-DEG-001.1:** When an agent run is captured, the SDK shall represent captured workflow elements as a Decision Evidence Graph rather than as an unstructured list of logs.
* **AC-FAL-DEG-001.2:** Each Workflow Element shall record its kind, timestamp, payload, and relationship to prior elements where that relationship is known.
* **AC-FAL-DEG-001.3:** The SDK shall preserve the order of Workflow Elements that affect replay or root-cause analysis.
* **AC-FAL-DEG-001.4:** The SDK shall include each Workflow Element in the Forensic Snapshot sealing process so changes to any captured element alter the Root Hash.

### REQ-FAL-DEG-002: Capture Model Invocation Details

**User Story:** As a developer, I want model calls captured with exact model and parameter details, so that replay and investigation can distinguish model behavior from surrounding workflow behavior.

**Acceptance Criteria:**

* **AC-FAL-DEG-002.1:** When the agent invokes a model, the SDK shall capture the provider, model name, model version where available, and invocation parameters.
* **AC-FAL-DEG-002.2:** When the agent sends input messages to a model, the SDK shall capture the messages or a configured redacted representation.
* **AC-FAL-DEG-002.3:** When the model returns an output, tool-call proposal, refusal, or error, the SDK shall capture that result as a Workflow Element.
* **AC-FAL-DEG-002.4:** If randomness, seed, temperature, or sampling configuration affects a model invocation, the SDK shall capture the value used where available.

### REQ-FAL-DEG-003: Capture Prompt and Policy Context

**User Story:** As a compliance officer, I want prompt and policy versions captured, so that I can tell which rule or instruction governed a decision.

**Acceptance Criteria:**

* **AC-FAL-DEG-003.1:** When an agent run uses a system prompt, policy, or rule configuration, the SDK shall capture its name or reference and version where available.
* **AC-FAL-DEG-003.2:** When full prompt or policy text is captured, the SDK shall include it in the sealed snapshot or record a sealed hash and reference if the customer configures reference-only capture.
* **AC-FAL-DEG-003.3:** When a decision depends on a policy evaluation, the SDK shall capture the evaluated condition and the policy outcome.

### REQ-FAL-DEG-004: Capture RAG and Retrieval Events

**User Story:** As a developer, I want retrieval context captured, so that I can determine whether stale, missing, or unauthorized context caused a bad decision.

**Acceptance Criteria:**

* **AC-FAL-DEG-004.1:** When the agent performs retrieval or search, the SDK shall capture the retrieval query, retrieval source, index or collection name, and index version where available.
* **AC-FAL-DEG-004.2:** When the retrieval uses embeddings, the SDK shall capture the embedding model and relevant retrieval parameters such as top-k, filters, or reranker configuration where available.
* **AC-FAL-DEG-004.3:** When documents or chunks are retrieved, the SDK shall capture document IDs, chunk IDs, scores, and content hashes; full content capture shall be configurable.
* **AC-FAL-DEG-004.4:** The SDK shall record the final retrieval context supplied to the model or a sealed reference to that context.

### REQ-FAL-DEG-005: Capture MCP Tool Calls

**User Story:** As an AI platform engineer, I want MCP tool calls captured as first-class evidence, so that tool use can be replayed and verified.

**Acceptance Criteria:**

* **AC-FAL-DEG-005.1:** When an agent calls an MCP tool, the SDK shall capture the MCP server name, tool name, tool version where available, input arguments, and permission scope.
* **AC-FAL-DEG-005.2:** When an MCP tool returns a response or error, the SDK shall capture the response or error as a Workflow Element.
* **AC-FAL-DEG-005.3:** The SDK shall record MCP tool responses as cassette entries so replay can answer the same tool call from the sealed record.
* **AC-FAL-DEG-005.4:** If an MCP call performs or proposes a side effect, the SDK shall capture whether the side effect was proposed, approved, executed, rejected, or failed.

### REQ-FAL-DEG-006: Capture Connector Calls and External Side Effects

**User Story:** As a compliance officer, I want external connector calls and side effects captured, so that I can trace how an AI decision affected business systems.

**Acceptance Criteria:**

* **AC-FAL-DEG-006.1:** When the agent calls a non-MCP connector or API, the SDK shall capture the system name, endpoint or tool name, request, response, status, and error state.
* **AC-FAL-DEG-006.2:** When a connector call creates, updates, deletes, sends, closes, pays, refunds, escalates, or otherwise changes a business object, the SDK shall capture a Business Side Effect record.
* **AC-FAL-DEG-006.3:** The SDK shall distinguish read-only connector calls from write or side-effecting connector calls.
* **AC-FAL-DEG-006.4:** The SDK shall record connector responses as cassette entries where those responses are needed for replay.

### REQ-FAL-DEG-007: Capture Guardrails, Safety Checks, and Routing Decisions

**User Story:** As a risk owner, I want guardrail and routing decisions captured, so that I can determine whether the agent followed required safety and escalation policies.

**Acceptance Criteria:**

* **AC-FAL-DEG-007.1:** When a safety, policy, or compliance guardrail evaluates model output or tool use, the SDK shall capture the guardrail name, version, score, threshold, and outcome where available.
* **AC-FAL-DEG-007.2:** When an agent makes a routing decision such as continue bot, escalate to human, route to specialist, approve, deny, or hold for review, the SDK shall capture the routing decision and its policy basis where available.
* **AC-FAL-DEG-007.3:** When a guardrail blocks or escalates an action, the SDK shall capture the blocked or escalated action and reason.

### REQ-FAL-DEG-008: Capture Human Actions and Expected Outcomes

**User Story:** As a business operator, I want human overrides and QA labels captured, so that real corrections can become replayable scenarios.

**Acceptance Criteria:**

* **AC-FAL-DEG-008.1:** When a human reviews, approves, rejects, overrides, escalates, or corrects an agent decision, the SDK or platform shall capture the Human Action as part of the Decision Evidence Graph.
* **AC-FAL-DEG-008.2:** When a human supplies an expected correct behavior, the system shall associate it with the relevant Verification Record or Scenario.
* **AC-FAL-DEG-008.3:** When a human override differs from the agent's original decision, the system shall preserve both the original agent decision and the human-corrected outcome.
* **AC-FAL-DEG-008.4:** Human Action capture shall record role or system identity without requiring storage of unnecessary personal data.

### REQ-FAL-DEG-009: Capture Release Context

**User Story:** As an AI engineer, I want release context captured for each run, so that Notary can compare behavior across agent versions and gate future releases.

**Acceptance Criteria:**

* **AC-FAL-DEG-009.1:** When release context is available, the SDK shall capture the agent version, git commit, prompt version, policy version, model version, RAG index version, connector version, feature flags, and environment.
* **AC-FAL-DEG-009.2:** When a run is used as a Scenario, the Scenario shall retain the release context of the source run.
* **AC-FAL-DEG-009.3:** When a future Scenario Run or Readiness Check is executed, the platform shall record the release context of the candidate version under test.

### REQ-FAL-DEG-010: Support Privacy-Preserving Capture

**User Story:** As a CISO, I want sensitive workflow data captured with field controls, so that Notary can preserve evidence without over-exposing personal or proprietary data.

**Acceptance Criteria:**

* **AC-FAL-DEG-010.1:** The SDK shall support field-level redaction, hashing, or reference-only capture for configured Workflow Element fields.
* **AC-FAL-DEG-010.2:** When a field is redacted, hashed, or captured by reference, the SDK shall preserve enough metadata to prove the field existed and was handled according to configuration.
* **AC-FAL-DEG-010.3:** Privacy-preserving capture settings shall be reflected in the Forensic Snapshot so later reviewers know which fields are raw, redacted, hashed, or reference-only.

### Decision Context and Risk Metadata

## Overview

Decision Context and Risk Metadata captures the surrounding facts that determine whether an AI decision is risky, certifiable, and worth investigating. The Decision Evidence Graph records what the agent saw and did. This feature records the context around that graph: who or what identity acted, what permissions were used, whether approval or consent was required, whether data was fresh, what fallback paths occurred, how severe the customer or business impact was, and whether later outcomes such as complaints or overrides changed the risk posture.

This context matters because two identical agent actions can carry very different risk. A support response to a low-value FAQ is not the same as a response about fraud, healthcare, payments, account closure, or a VIP customer threatening churn. Notary needs this metadata to decide what becomes a Verification Record, what should be promoted to an Incident, what can be certified, and what should become a Scenario for future release gates.

## Terminology

* **Decision Evidence Graph**: The sealed graph of decision-relevant workflow elements for one AI run. Defined formally in the Decision Evidence Graph Capture feature.
* **Decision Context**: The metadata surrounding an AI run that affects its risk, authorization, business impact, or certifiability.
* **Acting Identity**: The user, service account, agent identity, or delegated identity under which an agent performed an action.
* **Authorization Context**: The permission scope, role, tenant, organization, or policy that allowed the agent to use a tool, connector, data source, or side-effecting action.
* **Approval State**: Whether a proposed or executed action required approval or consent, and whether that approval or consent was granted, denied, or missing.
* **Data Freshness**: The timestamp, version, or freshness indicator for data used by the agent.
* **Fallback Path**: A degraded or alternate path the agent used after a tool, connector, retrieval source, or model call failed, timed out, or returned incomplete data.
* **Uncertainty Signal**: A confidence, ambiguity, sentiment, risk, or threshold signal that affects whether the agent should proceed, escalate, or defer.
* **Impact Severity**: The business or customer impact level of the decision, including value, regulated topic, customer tier, reversibility, and harm severity.
* **Post-Decision Outcome**: A later event that changes the interpretation of a decision, such as a complaint, ticket reopen, appeal, chargeback, human reversal, or regulatory inquiry.
* **Evidence Completeness**: A summary of which evidence inputs are present, redacted, missing, unsupported, unverifiable, or non-deterministic.

## Requirements

### REQ-FAL-DRM-001: Capture Acting Identity and Authorization Context

**User Story:** As a CISO, I want each captured AI action to record the identity and authorization context used, so that I can verify the agent acted under the correct permissions.

**Acceptance Criteria:**

* **AC-FAL-DRM-001.1:** When an agent uses a tool, connector, data source, or side-effecting action, the SDK shall capture the Acting Identity where available.
* **AC-FAL-DRM-001.2:** When an agent uses a tool, connector, data source, or side-effecting action, the SDK shall capture the Authorization Context where available.
* **AC-FAL-DRM-001.3:** If the Acting Identity or Authorization Context is unavailable, then the SDK shall mark it as unavailable rather than omitting the field silently.
* **AC-FAL-DRM-001.4:** The platform shall expose Acting Identity and Authorization Context as part of the record's defensibility context.

### REQ-FAL-DRM-002: Capture Approval and Consent State

**User Story:** As a compliance officer, I want approval and consent state captured for sensitive actions, so that I can prove whether the agent had authority to proceed.

**Acceptance Criteria:**

* **AC-FAL-DRM-002.1:** When an agent proposes or executes an action that requires approval, the SDK shall capture whether approval was required.
* **AC-FAL-DRM-002.2:** When approval was required, the SDK or platform shall capture whether approval was granted, denied, missing, or expired.
* **AC-FAL-DRM-002.3:** When a decision requires customer consent, the SDK or platform shall capture whether consent was present, absent, or not applicable.
* **AC-FAL-DRM-002.4:** If an action executes without required approval or consent, then the platform shall be able to classify the record as a policy-breach candidate.

### REQ-FAL-DRM-003: Capture Data Freshness and Source Lineage

**User Story:** As an AI engineer, I want source freshness and lineage captured, so that stale or wrong data can be identified as a cause of failure.

**Acceptance Criteria:**

* **AC-FAL-DRM-003.1:** When an agent uses data from a source system, document, index, connector, or retrieval result, the SDK shall capture source identity and version where available.
* **AC-FAL-DRM-003.2:** When data freshness is available, the SDK shall capture the freshness timestamp or version indicator.
* **AC-FAL-DRM-003.3:** If a decision used stale data according to the customer's configured freshness rule, then the platform shall be able to represent that condition in the record's evidence context.

### REQ-FAL-DRM-004: Capture Fallback Paths and Tool Availability

**User Story:** As a business operator, I want fallback paths captured, so that I can tell when an agent guessed, degraded, or routed differently because a dependency failed.

**Acceptance Criteria:**

* **AC-FAL-DRM-004.1:** When a model, tool, connector, retrieval source, or MCP server is unavailable, times out, or returns an error, the SDK shall capture that failure state.
* **AC-FAL-DRM-004.2:** When an agent uses a Fallback Path after a dependency failure, the SDK shall capture the fallback used and the reason for fallback.
* **AC-FAL-DRM-004.3:** When no fallback is available and the run cannot complete, the SDK shall capture the incomplete state rather than dropping the run.

### REQ-FAL-DRM-005: Capture Uncertainty and Escalation Signals

**User Story:** As a support operations leader, I want confidence and escalation signals captured, so that I can verify whether an agent should have escalated instead of proceeding.

**Acceptance Criteria:**

* **AC-FAL-DRM-005.1:** When an agent or classifier produces a confidence score, sentiment score, ambiguity score, or risk score used in a decision, the SDK shall capture the score and threshold where available.
* **AC-FAL-DRM-005.2:** When escalation policy depends on an Uncertainty Signal, the SDK shall capture the evaluated condition and routing outcome.
* **AC-FAL-DRM-005.3:** When a user requests human handoff, the SDK or platform shall capture the request count and whether handoff was offered, accepted, or denied where available.
* **AC-FAL-DRM-005.4:** When a handoff occurs, the SDK or platform shall capture whether conversation context was transferred to the human agent where available.

### REQ-FAL-DRM-006: Capture Impact Severity

**User Story:** As a risk owner, I want each captured decision to include impact severity, so that high-risk records can be prioritized and promoted to incidents.

**Acceptance Criteria:**

* **AC-FAL-DRM-006.1:** When impact metadata is available, the platform shall capture the customer tier, transaction value, regulated-topic flag, risk class, reversibility, and harm severity.
* **AC-FAL-DRM-006.2:** If a record crosses a configured impact threshold, then the platform shall be able to classify it as high-risk.
* **AC-FAL-DRM-006.3:** Impact Severity shall be usable by Capture Rules when deciding whether to create a Verification Record or promote one to an Incident.

### REQ-FAL-DRM-007: Capture Post-Decision Outcomes

**User Story:** As a compliance officer, I want later outcomes connected back to the original AI decision, so that a clean-looking decision can be reclassified when it is later disputed or reversed.

**Acceptance Criteria:**

* **AC-FAL-DRM-007.1:** When a later complaint, ticket reopen, appeal, chargeback, human reversal, regulatory inquiry, or similar outcome is associated with a captured decision, the platform shall link that Post-Decision Outcome to the original record.
* **AC-FAL-DRM-007.2:** When a Post-Decision Outcome indicates the original decision may have been wrong, the platform shall be able to promote the record to an Incident or Scenario candidate.
* **AC-FAL-DRM-007.3:** The platform shall preserve both the original decision and the later outcome so the difference is auditable.

### REQ-FAL-DRM-008: Report Evidence Completeness

**User Story:** As an auditor, I want to know which evidence inputs are present or missing, so that I can judge whether a replay, certificate, or readiness result is reliable.

**Acceptance Criteria:**

* **AC-FAL-DRM-008.1:** The platform shall compute an Evidence Completeness summary for each Verification Record.
* **AC-FAL-DRM-008.2:** The Evidence Completeness summary shall identify required evidence that is present, missing, redacted, reference-only, unsupported, unverifiable, or non-deterministic.
* **AC-FAL-DRM-008.3:** If missing or unsupported evidence prevents replay, mutation testing, certification, or readiness verification, then the platform shall identify the blocking input rather than presenting the record as verified.
* **AC-FAL-DRM-008.4:** Evidence Completeness shall be available to the dashboard, certificates, and reports where relevant.

## Forensics Platform

## Overview

The Forensics Platform is the managed cloud application at the center of Notary. It receives Forensic Snapshots and other captured decision records, validates cryptographic integrity where the required verification inputs are available, and stores the result as a tamper-evident Verification Record. From that trusted foundation, the platform orchestrates the active release-gate workflow: cassette-first replay, fix verification, bounded proof generation, Scenario promotion, Scenario Runs, Proof of Readiness, and Release Gate decisions.

This document covers the platform's foundational capabilities: ingestion, integrity handling, immutable evidence storage, custody, and the record lifecycle that child features build on. The child features define the heavier downstream capabilities: Deterministic Replay, Mutation Testing, Proof of Mitigation Certificates, Scenario Library, Proof Claim Scope and Label Provenance, and Proof of Readiness. Incident remains the failure-triggered type of Verification Record; the broader product works with any Verification Record worth proving, including overrides, disputes, threshold crossings, and pre-release checks.

## Terminology

* **Forensic Snapshot**: The structured, cryptographically sealed record of a single agent run produced by the Forensic Agent Logger SDK. Defined formally in the Forensic Agent Logger SDK feature.
* **Root Hash**: The single top-level Merkle hash representing an entire Forensic Snapshot. Defined formally in the Forensic Agent Logger SDK feature.
* **Verification Record**: The platform-side record created from an ingested Forensic Snapshot or other captured decision record, against which replay, mutation testing, proof generation, Scenario promotion, and readiness checks are performed over time. Defined formally in the Capture Rules and Decision Triggers feature.
* **Incident**: A Verification Record whose Capture Trigger is a production failure or other investigation-worthy failure condition. Existing incident terminology remains valid for the failure case.
* **Record Ingestion**: The process of receiving a Forensic Snapshot or normalized decision record via API, validating its cryptographic integrity where possible, persisting evidence, and creating a Verification Record.
* **Integrity Validation**: Recomputing the Root Hash of an ingested snapshot and comparing it to the submitted Root Hash to confirm the snapshot has not been tampered with.
* **Immutable Log**: The append-only, tamper-proof store where validated snapshots and Incidents are persisted and cannot be altered or deleted after write.
* **Record Status**: The lifecycle state of a Verification Record as it moves through the proof workflow. The states include `ingested`, `integrity_verified`, `integrity_unverified`, `replay_pending`, `replayed_reproduced`, `replayed_not_reproduced`, `replay_incomplete`, `replay_non_deterministic`, `replay_escalation_required`, `mutation_pending`, `mitigation_verified`, `mitigation_not_verified`, `mutation_incomplete`, `certified`, and `promoted_to_scenario`.
* **Custody Event**: A recorded action in the evidence lifecycle that identifies what happened to an Incident, who or what performed the action, when it happened, and which evidence artifact or workflow step it affected.
* **Defensibility Summary**: The platform's incident-level summary of whether the evidence record is custody-complete, integrity-verified, reproducible, and eligible for downstream certificate or report generation.

## Requirements

The requirements below preserve the established Incident wording where the workflow begins with a production failure. Unless an acceptance criterion explicitly says otherwise, the same behavior applies to the broader Verification Record type used by capture rules, manual submissions, source-system connectors, Scenario promotion, and Release Gate workflows.

### REQ-FP-001: Ingest a Forensic Snapshot

**User Story:** As a compliance officer, I want to submit a forensic snapshot to the platform, so that a production incident becomes an investigable record.

**Acceptance Criteria:**

* **AC-FP-001.1:** When a client submits a Forensic Snapshot to the ingestion API, the platform shall accept the snapshot for Integrity Validation.
* **AC-FP-001.2:** When a submitted snapshot passes Integrity Validation, the platform shall create an Incident record from it.
* **AC-FP-001.3:** If a submitted snapshot is malformed or missing required elements, then the platform shall reject it and return an error identifying the problem.
* **AC-FP-001.4:** When an Incident is created, the platform shall assign it an initial Incident Status of ingested.

### REQ-FP-002: Validate Cryptographic Integrity on Ingestion

**User Story:** As a compliance officer, I want the platform to verify a snapshot's integrity when it arrives, so that only untampered evidence enters the record.

**Acceptance Criteria:**

* **AC-FP-002.1:** When a snapshot is submitted, the platform shall recompute its Root Hash and compare it to the submitted Root Hash.
* **AC-FP-002.2:** When the recomputed Root Hash matches the submitted Root Hash, the platform shall mark the snapshot as integrity-verified.
* **AC-FP-002.3:** If the recomputed Root Hash does not match the submitted Root Hash, then the platform shall reject the snapshot and record that tampering was detected.
* **AC-FP-002.4:** If integrity validation cannot be completed because required verification inputs are absent, then the platform shall preserve the record with an explicit integrity limitation rather than presenting it as integrity-verified.

### REQ-FP-003: Store Incidents in a Tamper-Proof Immutable Log

**User Story:** As a general counsel, I want incidents stored in an append-only immutable log, so that the chain of custody is defensible in audits and litigation.

**Acceptance Criteria:**

* **AC-FP-003.1:** When an Incident is created, the platform shall persist it and its source snapshot to the Immutable Log.
* **AC-FP-003.2:** The platform shall write to the Immutable Log in an append-only manner.
* **AC-FP-003.3:** If any request attempts to modify or delete a record in the Immutable Log, then the platform shall deny the operation.
* **AC-FP-003.4:** The Immutable Log shall retain each Incident so that it remains verifiable at any later time.

### REQ-FP-004: Retrieve an Incident

**User Story:** As a compliance officer, I want to retrieve a stored incident and its details, so that I can review the captured evidence before acting on it.

**Acceptance Criteria:**

* **AC-FP-004.1:** When the user requests an Incident by its identifier, the platform shall return the Incident, its Captured Elements, and its integrity-verification result.
* **AC-FP-004.2:** When the user lists Incidents, the platform shall return the set of Incidents with their current Incident Status.
* **AC-FP-004.3:** If the requested Incident does not exist, then the platform shall return a not-found error.
* **AC-FP-004.4:** When no Incidents exist, the platform shall return an empty list rather than an error.

### REQ-FP-005: Track Incident Lifecycle Status

**User Story:** As a compliance officer, I want each incident to reflect where it is in the forensic workflow, so that I know what has been done and what remains.

**Acceptance Criteria:**

* **AC-FP-005.1:** When a downstream step completes for an Incident (replay, mutation testing, or certification), the platform shall update the Incident Status to reflect the furthest completed step.
* **AC-FP-005.2:** While no downstream step has been performed, the Incident Status shall remain ingested.
* **AC-FP-005.3:** When the Incident Status changes, the platform shall record the transition as an append-only event in the Immutable Log, preserving prior status history rather than overwriting it.
* **AC-FP-005.4:** Any status view the platform serves for querying shall be derivable from the append-only status transition events in the Immutable Log.

### REQ-FP-006: Authenticated and Isolated Access

**User Story:** As a CISO, I want incident data access restricted to authorized users of our organization, so that sensitive forensic evidence is not exposed.

**Acceptance Criteria:**

* **AC-FP-006.1:** If an unauthenticated request is made to any incident endpoint, then the platform shall deny the request.
* **AC-FP-006.2:** When a user requests Incidents, the platform shall return only Incidents belonging to that user's organization.
* **AC-FP-006.3:** If a user requests an Incident belonging to another organization, then the platform shall deny access.

### REQ-FP-007: Enforce the Incident Lifecycle State Machine

**User Story:** As a compliance officer, I want the platform to enforce a defined order of forensic steps with predictable failure handling, so that an incident's workflow is unambiguous and its timeline is defensible.

**Acceptance Criteria:**

* **AC-FP-007.1:** While an Incident is `ingested`, the platform shall allow a replay to be started and shall reject requests to start mutation testing or certificate generation.
* **AC-FP-007.2:** When a replay is started, the platform shall move the Incident to `replaying`; when it succeeds, to `replayed`; and if it fails or is cancelled, back to `ingested` so it can be retried.
* **AC-FP-007.3:** While an Incident is `replayed` and marked reproducible, the platform shall allow mutation testing to be started; if the replay found the incident not reproducible, the platform shall reject mutation testing.
* **AC-FP-007.4:** When mutation testing is started, the platform shall move the Incident to `mutating`; when the fix is verified, to `mitigated`; and if the test fails or is not verified, back to `replayed` so a corrected fix can be re-submitted.
* **AC-FP-007.5:** When a mutation test has failed a configurable number of times for an Incident, the platform shall require compliance-officer approval before accepting a further mutation-test attempt.
* **AC-FP-007.6:** While an Incident is `mitigated`, the platform shall allow certificate generation; when it is started, the platform shall move the Incident to `certifying` and, on success, to `certified`.
* **AC-FP-007.7:** While an Incident is `certified`, the platform shall treat the state as terminal and shall reject requests to re-run replay, mutation testing, or certification for that Incident.
* **AC-FP-007.8:** If a request is made to start a step that is not permitted from the Incident's current state, then the platform shall reject it and return the current state and the allowed next steps.
* **AC-FP-007.9:** While a step is in a transient state (`replaying`, `mutating`, `certifying`), the platform shall reject a second concurrent step for the same Incident.

### REQ-FP-008: Record Custody Events

**User Story:** As a general counsel, I want the platform to record custody events across the evidence lifecycle, so that the evidence record can show who or what handled it and when.

**Acceptance Criteria:**

* **AC-FP-008.1:** When an Incident is created, the platform shall record a Custody Event for ingestion.
* **AC-FP-008.2:** When integrity validation completes, the platform shall record a Custody Event identifying the validation outcome.
* **AC-FP-008.3:** When replay, mutation testing, certificate generation, report generation, or export occurs for an Incident, the platform shall record a Custody Event for that action.
* **AC-FP-008.4:** Each Custody Event shall identify the acting user or system component, the event time, the affected Incident, the action performed, and the resulting evidence artifact or workflow state.
* **AC-FP-008.5:** If a Custody Event cannot be recorded for a required lifecycle action, then the platform shall treat the action as incomplete and shall not present the resulting evidence as custody-complete.

### REQ-FP-009: Provide a Defensibility Summary

**User Story:** As a compliance officer, I want to see whether an incident's evidence is defensible, so that I know whether it is ready for external submission.

**Acceptance Criteria:**

* **AC-FP-009.1:** When the user retrieves an Incident, the platform shall include a Defensibility Summary for that Incident.
* **AC-FP-009.2:** The Defensibility Summary shall indicate whether the Incident has complete custody events for each completed lifecycle step.
* **AC-FP-009.3:** The Defensibility Summary shall indicate the integrity-verification result and any limitation that prevents server-side verification.
* **AC-FP-009.4:** The Defensibility Summary shall indicate whether replay has produced a deterministic Reproducibility Result.
* **AC-FP-009.5:** The Defensibility Summary shall indicate whether the Incident is eligible for certificate or report generation based on its current evidence state.
* **AC-FP-009.6:** If any defensibility input is missing, then the Defensibility Summary shall identify the missing input rather than reporting the Incident as submission-ready.

### Deterministic Replay

## Overview

Deterministic Replay reproduces a stored incident by re-executing its captured calls under controlled conditions and comparing the replayed result to the original. By default it replays against the incident's sealed Response Cassette — the recorded provider responses from incident time — which is fast, portable, and reproducible independent of the provider. When a fix changes which external calls fire (so the cassette has no recorded answer) or a customer opts into live confirmation, replay escalates to a clean real-provider sandbox (Stripe test mode, GitHub test org, Salesforce sandbox). If the replayed result matches the original, the incident is proven reproducible, establishing that the root cause lies in the agent's own logic rather than a transient API error or environmental factor.

This capability extends the Forensics Platform: it operates on an Incident that has already been ingested and integrity-verified. Cassette replay is the default because a sealed recording remains reproducible years later even if the provider changes or retires its test mode; real sandboxes matter as the escalation path because a recording cannot answer a call a fix newly introduces, and live validation is the stronger claim when a fix changes external behavior. Hand-written mocks are used in neither path — the cassette is a sealed capture of the real responses, not a hand-authored stub.

## Supported Providers

Cassette replay works for any incident regardless of provider, because it replays the sealed recording rather than a live system. Sandbox escalation, by contrast, is supported at launch for three providers: Stripe test mode, GitHub test org, and Salesforce sandbox. When a fix requires sandbox validation for a provider outside this set, that validation is reported as unsupported (see REQ-FP-RP-001.5); the incident and its cassette replay still stand, but a fix that changes calls to an unsupported provider cannot yet be validated live. Additional providers (for example HL7 FHIR, Workday, and SAP) are roadmap items added as new provider adapters rather than product redesign. This scope should inform go-to-market: cassette-backed forensics is broadly available, while live fix-validation coverage should be confirmed against a given customer's stack rather than assumed.

## Terminology

* **Incident**: The platform-side record of an ingested agent run. Defined formally in the Forensics Platform feature.
* **Response Cassette**: The sealed set of external call/response pairs recorded during the incident, indexed by call signature and replayed as the default source of external responses. Defined formally in the Sandbox Orchestration and Replay blueprint.
* **Sandbox Environment**: A clean, isolated test instance of a real external API provider (for example, Stripe test mode, GitHub test org, Salesforce sandbox) used to validate a fix when the cassette cannot answer a call or the customer opts into live validation.
* **Sandbox Orchestration**: The automatic provisioning and seeding of a Sandbox Environment with state equivalent to the incident, requiring no customer setup.
* **Replay Run**: A single re-execution of an incident's captured calls, against the Response Cassette by default or a provisioned Sandbox Environment on escalation.
* **Replay Response**: The response produced during a Replay Run, from the Response Cassette or the Sandbox Environment.
* **Original Response**: The API response captured in the incident's Forensic Snapshot at the time of the production failure.
* **Reproducibility Result**: The outcome of comparing the Replay Response to the Original Response, indicating whether the incident reproduced.
* **Deterministic Execution Conditions**: The set of controls that make a Replay Run reproducible so that two runs of the same incident differ only by intended changes: external responses answered from the Response Cassette (or an escalated sandbox), the captured call order enforced, the captured time supplied to the agent, and any randomness seeded identically.

## Requirements

### REQ-FP-RP-001: Provision a Sandbox Environment

**User Story:** As a compliance officer, I want the platform to provision a clean sandbox for an incident automatically, so that I can replay it without any manual setup.

**Acceptance Criteria:**

* **AC-FP-RP-001.1:** When a Replay Run is requested for an Incident, the platform shall provision a clean Sandbox Environment matching the API provider used in the incident.
* **AC-FP-RP-001.2:** When provisioning a Sandbox Environment, the platform shall seed it with state equivalent to the incident without requiring customer input.
* **AC-FP-RP-001.3:** The platform shall support provisioning Stripe test mode, GitHub test org, and Salesforce sandbox environments.
* **AC-FP-RP-001.4:** The Sandbox Environment shall be isolated from any production environment.
* **AC-FP-RP-001.5:** If a run requires sandbox escalation for a provider that has no supported sandbox, then the platform shall report that live validation is unsupported for that provider and shall not start a sandbox Replay Run, while still allowing cassette replay of the incident.

### REQ-FP-RP-002: Re-Execute Captured Calls

**User Story:** As a compliance officer, I want the platform to re-run the incident's captured calls under controlled conditions, so that the production interaction is faithfully reproduced.

**Acceptance Criteria:**

* **AC-FP-RP-002.1:** When a Replay Run executes, the platform shall answer each external call from the incident's Response Cassette by default, using the captured request parameters and call order.
* **AC-FP-RP-002.2:** When a call is answered, the platform shall record the Replay Response, whether it came from the Response Cassette or an escalated Sandbox Environment.
* **AC-FP-RP-002.3:** If a Replay Run fails to execute a captured call, then the platform shall record the failure and mark the Replay Run as incomplete.

### REQ-FP-RP-003: Compare Replay to Original

**User Story:** As a compliance officer, I want the platform to compare the replayed response to the original, so that I know whether the incident is reproducible.

**Acceptance Criteria:**

* **AC-FP-RP-003.1:** When a Replay Run completes, the platform shall compare the Replay Response to the Original Response and produce a Reproducibility Result.
* **AC-FP-RP-003.2:** When the Replay Response matches the Original Response, the platform shall mark the incident as reproducible.
* **AC-FP-RP-003.3:** If the Replay Response differs from the Original Response, then the platform shall mark the incident as not reproduced and record the difference.
* **AC-FP-RP-003.4:** When a Reproducibility Result is produced, the platform shall associate it with the Incident and update the Incident Status to reflect that replay has been performed.

### REQ-FP-RP-004: Concurrent Replays

**User Story:** As a compliance officer, I want multiple replays to run at the same time, so that investigations are not serialized behind one another.

**Acceptance Criteria:**

* **AC-FP-RP-004.1:** When multiple Replay Runs are requested, the platform shall provision an isolated Sandbox Environment per run so that runs do not share state.
* **AC-FP-RP-004.2:** While concurrent Replay Runs are executing, the platform shall keep each run's results attributed to its own Incident.

### REQ-FP-RP-005: Deterministic Replay Execution

**User Story:** As a compliance officer, I want each replay to run under controlled, reproducible conditions, so that a difference in outcome reflects a real change and not sandbox drift.

**Acceptance Criteria:**

* **AC-FP-RP-005.1:** When a Replay Run answers external calls from the Response Cassette, the platform shall use the sealed recorded responses; when a run escalates to a Sandbox Environment, the platform shall provision a fresh sandbox seeded identically for the incident, with no state carried over from any previous run.
* **AC-FP-RP-005.2:** When re-executing captured calls, the platform shall enforce the same call order that was captured in the incident.
* **AC-FP-RP-005.3:** Where the agent reads the current time, the platform shall supply the timestamp captured in the incident rather than the wall-clock time of the replay.
* **AC-FP-RP-005.4:** Where the agent uses randomness, the platform shall seed it with the value captured in the incident so the run is repeatable.
* **AC-FP-RP-005.5:** Where the Deterministic Execution Conditions cannot be met for an incident (for example, an unrecoverable random seed), the platform shall record that the run is non-deterministic rather than reporting a definitive Reproducibility Result.

### REQ-FP-RP-006: Tier-Gated Replay Access

**User Story:** As a platform owner, I want replay access to respect the organization's subscription tier, so that replay volume and provider coverage match entitlements.

**Acceptance Criteria:**

* **AC-FP-RP-006.1:** When a Replay Run is requested, the platform shall check the organization's entitlements (per the Tiers and Entitlements feature) for replay volume and the requested sandbox provider before starting the run.
* **AC-FP-RP-006.2:** If the requested sandbox provider is not included in the organization's Tier, then the platform shall deny the run and indicate the provider requires a higher Tier.
* **AC-FP-RP-006.3:** While the organization's deterministic-replay Usage Limit is reached, the platform shall deny or defer further Replay Runs and indicate the limit was reached.

### Mutation Testing

## Overview

Mutation Testing verifies that a proposed fix actually resolves a reproduced incident. After an incident has been replayed and shown reproducible, a developer proposes a fix by pointing the platform at a git branch and commit. The platform re-runs the exact replay with the fixed agent logic applied, then compares the new decision to the original. If the fixed agent now produces correct behavior against the real incident scenario, the fix is verified—not assumed. This verified result is the precondition for issuing a Proof of Mitigation certificate.

This capability extends Deterministic Replay: it reuses the same replay mechanism — cassette-first, escalating to a sandbox when needed — but substitutes the developer's modified agent logic in place of the original. When the fix leaves external calls unchanged, the sealed Response Cassette answers them and the test runs in milliseconds; when the fix changes which calls fire, the cassette cannot answer the new call, so the run escalates to a real provider sandbox before a verdict is issued. Its value is turning "we think the fix works" into "we proved the fix works against the real incident."

## Terminology

* **Incident**: The platform-side record of an ingested agent run. Defined formally in the Forensics Platform feature.
* **Replay Run**: A single re-execution of an incident's captured calls, against the Response Cassette by default or an escalated sandbox. Defined formally in the Deterministic Replay feature.
* **Fix Reference**: The git branch and commit hash supplied by a developer that identifies the modified agent logic to test.
* **Expected Correct Behavior**: The correct Agent Decision for the incident scenario, supplied by the requester when submitting a Mutation Test, against which the Mutated Decision is judged.
* **Mutation Test**: A Replay Run executed with the developer's Fix Reference applied in place of the original agent logic.
* **Original Decision**: The Agent Decision captured in the incident at the time of the production failure.
* **Mutated Decision**: The Agent Decision produced by the Mutation Test with the Fix Reference applied.
* **Fix Verification Result**: The outcome of comparing the Mutated Decision to the Expected Correct Behavior, indicating whether the fix resolves the incident.

## Requirements

### REQ-FP-MT-001: Submit a Fix for Testing

**User Story:** As a developer, I want to submit my fix by git branch and commit, so that the platform can test my actual code change against the incident.

**Acceptance Criteria:**

* **AC-FP-MT-001.1:** When a developer requests a Mutation Test, the platform shall accept a Fix Reference consisting of a git branch and commit hash.
* **AC-FP-MT-001.2:** When a developer requests a Mutation Test, the platform shall accept an Expected Correct Behavior for the incident scenario.
* **AC-FP-MT-001.3:** If the incident has not been marked reproducible by a prior replay, then the platform shall reject the Mutation Test request and report that the incident must be reproduced first.
* **AC-FP-MT-001.4:** If the supplied Fix Reference cannot be resolved to retrievable code, then the platform shall reject the request and return an error.
* **AC-FP-MT-001.5:** If no Expected Correct Behavior is supplied, then the platform shall reject the request and report that it is required.

### REQ-FP-MT-002: Re-Run Replay with the Fix Applied

**User Story:** As a developer, I want the platform to re-run the exact incident replay with my fix in place, so that the fix is tested against the real scenario.

**Acceptance Criteria:**

* **AC-FP-MT-002.1:** When a Mutation Test starts, the platform shall re-run under the same Deterministic Execution Conditions as the original replay (defined in the Deterministic Replay feature), answering external calls from the Response Cassette so the scenario differs only by the substituted fix code.
* **AC-FP-MT-002.2:** When the environment is ready, the platform shall check out the code identified by the Fix Reference and execute the replay with the modified agent logic.
* **AC-FP-MT-002.3:** If the fix issues an external call the Response Cassette cannot answer, then the platform shall escalate that Mutation Test to a real provider sandbox before producing a verdict, and shall report requiring-sandbox status if no supported sandbox exists for the provider.
* **AC-FP-MT-002.4:** When the Mutation Test completes, the platform shall record the Mutated Decision.
* **AC-FP-MT-002.5:** If the Mutation Test fails to execute, then the platform shall record the failure and mark the Mutation Test as incomplete.

### REQ-FP-MT-003: Verify the Fix Resolves the Incident

**User Story:** As a compliance officer, I want the platform to determine whether the fix produces correct behavior, so that I know the incident is genuinely mitigated.

**Acceptance Criteria:**

* **AC-FP-MT-003.1:** When a Mutation Test completes, the platform shall compare the Mutated Decision to the Expected Correct Behavior to produce a Fix Verification Result.
* **AC-FP-MT-003.2:** When the Mutated Decision matches the Expected Correct Behavior, the platform shall mark the fix as verified.
* **AC-FP-MT-003.3:** If the Mutated Decision does not match the Expected Correct Behavior, then the platform shall mark the fix as not verified and record the resulting decision.
* **AC-FP-MT-003.4:** When a fix is marked verified, the platform shall update the Incident Status to reflect that mitigation has been verified.

### REQ-FP-MT-004: Record Mutation Test Evidence

**User Story:** As a general counsel, I want the mutation test details preserved, so that the verification can back a defensible mitigation claim.

**Acceptance Criteria:**

* **AC-FP-MT-004.1:** When a Mutation Test completes, the platform shall associate the Fix Reference, the Mutated Decision, and the Fix Verification Result with the Incident.
* **AC-FP-MT-004.2:** The platform shall persist Mutation Test evidence to the Immutable Log in an append-only manner.

### Proof of Mitigation Certificates

## Overview

Proof of Mitigation Certificates turn a verified fix into portable, cryptographically signed evidence. Once a Mutation Test verifies that a fix resolves a reproduced incident, the platform generates a certificate documenting the reproducible incident, the implemented fix (git commit and code diff), the deterministic replay method, and the verified correct outcome. The certificate is cryptographically signed so its authenticity can be proven independently, and it is exportable to formats that regulators and courts can review; GRC delivery remains a planned downstream integration rather than part of the release-gate build horizon.

This capability extends the Forensics Platform and depends on Mutation Testing: a certificate can only be issued for an incident whose fix has been verified. The certificate is the tangible artifact a compliance officer or general counsel uses as proof of good-faith, tested remediation under the recorded conditions and disclosed limitations.

## Terminology

* **Incident**: The platform-side record of an ingested agent run. Defined formally in the Forensics Platform feature.
* **Fix Verification Result**: The outcome indicating whether a fix resolves an incident. Defined formally in the Mutation Testing feature.
* **Replay Method**: The method used to verify the incident or fix: cassette replay from the sealed Response Cassette by default, or sandbox escalation where the cassette cannot answer a changed call or customer-approved live validation is required. Defined formally in the Deterministic Replay feature.
* **Proof of Mitigation Certificate**: The signed artifact attesting that an incident was reproducible, a specific fix was applied, the fix was tested deterministically under the recorded or escalated validation conditions, and the fix produced correct behavior.
* **Certificate Signature**: The asymmetric cryptographic signature (ECDSA or RSA) applied to a certificate that allows its authenticity and integrity to be verified independently by any party holding the corresponding public key, without access to any secret.
* **Certificate Export**: The production of a certificate in a portable format (PDF or JSON).
* **Defensibility Bundle**: The evidence included with a certificate that lets a recipient evaluate custody, integrity, reproducibility, fix verification, signing, tool versions, replay method, and known limitations without relying on narrative claims alone.

## Requirements

### REQ-FP-CERT-001: Generate a Certificate for a Verified Fix

**User Story:** As a compliance officer, I want a certificate generated once a fix is verified, so that I have documented proof of tested remediation.

**Acceptance Criteria:**

* **AC-FP-CERT-001.1:** When a fix for an Incident is marked verified, the platform shall allow a Proof of Mitigation Certificate to be generated for that Incident.
* **AC-FP-CERT-001.2:** If a certificate is requested for an Incident whose fix is not verified, then the platform shall reject the request and report that verification is required first.
* **AC-FP-CERT-001.3:** When a certificate is generated, it shall document the reproducibility of the incident, the applied fix identified by git commit and code diff, the Replay Method used for verification, and the verified correct behavior.

### REQ-FP-CERT-002: Cryptographically Sign the Certificate

**User Story:** As a general counsel, I want each certificate cryptographically signed, so that its authenticity holds up in audits and litigation.

**Acceptance Criteria:**

* **AC-FP-CERT-002.1:** When a certificate is generated, the platform shall apply an asymmetric Certificate Signature to it.
* **AC-FP-CERT-002.2:** When presented with a certificate and its signature, any party holding the published public key shall be able to verify the certificate's authenticity and confirm it has not been altered, without access to any secret.
* **AC-FP-CERT-002.3:** If a certificate's contents are altered after signing, then signature verification shall fail.
* **AC-FP-CERT-002.4:** The platform shall support both ECDSA and RSA signing, with the algorithm selected per deployment.
* **AC-FP-CERT-002.5:** The platform shall gate available signing algorithms by the organization's Tier (per the Tiers and Entitlements feature): ECDSA on the Free Tier, ECDSA and RSA on Professional, and custom signing on Enterprise.

### REQ-FP-CERT-003: Export the Certificate

**User Story:** As a compliance officer, I want to export certificates in standard formats, so that I can submit them to regulators and attach them to compliance records.

**Acceptance Criteria:**

* **AC-FP-CERT-003.1:** When the user requests an export, the platform shall produce the certificate as PDF or JSON.
* **AC-FP-CERT-003.2:** Planned for post-release-gate integration: where a GRC integration is configured, the platform shall support delivering the certificate to the connected GRC system.
* **AC-FP-CERT-003.3:** The exported certificate shall include the public key and algorithm identifier needed to verify its Certificate Signature independently.
* **AC-FP-CERT-003.4:** The PDF export shall be human-readable for submission and printing, conveying the incident summary, the identified root cause, the applied fix (including its git commit reference), the mutation-test verification outcome, and a means for a reader to reach the machine-verifiable representation.
* **AC-FP-CERT-003.5:** The JSON export shall be machine-verifiable for GRC ingestion and automated checking, conveying the same evidence as the PDF plus the data required to verify the certificate independently, including the Merkle chain and hashes, the signature, and the signing key version.
* **AC-FP-CERT-003.6:** Both export formats shall carry enough information for a recipient to verify the Certificate Signature without contacting Notary.
* **AC-FP-CERT-003.7:** The default export format shall be PDF when the user does not specify a format.

### REQ-FP-CERT-004: Preserve Issued Certificates

**User Story:** As a general counsel, I want issued certificates retained immutably, so that historical remediation evidence remains available.

**Acceptance Criteria:**

* **AC-FP-CERT-004.1:** When a certificate is generated, the platform shall persist it to the Immutable Log associated with its Incident.
* **AC-FP-CERT-004.2:** The platform shall retain issued certificates so they remain retrievable and verifiable at any later time.

### REQ-FP-CERT-005: Include a Defensibility Bundle

**User Story:** As a regulator or general counsel, I want the certificate to include the facts needed to evaluate forensic defensibility, so that I can verify the remediation evidence without relying only on Notary's narrative.

**Acceptance Criteria:**

* **AC-FP-CERT-005.1:** When a Proof of Mitigation Certificate is generated, it shall include a Defensibility Bundle.
* **AC-FP-CERT-005.2:** The Defensibility Bundle shall identify the custody history for the Incident through certificate generation.
* **AC-FP-CERT-005.3:** The Defensibility Bundle shall identify the integrity-verification result, Root Hash, signing algorithm, public key reference, and signing key version.
* **AC-FP-CERT-005.4:** The Defensibility Bundle shall identify the replay method, reproducibility result, mutation-test verification result, and fix reference.
* **AC-FP-CERT-005.5:** The Defensibility Bundle shall identify the SDK, replay, mutation, signing, and export tool versions used to produce the certificate.
* **AC-FP-CERT-005.6:** If any known limitation affects independent verification, then the certificate shall disclose that limitation.

### Compliance Reporting

## Overview

Compliance Reporting translates forensic evidence into the documents regulators expect. Using templates aligned to specific regulatory frameworks—the EU AI Act, NIST AI RMF, SEC disclosure rules, and OCC guidance—the platform assembles an incident's forensic record (integrity-verified snapshot, reproducibility result, verified fix, and Proof of Mitigation certificate) into a framework-specific report. This lets a compliance officer produce a regulator-ready document in minutes rather than assembling one manually over weeks.

This capability extends the Forensics Platform and draws on the outputs of Deterministic Replay, Mutation Testing, and Proof of Mitigation Certificates. Its value is directly tied to the product's core outcome: cutting investigation time and reducing fine severity through documented, framework-mapped evidence. Each report also includes a defensibility appendix so the recipient can review evidence-handling facts rather than only the report narrative.

## Terminology

* **Incident**: The platform-side record of an ingested agent run. Defined formally in the Forensics Platform feature.
* **Proof of Mitigation Certificate**: The signed artifact attesting an incident was reproduced, fixed, tested, and verified. Defined formally in the Proof of Mitigation Certificates feature.
* **Regulatory Framework**: A specific compliance standard the report is aligned to (EU AI Act, NIST AI RMF, SEC, OCC).
* **Compliance Report Template**: A predefined document structure that maps an incident's forensic evidence onto the requirements of a Regulatory Framework.
* **Compliance Report**: The generated document that presents an incident's evidence in the structure of a chosen Regulatory Framework.
* **Defensibility Appendix**: The section of a Compliance Report that summarizes custody, integrity, reproducibility, fix verification, signing, tool versions, and known limitations in a form suitable for forensic review.

## Requirements

### REQ-FP-COMP-001: Generate a Framework-Specific Report

**User Story:** As a compliance officer, I want to generate a report aligned to a specific regulatory framework, so that I can submit evidence in the form a regulator expects.

**Acceptance Criteria:**

* **AC-FP-COMP-001.1:** When the user requests a Compliance Report for an Incident and selects a Regulatory Framework, the platform shall generate a Compliance Report using the matching Compliance Report Template.
* **AC-FP-COMP-001.2:** The platform shall provide Compliance Report Templates for the EU AI Act, NIST AI RMF, SEC, and OCC.
* **AC-FP-COMP-001.3:** When generating a report, the platform shall populate it with the incident's forensic evidence, including the integrity-verification result, the reproducibility result, and any verified fix and Proof of Mitigation Certificate.
* **AC-FP-COMP-001.4:** If the selected Regulatory Framework requires evidence the incident does not yet have, then the platform shall generate the report and clearly mark the missing sections rather than failing silently.

### REQ-FP-COMP-002: Map Evidence to Framework Requirements

**User Story:** As a compliance officer, I want the report to map incident evidence to specific framework clauses, so that a regulator can see exactly how each requirement is satisfied.

**Acceptance Criteria:**

* **AC-FP-COMP-002.1:** When a report is generated, the platform shall map the incident's evidence to the corresponding requirements of the selected Regulatory Framework (for example, EU AI Act Article 10).
* **AC-FP-COMP-002.2:** Where a framework requirement has no corresponding evidence in the incident, the report shall indicate that requirement as unmet.

### REQ-FP-COMP-003: Export the Report

**User Story:** As a compliance officer, I want to export the report, so that I can submit it or attach it to compliance systems.

**Acceptance Criteria:**

* **AC-FP-COMP-003.1:** When the user requests an export, the platform shall produce the Compliance Report as PDF or JSON.
* **AC-FP-COMP-003.2:** The default export format shall be PDF when the user does not specify a format.
* **AC-FP-COMP-003.3:** Where a GRC integration is configured, the platform shall support delivering the Compliance Report to the connected GRC system.

### REQ-FP-COMP-004: Include a Defensibility Appendix

**User Story:** As a compliance officer, I want reports to include a defensibility appendix, so that regulators can review the evidence-handling facts behind the report.

**Acceptance Criteria:**

* **AC-FP-COMP-004.1:** When a Compliance Report is generated, the platform shall include a Defensibility Appendix.
* **AC-FP-COMP-004.2:** The Defensibility Appendix shall summarize custody completeness, integrity verification, replay reproducibility, fix verification, certificate signing, and export history for the Incident.
* **AC-FP-COMP-004.3:** The Defensibility Appendix shall identify tool versions and known limitations relevant to the evidence in the report.
* **AC-FP-COMP-004.4:** If the Incident lacks evidence needed for a defensibility item, then the Defensibility Appendix shall mark that item as missing rather than omitting it.

### Branching and Experiments

## Overview

Branching and Experiments lets an investigator fork a reproduced run at a chosen point, apply a change, and compare the result against the original — the "branch" and "diff" operations of the replay-first runtime. Where Mutation Testing answers a single yes/no question ("does this git fix resolve the incident?"), branching supports open-ended investigation: trying several candidate changes as named experiments, comparing them side by side, and seeing exactly where and how each one diverges from the original run before committing to a fix.

This feature builds on Deterministic Replay and shares the Forensics Platform's execution model. It is what makes Notary feel like version control for agent execution: an investigator can explore alternatives cheaply and safely against the real recorded run, then hand a chosen, verified branch to Mutation Testing for certificate-grade verification. It does not replace Mutation Testing; it feeds it.

## Terminology

* **Execution Run**: The ordered graph of an agent run that is captured, replayed, branched, and diffed. Defined formally in the Execution Model blueprint; referenced by requirements here as the run being branched.
* **Incident**: The platform-side record of an ingested agent run. Defined formally in the Forensics Platform feature.
* **Branch**: A child Execution Run forked from a base run at a chosen branch point, with a change applied, used to explore an alternative outcome without altering the original.
* **Branch Point**: The node in the base run at which a Branch diverges; everything before it is copied unchanged and everything after is recomputed.
* **Experiment**: A named, saved Branch (or set of Branches) an investigator creates while exploring candidate changes for an incident.
* **Change**: The modification applied on a Branch, either an agent-parameter override (for example a threshold value) or a code reference (git branch and commit).
* **Run Diff**: The structured, node-by-node comparison between two Execution Runs identifying the first divergence and how the runs differ from there.

## Requirements

### REQ-FP-BR-001: Create a Branch from a Reproduced Run

**User Story:** As a compliance officer, I want to branch a reproduced run at a chosen point and apply a change, so that I can explore whether a different decision was achievable without altering the original record.

**Acceptance Criteria:**

* **AC-FP-BR-001.1:** When the user creates a Branch from an Incident, the platform shall require the Incident to be reproducible and shall reject branching otherwise.
* **AC-FP-BR-001.2:** When creating a Branch, the platform shall accept a Branch Point and a Change (an agent-parameter override or a code reference).
* **AC-FP-BR-001.3:** When a Branch is created, the platform shall copy the base run's nodes up to the Branch Point unchanged and recompute the remaining nodes with the Change applied, under the same deterministic conditions as the original replay.
* **AC-FP-BR-001.4:** The platform shall preserve the original Execution Run unchanged when a Branch is created.
* **AC-FP-BR-001.5:** If the Change cannot be applied (for example an unresolvable code reference), then the platform shall reject the Branch and return the reason.

### REQ-FP-BR-002: Save and Manage Experiments

**User Story:** As a compliance officer, I want to save branches as named experiments for an incident, so that I can revisit and compare the alternatives I tried.

**Acceptance Criteria:**

* **AC-FP-BR-002.1:** When the user saves a Branch as an Experiment, the platform shall associate it with its Incident under a user-supplied name.
* **AC-FP-BR-002.2:** When the user lists Experiments for an Incident, the platform shall return each Experiment with its Change and outcome summary.
* **AC-FP-BR-002.3:** When no Experiments exist for an Incident, the platform shall return an empty list rather than an error.
* **AC-FP-BR-002.4:** When the user deletes an Experiment, the platform shall remove the Branch while leaving the original Incident and its Execution Run intact.

### REQ-FP-BR-003: Diff a Branch Against the Original Run

**User Story:** As a compliance officer, I want to see exactly where a branch diverges from the original run, so that I understand what my change actually altered.

**Acceptance Criteria:**

* **AC-FP-BR-003.1:** When the user requests a Run Diff between a Branch and its base run, the platform shall return a node-by-node comparison identifying the first divergent node.
* **AC-FP-BR-003.2:** When presenting a Run Diff, the platform shall classify each divergence by kind (input, output, decision, or state).
* **AC-FP-BR-003.3:** When two runs are identical, the Run Diff shall report no divergence.
* **AC-FP-BR-003.4:** When a Branch's recomputation is non-deterministic, the platform shall mark the Run Diff as inconclusive rather than reporting a definitive divergence.

### REQ-FP-BR-004: Compare Experiments

**User Story:** As a compliance officer, I want to compare multiple experiments for an incident, so that I can choose the change that produces the correct outcome.

**Acceptance Criteria:**

* **AC-FP-BR-004.1:** When the user compares two or more Experiments for an Incident, the platform shall present each Experiment's Change and its resulting decision against the original.
* **AC-FP-BR-004.2:** When an Experiment produces the desired outcome, the platform shall allow it to be promoted to a Mutation Test for certificate-grade verification.

### REQ-FP-BR-005: Preserve Branch Lineage

**User Story:** As a general counsel, I want branches to record their origin, so that the exploration behind a verified fix is itself part of the defensible record.

**Acceptance Criteria:**

* **AC-FP-BR-005.1:** When a Branch is created, the platform shall record its parent run and Branch Point.
* **AC-FP-BR-005.2:** The platform shall persist Experiments and their lineage to the Immutable Log in an append-only manner.

### Automated Incident Replay

## Overview

Automated Incident Replay turns replay from a human-initiated action into an event-driven one. Rather than waiting for someone to notice a failure and manually import a run, this feature evaluates captured runs against trigger rules and automatically replays the ones that match — surfacing reproducible failures before a regulator, auditor, or customer does. This shifts the product from reactive investigation ("we replayed it when asked") to continuous detection ("we caught it ourselves"), which is exactly the good-faith posture that reduces regulatory exposure. Automated replay is economically practical precisely because replay defaults to the sealed Response Cassette: cassette replays run in milliseconds with no provider dependency or provisioning cost, so evaluating and replaying many runs is cheap; sandbox escalation (and its cost) is incurred only for the subset of fixes that change external calls.

Triggers come from two sources: system-defined rules that Notary ships by default (for example, replay any run whose recorded decision was an error outcome), and user-defined rules a customer writes against their own execution graph (for example, replay every loan denial where the credit score was within a set margin of the threshold). When an automated replay reproduces a failure, the feature flags a new incident, notifies the responsible party, and auto-creates a branch with a suggested fix for a human to review — it never applies a remediation on its own. This feature builds on Deterministic Replay (which performs the actual re-execution) and shares the Forensics Platform's execution model; it decides *when and why* to replay, not *how*.

## Terminology

* **Execution Run**: The captured, sealed graph of an agent run. Defined formally in the Execution Model blueprint.
* **Incident**: The platform-side record of an ingested agent run. Defined formally in the Forensics Platform feature.
* **Replay Run**: A single deterministic re-execution of a run. Defined formally in the Deterministic Replay feature.
* **Branch**: A forked Execution Run with a change applied for experimentation. Defined formally in the Branching and Experiments feature.
* **Trigger Rule**: A condition evaluated against a captured Execution Run that, when satisfied, causes an automated Replay Run. A Trigger Rule is either System-Defined or User-Defined.
* **System-Defined Trigger**: A Trigger Rule shipped and maintained by Notary, enabled by default (for example, error-outcome runs).
* **User-Defined Trigger**: A Trigger Rule authored by a customer against fields of their own Execution Run (decision value, node type, provider, error status, metadata).
* **Replay Budget**: The per-organization limit on how many automated Replay Runs may execute in a period, protecting against unbounded sandbox cost.
* **Suggested Fix**: A candidate change auto-generated for a reproduced failure, materialized as a Branch for human review; never applied automatically.

## Requirements

### REQ-FP-AIR-001: Define Trigger Rules

**User Story:** As a compliance officer, I want to define rules that decide which runs are automatically replayed, so that failures I care about are investigated without manual effort.

**Acceptance Criteria:**

* **AC-FP-AIR-001.1:** The platform shall provide System-Defined Triggers enabled by default, including a trigger for runs whose recorded decision is an error outcome.
* **AC-FP-AIR-001.2:** When a user creates a User-Defined Trigger, the platform shall accept a condition expressed over an Execution Run's fields (decision value, node type, provider, error status, or metadata).
* **AC-FP-AIR-001.3:** When a user disables a System-Defined Trigger, the platform shall stop evaluating it for that organization while leaving it available to re-enable.
* **AC-FP-AIR-001.4:** If a User-Defined Trigger's condition is malformed, then the platform shall reject it and report the error rather than saving an unusable rule.
* **AC-FP-AIR-001.5:** The platform shall scope every Trigger Rule to the organization that owns it.

### REQ-FP-AIR-002: Evaluate Runs Against Triggers

**User Story:** As a compliance officer, I want captured runs checked against my triggers automatically, so that matching runs are queued for replay without me watching.

**Acceptance Criteria:**

* **AC-FP-AIR-002.1:** When an Execution Run is captured or ingested, the platform shall evaluate it against all enabled Trigger Rules for its organization.
* **AC-FP-AIR-002.2:** When a run satisfies at least one Trigger Rule, the platform shall queue an automated Replay Run for it.
* **AC-FP-AIR-002.3:** When a run satisfies no Trigger Rule, the platform shall take no automated replay action.
* **AC-FP-AIR-002.4:** When a run matches multiple Trigger Rules, the platform shall queue a single automated Replay Run rather than one per rule.

### REQ-FP-AIR-003: Govern Automated Replay Volume

**User Story:** As a platform owner, I want automated replays bounded, so that they cannot run up unbounded sandbox cost.

**Acceptance Criteria:**

* **AC-FP-AIR-003.1:** The platform shall enforce a per-organization Replay Budget on automated Replay Runs over a period.
* **AC-FP-AIR-003.2:** While the Replay Budget is exhausted, the platform shall defer or drop further automated Replay Runs and record that the budget was reached rather than failing silently.
* **AC-FP-AIR-003.3:** Where a Trigger Rule would match a high volume of runs, the platform shall support sampling so that a configurable fraction is replayed.
* **AC-FP-AIR-003.4:** The platform shall not let automated Replay Runs displace or delay user-initiated (manual) Replay Runs.

### REQ-FP-AIR-004: Handle the Replay Outcome

**User Story:** As a compliance officer, I want a reproduced automated failure turned into an actionable incident, so that my team can act on it immediately.

**Acceptance Criteria:**

* **AC-FP-AIR-004.1:** When an automated Replay Run reproduces the failure, the platform shall create an Incident (or associate the run with an existing one) and notify the responsible party.
* **AC-FP-AIR-004.2:** When an automated Replay Run reproduces the failure, the platform shall auto-create a Branch containing a Suggested Fix for human review.
* **AC-FP-AIR-004.3:** The platform shall not apply, verify, or certify a Suggested Fix automatically; a human must review and promote it through Mutation Testing.
* **AC-FP-AIR-004.4:** When an automated Replay Run does not reproduce the failure, the platform shall record the non-reproduction and shall not raise an incident.
* **AC-FP-AIR-004.5:** If an automated Replay Run cannot run deterministically (for example, an unsupported provider or unseeded randomness), then the platform shall flag the run as non-deterministic and notify the responsible party rather than reporting a definitive result.

### REQ-FP-AIR-005: Audit Automated Replay Activity

**User Story:** As a general counsel, I want automated replay activity recorded immutably, so that the decision to investigate is itself part of the defensible record.

**Acceptance Criteria:**

* **AC-FP-AIR-005.1:** When an automated Replay Run is triggered, the platform shall record which Trigger Rule fired, the run evaluated, and the outcome to the Immutable Log in an append-only manner.
* **AC-FP-AIR-005.2:** When the user views an Incident created by automation, the platform shall show that it originated from an automated trigger and which rule fired.

### REQ-FP-AIR-006: Tier-Gated Availability

**User Story:** As a platform owner, I want automated replay to be a paid-tier capability, so that automation aligns with the subscription model.

**Acceptance Criteria:**

* **AC-FP-AIR-006.1:** Where the organization's Tier does not include automated replay (per the Tiers and Entitlements feature), the platform shall not evaluate Trigger Rules or start automated Replay Runs for that organization.
* **AC-FP-AIR-006.2:** On the Free Tier, the platform shall offer only manual, user-initiated replay and shall indicate that automated replay requires a higher Tier.
* **AC-FP-AIR-006.3:** Automated Replay Runs shall count against the same tier-configured replay Usage Limit as manual runs.

### Scenario Library

## Overview

The Scenario Library turns Notary from an episodic incident tool into a system whose value compounds with use. Every incident that is reproduced during a forensic investigation is already a real, recorded test case: a sealed set of production conditions paired with a known-correct outcome. Today that record is used once, to investigate a single incident, and then sits idle as evidence. The Scenario Library preserves each reproduced incident as a reusable Scenario and collects them into a per-organization Library that grows every time the platform is used.

The value is durability and accumulation. A team that has used Notary across many incidents accumulates a Library of real failure conditions that exists nowhere else and cannot be reconstructed by a competitor or rebuilt from scratch. Because each Scenario is grounded in a real recorded run rather than a synthetic guess, re-running it later is a faithful regression check against conditions the agent actually faced. This document defines how Scenarios are created, curated, and re-run; the interactive surface for exploring and running them is defined in the child Testing Playground feature.

## Terminology

* **Incident**: The platform-side record created from an ingested Forensic Snapshot. Defined formally in the Forensics Platform feature.
* **Forensic Snapshot**: The structured, cryptographically sealed record of a single agent run. Defined formally in the Forensic Agent Logger SDK feature.
* **Response Cassette**: The sealed set of external call/response pairs recorded during an incident, replayed deterministically. Defined formally in the Sandbox Orchestration and Replay capability.
* **Scenario**: A saved, re-runnable test case derived from a reproduced Incident. It references the Incident's sealed Response Cassette and records the Expected Outcome the agent should produce under those conditions.
* **Expected Outcome**: The known-correct agent decision associated with a Scenario, against which a re-run is compared. For a Scenario derived from a mitigated Incident it is the verified corrected decision; for one derived from a reproduced-but-unmitigated Incident it is the original recorded decision.
* **Library**: The per-organization collection of Scenarios. Each organization has exactly one Library.
* **Scenario Run**: A single re-execution of one or more Scenarios against a specified agent version, producing a pass or fail result per Scenario by comparing the re-run decision to the Expected Outcome.

## Requirements

### REQ-FP-SL-001: Save a Reproduced Incident as a Scenario

**User Story:** As a developer, I want to save a reproduced incident as a reusable scenario, so that the conditions that once broke my agent become a permanent test.

**Acceptance Criteria:**

* **AC-FP-SL-001.1:** While an Incident has been successfully reproduced by replay, the platform shall allow the Incident to be saved as a Scenario.
* **AC-FP-SL-001.2:** If a user attempts to save a Scenario from an Incident that has not been reproduced, then the platform shall reject the request and return the reason.
* **AC-FP-SL-001.3:** When a Scenario is created, the platform shall reference the source Incident's sealed Response Cassette rather than copying or mutating it.
* **AC-FP-SL-001.4:** When a Scenario is created from a mitigated Incident, the platform shall set the Expected Outcome to the verified corrected decision.
* **AC-FP-SL-001.5:** When a Scenario is created from a reproduced Incident that has not been mitigated, the platform shall set the Expected Outcome to the original recorded decision.
* **AC-FP-SL-001.6:** When a Scenario is created, the platform shall add it to the organization's Library.

### REQ-FP-SL-002: Browse and Inspect the Library

**User Story:** As a developer, I want to see the scenarios my organization has accumulated, so that I understand what coverage I have.

**Acceptance Criteria:**

* **AC-FP-SL-002.1:** When the user opens the Library, the platform shall list the organization's Scenarios with, for each, its source Incident reference, Expected Outcome, and creation time.
* **AC-FP-SL-002.2:** When the user selects a Scenario, the platform shall display its details, including the source Incident and the Expected Outcome.
* **AC-FP-SL-002.3:** When the Library contains no Scenarios, the platform shall present an empty state rather than an error.
* **AC-FP-SL-002.4:** When a user browses the Library, the platform shall show only Scenarios belonging to that user's organization.

### REQ-FP-SL-003: Re-run Scenarios Against an Agent Version

**User Story:** As a developer, I want to re-run saved scenarios against a specified version of my agent, so that I can confirm none of them regress before I ship a change.

**Acceptance Criteria:**

* **AC-FP-SL-003.1:** When the user starts a Scenario Run for a selected set of Scenarios and a specified agent version, the platform shall re-execute each selected Scenario against that version using the Scenario's referenced Response Cassette.
* **AC-FP-SL-003.2:** When a Scenario re-execution completes, the platform shall compare the re-run decision to the Scenario's Expected Outcome and record a pass when they match and a fail when they differ.
* **AC-FP-SL-003.3:** When a Scenario Run completes, the platform shall report per-Scenario results and a summary of how many passed and failed.
* **AC-FP-SL-003.4:** If a re-execution requires an external call the referenced Response Cassette cannot answer, then the platform shall handle it under the existing replay escalation behavior and record the result rather than silently dropping the Scenario.
* **AC-FP-SL-003.5:** If a Scenario re-execution cannot be completed, then the platform shall record that Scenario as errored, distinct from a fail, and continue running the remaining Scenarios.
* **AC-FP-SL-003.6:** When the user selects no specific Scenarios and starts a Run, the platform shall run the entire Library by default.

### REQ-FP-SL-004: Curate the Library

**User Story:** As a developer, I want to name, annotate, and retire scenarios, so that the library stays meaningful as it grows.

**Acceptance Criteria:**

* **AC-FP-SL-004.1:** When the user renames or annotates a Scenario, the platform shall persist the change and leave the referenced Response Cassette and Expected Outcome unchanged.
* **AC-FP-SL-004.2:** When the user retires a Scenario, the platform shall exclude it from future default Library Runs while retaining it for reference.
* **AC-FP-SL-004.3:** While a Scenario is retired, the platform shall still allow it to be run when explicitly selected.
* **AC-FP-SL-004.4:** The platform shall not permit editing a Scenario's referenced Response Cassette, preserving the integrity of the recorded conditions.

### REQ-FP-SL-005: Preserve Scenario Integrity and Isolation

**User Story:** As a CISO, I want scenarios to inherit the same integrity and access guarantees as incidents, so that the library is as defensible as the evidence it derives from.

**Acceptance Criteria:**

* **AC-FP-SL-005.1:** The platform shall derive a Scenario's conditions solely from its source Incident's sealed Response Cassette, so that Scenario integrity follows from the Incident's tamper-evidence.
* **AC-FP-SL-005.2:** If an unauthenticated request is made to any Library or Scenario endpoint, then the platform shall deny the request.
* **AC-FP-SL-005.3:** When a user accesses a Scenario, the platform shall deny access if the Scenario belongs to another organization.

#### Testing Playground

## Overview

The Testing Playground is the interactive surface where a developer runs saved Scenarios against a chosen version of their agent and reads the results, without waiting for an incident. Where the Scenario Library defines the accumulating asset — the set of real, recorded test cases an organization builds up over time — the Playground is where that asset gets used between incidents: pick scenarios, run them against a candidate agent version, and see at a glance what passed, what regressed, and why.

The Playground gives teams a reason to open Notary on every change rather than only during a crisis. Before shipping a new agent version, a developer can re-run the scenarios that previously broke and confirm the change does not reintroduce a known failure. Because every Scenario is grounded in a real recorded run, a pass in the Playground is a faithful regression check against conditions the agent actually faced, not against synthetic guesses. Beyond confirming a single version, the Playground also supports iterative agent improvement: a developer changes the agent, re-runs the Library, and compares the new results against a prior baseline to see which Scenarios improved (now correct where they were wrong) and which regressed. This makes the Library a correctness-and-regression harness that guides iteration against real conditions. The Playground presents and orchestrates runs; it does not create Scenarios or alter their recorded conditions — those belong to the Scenario Library.

The Playground reports verdicts and evidence; it does not change the agent. It tells a developer *whether* a version got better or worse against real recorded conditions, but it never generates a fix, tunes a prompt, or suggests a logic change — the developer improves the agent, and Notary proves the result. This boundary is deliberate and is stated explicitly in Non-Goals below: an independent proving ground cannot also be the author of the changes it certifies without compromising the neutrality that makes its evidence trustworthy.

## Terminology

* **Scenario**: A saved, re-runnable test case derived from a reproduced Incident. Defined formally in the Scenario Library feature.
* **Expected Outcome**: The known-correct agent decision associated with a Scenario. Defined formally in the Scenario Library feature.
* **Library**: The per-organization collection of Scenarios. Defined formally in the Scenario Library feature.
* **Scenario Run**: A single re-execution of one or more Scenarios against a specified agent version. Defined formally in the Scenario Library feature.
* **Agent Version**: The identifier of the agent build under test for a Scenario Run, expressed as a code reference (git branch and commit), consistent with how mutation testing identifies fix code.
* **Run Result**: The per-Scenario outcome of a Scenario Run — pass, fail, or errored — together with the comparison between the re-run decision and the Expected Outcome.
* **Baseline Run**: A prior Scenario Run selected as the point of comparison for a later Run, used to determine per-Scenario improvement or regression between two Agent Versions.
* **Comparison**: The per-Scenario diff between a Run and a Baseline Run, classifying each Scenario as improved (fail-to-pass), regressed (pass-to-fail), or unchanged.

## Requirements

### REQ-FP-TP-001: Assemble a Run from the Library

**User Story:** As a developer, I want to select which scenarios to run and against which agent version, so that I can target the check to the change I am about to ship.

**Acceptance Criteria:**

* **AC-FP-TP-001.1:** When the user opens the Playground, the platform shall present the organization's Scenarios available to run and a control for specifying the Agent Version.
* **AC-FP-TP-001.2:** When the user selects a subset of Scenarios, the platform shall include only the selected Scenarios in the Run.
* **AC-FP-TP-001.3:** While no Scenarios are selected, the platform shall default the Run to the entire active Library.
* **AC-FP-TP-001.4:** If the user starts a Run without specifying an Agent Version, then the platform shall reject the start and prompt for a version.
* **AC-FP-TP-001.5:** When the Library is empty, the Playground shall present an empty state that directs the user to reproduce and save an incident first.

### REQ-FP-TP-002: Execute and Monitor a Run

**User Story:** As a developer, I want to start a run and watch its progress, so that I know when it is done and whether it is still working.

**Acceptance Criteria:**

* **AC-FP-TP-002.1:** When the user starts a Run, the platform shall execute the selected Scenarios against the specified Agent Version through the Scenario Library re-run behavior.
* **AC-FP-TP-002.2:** While a Run is in progress, the Playground shall indicate that it is running and show how many Scenarios have completed.
* **AC-FP-TP-002.3:** When the user cancels a Run in progress, the platform shall stop starting further Scenarios and report results for those already completed.
* **AC-FP-TP-002.4:** If a Run cannot be started, then the Playground shall report the reason and leave the Library unchanged.

### REQ-FP-TP-003: Read Run Results

**User Story:** As a developer, I want to see which scenarios passed and which regressed, so that I can decide whether the change is safe to ship.

**Acceptance Criteria:**

* **AC-FP-TP-003.1:** When a Run completes, the Playground shall display a summary of how many Scenarios passed, failed, and errored.
* **AC-FP-TP-003.2:** When a Run completes, the Playground shall list each Scenario with its Run Result.
* **AC-FP-TP-003.3:** When the user selects a failed Scenario, the Playground shall show the Expected Outcome alongside the re-run decision so the divergence is visible.
* **AC-FP-TP-003.4:** When a Scenario is errored rather than failed, the Playground shall present it distinctly from a fail and indicate why it could not be evaluated.

### REQ-FP-TP-004: Review Past Runs

**User Story:** As a developer, I want to see previous runs, so that I can compare results across agent versions over time.

**Acceptance Criteria:**

* **AC-FP-TP-004.1:** When the user opens the run history, the platform shall list prior Scenario Runs with their Agent Version, start time, and pass/fail/errored summary.
* **AC-FP-TP-004.2:** When the user selects a past Run, the platform shall display its per-Scenario Run Results.
* **AC-FP-TP-004.3:** When no prior Runs exist, the platform shall present an empty state rather than an error.
* **AC-FP-TP-004.4:** When a user reviews run history, the platform shall show only Runs belonging to that user's organization.

### REQ-FP-TP-005: Compare a Run Against a Baseline

**User Story:** As a developer improving my agent, I want to compare a run against an earlier run, so that I can see which scenarios my change improved and which it regressed.

**Acceptance Criteria:**

* **AC-FP-TP-005.1:** When the user selects a completed Run and a Baseline Run, the platform shall produce a Comparison classifying each Scenario as improved, regressed, or unchanged.
* **AC-FP-TP-005.2:** When a Comparison is displayed, the Playground shall summarize how many Scenarios improved, regressed, and were unchanged.
* **AC-FP-TP-005.3:** When the user selects a regressed Scenario in a Comparison, the Playground shall show the Expected Outcome, the Baseline Run decision, and the current Run decision so the change is visible.
* **AC-FP-TP-005.4:** If the two Runs were executed over different sets of Scenarios, then the platform shall base the Comparison only on the Scenarios common to both and indicate which Scenarios were excluded.
* **AC-FP-TP-005.5:** If a Scenario was errored in either Run, then the platform shall exclude it from the improved/regressed classification and report it separately as not comparable.

## Non-Goals

The Playground is a proving ground, not an agent-development tool. The following are explicitly out of scope, and the boundary is deliberate rather than a matter of sequencing:

* **The platform shall not generate, author, or auto-apply fixes, prompt changes, or agent logic changes.** Notary reports whether a developer-supplied Agent Version is better or worse; the developer authors every change. An independent verifier that also authored the changes it certifies would forfeit the neutrality that makes its evidence defensible to a regulator.
* **The platform shall not recommend or suggest specific code, prompt, or configuration changes.** Surfacing which Scenarios failed and how the decision diverged is in scope; prescribing what to change to fix them is not.
* **The platform shall not continuously monitor, trend, or alert on live agent performance.** All evaluation is discrete and on-demand: a specified Agent Version is run against selected Scenarios to produce a result. Continuous performance tracking or anomaly alerting is observability, a category Notary deliberately does not enter (see the Product Direction and Phases document).

#### Evidence Export

## Overview

Evidence Export lets an organization take its own accumulated Verification Records and Scenarios out of Notary as a structured, provenance-carrying dataset for its own use — most often to feed the customer's model or agent team an evaluation or training set built from real, verified decisions. Notary's records are rare in that they are both real and tamper-evident: each carries a sealed origin and a known-correct outcome, which makes them better improvement evidence than an unverified log. This feature turns that latent asset into a second use without compromising the trust guarantees that make the asset valuable.

The feature supports a spectrum from a one-off manual export through a standing Improvement Dataset that the customer's own systems pull on demand and that automatically includes newly qualifying records as the Library grows. The controlling principle is that the customer pulls; Notary never autonomously ships records outward, never aggregates across organizations, and never routes evidence to a foundation-model provider. Notary is the source and conduit of the customer's own verified evidence, not an evaluation platform, a training-data broker, or an optimizer.

## Terminology

* **Verification Record**: The platform-side record of a single captured agent decision. Defined formally in the Capture Rules and Decision Triggers feature.
* **Scenario**: A saved, re-runnable test case with a known-correct outcome. Defined formally in the Scenario Library feature.
* **Expected Outcome**: The known-correct decision associated with a Scenario. Defined formally in the Scenario Library feature.
* **Export Set**: A defined selection of the organization's Verification Records and/or Scenarios to be exported, together with the field scope that controls which parts of each record are included.
* **Field Scope**: The configuration that governs which parts of a record leave in an export — for example, decision and expected outcome only, versus the full recorded conditions — used to control exposure of sensitive data.
* **Provenance Manifest**: The metadata accompanying an export that records, for each item, its sealed origin reference and integrity root, so the exported evidence can be verified as authentic and traced to its source record.
* **Improvement Dataset**: A named, standing Export Set that the organization's own systems pull on demand and that automatically includes newly qualifying records as they are captured, without re-defining the selection each time.
* **Export Pull**: An authenticated retrieval of an Export Set or Improvement Dataset by the organization's own system.

## Requirements

### REQ-FP-EE-001: Define an Export Set

**User Story:** As a rule administrator, I want to select which records and scenarios to export and how much of each, so that I can share verified evidence with our own teams without over-exposing sensitive data.

**Acceptance Criteria:**

* **AC-FP-EE-001.1:** When a Rule Administrator defines an Export Set, the platform shall allow selection of the organization's Verification Records and Scenarios and a Field Scope for the export.
* **AC-FP-EE-001.2:** The platform shall default the Field Scope to decision and Expected Outcome only, excluding full recorded conditions unless explicitly included.
* **AC-FP-EE-001.3:** The platform shall include in an Export Set only records and Scenarios belonging to the caller's organization.
* **AC-FP-EE-001.4:** If a user who is not a Rule Administrator attempts to define or change an Export Set, then the platform shall deny the action.
* **AC-FP-EE-001.5:** The platform shall default an Export Set to Scenarios with a verified Expected Outcome, so unverified records are not exported as labeled data unless explicitly included.

### REQ-FP-EE-002: Export with Provenance

**User Story:** As a compliance officer, I want exported evidence to carry proof of its origin, so that data used downstream remains verifiable and auditable.

**Acceptance Criteria:**

* **AC-FP-EE-002.1:** When an Export Set is exported, the platform shall produce the data in a structured, machine-readable format together with a Provenance Manifest.
* **AC-FP-EE-002.2:** The platform shall record in the Provenance Manifest, for each exported item, its sealed origin reference and integrity root.
* **AC-FP-EE-002.3:** The platform shall apply the Export Set's Field Scope so that excluded fields do not appear in the exported data.
* **AC-FP-EE-002.4:** The platform shall record that an export occurred, including who initiated it and the Export Set exported, so exports are auditable.

### REQ-FP-EE-003: Maintain a Standing Improvement Dataset

**User Story:** As an AI platform team member, I want a standing dataset that grows as we capture more records, so that our model team can pull current verified evidence without re-defining the selection each time.

**Acceptance Criteria:**

* **AC-FP-EE-003.1:** When a Rule Administrator creates an Improvement Dataset, the platform shall persist its selection criteria and Field Scope as a named, standing Export Set.
* **AC-FP-EE-003.2:** When a new record or Scenario matches an Improvement Dataset's selection criteria, the platform shall include it in the Dataset without requiring the selection to be redefined.
* **AC-FP-EE-003.3:** When the organization's system performs an Export Pull of an Improvement Dataset, the platform shall return the current contents with a Provenance Manifest.
* **AC-FP-EE-003.4:** The platform shall scope an Improvement Dataset and its Export Pulls to the owning organization.

### REQ-FP-EE-004: Pull Under Customer Control

**User Story:** As a CISO, I want exports to happen only when our systems request them, so that our evidence never leaves without our action.

**Acceptance Criteria:**

* **AC-FP-EE-004.1:** The platform shall provide exported data only in response to an authenticated Export Pull initiated by the organization.
* **AC-FP-EE-004.2:** If an Export Pull is unauthenticated or targets another organization's Export Set, then the platform shall deny it.
* **AC-FP-EE-004.3:** While an Export Pull would exceed the organization's configured export Usage Limit, the platform shall defer or deny the pull and indicate the limit was reached rather than failing silently.

## Non-Goals

The following are explicitly out of scope, and the boundaries are deliberate rather than a matter of sequencing:

* **The platform shall not autonomously push or transmit exported records to any external destination.** Export occurs only via a customer-initiated Export Pull; Notary never ships evidence outward on its own.
* **The platform shall not aggregate, combine, or share records across organizations.** Every export contains only the initiating organization's own records.
* **The platform shall not route or share exported evidence with foundation-model providers or any third party on the customer's behalf.** Where the customer's own system takes the exported data is the customer's responsibility, not a Notary-brokered transfer.
* **The platform shall not perform model training, fine-tuning, evaluation scoring, or agent optimization.** It exports verified evidence for the customer's own tooling to consume; it is not an evaluation or training platform.

#### Scenario Intelligence

## Overview

Scenario Intelligence turns an organization's historical AI decisions, escalations, overrides, denials, and complaints into a source of candidate scenarios. Instead of relying only on a user to notice one failure and save it manually, the platform helps teams discover recurring failure patterns across their decision history, verify which patterns are reproducible, label the expected correct outcome, and promote the verified cases into the Scenario Library. This is the capability that makes the library compound rather than sit still.

This feature does not make Notary an observability, QA analytics, or process-mining product. It is scoped to candidate scenario discovery for replay and release assurance. The platform may cluster records and identify policy gaps, but a human reviewer must confirm the expected correct outcome before a candidate becomes a Scenario that can gate future releases.

## Terminology

* **Verification Record**: The platform-side record of a captured AI decision. Defined formally in the Capture Rules and Decision Triggers feature.
* **Scenario**: A saved, re-runnable test case with a known-correct outcome. Defined formally in the Scenario Library feature.
* **Scenario Candidate**: A potential Scenario discovered from historical records, overrides, escalations, denials, complaints, or policy gaps, pending review and reproducibility verification.
* **Scenario Intelligence Run**: A batch analysis over an organization's eligible Verification Records to surface Scenario Candidates.
* **Pattern Cluster**: A group of related records sharing similar intent, policy, outcome, override, complaint, or failure characteristics.
* **Policy Gap**: A mismatch between a stated policy or expected behavior and the AI system's actual decision outcome.
* **Regulatory Mapping**: An association between a Scenario Candidate and a regulatory or policy obligation such as HIPAA, FCRA, GLBA, NAIC, ADA, or the EU AI Act.
* **Managed Library Expansion**: A recurring workflow in which Notary surfaces Scenario Candidates, the customer labels expected outcomes, and verified candidates are promoted into the Scenario Library.

## Requirements

### REQ-FP-SI-001: Discover Scenario Candidates

**User Story:** As an AI operations leader, I want Notary to surface candidate scenarios from historical decisions, so that failures and overrides do not remain buried in transcripts or logs.

**Acceptance Criteria:**

* **AC-FP-SI-001.1:** When a Scenario Intelligence Run is started, the platform shall analyze eligible Verification Records for candidate failure patterns.
* **AC-FP-SI-001.2:** The platform shall be able to create Scenario Candidates from records involving human overrides, escalations, denials, customer complaints, policy breaches, and high-risk outcomes.
* **AC-FP-SI-001.3:** When the platform surfaces a Scenario Candidate, it shall show the source records that support the candidate.
* **AC-FP-SI-001.4:** If no Scenario Candidates are found, then the platform shall report an empty result rather than an error.

### REQ-FP-SI-002: Cluster Related Failure Patterns

**User Story:** As a support operations leader, I want related overrides and escalations grouped together, so that I can see recurring failure modes instead of reviewing one case at a time.

**Acceptance Criteria:**

* **AC-FP-SI-002.1:** When a Scenario Intelligence Run analyzes records, the platform shall group related records into Pattern Clusters based on available intent, outcome, policy, override, complaint, and failure metadata.
* **AC-FP-SI-002.2:** Each Pattern Cluster shall include a summary explaining why the records were grouped.
* **AC-FP-SI-002.3:** Each Pattern Cluster shall identify the dominant original outcome and the dominant human-corrected or expected outcome where available.
* **AC-FP-SI-002.4:** If a Pattern Cluster contains too little evidence to support a candidate scenario, then the platform shall mark it as insufficient rather than promoting it automatically.

### REQ-FP-SI-003: Identify Policy Gaps

**User Story:** As a compliance officer, I want Notary to compare actual AI outcomes against stated policies, so that I can see where the system's behavior disagreed with our rules.

**Acceptance Criteria:**

* **AC-FP-SI-003.1:** When a Verification Record includes policy context and outcome data, the platform shall be able to compare the actual outcome against the policy condition.
* **AC-FP-SI-003.2:** When the actual outcome conflicts with the policy condition, the platform shall mark the record or candidate as a Policy Gap.
* **AC-FP-SI-003.3:** When presenting a Policy Gap, the platform shall show the policy reference, actual outcome, and expected outcome where available.

### REQ-FP-SI-004: Map Scenario Candidates to Regulatory Obligations

**User Story:** As a risk owner, I want candidate scenarios mapped to relevant regulatory obligations, so that we know which failures matter before an examiner asks.

**Acceptance Criteria:**

* **AC-FP-SI-004.1:** When a Scenario Candidate contains regulated-domain metadata, the platform shall be able to associate it with relevant obligations such as HIPAA, FCRA, GLBA, NAIC, ADA, or the EU AI Act where applicable.
* **AC-FP-SI-004.2:** A Regulatory Mapping shall identify the obligation, the reason for the mapping, and the evidence fields that support it.
* **AC-FP-SI-004.3:** If the platform cannot determine a regulatory mapping, it shall leave the mapping empty rather than inventing one.

### REQ-FP-SI-005: Require Human Labeling Before Promotion

**User Story:** As a compliance officer, I want a reviewer to confirm the expected correct outcome before a candidate becomes a scenario, so that Notary does not certify an unlabeled assumption.

**Acceptance Criteria:**

* **AC-FP-SI-005.1:** The platform shall not promote a Scenario Candidate into the Scenario Library until a human reviewer confirms the Expected Outcome.
* **AC-FP-SI-005.2:** When a reviewer labels a Scenario Candidate, the platform shall record the expected outcome, reviewer role, label time, and policy or business basis where provided.
* **AC-FP-SI-005.3:** If a reviewer rejects a Scenario Candidate, then the platform shall retain the rejection reason for audit and exclude the candidate from promotion.

### REQ-FP-SI-006: Verify Reproducibility Before Promotion

**User Story:** As an AI engineer, I want candidate scenarios tested for replayability before they enter the library, so that the release gate contains scenarios Notary can actually run.

**Acceptance Criteria:**

* **AC-FP-SI-006.1:** Before promotion, the platform shall evaluate whether a Scenario Candidate can be replayed from available evidence.
* **AC-FP-SI-006.2:** The platform shall classify candidate replayability as fully replayable, partially replayable, requires sandbox, not replayable, or missing evidence.
* **AC-FP-SI-006.3:** If a Scenario Candidate is not replayable, then the platform shall identify the missing or unsupported evidence that prevents replay.
* **AC-FP-SI-006.4:** The platform shall not represent a non-replayable candidate as a release-gate Scenario.

### REQ-FP-SI-007: Support Managed Library Expansion

**User Story:** As an AI operations leader, I want Notary to surface scenario candidates on a recurring basis, so that the scenario library grows as our AI systems encounter new real-world cases.

**Acceptance Criteria:**

* **AC-FP-SI-007.1:** The platform shall support recurring Scenario Intelligence Runs for an organization.
* **AC-FP-SI-007.2:** When recurring runs are enabled, the platform shall surface new Scenario Candidates without requiring the customer to reconfigure the run each time.
* **AC-FP-SI-007.3:** The platform shall distinguish newly discovered candidates from candidates already reviewed, promoted, or rejected.
* **AC-FP-SI-007.4:** The platform shall report library growth over time, including candidates surfaced, labeled, promoted, rejected, and blocked by missing evidence.

### Capture Rules and Decision Triggers

## Overview

This feature defines what becomes an investigable record in Notary and how that record comes to exist. Originally the platform had one implicit answer: a developer uploads a snapshot of a production failure, and that snapshot becomes an Incident. As the product widens beyond reactive failures to any agent decision worth proving — overridden decisions, disputed decisions, decisions that crossed a risk threshold, and sampled routine decisions — that single implicit answer no longer holds. This feature makes the answer explicit: it introduces the Verification Record as the general unit of captured work, the Capture Trigger that records why a decision was captured, and the Capture Rule that lets an organization decide systematically which decisions to capture rather than relying on a person to notice and upload each one.

The value is that the organization, not chance, governs what enters the forensic record. A compliance officer or platform team configures Capture Rules once, and every qualifying decision is captured with a known reason attached, while a developer can still manually flag any individual decision worth proving. This turns "capture what someone happened to upload" into a governed, auditable policy, and it is the mechanism that makes the broader verification-event direction operable rather than aspirational.

Notary uses a decision-event model for both live capture and historical import. Like process-mining systems that reconstruct a process from case, activity, and timestamp, Notary reconstructs a captured AI decision from Decision ID, Event Kind, Timestamp, Source System, and Payload. The platform groups Decision Events into Verification Records, then applies Capture Rules, replayability assessment, label requirements, and Scenario candidacy. SDKs may apply lightweight local filtering, but the platform owns the canonical classification and proof eligibility decisions.

## Terminology

* **Forensic Snapshot**: The structured, cryptographically sealed record of a single agent run produced by the SDK. Defined formally in the Forensic Agent Logger SDK feature.
* **Verification Record**: The platform-side record of a single captured agent decision, created from an ingested Forensic Snapshot, against which replay, mutation testing, and certification are performed over time. It is the general term; an Incident is one type of Verification Record. Every Verification Record carries the Capture Trigger that caused it to be captured.
* **Incident**: A Verification Record whose Capture Trigger is a production failure — the reactive, failure-driven case. Defined formally in the Forensics Platform feature; referenced here as one Capture Trigger type.
* **Capture Trigger**: The reason a decision was captured, recorded on every Verification Record. One of: failure, human override, external dispute, risk-threshold breach, sample, or manual flag.
* **Decision Event**: A normalized event in an AI decision timeline, carrying a Decision ID, Event Kind, Timestamp, Source System, and Payload. Decision Events are grouped into Verification Records.
* **Decision ID**: The stable identifier used to group Decision Events that belong to the same AI decision, such as a support case ID, claim ID, loan application ID, trace ID, or SDK run ID.
* **Event Kind**: The normalized type of a Decision Event, such as customer input, model call, tool response, policy lookup, final decision, human override, expected outcome label, or release context.
* **Capture Rule**: An organization-level policy that automatically marks decisions matching a defined condition for capture, so qualifying decisions become Verification Records without a person uploading each one.
* **Capture Source**: Whether a Verification Record was captured manually, automatically through a Capture Rule, submitted through an API or webhook, captured by an SDK, or created from historical import.
* **Rule Administrator**: A user permitted to create, edit, enable, or disable Capture Rules — the compliance officer or AI platform team, not every developer.

## Requirements

### REQ-FP-CR-001: Record a Capture Trigger on Every Verification Record

**User Story:** As a compliance officer, I want every captured decision to record why it was captured, so that the forensic record is governed and auditable rather than arbitrary.

**Acceptance Criteria:**

* **AC-FP-CR-001.1:** When a Verification Record is created, the platform shall record its Capture Trigger and its Capture Source.
* **AC-FP-CR-001.2:** The platform shall classify a Verification Record whose Capture Trigger is failure as an Incident.
* **AC-FP-CR-001.3:** If a Verification Record is created without a determinable Capture Trigger, then the platform shall reject the capture and return the reason rather than storing an untagged record.
* **AC-FP-CR-001.4:** When the user views a Verification Record, the platform shall display its Capture Trigger and Capture Source.

### REQ-FP-CR-002: Manually Flag a Decision for Capture

**User Story:** As a developer, I want to flag a specific agent decision as worth proving, so that I can capture something noteworthy even when no rule covers it.

**Acceptance Criteria:**

* **AC-FP-CR-002.1:** When a developer manually flags an available decision for capture, the platform shall create a Verification Record with Capture Source manual and an appropriate Capture Trigger.
* **AC-FP-CR-002.2:** If the referenced decision cannot be captured because its Forensic Snapshot is unavailable, then the platform shall reject the request and return the reason.
* **AC-FP-CR-002.3:** When the same decision is manually flagged more than once, the platform shall not create duplicate Verification Records for it.

### REQ-FP-CR-003: Define an Organization Capture Rule

**User Story:** As a rule administrator, I want to configure which decisions are captured automatically, so that our capture policy is systematic rather than dependent on someone noticing.

**Acceptance Criteria:**

* **AC-FP-CR-003.1:** When a Rule Administrator creates a Capture Rule, the platform shall require a Capture Trigger type and the condition that qualifies a decision (for example, decision failed, decision overridden by a human, external dispute recorded, a named risk threshold breached, or a sampling rate).
* **AC-FP-CR-003.2:** When a Capture Rule specifies a sampling rate, the platform shall capture a proportional share of matching decisions rather than all of them.
* **AC-FP-CR-003.3:** The platform shall scope every Capture Rule to the organization that created it and apply it only to that organization's decisions.
* **AC-FP-CR-003.4:** Where no Capture Rule is configured, the platform shall default to capturing only manually flagged decisions, so an organization captures nothing automatically until it opts in.
* **AC-FP-CR-003.5:** If a user who is not a Rule Administrator attempts to create, edit, enable, or disable a Capture Rule, then the platform shall deny the action.

### REQ-FP-CR-004: Capture Decisions Automatically When a Rule Matches

**User Story:** As a compliance officer, I want decisions that match our rules captured automatically, so that qualifying decisions are proven without manual effort.

**Acceptance Criteria:**

* **AC-FP-CR-004.1:** When a decision matches an enabled Capture Rule, the platform shall create a Verification Record with Capture Source automated and the rule's Capture Trigger.
* **AC-FP-CR-004.2:** While a Capture Rule is disabled, the platform shall not capture decisions on its behalf.
* **AC-FP-CR-004.3:** If a single decision matches more than one enabled Capture Rule, then the platform shall create a single Verification Record and record each matching Capture Trigger rather than creating duplicates.
* **AC-FP-CR-004.4:** While automatic capture would exceed the organization's configured capture Usage Limit, the platform shall defer or deny further automatic capture and indicate the limit was reached rather than failing silently.

### REQ-FP-CR-005: Manage Capture Rules

**User Story:** As a rule administrator, I want to review and change our capture rules over time, so that our policy stays current as the agent and regulations change.

**Acceptance Criteria:**

* **AC-FP-CR-005.1:** When a Rule Administrator lists Capture Rules, the platform shall show each rule's Capture Trigger, condition, enabled state, and Capture Source it produces.
* **AC-FP-CR-005.2:** When a Rule Administrator edits or disables a Capture Rule, the platform shall apply the change to subsequent decisions only and leave Verification Records already captured under the prior rule unchanged.
* **AC-FP-CR-005.3:** The platform shall record Capture Rule changes so the rule in effect at any past time can be determined.
* **AC-FP-CR-005.4:** When no Capture Rules exist, the platform shall present an empty state rather than an error.

### REQ-FP-CR-006: Normalize Decision Events

**User Story:** As an integration engineer, I want Notary to normalize SDK, webhook, API, and imported events into one decision-event format, so that the platform can create Verification Records consistently across capture sources.

**Acceptance Criteria:**

* **AC-FP-CR-006.1:** When the platform receives SDK, webhook, API, or imported evidence, the platform shall normalize each evidence item into a Decision Event where a Decision ID, Event Kind, Timestamp, Source System, and Payload can be determined.
* **AC-FP-CR-006.2:** When multiple Decision Events share the same Decision ID, the platform shall group them into the same Verification Record.
* **AC-FP-CR-006.3:** If a required Decision ID cannot be determined for an event, then the platform shall reject or quarantine the event and identify the missing mapping rather than creating an ungrouped Verification Record.
* **AC-FP-CR-006.4:** When imported records use customer-specific field names, the platform shall apply the customer-confirmed field mapping before creating Decision Events.
* **AC-FP-CR-006.5:** The platform shall preserve the Source System and original source reference for each Decision Event so the customer can trace a Verification Record back to its system of record.

### REQ-FP-CR-007: Keep Capture Discrete, Not Continuous Monitoring

**User Story:** As a CISO, I want capture to remain discrete evidence collection rather than live monitoring, so that Notary stays a forensic system and does not become an observability tool.

**Acceptance Criteria:**

* **AC-FP-CR-007.1:** The platform shall capture a Verification Record only as an after-the-fact record of an individual decision, not as a continuous stream of live agent telemetry.
* **AC-FP-CR-007.2:** The platform shall not raise real-time operational alerts, dashboards, or anomaly notifications from Capture Rules; a Capture Rule's only effect is to create Verification Records.
* **AC-FP-CR-007.3:** When a sampling Capture Rule is active, the platform shall record only the sampled decisions as discrete Verification Records and shall not retain a continuous performance trend of unsampled decisions.

#### Manual Submission and Source-System Connectors

## Overview

Manual Submission and Source-System Connectors defines how decisions enter Notary when they are not captured automatically by the SDK. Notary must live where business users already work: contact-center tools, claims systems, loan review systems, GRC tools, case-management platforms, and internal dashboards. A human reviewer should be able to send a suspicious AI decision, failed handoff, human override, complaint, or high-risk case to Notary from the source system without leaving their workflow.

This feature creates the manual, connector-based, and import-based path into AI Decision Assurance. A "Send to Notary" action, webhook submission, generic API call, or historical import creates Decision Events that Notary groups into Verification Records or Scenario Candidates with the source-system reference, capture trigger, expected outcome label if available, and enough evidence for replayability evaluation. The source system remains the system of record for the ticket, claim, application, or case; Notary owns the evidence, replayability status, scenario candidacy, proof workflow, and release-assurance result.

For high-volume customers, this feature must avoid turning every historical log row into a full evidence record. The customer maps source fields into Notary's decision-event schema, applies record-selection rules, previews how many conversations or cases would become Verification Records, and approves the import before records are committed.

## Terminology

* **Verification Record**: The platform-side record of a captured AI decision. Defined formally in the Capture Rules and Decision Triggers feature.
* **Scenario Candidate**: A potential Scenario discovered from historical records or manual submission. Defined formally in the Scenario Intelligence feature.
* **Source System**: The external business system where the decision or case is handled, such as Zendesk, Salesforce Service Cloud, Intercom, Genesys, NICE, ServiceNow, a claims platform, a loan origination system, or an internal case tool.
* **Source Record**: The ticket, conversation, claim, application, authorization request, case, or workflow item in the Source System.
* **Decision Event**: A normalized event in an AI decision timeline. Defined formally in the Capture Rules and Decision Triggers feature.
* **Field Mapping**: The customer-confirmed mapping from source-system fields to Notary fields such as Decision ID, Event Kind, Timestamp, Source System, Payload, final decision, and expected outcome.
* **Import Preview**: The pre-commit summary showing how many source rows or events would become Verification Records, which records would be ignored, and how the matched records break down by replayability and Scenario candidacy.
* **Send to Notary Action**: A manual action in a Source System or Notary UI that submits a Source Record to Notary for evidence capture, investigation, or scenario candidacy.
* **Submission Reason**: The reason a user sends a Source Record to Notary, such as human override, failed handoff, customer complaint, policy breach, high-risk decision, regulator request, or other.
* **Expected Outcome Label**: The reviewer-supplied expected correct behavior for the Source Record, such as escalate to human, approve, deny, route to specialist, hold for review, or custom.
* **Connector Submission**: A submission created through a source-system integration, webhook, API call, app/plugin action, or connector button.
* **Manual Submission**: A submission created directly by a user through Notary or by pasting/uploading a source record.
* **Replayability Status**: The platform's evaluation of whether a submitted record has enough evidence to be replayed.

## Requirements

### REQ-FP-MSC-001: Submit a Source Record Manually

**User Story:** As a support supervisor or compliance analyst, I want to send a suspicious decision to Notary manually, so that it can be investigated even if no automatic rule captured it.

**Acceptance Criteria:**

* **AC-FP-MSC-001.1:** When a user creates a Manual Submission, the platform shall require a Source System or source description, a Source Record reference, and a Submission Reason.
* **AC-FP-MSC-001.2:** When a user creates a Manual Submission, the platform shall allow the user to provide an Expected Outcome Label and notes.
* **AC-FP-MSC-001.3:** If required fields are missing, then the platform shall reject the submission and identify the missing fields.
* **AC-FP-MSC-001.4:** When a Manual Submission succeeds, the platform shall create a Verification Record or Scenario Candidate according to the selected Submission Reason and available evidence.

### REQ-FP-MSC-002: Send a Record from a Source System

**User Story:** As a QA reviewer, I want a Send to Notary action inside the system where I review work, so that I can capture bad AI decisions without leaving my workflow.

**Acceptance Criteria:**

* **AC-FP-MSC-002.1:** Where a Source System connector is configured, the Source System shall provide a Send to Notary Action for eligible Source Records.
* **AC-FP-MSC-002.2:** When a user invokes the Send to Notary Action, the platform shall receive the Source Record reference, Source System identity, Submission Reason, and available evidence payload.
* **AC-FP-MSC-002.3:** When the Source System supplies an Expected Outcome Label, the platform shall record the label and its provenance.
* **AC-FP-MSC-002.4:** When connector submission succeeds, the platform shall return a Notary record reference to the Source System where possible.
* **AC-FP-MSC-002.5:** If connector submission fails, then the Source System shall surface the failure reason where possible and the platform shall record the failed submission attempt.

### REQ-FP-MSC-003: Capture Submission Reason and Expected Outcome

**User Story:** As a compliance officer, I want each submitted record to say why it was sent and what should have happened, so that Notary can decide whether it belongs in the scenario workflow.

**Acceptance Criteria:**

* **AC-FP-MSC-003.1:** The platform shall store the Submission Reason on each submitted record.
* **AC-FP-MSC-003.2:** Supported Submission Reasons shall include human override, failed handoff, customer complaint, policy breach, high-risk decision, regulator or audit request, and other.
* **AC-FP-MSC-003.3:** The platform shall allow an Expected Outcome Label to be added at submission time or later during review.
* **AC-FP-MSC-003.4:** If no Expected Outcome Label is supplied, then the platform shall keep the record eligible for review but shall not promote it to a Scenario until a label is provided and approved.

### REQ-FP-MSC-004: Evaluate Replayability of Submitted Records

**User Story:** As an AI engineer, I want Notary to tell me whether a submitted record has enough evidence to replay, so that I know what can become a regression scenario.

**Acceptance Criteria:**

* **AC-FP-MSC-004.1:** When a submitted record is created, the platform shall evaluate its Replayability Status.
* **AC-FP-MSC-004.2:** Replayability Status shall identify whether the record is fully replayable, partially replayable, requires sandbox, not replayable, or missing evidence.
* **AC-FP-MSC-004.3:** If evidence is missing, then the platform shall identify which required evidence is missing where possible.
* **AC-FP-MSC-004.4:** The platform shall not represent a submitted record as release-gate ready unless it is replayable and has an approved Expected Outcome Label.

### REQ-FP-MSC-005: Preserve Source-System Context Without Owning the Case

**User Story:** As a business operator, I want Notary to preserve the source-system context without taking over the original case, so that our existing tools remain the operational system of record.

**Acceptance Criteria:**

* **AC-FP-MSC-005.1:** The platform shall store the Source System identity and Source Record reference for every submitted record.
* **AC-FP-MSC-005.2:** The platform shall not become the system of record for the original ticket, claim, application, or case.
* **AC-FP-MSC-005.3:** Where the Source System supports backlinks, the platform shall store a link back to the Source Record.
* **AC-FP-MSC-005.4:** The platform shall expose the Notary record status to the Source System where the connector supports status updates.

### REQ-FP-MSC-006: Protect Sensitive Source Data

**User Story:** As a CISO, I want connector submissions to limit sensitive data exposure, so that sending records to Notary does not over-share customer or business data.

**Acceptance Criteria:**

* **AC-FP-MSC-006.1:** Connector Submissions shall support field scope configuration so customers can choose which fields are sent raw, redacted, hashed, reference-only, or omitted.
* **AC-FP-MSC-006.2:** When a field is redacted, hashed, reference-only, or omitted, the platform shall reflect that in the evidence completeness context.
* **AC-FP-MSC-006.3:** If a requested replay or scenario promotion requires a field that was omitted or reference-only, then the platform shall identify the limitation rather than silently treating the record as complete.

### REQ-FP-MSC-007: Support Generic API and Webhook Submission

**User Story:** As an integration engineer, I want to submit records through a generic API or webhook, so that we can connect internal tools before a native connector exists.

**Acceptance Criteria:**

* **AC-FP-MSC-007.1:** The platform shall provide an authenticated generic submission API for Source Records.
* **AC-FP-MSC-007.2:** The generic submission API shall accept Source System identity, Source Record reference, Submission Reason, evidence payload, and optional Expected Outcome Label.
* **AC-FP-MSC-007.3:** The generic submission API shall return a Notary record reference when submission succeeds.
* **AC-FP-MSC-007.4:** If the generic submission is unauthenticated or scoped to the wrong organization, then the platform shall deny it.

### REQ-FP-MSC-008: Preview Historical Import

**User Story:** As an AI platform engineer, I want to preview how historical logs will be converted before committing them, so that we do not over-capture irrelevant conversations or miss required evidence.

**Acceptance Criteria:**

* **AC-FP-MSC-008.1:** When the user starts a historical import, the platform shall require a Source System or source description and a Field Mapping sufficient to identify a Decision ID, Event Kind, Timestamp where available, and evidence Payload.
* **AC-FP-MSC-008.2:** When the platform previews an import, it shall report total source rows or events, matched records, ignored records, replayable records, records needing labels, records missing cassette context, evidence-only records, and Scenario Candidate estimates.
* **AC-FP-MSC-008.3:** When required mapped fields are missing from the import sample, the platform shall identify the missing fields before committing records.
* **AC-FP-MSC-008.4:** The platform shall not commit imported Verification Records until the user approves the Import Preview.
* **AC-FP-MSC-008.5:** When import preview runs, the platform shall apply the same Capture Rules and replayability assessment used for live SDK, API, and webhook submissions.

### REQ-FP-MSC-009: Commit Historical Import

**User Story:** As an AI platform engineer, I want approved imports to create Verification Records and Scenario Candidates, so that historical failures can become release-gate coverage.

**Acceptance Criteria:**

* **AC-FP-MSC-009.1:** When the user commits an import, the platform shall create Verification Records only for source rows or Decision Events that match enabled Capture Rules.
* **AC-FP-MSC-009.2:** When imported source rows use real source identifiers, the platform shall preserve those identifiers on the resulting Verification Records rather than replacing them with synthetic row identifiers.
* **AC-FP-MSC-009.3:** When imported records include source metadata, expected outcome labels, agent version, model metadata, or policy version, the platform shall preserve those fields on the resulting Verification Records where mapped.
* **AC-FP-MSC-009.4:** When imported records share a failure pattern that matches Scenario Candidate criteria, the platform shall create or recommend Scenario Candidates rather than requiring users to review every record individually.
* **AC-FP-MSC-009.5:** If an imported record lacks evidence required for replay or proof, then the platform shall create the record with the corresponding Replayability Status and missing-prerequisite explanation rather than treating it as complete.

### REQ-FP-MSC-010: Show Submission Status in Notary

**User Story:** As a reviewer, I want to see submitted records and their status in Notary, so that I can complete labeling, replayability review, and scenario promotion.

**Acceptance Criteria:**

* **AC-FP-MSC-010.1:** The platform shall list submitted records with Source System, Source Record reference, Submission Reason, Expected Outcome Label status, Replayability Status, and Scenario Candidate status.
* **AC-FP-MSC-010.2:** When a submitted record lacks an Expected Outcome Label, the platform shall indicate that labeling is required.
* **AC-FP-MSC-010.3:** When a submitted record lacks evidence required for replay, the platform shall indicate that evidence is missing and identify the missing evidence where possible.
* **AC-FP-MSC-010.4:** When a submitted record becomes a Scenario Candidate or Scenario, the platform shall show that lifecycle state.

### Proof of Readiness

## Overview

Proof of Readiness applies Notary's capture-replay-verify engine before an agent ships rather than after it fails. A team defines a set of scenarios an agent must handle correctly, and Notary runs the agent against them deterministically, comparing each result to the expected outcome. When the agent behaves correctly across every required scenario, Notary issues a cryptographically signed Proof of Readiness certificate documenting which scenarios were tested, the agent version under test, the deterministic testing method, and the verified outcomes. It is the pre-deployment counterpart to the Proof of Mitigation certificate: the same proof machinery, pointed at "will this agent behave correctly" instead of "did this fix resolve the incident."

Delivered as a CI/CD gate, this fits how engineering teams already work with release gates: a developer commits agent code and a readiness scenario set, the pipeline triggers Notary verification against the accumulated Scenario Library, and deployment is permitted only when every required scenario passes. This turns the Scenario Library from a reactive regression asset into a forward-looking release gate, and gives the platform a reason to run on every deploy rather than only after an incident.

## Terminology

* **Scenario**: A saved, re-runnable test case with a known-correct outcome. Defined formally in the Scenario Library feature.
* **Scenario Run**: A single re-execution of a set of Scenarios against a specified agent version. Defined formally in the Scenario Library feature.
* **Agent Version**: The identifier of the agent build under test, expressed as a code reference (git branch and commit). Defined formally in the Testing Playground feature.
* **Readiness Policy**: The organization-defined set of Scenarios an Agent Version must pass, together with the pass condition (for example, all required Scenarios must pass), that determines whether a Proof of Readiness certificate is issued.
* **Readiness Check**: A single evaluation of an Agent Version against a Readiness Policy, producing a pass or fail verdict and, on pass, a Proof of Readiness Certificate.
* **Proof of Readiness Certificate**: A cryptographically signed certificate attesting that an Agent Version passed every Scenario required by a Readiness Policy, documenting the scenarios tested, the agent version, the testing method, and the outcomes.
* **Release Gate**: The CI/CD integration that triggers a Readiness Check from a pipeline and reports a pass, fail, or system-error result the pipeline can gate deployment on.

## Requirements

### REQ-FP-PR-001: Define a Readiness Policy

**User Story:** As a rule administrator, I want to define which scenarios an agent must pass before it ships, so that our readiness bar is explicit and enforceable.

**Acceptance Criteria:**

* **AC-FP-PR-001.1:** When a Rule Administrator creates a Readiness Policy, the platform shall require the set of Scenarios the Agent Version must pass and the pass condition.
* **AC-FP-PR-001.2:** The platform shall scope a Readiness Policy to the organization that created it.
* **AC-FP-PR-001.3:** When a Readiness Policy references Scenarios, the platform shall include only Scenarios belonging to the same organization.
* **AC-FP-PR-001.4:** If a user who is not a Rule Administrator attempts to create or edit a Readiness Policy, then the platform shall deny the action.
* **AC-FP-PR-001.5:** When a Readiness Policy is edited, the platform shall apply the change to subsequent Readiness Checks only and record the change so the policy in effect at any past time can be determined.

### REQ-FP-PR-002: Run a Readiness Check

**User Story:** As a developer, I want to check an agent version against our readiness policy, so that I know whether it is safe to ship before I deploy it.

**Acceptance Criteria:**

* **AC-FP-PR-002.1:** When a Readiness Check is started for an Agent Version and a Readiness Policy, the platform shall execute the Policy's Scenarios against that Agent Version as a Scenario Run.
* **AC-FP-PR-002.2:** When every Scenario required by the Readiness Policy passes, the platform shall record the Readiness Check as passed.
* **AC-FP-PR-002.3:** If any Scenario required by the Readiness Policy fails, then the platform shall record the Readiness Check as failed and identify the failing Scenarios.
* **AC-FP-PR-002.4:** If a required Scenario cannot be evaluated (errored), then the platform shall record the Readiness Check as failed rather than passed, and identify the errored Scenario.
* **AC-FP-PR-002.5:** When a Readiness Check completes, the platform shall report the per-Scenario results and the overall verdict.

### REQ-FP-PR-003: Issue a Proof of Readiness Certificate

**User Story:** As a compliance officer, I want a signed certificate when an agent passes its readiness policy, so that we have defensible evidence the agent was tested before deployment.

**Acceptance Criteria:**

* **AC-FP-PR-003.1:** When a Readiness Check passes, the platform shall issue a Proof of Readiness Certificate.
* **AC-FP-PR-003.2:** The platform shall document in the Certificate the Scenarios tested, the Agent Version, the deterministic testing method, and the verified outcomes.
* **AC-FP-PR-003.3:** The platform shall cryptographically sign the Certificate using the same signing custody as the Proof of Mitigation Certificate.
* **AC-FP-PR-003.4:** If a Readiness Check fails, then the platform shall not issue a Certificate.
* **AC-FP-PR-003.5:** The platform shall persist the Certificate to the immutable evidence log so it remains verifiable at any later time.

### REQ-FP-PR-004: Gate a Deployment from CI/CD

**User Story:** As a developer, I want my pipeline to trigger a readiness check and block deployment on failure, so that no agent version ships without passing.

**Acceptance Criteria:**

* **AC-FP-PR-004.1:** When a Release Gate triggers a Readiness Check from a pipeline for an Agent Version, the platform shall run the Check and return a pass or fail result to the caller.
* **AC-FP-PR-004.2:** When the result is pass, the Release Gate shall return a reference to the issued Proof of Readiness Certificate.
* **AC-FP-PR-004.3:** If the result is fail, then the Release Gate shall return the failing Scenarios so the pipeline can block deployment.
* **AC-FP-PR-004.4:** If a Readiness Check cannot be started, then the Release Gate shall return an error distinct from a fail verdict so the pipeline can distinguish a system failure from a readiness failure.
* **AC-FP-PR-004.5:** The platform shall authenticate the Release Gate request and scope it to the caller's organization.

### REQ-FP-PR-005: Review Readiness History

**User Story:** As a compliance officer, I want to see past readiness checks and their certificates, so that I can demonstrate an agent's pre-deployment testing history.

**Acceptance Criteria:**

* **AC-FP-PR-005.1:** When the user lists Readiness Checks, the platform shall show each Check's Agent Version, Readiness Policy, verdict, and time, scoped to the user's organization.
* **AC-FP-PR-005.2:** When the user selects a past Readiness Check, the platform shall display its per-Scenario results and, if issued, its Proof of Readiness Certificate.
* **AC-FP-PR-005.3:** When no Readiness Checks exist, the platform shall present an empty state rather than an error.

### Data Lifecycle and Retention

## Overview

This feature governs the lifecycle of forensic evidence over its multi-year life: how long records are retained, how they are archived for long-horizon reproducibility, and how the platform reconciles two of its own requirements that are in direct tension — the append-only immutability that makes evidence defensible, and data-protection law (notably GDPR Article 17, the right to erasure) that can require removing an individual's personal data on request. Evidence records can contain personal data (an applicant's financial details, a patient's information) captured inside a sealed snapshot. An unqualified "keep everything forever, never delete" policy is what makes the chain of custody trustworthy, and it is also what a data-subject erasure request directly challenges. This document makes that tension explicit and defines the retention, archival, and erasure behavior the platform must provide, while deliberately leaving the specific erasure mechanism as an open decision to be resolved before enterprise general availability.

The value is that the immutability guarantee and the legal obligation to honor erasure are reconciled by design rather than colliding at the first regulated customer. It defines what the platform retains, for how long, what an authorized erasure request does to a sealed record, and how integrity verification behaves afterward — so that neither the defensibility of the evidence nor the customer's legal compliance is silently compromised.

## Terminology

* **Verification Record**: The platform-side record of a single captured agent decision. Defined formally in the Capture Rules and Decision Triggers feature; an Incident is the failure-triggered type.
* **Immutable Log**: The append-only, tamper-proof store where validated snapshots and records are persisted. Defined formally in the Forensics Platform feature.
* **Retention Window**: The configured period for which a Verification Record is retained before it becomes eligible for archival or expiry, subject to Tier limits.
* **Archival Tier**: A lower-cost, long-horizon storage state for evidence that must remain reproducible for years but is no longer in active use, distinct from expiry (deletion).
* **Erasure Request**: An authorized request to remove an identified data subject's personal data from evidence, originating from a data-protection obligation such as GDPR Article 17.
* **Erasure Method**: The mechanism by which an Erasure Request is satisfied against append-only evidence. The candidate methods are defined in this document; the chosen method is an open decision.
* **Integrity Verification**: Recomputing and comparing a record's Root Hash to confirm it has not been tampered with. Defined formally in the Forensics Platform feature.

## Requirements

### REQ-FP-DL-001: Enforce a Retention Window

**User Story:** As a compliance officer, I want evidence retained for a defined period appropriate to our regulatory obligations, so that records are available as long as they may be needed and not indefinitely by accident.

**Acceptance Criteria:**

* **AC-FP-DL-001.1:** The platform shall associate every Verification Record with a Retention Window determined by the organization's configuration and Tier.
* **AC-FP-DL-001.2:** While a Verification Record is within its Retention Window, the platform shall retain it and keep it independently verifiable.
* **AC-FP-DL-001.3:** The platform shall record the Retention Window in effect for a record so it can be determined at any later time.
* **AC-FP-DL-001.4:** Where no organization-specific Retention Window is configured, the platform shall apply the default for the organization's Tier.

### REQ-FP-DL-002: Archive Evidence for Long-Horizon Reproducibility

**User Story:** As a general counsel, I want old evidence preserved in a durable, reproducible form, so that an incident from years ago can still be verified during a late audit or litigation.

**Acceptance Criteria:**

* **AC-FP-DL-002.1:** When a Verification Record passes out of active use but remains within a retention or legal-hold obligation, the platform shall move it to the Archival Tier rather than deleting it.
* **AC-FP-DL-002.2:** While a record is in the Archival Tier, the platform shall keep it self-contained and independently verifiable without dependence on live external services.
* **AC-FP-DL-002.3:** When an archived record is retrieved, the platform shall support Integrity Verification against it as for an active record.

### REQ-FP-DL-003: Reconcile Erasure Requests with Immutability

**User Story:** As a data protection officer, I want an authorized erasure request to remove a data subject's personal data without destroying the integrity of unrelated evidence, so that we can meet legal obligations without invalidating the chain of custody.

**Acceptance Criteria:**

* **AC-FP-DL-003.1:** When an authorized Erasure Request is accepted for an identified data subject, the platform shall render that subject's personal data in affected Verification Records unrecoverable.
* **AC-FP-DL-003.2:** If an Erasure Request is not authorized, then the platform shall deny it and record the denial.
* **AC-FP-DL-003.3:** When personal data is erased from a record, the platform shall preserve the record's existence and its non-personal forensic content rather than deleting the whole record, unless the whole record must be removed to satisfy the obligation.
* **AC-FP-DL-003.4:** When a record has been subject to erasure, the platform shall represent that an authorized erasure occurred, so the change is auditable and is not indistinguishable from tampering.
* **AC-FP-DL-003.5:** The platform shall record every Erasure Request and its outcome in an auditable manner.

### REQ-FP-DL-004: Make Integrity Verification Honest After Erasure

**User Story:** As an auditor, I want to distinguish an authorized erasure from tampering, so that a record altered for legal compliance is not mistaken for a compromised one.

**Acceptance Criteria:**

* **AC-FP-DL-004.1:** When Integrity Verification is performed on a record that has undergone authorized erasure, the platform shall report the record as authentically erased rather than simply reporting a hash mismatch as tampering.
* **AC-FP-DL-004.2:** The platform shall retain enough non-personal metadata about an erased record to demonstrate the record's original existence and the authorized nature of the erasure.
* **AC-FP-DL-004.3:** If verification cannot distinguish authorized erasure from tampering for a record, then the platform shall treat the record as unverifiable rather than asserting it is authentic.

## Open Decision: Erasure Method

The mechanism for satisfying an Erasure Request against append-only evidence is not yet decided. This section records the candidate approaches and their tradeoffs so the decision can be made before enterprise general availability; the requirements above are written to hold regardless of which is chosen.

* **Crypto-shredding.** Encrypt personal data within a sealed record under a per-subject key and satisfy erasure by destroying that key, leaving the record present but its personal content unrecoverable. Preserves the record and its Merkle structure, and keeps erasure auditable; requires per-subject key management and a sealing design that isolates personal fields under their own key.
* **Pseudonymization at capture.** Have the SDK avoid sealing raw personal data at all, storing references or tokens the customer can break instead. Minimizes personal data in the evidence log entirely; shifts responsibility to capture-time configuration and depends on the customer maintaining the reference mapping.
* **Documented legal basis for retention.** Rely on a legal-obligation or legal-claims basis to retain evidence and decline erasure where the obligation applies, with no technical erasure mechanism. Simplest technically; carries the most legal risk and depends on jurisdiction and the specific obligation.

The chosen Erasure Method interacts with the Cryptographic Evidence Sealing design (how personal fields are sealed) and with BYOK key custody, and those blueprints must be revisited once the method is selected.

### Proof Claim Scope and Label Provenance

## Overview

Proof Claim Scope and Label Provenance keeps Notary's proof language precise. Notary verifies that a customer-supplied fix or candidate release produces a customer-approved expected outcome under the recorded scenario conditions. It does not independently determine the morally, legally, or medically correct answer, and it does not certify that an AI system is safe in general. This feature defines how expected outcomes are labeled, how label provenance is stored, and how certificates and readiness reports state the exact scope of what was verified.

This matters because Notary operates in regulated and litigation-adjacent settings. A certificate that overstates its claim becomes a liability. A well-scoped proof states what evidence was tested, which version was tested, who supplied the expected outcome, what passed, what did not, and what limitations remain.

## Terminology

* **Expected Outcome**: The customer-approved behavior or decision a fixed agent or release should produce under a Scenario's recorded conditions.
* **Label Provenance**: The record of who or what supplied an Expected Outcome, when it was supplied, under which policy or business basis, and whether it was reviewed or approved.
* **Proof Claim**: The statement a certificate, readiness report, or dashboard makes about what was verified.
* **Claim Scope**: The boundaries of a Proof Claim, including scenario set, evidence set, expected outcomes, agent version, replay method, limitations, and time of verification.
* **Known Limitation**: Any condition that weakens or bounds the proof, such as missing evidence, redaction, BYOK withheld key, non-deterministic replay, live-model dependency, partial cassette coverage, or human-labeled expected outcome.
* **Readiness Report**: A report or certificate showing that an agent version passed a defined Scenario set, without asserting general system safety.

## Requirements

### REQ-FP-PCS-001: Record Label Provenance

**User Story:** As a compliance officer, I want expected outcomes to carry provenance, so that a proof shows who defined correctness and why.

**Acceptance Criteria:**

* **AC-FP-PCS-001.1:** When an Expected Outcome is supplied for a Scenario, Mutation Test, or Readiness Check, the platform shall record Label Provenance.
* **AC-FP-PCS-001.2:** Label Provenance shall identify the reviewer role or source system, label time, expected outcome, and policy or business basis where provided.
* **AC-FP-PCS-001.3:** If an Expected Outcome is supplied by an automated process, the platform shall mark it as automated and require human approval before it can support a certificate-grade proof.
* **AC-FP-PCS-001.4:** The platform shall preserve prior labels when an Expected Outcome is changed, so label history remains auditable.

### REQ-FP-PCS-002: Bound Proof Claims to Tested Conditions

**User Story:** As a general counsel, I want each proof to state exactly what was tested, so that the certificate cannot be read as a broad safety guarantee.

**Acceptance Criteria:**

* **AC-FP-PCS-002.1:** Each Proof Claim shall identify the Scenario or Scenario set tested.
* **AC-FP-PCS-002.2:** Each Proof Claim shall identify the agent version, fix reference, release context, or configuration under test.
* **AC-FP-PCS-002.3:** Each Proof Claim shall identify the Expected Outcome and its Label Provenance.
* **AC-FP-PCS-002.4:** Each Proof Claim shall state that the proof applies to the tested scenario conditions and does not certify general safety outside that scope.

### REQ-FP-PCS-003: Disclose Known Limitations

**User Story:** As an auditor, I want proof artifacts to disclose limitations, so that I can judge whether the evidence is strong enough for its intended use.

**Acceptance Criteria:**

* **AC-FP-PCS-003.1:** When a certificate or readiness report is generated, the platform shall include Known Limitations that affect independent verification or claim strength.
* **AC-FP-PCS-003.2:** Known Limitations shall include missing evidence, redaction, reference-only capture, BYOK withheld key, partial replayability, required sandbox, non-determinism, live-model dependency, and human-labeled expected outcome where applicable.
* **AC-FP-PCS-003.3:** If a Known Limitation prevents certificate-grade verification, then the platform shall block certificate issuance rather than burying the limitation.

### REQ-FP-PCS-004: Calibrate Readiness Language

**User Story:** As a risk owner, I want readiness reports to avoid overclaiming safety, so that they are useful evidence without becoming a liability.

**Acceptance Criteria:**

* **AC-FP-PCS-004.1:** A Readiness Report shall state which Scenario set was tested and which agent version was tested.
* **AC-FP-PCS-004.2:** A Readiness Report shall report pass/fail/errored results for the tested Scenario set.
* **AC-FP-PCS-004.3:** A Readiness Report shall not state or imply that the AI system is safe in general.
* **AC-FP-PCS-004.4:** A Readiness Report may state that the tested agent version did not repeat the covered known failure modes when all required Scenarios pass.

### REQ-FP-PCS-005: Make Claim Scope Visible in the Dashboard

**User Story:** As a compliance officer, I want the dashboard to show the scope of proof before I export it, so that I understand what the certificate does and does not claim.

**Acceptance Criteria:**

* **AC-FP-PCS-005.1:** When the dashboard displays a certificate or readiness result, it shall show the Claim Scope.
* **AC-FP-PCS-005.2:** When the dashboard displays a certificate or readiness result with Known Limitations, it shall show those limitations in plain language.
* **AC-FP-PCS-005.3:** When a proof is based on a human-labeled Expected Outcome, the dashboard shall identify the label source or reviewer role where available.

## GRC Integrations

## Overview

GRC Integrations connect Notary to the enterprise Governance, Risk, and Compliance systems where compliance teams already manage their work—ServiceNow, OneTrust, and AuditBoard. When Notary generates a Proof of Mitigation certificate, the integration automatically creates a corresponding incident record in the customer's GRC system, attaches the forensic evidence, and maps it to the relevant regulatory frameworks. This lets compliance teams close audit findings inside their existing tooling without manually re-entering evidence.

This feature is a distinct capability that consumes the outputs of the Forensics Platform (certificates, replay logs, mutation test results) and pushes them outward. Notary generates evidence; GRC systems manage the compliance workflow. The integration is the bridge that lets Notary feed directly into the systems of record that regulators and auditors ultimately review.

## Terminology

* **Proof of Mitigation Certificate**: The signed forensic artifact produced by Notary. Defined formally in the Proof of Mitigation Certificates feature.
* **GRC System**: An external enterprise Governance, Risk, and Compliance platform (ServiceNow, OneTrust, or AuditBoard) that manages compliance workflows and evidence.
* **GRC Connection**: A configured, authenticated link between a Notary organization and a specific GRC System instance.
* **GRC Incident Record**: The record created in the GRC System that corresponds to a Notary Incident and holds its attached forensic evidence.
* **Framework Mapping**: The association of attached evidence to specific regulatory framework requirements (for example, EU AI Act Article 10, NIST AI RMF) within the GRC System.
* **Evidence Attachment**: The forensic artifacts pushed to the GRC System, including the certificate, replay logs, and mutation test results.

## Requirements

### REQ-GRC-001: Configure a GRC Connection

**User Story:** As a compliance officer, I want to connect Notary to our GRC system, so that evidence can flow into the tools we already use.

**Acceptance Criteria:**

* **AC-GRC-001.1:** When the user configures a GRC Connection, the platform shall accept and store the credentials needed to authenticate to the selected GRC System.
* **AC-GRC-001.2:** The platform shall support GRC Connections to ServiceNow, OneTrust, and AuditBoard.
* **AC-GRC-001.3:** When a GRC Connection is saved, the platform shall verify it can authenticate to the GRC System and report the connection status.
* **AC-GRC-001.4:** If authentication to the GRC System fails, then the platform shall report the failure and shall not mark the connection as active.
* **AC-GRC-001.5:** The platform shall store GRC credentials securely and shall not expose them in retrieval responses.
* **AC-GRC-001.6:** The platform shall gate GRC Connections by the organization's Tier (per the Tiers and Entitlements feature): none on the Free Tier, up to the configured limit on Professional, and unlimited plus custom connectors on Enterprise.
* **AC-GRC-001.7:** If creating a GRC Connection would exceed the organization's Tier limit, then the platform shall deny it and indicate a higher Tier is required.

### REQ-GRC-002: Create a GRC Incident Record on Certificate Generation

**User Story:** As a compliance officer, I want a GRC incident record created automatically when a certificate is issued, so that remediation evidence appears in our system of record without manual entry.

**Acceptance Criteria:**

* **AC-GRC-002.1:** When a Proof of Mitigation Certificate is generated and an active GRC Connection exists, the platform shall create a GRC Incident Record in the connected GRC System.
* **AC-GRC-002.2:** When creating a GRC Incident Record, the platform shall populate it with the Notary Incident's identifying details and root-cause summary.
* **AC-GRC-002.3:** If no active GRC Connection exists when a certificate is generated, then the platform shall complete certificate generation without attempting a push.
* **AC-GRC-002.4:** If the GRC System rejects the record creation, then the platform shall record the failure and make the push retryable rather than losing the evidence.

### REQ-GRC-003: Attach Forensic Evidence

**User Story:** As a compliance officer, I want the forensic evidence attached to the GRC record, so that auditors can review it in context.

**Acceptance Criteria:**

* **AC-GRC-003.1:** When a GRC Incident Record is created, the platform shall attach the Proof of Mitigation Certificate, replay logs, and mutation test results as Evidence Attachments.
* **AC-GRC-003.2:** If an Evidence Attachment fails to upload, then the platform shall record the failure and allow the attachment to be retried.

### REQ-GRC-004: Map Evidence to Regulatory Frameworks

**User Story:** As a compliance officer, I want evidence mapped to framework requirements in the GRC system, so that audit findings can be closed against specific controls.

**Acceptance Criteria:**

* **AC-GRC-004.1:** When evidence is attached to a GRC Incident Record, the platform shall apply a Framework Mapping associating the evidence with the relevant regulatory framework requirements.
* **AC-GRC-004.2:** The platform shall support Framework Mappings for the EU AI Act, NIST AI RMF, SEC, and OCC where the target GRC System supports control mapping.
* **AC-GRC-004.3:** Where the target GRC System does not support control mapping, the platform shall still attach the evidence and record that mapping was unavailable.

### REQ-GRC-005: Retry and Report Push Failures

**User Story:** As a compliance officer, I want failed pushes surfaced and retryable, so that no forensic evidence is silently lost in transit.

**Acceptance Criteria:**

* **AC-GRC-005.1:** When a push to a GRC System fails, the platform shall record the failure with its cause and mark the push as pending retry.
* **AC-GRC-005.2:** When a push fails, the platform shall automatically retry using exponential backoff at approximately 5 seconds, 30 seconds, 3 minutes, and 30 minutes, and shall stop automatic retries after 24 hours from the first attempt.
* **AC-GRC-005.3:** When automatic retries are exhausted, the platform shall notify the compliance officer by email that the push failed and requires attention.
* **AC-GRC-005.4:** When a push is pending retry or has exhausted retries, the platform shall allow the compliance officer to trigger a manual retry.
* **AC-GRC-005.5:** When any retry (automatic or manual) runs, the platform shall re-attempt record creation and evidence attachment without duplicating an already-created GRC Incident Record.
* **AC-GRC-005.6:** While a push is pending retry, the platform shall preserve the association between the Notary Incident and the intended GRC System.
* **AC-GRC-005.7:** When a certificate is generated but its push has not succeeded, the platform shall treat the certificate as issued and the GRC push as a separate, independently tracked delivery state.

## Web Dashboard

## Overview

The Web Dashboard is the browser-based interface teams use to operate Notary without writing code. Through it, a user installs or verifies the SDK, reviews Verification Records, inspects captured Decision Evidence Graph elements, triggers cassette replay, verifies a fix, issues Proof of Mitigation, promotes verified cases into Scenarios, runs Scenario sets, creates Readiness Policies, and triggers Release Gate checks. It presents the active release-gate product in one place, so compliance, operations, and engineering users can follow the path from captured decision to proof and recurrence prevention.

The dashboard is a thin client: it holds no forensic logic and stores no evidence itself. Every operation it offers is backed by an authenticated Forensics Platform capability, and every piece of data it shows is scoped to the user's organization. Its job is to make the discovery and proof workflow operable: show what was captured, what sources and context are connected, which actions are available, why blocked actions are unavailable, what proof claims and known limitations exist, and whether an agent version passes the Release Gate.

## Terminology

* **Verification Record**: The platform-side record of a captured AI decision. Defined formally in the Capture Rules and Decision Triggers feature.
* **Incident**: A Verification Record whose trigger is a production failure or other investigation-worthy failure condition. Defined formally in the Forensics Platform feature.
* **Decision Evidence Graph**: The sealed graph of captured workflow elements. Defined formally in the Decision Evidence Graph Capture feature.
* **Replay**: The deterministic replay capability. Defined formally in the Deterministic Replay feature.
* **Mutation Test**: The fix-verification capability. Defined formally in the Mutation Testing feature.
* **Proof of Mitigation Certificate**: The signed remediation artifact. Defined formally in the Proof of Mitigation Certificates feature.
* **Scenario**: A saved, re-runnable test case. Defined formally in the Scenario Library feature.
* **Scenario Run**: A re-execution of one or more Scenarios against an agent version. Defined formally in the Scenario Library feature.
* **Readiness Policy**: The Scenario set an agent version must pass before release. Defined formally in the Proof of Readiness feature.
* **Readiness Check**: A single evaluation of an agent version against a Readiness Policy. Defined formally in the Proof of Readiness feature.
* **Release Gate**: The CI/CD-facing contract that returns pass, fail, or system error from a Readiness Check. Defined formally in the Proof of Readiness feature.
* **Operation Status**: The dashboard's representation of an operation's state, such as pending, succeeded, failed, errored, or blocked.

## Requirements

### REQ-WD-001: Authenticate and Scope Dashboard Access

**User Story:** As a compliance officer, I want to authenticate before operating Notary, so that evidence and proof workflows are visible only to authorized users of my organization.

**Acceptance Criteria:**

* **AC-WD-001.1:** While the user is not authenticated, the dashboard shall display an authentication prompt and shall not display organization data.
* **AC-WD-001.2:** When the user's session token is missing, invalid, or expired, the dashboard shall prevent authenticated API actions and prompt for a valid token.
* **AC-WD-001.3:** The dashboard shall display only data belonging to the authenticated user's organization.

### REQ-WD-002: Set Up SDK Capture

**User Story:** As a developer, I want accurate SDK setup instructions, so that I can create a Verification Record from a real captured decision.

**Acceptance Criteria:**

* **AC-WD-002.1:** When the user opens SDK setup, the dashboard shall show the correct Python SDK installation command for the current package publication state.
* **AC-WD-002.2:** When the user views deployed-demo setup, the dashboard shall show the deployed API URL rather than a local development URL.
* **AC-WD-002.3:** When the user views local setup, the dashboard shall distinguish local commands from deployed-demo commands.
* **AC-WD-002.4:** The dashboard shall provide a minimal capture example that uses the actual SDK API and submits a Verification Record to Notary.
* **AC-WD-002.5:** When the user copies a setup command or code sample, the dashboard shall copy the visible text and indicate that the copy succeeded.

### REQ-WD-002A: Start With Discovery Before Full Setup

**User Story:** As an AI platform owner, I want the first screen to show what Notary can already learn from the sources I connect, so that setup begins with evidence instead of a long questionnaire.

**Acceptance Criteria:**

* **AC-WD-002A.1:** After the first valid source is connected, the dashboard shall display an initial decision map with discovered decisions or decision families, source coverage, and current evidence sufficiency.
* **AC-WD-002A.2:** The dashboard shall distinguish required corrections from optional enrichment and explain which evaluators or proof actions each missing input would unlock.
* **AC-WD-002A.3:** The dashboard shall allow a user to confirm mappings and context progressively rather than requiring all mappings before any discovery result is shown.
* **AC-WD-002A.4:** If continuous monitoring or recurring Sweep execution is offered, the dashboard shall present it as a confirmation step after initial discovery rather than as a prerequisite for first value.

### REQ-WD-003: Review Verification Records

**User Story:** As a compliance officer, I want to inspect captured Verification Records, so that I understand what was captured and what actions are available.

**Acceptance Criteria:**

* **AC-WD-003.1:** When the user opens the Verification Records view, the dashboard shall display each record with its source, capture trigger, replayability status, integrity status, and next recommended action.
* **AC-WD-003.2:** When no Verification Records exist, the dashboard shall display an empty state rather than an error.
* **AC-WD-003.3:** When the user opens a Verification Record detail, the dashboard shall display its Decision Evidence Graph elements, source metadata, integrity status, replayability, missing prerequisites, labels, evidence references, and custody history.
* **AC-WD-003.4:** If the requested Verification Record does not exist or is not accessible, then the dashboard shall display a not-found or access-denied state.

### REQ-WD-004: Show Action Eligibility

**User Story:** As an operator, I want unavailable actions to explain why they are blocked, so that I know what must happen next.

**Acceptance Criteria:**

* **AC-WD-004.1:** When the dashboard displays replay, mutation, proof, Scenario promotion, Scenario Run, Readiness Check, or Release Gate actions, it shall enable only actions whose server-side eligibility check passes.
* **AC-WD-004.2:** When an action is unavailable, the dashboard shall keep the action visible where it is part of the primary workflow and shall display the reason returned by the platform.
* **AC-WD-004.3:** If a user attempts an action that becomes unavailable after the view loads, then the dashboard shall display the latest server-returned reason rather than failing silently.

### REQ-WD-005: Operate Replay, Fix Verification, and Proof

**User Story:** As a compliance officer, I want to run the proof loop from a record detail, so that I can prove a failure was reproduced and fixed.

**Acceptance Criteria:**

* **AC-WD-005.1:** When the user triggers Replay for an eligible Verification Record, the dashboard shall submit the request and display the Replay Run result, replay method, and known limitations.
* **AC-WD-005.2:** When the user submits a Mutation Test, the dashboard shall collect or reference the fix configuration and expected outcome required by the platform.
* **AC-WD-005.3:** When the Mutation Test completes, the dashboard shall display whether the fix was verified and shall show the original and mutated decisions.
* **AC-WD-005.4:** When a Proof of Mitigation Certificate is issued, the dashboard shall display the certificate reference, signature status, claim scope, and known limitations.
* **AC-WD-005.5:** If any proof-loop step fails or is incomplete, then the dashboard shall display the failure state and platform-returned reason.

### REQ-WD-006: Manage Scenarios and Scenario Runs

**User Story:** As an AI engineer, I want to promote verified records into Scenarios and run them against agent versions, so that known failures become release checks.

**Acceptance Criteria:**

* **AC-WD-006.1:** When the user views Scenario Candidates, the dashboard shall show each candidate's source record, replayability, approved label status, next action, and blocked or ready state.
* **AC-WD-006.2:** When the user promotes an eligible candidate or record, the dashboard shall create or display the resulting Scenario.
* **AC-WD-006.3:** When the user views the Scenario Library, the dashboard shall show active and retired Scenarios with their source record and expected outcome.
* **AC-WD-006.4:** When the user starts a Scenario Run, the dashboard shall submit the selected Scenarios and agent version to the platform.
* **AC-WD-006.5:** When a Scenario Run completes, the dashboard shall display the per-Scenario pass, fail, or errored results and the run summary.

### REQ-WD-007: Operate Readiness and Release Gates

**User Story:** As a developer, I want to trigger readiness checks and release gates from the dashboard, so that I can see whether a candidate agent version can ship.

**Acceptance Criteria:**

* **AC-WD-007.1:** When the user creates or edits a Readiness Policy, the dashboard shall show the selected Scenario set and pass condition.
* **AC-WD-007.2:** When the user starts a Readiness Check, the dashboard shall display the Scenario Run results and the overall readiness verdict.
* **AC-WD-007.3:** When the Readiness Check passes, the dashboard shall display the Proof of Readiness certificate reference.
* **AC-WD-007.4:** When the Release Gate returns fail, the dashboard shall display the failing and errored Scenarios.
* **AC-WD-007.5:** When the Release Gate returns a system error, the dashboard shall distinguish it from a readiness failure.
* **AC-WD-007.6:** The dashboard shall provide a copyable CI/CD request example for the Release Gate.

### REQ-WD-008: Represent Product State Reliably

**User Story:** As a user evaluating Notary, I want the dashboard to reflect real product state, so that I can trust that I am seeing implemented workflow behavior rather than static demo copy.

**Acceptance Criteria:**

* **AC-WD-008.1:** The dashboard shall render statuses from persisted platform objects or service results, not from hardcoded static panels.
* **AC-WD-008.2:** When demo data is shown, the dashboard shall clearly identify it as demo data.
* **AC-WD-008.3:** When a view is loading, empty, or failed, the dashboard shall display the corresponding loading, empty, or error state.
* **AC-WD-008.4:** Every primary visible action shall either call a working platform endpoint or be disabled with a platform-provided reason.

## Tiers and Entitlements

## Overview

Tiers and Entitlements defines the three subscription tiers Notary sells — Free, Professional, and Enterprise — and governs which capabilities and usage limits each unlocks. It is the single source of truth for feature-gating: every other feature that behaves differently by tier (replay volume, automated replay, certificate signing options, GRC connections, retention, access controls) references the entitlements defined here rather than encoding tier logic of its own. The tier structure follows the go-to-market motion: Free lands developers through the open source SDK, Professional is the paid tier for compliance and legal teams running real investigations, and Enterprise adds organization-scale controls and custom terms.

This feature exists so that gating is consistent and enforceable rather than scattered and implicit. Exact prices and numeric quotas are deliberately left as to-be-determined here and in the features that reference them; what is fixed is the tier set, the relative capability boundaries between tiers, and the requirement that the platform enforce whatever limits are configured. Pricing figures shown on marketing surfaces are indicative and are not treated as committed values by these requirements.

## Terminology

* **Tier**: One of the three subscription levels — Free, Professional, or Enterprise — that an organization is subscribed to at a given time.
* **Entitlement**: A specific capability or numeric limit granted by a Tier (for example, automated replay enabled, or a maximum number of GRC connections).
* **Usage Limit**: A quota-type Entitlement measured over a period or scope (for example, deterministic replays per month, branches per incident, data retention window). Exact values are TBD.
* **Feature Gate**: A check the platform performs before allowing an action, comparing the organization's Tier entitlements against what the action requires.
* **Upgrade / Downgrade**: A change of an organization's Tier that changes the entitlements in effect.

## Requirements

### REQ-TIER-001: Define the Tier Set

**User Story:** As a product owner, I want a fixed set of subscription tiers with defined capability boundaries, so that gating across the product is consistent.

**Acceptance Criteria:**

* **AC-TIER-001.1:** The platform shall support exactly three Tiers: Free, Professional, and Enterprise.
* **AC-TIER-001.2:** The platform shall associate every organization with exactly one active Tier at any time.
* **AC-TIER-001.3:** Where no paid Tier has been purchased, the platform shall default an organization to the Free Tier.
* **AC-TIER-001.4:** The platform shall treat each higher Tier as a superset of the capabilities of the Tier below it, except where a capability is explicitly Enterprise-only.

### REQ-TIER-002: Gate Capabilities by Tier

**User Story:** As a compliance officer, I want features to be available according to my organization's tier, so that entitlements match what we pay for.

**Acceptance Criteria:**

* **AC-TIER-002.1:** When an action requires a capability the organization's Tier does not include, the platform shall deny the action and indicate that the capability requires a higher Tier.
* **AC-TIER-002.2:** The platform shall gate the following capability boundaries by Tier, per the entitlement matrix below: framework/SDK support breadth, deterministic replay volume, available real-sandbox providers, branches per incident, manual versus automated mutation testing and replay, certificate signing algorithms, compliance report availability, number of GRC connections, audit logging, role-based access control, single sign-on, service-level commitments, support level, and data retention window.
* **AC-TIER-002.3:** Enterprise-only capabilities (single sign-on and custom sandbox providers, signing, and connectors) shall be denied on Free and Professional Tiers.

### REQ-TIER-003: Enforce Usage Limits

**User Story:** As a platform owner, I want per-tier usage limits enforced, so that consumption-based capabilities stay within what a tier grants.

**Acceptance Criteria:**

* **AC-TIER-003.1:** The platform shall enforce each configured Usage Limit for the organization's Tier (for example, deterministic replays per period, branches per incident, retention window, stored Scenarios in the Library, and Scenario Runs per period).
* **AC-TIER-003.2:** While a Usage Limit is reached, the platform shall deny or defer further consumption of that capability and indicate the limit was reached rather than failing silently.
* **AC-TIER-003.3:** Exact numeric values for Usage Limits are configurable and are to be determined; the platform shall not hard-code them such that they cannot be adjusted per Tier.

### REQ-TIER-004: Change Tier

**User Story:** As a customer, I want my entitlements to change when my tier changes, so that upgrades and downgrades take effect predictably.

**Acceptance Criteria:**

* **AC-TIER-004.1:** When an organization's Tier changes, the platform shall apply the new Tier's entitlements to subsequent actions.
* **AC-TIER-004.2:** If a downgrade would place existing data or configuration beyond the lower Tier's limits (for example, more GRC connections than the lower Tier allows), then the platform shall retain the existing evidence and records and restrict only further creation, rather than deleting data.
* **AC-TIER-004.3:** The platform shall record Tier changes so the entitlements in effect at any past time can be determined.

## Entitlement Matrix

Capability boundaries by Tier. Exact prices and numeric quotas are TBD; the relative boundaries are the fixed part.

| Capability | Free | Professional | Enterprise |
| --- | --- | --- | --- |
| SDK: capture, HMAC sealing, local verify | Yes | Yes | Yes |
| Framework support | Basic / raw | All frameworks | All + custom |
| Deterministic replay volume | Limited (free quota, TBD) | Unlimited | Unlimited |
| Cassette replay (default) | Yes | Yes | Yes |
| Stored Scenarios in the Library | Limited (free quota, TBD) | Higher limit (TBD) | Unlimited |
| Scenario Runs (Testing Playground) per period | Limited (free quota, TBD) | Unlimited | Unlimited |
| Live sandbox validation (escalation) | Stripe only | Stripe, GitHub, Salesforce | \+ custom providers |
| Branches per incident | 1 | Unlimited | Unlimited |
| Mutation testing / automated replay | Manual only | Automated | Automated |
| Proof of Mitigation certificates | Yes | Yes | Yes |
| Certificate signature | ECDSA | ECDSA + RSA | Custom |
| Compliance reports | None | All frameworks | Custom |
| GRC connections | 0 | Multiple (limit TBD) | Unlimited + custom connectors |
| Audit logging / RBAC | No | Yes | Yes |
| Single sign-on | No | No | Yes |
| Service-level commitment | None | 99.5% | 99.9% |
| Support | Community | Priority | Dedicated |
| Data retention | 30 days | 1 year | Custom |

Notes: This three-tier structure supersedes any earlier four-tier framing (a separate "Essentials" tier) referenced in older material. Where marketing surfaces show specific prices, they are indicative and not binding on these requirements.

### Decision Evidence Discovery and Sweep

## Overview

Decision Evidence Discovery and Sweep is the platform capability that finds assurance concerns before a customer has assembled a complete forensic snapshot or declared an incident. It ingests evidence from SDK capture, DEP providers, generic APIs, files, OpenTelemetry, and selected source connectors; preserves each source's provenance; links evidence around a decision; resolves the context applicable when that decision occurred; and runs only evaluations supported by the available evidence.

The feature produces explainable Assurance Candidates, not automatic declarations that an AI system failed. An authorized reviewer or explicitly delegated deterministic rule decides whether a candidate becomes an Incident. Accepted Incidents enter the existing replay, mutation, certificate, Scenario, and Release Gate workflow without creating a parallel proof system.

Discovery is progressive. A customer can begin with one source and receive evidence-quality or replayability findings before connecting policy, business outcome, or governance systems. The platform requests additional context only when it resolves ambiguity, enables an evaluator, or raises the supported evidence level. Logs are one input, not the whole answer: meaningful assurance depends on connecting context from policy, expected-outcome, guardrail, deployment, and source-of-truth systems over time.

## Terminology

* **Decision Evidence Protocol (DEP):** The independent interchange protocol used to represent observations, context, assessments, review decisions, evidence bundles, and verification claims.
* **Decision Evidence Resource:** An immutable DEP resource received from a provider or produced by a recorded transformation.
* **Decision Evidence Record (DER):** The logical, linked set of resources concerning one decision or decision family. It may be incomplete.
* **Provider:** A source that advertises and supplies one or more DEP resource types.
* **Source Profile:** A non-authoritative summary of a connected source's schemas, timestamps, identifiers, volume, coverage, and candidate mappings.
* **Context Binding:** A versioned assertion that a policy, expected outcome, guardrail, evidence requirement, deployment, or other artifact applied to a subject during an effective period.
* **Evaluator Contract:** A machine-readable declaration of an evaluator's required inputs, minimum evidence level, method class, outputs, authority, and version.
* **Evidence Sufficiency Level:** `E0` observation only, `E1` context linked, `E2` authoritative or corroborated context, `E3` sealed replay-ready evidence, or `E4` completed before-and-after fix verification.
* **Sweep Definition:** Versioned organization configuration describing evidence scope, time range, mappings, enabled evaluators, limits, review policy, and retention controls.
* **Sweep Run:** An immutable execution record containing frozen inputs, resolved context, evaluator versions, results, skips, failures, suppressions, and generated candidates.
* **Assurance Candidate:** A potential concern supported by referenced evidence and awaiting review or delegated deterministic promotion.
* **Evidence Gap:** A supported finding that required evidence is missing, conflicted, stale, redacted, or unverifiable. It does not imply that the underlying decision was wrong.
* **Policy Candidate:** An advisory suggestion that a policy, rule family, or policy source appears relevant to a decision family and should be confirmed by the customer before authoritative evaluation.
* **Policy Pack:** A versioned starter library of industry-specific policies, evaluator presets, scenario seeds, and review guidance that a customer may adopt, edit, fork, or reject.

## Requirements

### REQ-FP-DES-001: Start Discovery Progressively

**User Story:** As an AI platform owner, I want to begin discovery with the evidence I already have, so that setup produces value before every context system is connected.

**Acceptance Criteria:**

* **AC-FP-DES-001.1:** The platform shall allow an organization to begin discovery with any supported SDK, DEP, API, OTLP, file, or connector source without requiring all source categories.
* **AC-FP-DES-001.2:** After the first valid source is connected, the platform shall show which resource types and decision fields are available, missing, or unmapped.
* **AC-FP-DES-001.3:** The platform shall request a mapping or additional context only when it is required to identify decisions, determine applicability, enable a selected evaluator, or increase evidence sufficiency.
* **AC-FP-DES-001.4:** The setup workflow shall distinguish required corrections from optional enrichment and shall permit the user to continue when only optional enrichment is missing.

### REQ-FP-DES-002: Ingest DEP Resources

**User Story:** As an integration engineer, I want Notary to accept standards-based decision evidence, so that I can reuse evidence from existing systems without a proprietary payload for every source.

**Acceptance Criteria:**

* **AC-FP-DES-002.1:** The platform shall accept DEP resources through supported HTTP, CloudEvents, batch bundle, and OTLP bridge profiles.
* **AC-FP-DES-002.2:** On receipt, the platform shall validate protocol version, schema, stable identity, organization scope, provenance, and integrity metadata where supplied.
* **AC-FP-DES-002.3:** If a resource is invalid, the platform shall reject or quarantine it with a machine-readable error identifying the failed validation.
* **AC-FP-DES-002.4:** Re-delivery of the same resource identifier and digest shall be idempotent; reuse of an identifier with a different digest shall create an integrity conflict.

### REQ-FP-DES-003: Preserve Source Fidelity and Provenance

**User Story:** As an investigator, I want normalized evidence traceable to its source, so that I can distinguish source facts from platform transformations.

**Acceptance Criteria:**

* **AC-FP-DES-003.1:** Every normalized resource shall retain its provider identity, native object identifier, collection time, source reference, epistemic status, and transformation history.
* **AC-FP-DES-003.2:** Normalization shall not silently convert asserted, derived, inferred, missing, or conflicted information into observed information.
* **AC-FP-DES-003.3:** A redacted representation shall have its own digest and explicit relationship to the source representation.
* **AC-FP-DES-003.4:** The platform shall not claim authorship or authority over imported customer or provider context.

### REQ-FP-DES-004: Profile Sources Before Committing Mappings

**User Story:** As an integration engineer, I want to preview what a source contains, so that I can confirm how its records should become decision evidence.

**Acceptance Criteria:**

* **AC-FP-DES-004.1:** The platform shall profile available schemas, timestamps, identifiers, field types, volumes, outcome distributions, and candidate join keys without creating Incidents.
* **AC-FP-DES-004.2:** Proposed identity or field mappings generated by heuristic or model-based methods shall be labeled inferred until confirmed by an authorized user.
* **AC-FP-DES-004.3:** The preview shall show sample records, estimated decision count, unmapped fields, sensitive-field handling, and evaluators the mapping would enable.
* **AC-FP-DES-004.4:** Committing a mapping shall create a versioned configuration; later edits shall not rewrite prior Sweep Runs.

### REQ-FP-DES-005: Build Decision Evidence Records Without Flattening Evidence

**User Story:** As an investigator, I want related evidence assembled around a decision without losing source boundaries, so that the record remains contestable and auditable.

**Acceptance Criteria:**

* **AC-FP-DES-005.1:** The platform shall group or link resources into a DER while retaining each resource as an immutable, independently attributable item.
* **AC-FP-DES-005.2:** Exact source identifiers shall take precedence over inferred similarity when resolving decision identity.
* **AC-FP-DES-005.3:** Ambiguous identity matches shall remain explicit candidate links and shall not be treated as confirmed identity without configured deterministic authority or human confirmation.
* **AC-FP-DES-005.4:** A correction to identity resolution shall supersede the prior link without deleting the original assertion or prior Sweep Run.

### REQ-FP-DES-006: Resolve Decision-Time Context

**User Story:** As a compliance reviewer, I want findings evaluated against the context effective when the decision occurred, so that current policies are not incorrectly applied to historical behavior.

**Acceptance Criteria:**

* **AC-FP-DES-006.1:** Every Context Binding shall identify subject scope, relationship, effective start, optional effective end, selectors, provenance, authority basis, and artifact version or digest.
* **AC-FP-DES-006.2:** The platform shall evaluate applicability at the decision timestamp and shall not use artifact creation time as a substitute for effective time.
* **AC-FP-DES-006.3:** Explicit supersession and configured authority shall control precedence; the newest collected artifact shall not automatically win.
* **AC-FP-DES-006.4:** Equally authoritative applicable artifacts that materially disagree shall produce a context conflict and block authoritative evaluators requiring the conflicted context.
* **AC-FP-DES-006.5:** The candidate view shall show which artifact version was applied and why.

### REQ-FP-DES-007: Enforce Evaluator Prerequisites

**User Story:** As a risk owner, I want checks to run only when their evidence requirements are met, so that missing context does not become a false failure claim.

**Acceptance Criteria:**

* **AC-FP-DES-007.1:** Every enabled evaluator shall have a versioned Evaluator Contract declaring required inputs, minimum evidence level, method class, output type, and authority.
* **AC-FP-DES-007.2:** Before execution, the platform shall compare the frozen DER against the evaluator's prerequisites.
* **AC-FP-DES-007.3:** When prerequisites are unavailable or conflicted, the platform shall record the evaluator as skipped and list exact missing prerequisites rather than infer a result.
* **AC-FP-DES-007.4:** Probabilistic evaluators shall produce advisory assessments unless an authorized review or deterministic rule separately confirms the result.

### REQ-FP-DES-008: Support Certified, Customer, and Third-Party Evaluators

**User Story:** As a customer, I want to evaluate my private business rules while knowing which findings carry platform assurance, so that extensibility does not blur authority.

**Acceptance Criteria:**

* **AC-FP-DES-008.1:** The platform shall distinguish Notary-certified, customer-defined, and third-party evaluator classes.
* **AC-FP-DES-008.2:** Customer-defined and third-party evaluator outputs shall retain author, version, method, and authority labels in every assessment and candidate.
* **AC-FP-DES-008.3:** An uncertified evaluator shall not independently produce a Notary-certified proof claim.
* **AC-FP-DES-008.4:** Certification status changes shall apply prospectively and shall not rewrite historical assessment provenance.

### REQ-FP-DES-009: Provide Initial Assurance Evaluators

**User Story:** As an assurance reviewer, I want focused checks for common decision failures, so that discovery produces actionable candidates rather than generic anomaly scores.

**Acceptance Criteria:**

* **AC-FP-DES-009.1:** The platform shall support evaluator contracts for policy mismatch, expected-outcome mismatch, missing evidence, guardrail violation, consistency mismatch, and replayability failure.
* **AC-FP-DES-009.2:** Policy mismatch shall require an observed decision, applicable structured policy, policy-relevant inputs, and a decision-time binding.
* **AC-FP-DES-009.3:** Consistency mismatch shall require a confirmed cohort definition, comparison fields, normalized outcomes, and allowed-variance rule; similarity alone shall not establish a violation.
* **AC-FP-DES-009.4:** Replayability failure shall identify missing cassette elements, mutable dependencies, unsupported tools, and the capture action needed to improve replayability.

### REQ-FP-DES-010: Calculate Evidence Sufficiency Deterministically

**User Story:** As an auditor, I want evidence strength to have an explainable basis, so that a score cannot conceal what the platform actually possesses.

**Acceptance Criteria:**

* **AC-FP-DES-010.1:** The platform shall calculate `E0` through `E4` from declared resource, relationship, authority, sealing, replay, and verification prerequisites rather than an LLM estimate.
* **AC-FP-DES-010.2:** The platform shall display the current level, its satisfied conditions, and the exact conditions required for the next level.
* **AC-FP-DES-010.3:** Evidence sufficiency shall remain separate from business severity, evaluator confidence, and incident priority.
* **AC-FP-DES-010.4:** A high-severity candidate with weak evidence shall retain its weak evidence level, and a low-severity fully verified finding may reach `E4`.

### REQ-FP-DES-011: Execute Reproducible Sweep Runs

**User Story:** As an AI operations leader, I want discovery runs to be reproducible and auditable, so that I can explain why a candidate appeared.

**Acceptance Criteria:**

* **AC-FP-DES-011.1:** A Sweep Definition shall version source scopes, time window or cursor, mappings, enabled evaluator versions, limits, review policy, and retention policy.
* **AC-FP-DES-011.2:** A Sweep Run shall freeze source cursors, resource digests, resolved context, evaluator versions, parameters, and suppression rules used.
* **AC-FP-DES-011.3:** The run shall record executed, skipped, failed, and suppressed evaluations separately.
* **AC-FP-DES-011.4:** Re-executing the same deterministic manifest shall produce the same assessments, or the platform shall report the source of non-reproducibility.
* **AC-FP-DES-011.5:** Scheduled Sweeps shall operate as bounded background jobs and shall not create a live observability or real-time alerting surface.

### REQ-FP-DES-012: Produce Explainable Assurance Candidates

**User Story:** As a non-technical business reviewer, I want to understand why a decision was flagged, so that I can judge it without interpreting raw traces.

**Acceptance Criteria:**

* **AC-FP-DES-012.1:** Every Assurance Candidate shall identify candidate type, affected decision or family, actual outcome, expected outcome where known, business impact where supplied, supporting resources, applied context, evaluator method, evidence level, and lifecycle state.
* **AC-FP-DES-012.2:** The candidate shall show missing, conflicted, redacted, stale, or unverifiable prerequisites and how each limitation affects available actions.
* **AC-FP-DES-012.3:** Generated summaries shall link back to source evidence and shall not introduce unsupported factual claims.
* **AC-FP-DES-012.4:** Candidate ranking or clustering shall not change the underlying evidence, authority, or individual disposition.

### REQ-FP-DES-013: Review and Correct Candidates

**User Story:** As an authorized reviewer, I want to approve, dismiss, enrich, suppress, accept, or defer candidates, so that business authority remains explicit.

**Acceptance Criteria:**

* **AC-FP-DES-013.1:** An authorized reviewer shall be able to approve as Incident, dismiss with reason, request context, accept risk, create a scoped suppression, or request instrumentation of the next occurrence.
* **AC-FP-DES-013.2:** Review decisions shall be append-only and identify reviewer, role, time, basis, scope, and superseded decision where applicable.
* **AC-FP-DES-013.3:** A dismissal or suppression shall apply only to its declared decision family, conditions, and effective period and shall not hide unrelated candidates.
* **AC-FP-DES-013.4:** Reviewer corrections to mappings or context shall affect subsequent Sweep Runs without rewriting prior run outputs.

### REQ-FP-DES-014: Control Automated Incident Promotion

**User Story:** As a compliance officer, I want automation to promote only findings covered by explicit authority, so that probabilistic signals do not become official incidents silently.

**Acceptance Criteria:**

* **AC-FP-DES-014.1:** By default, a Sweep Run shall create Assurance Candidates and shall not create Incidents automatically.
* **AC-FP-DES-014.2:** An organization may delegate promotion to a versioned deterministic rule that declares candidate type, prerequisites, scope, and effective period.
* **AC-FP-DES-014.3:** Delegated promotion shall be visible, auditable, revocable, and recorded on every Incident it creates.
* **AC-FP-DES-014.4:** Probabilistic assessment alone shall never satisfy delegated promotion authority.

### REQ-FP-DES-015: Bridge Accepted Candidates Into the Proof Loop

**User Story:** As an AI engineer, I want an accepted discovery finding to enter the existing investigation workflow, so that discovery and proof form one continuous lifecycle.

**Acceptance Criteria:**

* **AC-FP-DES-015.1:** On approval, the platform shall create or classify exactly one Incident linked to the candidate, DER, Sweep Run, review decision, and supporting resource digests.
* **AC-FP-DES-015.2:** Before replay, the platform shall report whether the evidence is fully replayable, partially replayable, requires sandbox, not replayable, or missing evidence.
* **AC-FP-DES-015.3:** The existing replay, mutation testing, proof certificate, Scenario promotion, and Release Gate requirements shall apply without a separate discovery-specific execution path.
* **AC-FP-DES-015.4:** When proof prerequisites are missing, the platform shall return the exact missing prerequisite and available enrichment or future-instrumentation action.

### REQ-FP-DES-016: Protect Tenant Data and Learning Boundaries

**User Story:** As a CISO, I want discovery evidence isolated and minimized, so that connecting more context does not create an uncontrolled data pool.

**Acceptance Criteria:**

* **AC-FP-DES-016.1:** Every source, resource, mapping, binding, evaluator, Sweep Definition, Sweep Run, candidate, and review decision shall be scoped to one organization and environment unless an explicit federation policy permits otherwise.
* **AC-FP-DES-016.2:** The platform shall support raw, redacted, hashed, reference-only, and omitted field handling and shall expose the assurance limitations of each choice.
* **AC-FP-DES-016.3:** Customer evidence, mappings, labels, or review decisions shall not be used for cross-customer learning by default.
* **AC-FP-DES-016.4:** Any cross-customer aggregate learning shall require explicit opt-in, de-identification controls, documented purpose, and auditable governance.

### REQ-FP-DES-017: Provide Advisory Discovery Intelligence

**User Story:** As a setup owner, I want Notary to suggest likely policies, missing context, and next integration steps without silently deciding for me, so that onboarding gets smarter without becoming opaque.

**Acceptance Criteria:**

* **AC-FP-DES-017.1:** The platform shall be able to suggest policy candidates, context-source candidates, decision-family link hypotheses, and unlock plans based on observed evidence patterns and confirmed prior mappings.
* **AC-FP-DES-017.2:** Every suggestion shall identify whether it was generated deterministically, heuristically, or with model assistance, and shall remain advisory until confirmed by an authorized user or deterministic rule.
* **AC-FP-DES-017.3:** Suggestions shall cite the supporting source fields, sample records, or prior confirmed mappings that caused them to appear.
* **AC-FP-DES-017.4:** Rejecting or editing a suggestion shall affect subsequent recommendations without rewriting prior Sweep Runs or prior review history.

### REQ-FP-DES-018: Support Industry Policy Packs as Accelerators

**User Story:** As a regulated customer, I want starter policy packs and evaluator presets for my industry, so that I can get to a credible first review faster without surrendering control over what is authoritative.

**Acceptance Criteria:**

* **AC-FP-DES-018.1:** The platform shall support versioned Policy Packs containing starter policies, evaluator presets, scenario seeds, mapping hints, and review guidance for a named domain.
* **AC-FP-DES-018.2:** A customer shall be able to preview, adopt, fork, edit, disable, or reject a Policy Pack independently of other packs.
* **AC-FP-DES-018.3:** A Policy Pack shall be labeled as starter guidance and shall not become authoritative for a customer organization until adopted and confirmed through the organization's own mappings or review workflow.
* **AC-FP-DES-018.4:** Changes to a Policy Pack or a customer's fork shall apply prospectively and shall not rewrite historical candidates, Sweep Runs, or proof artifacts.

## Non-Goals

* Decision Evidence Discovery and Sweep is not a tracing backend, process-mining system, GRC system of record, policy authoring suite, ticketing platform, or real-time operations monitor.
* It does not claim that logs alone establish policy applicability, expected outcomes, fairness, compliance, or correctness.
* It does not automatically certify probabilistic evaluator output or customer-authored rules as Notary-certified truth.
* It does not replay production side effects without the isolation and authorization required by the existing Deterministic Replay requirements.
