# DEP Governance

## Versioning

DEP uses semantic versioning (`MAJOR.MINOR.PATCH`). The current version is `0.1.0`.

- **MAJOR** — breaking changes to required fields or resource structure.
- **MINOR** — new resource types or optional fields.
- **PATCH** — documentation, examples, or fixture corrections.

## Schema evolution

1. A field may be added only as `optional` (not in `required`).
2. An enum may be extended but existing values must not be removed.
3. A required field may become optional, but optional fields must not become required within the same MAJOR version.
4. A schema must never remove a previously required field within the same MAJOR version.
5. New resource types may be added at any MINOR version.

## Extensibility

Implementations may add private fields using a prefixed namespace (e.g. `_vendor_field`). These fields are ignored by standard DEP validators and are not part of the public contract.

## Registry

The canonical DEP schema registry is maintained at `schemas/dep/` in this repository. Implementations should load schemas from their local copy and resolve `$ref` references without network access.
