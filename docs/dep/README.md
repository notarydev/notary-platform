# Decision Evidence Protocol (DEP) v0.1

A vendor-neutral specification for packaging, verifying, and linking evidence of AI system decisions.

DEP enables:

- **Immutable evidence capture** — every observation, context artifact, and assessment is enveloped with provenance and digest.
- **Deterministic verification** — canonical JSON and digest computation are defined once and used by all implementations.
- **Context linking** — decisions are evaluated against the policies, configurations, and expected outcomes applicable at decision time.
- **Auditable assessment** — evaluator results and findings are preserved with full provenance, not overwritten.

## Repository structure

- `schemas/dep/` — JSON Schema definitions for all DEP resource types.
- `docs/dep/` — Specification, whitepaper, and governance.
- `src/notary_platform/dep/` — Reference implementation: schema registry, canonical JSON, validation, and CLI.

## Quick start

```bash
# Validate a DEP envelope
dep validate path/to/envelope.json

# Compute canonical digest
dep digest path/to/envelope.json

# List registered schemas
dep schema list
```

## License

Apache 2.0
