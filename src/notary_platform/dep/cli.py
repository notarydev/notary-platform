"""Standalone DEP validation CLI.

Usage::

    python -m notary_platform.dep.cli validate <file>
    python -m notary_platform.dep.cli digest <file>
    python -m notary_platform.dep.cli schema list
"""

from __future__ import annotations

import json
import sys

from notary_platform.dep.canonical import compute_digest
from notary_platform.dep.registry import SchemaRegistry
from notary_platform.dep.validation import validate_envelope


def _load_json(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def cmd_validate(args: list[str]) -> int:
    if not args:
        print("Usage: dep validate <file> [<file> ...]", file=sys.stderr)
        return 2
    registry = SchemaRegistry()
    exit_code = 0
    for path in args:
        try:
            data = _load_json(path)
        except Exception as exc:
            print(f"{path}: failed to load: {exc}", file=sys.stderr)
            exit_code = 2
            continue
        result = validate_envelope(data, registry)
        if result.valid:
            print(f"{path}: VALID")
        else:
            print(f"{path}: INVALID", file=sys.stderr)
            for err in result.errors:
                d = err.to_dict()
                print(f"  [{d['code']}] {d['message']}", file=sys.stderr)
            exit_code = 1
    return exit_code


def cmd_digest(args: list[str]) -> int:
    if not args:
        print("Usage: dep digest <file>", file=sys.stderr)
        return 2
    for path in args:
        try:
            data = _load_json(path)
        except Exception as exc:
            print(f"{path}: failed to load: {exc}", file=sys.stderr)
            return 2
        digest = compute_digest(data)
        print(digest)
    return 0


def cmd_schema(args: list[str]) -> int:
    sub = args[0] if args else ""
    if sub == "list":
        registry = SchemaRegistry()
        for name in registry.list_schemas():
            print(name)
        return 0
    print("Usage: dep schema list", file=sys.stderr)
    return 2


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: dep <command> [args...]", file=sys.stderr)
        print("Commands: validate, digest, schema", file=sys.stderr)
        return 2

    command = sys.argv[1]
    rest = sys.argv[2:]

    if command == "validate":
        return cmd_validate(rest)
    elif command == "digest":
        return cmd_digest(rest)
    elif command == "schema":
        return cmd_schema(rest)
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
