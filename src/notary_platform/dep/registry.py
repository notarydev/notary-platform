"""DEP schema registry — loads schemas once and resolves ``$ref`` references
locally without network access.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import jsonschema
from jsonschema import RefResolver

from notary_platform.dep.errors import SchemaNotFoundError

_SCHEMA_DIR = Path(__file__).resolve().parents[3] / "schemas" / "dep"
_REF_PATTERN = re.compile(r"dep://schema/([\w-]+)")


class SchemaRegistry:
    """Loads and caches DEP JSON Schemas from a directory.

    Usage::

        registry = SchemaRegistry()
        schema = registry.get_schema("envelope")
        errors = registry.validate(data, "envelope")
    """

    def __init__(self, schema_dir: str | Path | None = None) -> None:
        self._schema_dir = Path(schema_dir) if schema_dir else _SCHEMA_DIR
        self._schemas: dict[str, dict[str, Any]] = {}
        self._resolver: RefResolver | None = None
        self._load_all()

    def _load_all(self) -> None:
        if not self._schema_dir.is_dir():
            raise FileNotFoundError(f"Schema directory not found: {self._schema_dir}")
        for path in sorted(self._schema_dir.glob("*.schema.json")):
            name = path.stem.replace(".schema", "")
            with open(path, "r") as f:
                self._schemas[name] = json.load(f)

    def _build_resolver(self) -> RefResolver:
        store: dict[str, dict[str, Any]] = {}
        for s in self._schemas.values():
            sid = s.get("$id")
            if sid:
                store[sid] = s
        envelope = self._schemas.get("envelope", {})
        return RefResolver.from_schema(envelope, store=store)

    def get_schema(self, name: str) -> dict[str, Any]:
        """Return the parsed schema for *name*, or raise ``SchemaNotFoundError``."""
        schema = self._schemas.get(name)
        if schema is None:
            raise SchemaNotFoundError(f"Schema '{name}' not found in {self._schema_dir}")
        return schema

    def list_schemas(self) -> list[str]:
        """Return sorted list of registered schema names."""
        return sorted(self._schemas.keys())

    def resolve_ref(self, ref: str) -> dict[str, Any]:
        """Resolve a ``$ref`` string like ``dep://schema/envelope`` to the
        actual schema object.  Only ``dep://schema/`` references are supported.
        """
        m = _REF_PATTERN.match(ref)
        if not m:
            raise SchemaNotFoundError(f"Cannot resolve external ref: {ref}")
        return self.get_schema(m.group(1))

    def resolve_all_refs(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Return a copy of *schema* with all local ``dep://schema/`` ``$ref``
        values replaced by their resolved schema objects (inline).
        """
        resolved = _resolve_refs_inner(schema, self)
        return resolved

    def validate(
        self,
        data: dict[str, Any],
        schema_name: str,
    ) -> list[dict[str, Any]]:
        """Validate *data* against the JSON Schema named *schema_name* using
        ``jsonschema``.  Returns a list of error dicts, each with ``code``,
        ``json_pointer``, and ``message``.  An empty list means valid.
        """
        schema = self.get_schema(schema_name)
        resolver = self._build_resolver()
        try:
            jsonschema.validate(data, schema, resolver=resolver)
            return []
        except jsonschema.ValidationError as e:
            return [_map_jsonschema_error(e)]


def _resolve_refs_inner(node: Any, registry: SchemaRegistry) -> Any:
    if isinstance(node, dict):
        if "$ref" in node:
            resolved = registry.resolve_ref(node["$ref"])
            merged = dict(resolved)
            for k, v in node.items():
                if k != "$ref":
                    merged[k] = v
            return _resolve_refs_inner(merged, registry)
        return {k: _resolve_refs_inner(v, registry) for k, v in node.items()}
    if isinstance(node, list):
        return [_resolve_refs_inner(item, registry) for item in node]
    return node


def _map_jsonschema_error(e: jsonschema.ValidationError) -> dict[str, Any]:
    path = "/" + "/".join(str(p) for p in e.absolute_path) if e.absolute_path else ""
    return {
        "code": "schema_validation_error",
        "json_pointer": path,
        "message": e.message,
    }
