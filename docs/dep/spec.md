# DEP Specification v0.1

## 1. Motivation

AI systems make decisions that affect users, customers, and regulated outcomes. When something goes wrong — a harmful response, a policy violation, a compliance failure — investigators need trusted evidence of what happened, under what context, and whether corrective action works. Existing observability tools capture logs but not verifiable provenance. DEP defines a portable, verifiable evidence format.

## 2. Protocol overview

Every unit of evidence is packaged in a **DEP Envelope** that carries:

- The resource payload
- Provenance metadata (collection time, source)
- A content digest
- Optional signature

Resources are typed. The initial types are:

| Resource type | Purpose |
|---|---|
| observation | An atomic event or trace element |
| context-artifact | A document, policy, or configuration |
| context-binding | Links a decision to applicable context |
| assessment | An evaluator result |
| finding | A specific issue discovered |
| link-assertion | A declared relationship |
| integrity-conflict | A digest mismatch record |
| evidence-bundle | A group of related resources |
| proof-claim | A signed verification claim |
| redaction-log | Redaction history |
| provider-registration | Provider metadata |
| resource-index | Source inventory |

## 3. Envelope format

```json
{
  "$schema": "dep://schema/envelope",
  "id": "dep://example/envelope/abc123",
  "version": "0.1.0",
  "resource": {
    "type": "observation",
    "id": "obs-001",
    "provider_id": "provider-x"
  },
  "provenance": {
    "collected_at": "2026-07-01T12:00:00Z"
  },
  "digest": {
    "algorithm": "sha256",
    "value": "u-ndJZg6QmB8Z5yq4Hm8Xw=="
  }
}
```

## 4. Canonical JSON

Canonical JSON is used for digest computation and signature verification. The canonical form:

1. Serialize with sorted keys at every nesting level.
2. No whitespace between tokens.
3. UTF-8 encoding.
4. Use `json.dumps(data, sort_keys=True, separators=(",", ":"))`.

## 5. Digest computation

1. Compute canonical JSON of the envelope (excluding the digest field).
2. Compute the hash using the declared algorithm.
3. Encode as base64url (RFC 4648 §5, no padding).
4. Format: `{algorithm}:{base64url_hash}`.

## 6. Evidence levels

DEP defines five evidence levels for decision records:

| Level | Requirements |
|---|---|
| E0 | At least one attributable observation |
| E1 | E0 + applicable context binding, no identity ambiguity |
| E2 | E1 + authoritative or independently corroborated context |
| E3 | E2 + integrity-verified sealed evidence |
| E4 | E3 + reproduced outcome and verified fix |

## 7. Extension points

- Custom resource types via the `resource.type` field.
- Private implementation fields with underscore prefix.
- Additional digest algorithms beyond sha256/sha512.
