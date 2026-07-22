# Decision Evidence Protocol Governance

**Status:** Public draft
**Applies to:** DEP specifications, schemas, namespaces, examples, conformance fixtures, and reference verifier behavior

## Purpose

DEP governance exists to keep the protocol implementation-neutral, interoperable, secure, and usable by parties that do not share a vendor. Governance controls the public protocol boundary. It does not govern proprietary processors, evaluators, ranking methods, user interfaces, or hosted services.

## Principles

- Decisions are made in public from written proposals and recorded rationale.
- Protocol changes solve interoperability problems demonstrated by at least one use case.
- No implementation receives privileged semantics or a reserved path to conformance.
- Compatibility, evidence honesty, privacy, and independent verification take precedence over implementation convenience.
- Conformance tests describe observable behavior and do not require disclosure of proprietary internals.

## Change Process

Substantive changes use a Decision Evidence Protocol Proposal (DEPP). A proposal includes:

1. problem statement and affected participants;
2. proposed normative language;
3. schema and namespace impact;
4. security, privacy, and trust analysis;
5. compatibility and migration plan;
6. examples and conformance fixtures;
7. rejected alternatives.

A proposal moves through `draft`, `review`, `accepted`, `implemented`, and `released`. Editorial corrections that do not alter observable behavior may be merged without a DEPP but must remain visible in history.

## Decision Authority

Before an independent foundation or standards body is established, maintainers act as stewards. Acceptance requires public review, passing schema and conformance checks, and agreement from at least two maintainers who do not represent the same implementing organization when such maintainers exist.

Changes that alter trust semantics, authority, epistemic status, integrity, redaction, or verification scope require a documented security review. A maintainer with a direct commercial conflict discloses it and does not act as the sole approver.

The transition target is a multi-stakeholder technical steering group representing at least three of these constituencies: evidence producers, assurance processors, independent verifiers, enterprise adopters, researchers, auditors, or public-interest experts.

## Versioning

DEP uses semantic versioning for the protocol package.

- Patch releases clarify text and fix schemas without changing valid meaning.
- Minor releases add backward-compatible resource types, optional fields, relationships, or profiles.
- Major releases may remove or change semantics and must publish migration guidance.

Every resource identifies its schema version. Once published in a stable release, a schema version is immutable. Corrections that change validation behavior create a new schema identifier.

Draft versions may change incompatibly. Release candidates freeze namespaces and begin a defined compatibility window before version 1.0.

## Compatibility

Consumers must ignore unknown optional fields unless a profile says otherwise. Producers must not reuse identifiers with different content. Extensions use URI-qualified names and must not redefine core semantics.

Deprecation requires a replacement path and at least one minor-version notice period. Stable resources remain verifiable after their transport or profile is deprecated.

## Namespaces

Core event types use `org.dep.*`. Core schema identifiers use the canonical DEP schema namespace. Unregistered extensions use a namespace controlled by their publisher.

Registration of a core resource, relationship, epistemic status, or conformance profile requires an accepted DEPP. Vendor-specific concepts are not admitted to the core namespace solely to simplify one implementation.

## Conformance

Conformance is profile-based. An implementation claims only the Provider, Processor, Evaluator, Custodian, Verifier, or Full-chain profiles it passes.

A conforming release publishes:

- protocol and schema version tested;
- supported profiles and transports;
- conformance-suite result;
- known deviations or extensions;
- security contact.

Certification, if introduced, must be available on equal terms and must test published behavior. Self-attestation remains distinguishable from third-party certification.

## Security Disclosures

Security reports affecting unpublished vulnerabilities use a private coordinated-disclosure channel. Maintainers acknowledge reports, assess affected versions, coordinate fixes, and publish an advisory after remediation or at the end of the agreed disclosure period.

Security fixes may use an expedited process, but normative changes still receive a public rationale and versioned release after the immediate risk is contained.

## Intellectual Property

Specifications, schemas, examples, and conformance fixtures should be published under licenses that permit implementation, redistribution, and derivative interoperability work. Contributions require a developer certificate of origin or equivalent contribution attestation.

DEP conformance does not grant rights to third-party trademarks, patents, models, data, or proprietary evaluator content. Contributors disclose known essential patent claims associated with a proposal.

## Reference Implementations

Reference validators and verifiers demonstrate interoperability; they do not define the protocol. When code and specification disagree, the released normative specification and schemas control until the discrepancy is corrected through the change process.

No hosted service is the exclusive conformance oracle. Fixtures and verification behavior must be runnable independently.
