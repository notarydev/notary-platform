"""CI helper for Notary release gate result JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence, TextIO

PASS_EXIT_CODE = 0
FAIL_EXIT_CODE = 1
ERROR_EXIT_CODE = 2


def exit_code_for_result(result: dict[str, Any]) -> int:
    status = result.get("status")
    if status == "pass":
        return PASS_EXIT_CODE
    if status == "fail":
        return FAIL_EXIT_CODE
    return ERROR_EXIT_CODE


def load_result(path: str, stdin: TextIO) -> dict[str, Any]:
    raw = stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    loaded = json.loads(raw)
    if not isinstance(loaded, dict):
        raise ValueError("release gate result must be a JSON object")
    return loaded


def format_summary(result: dict[str, Any]) -> str:
    summary = {
        "status": result.get("status", "error"),
        "release_gate_result_id": result.get("id", ""),
        "readiness_check_id": result.get("readiness_check_id", ""),
        "scenario_run_id": result.get("scenario_run_id", ""),
        "failing_scenarios": result.get("failing_scenarios", []),
        "errored_scenarios": result.get("errored_scenarios", []),
        "error_code": result.get("error_code", ""),
        "evidence_refs": result.get("evidence_refs", []),
    }
    return json.dumps(summary, sort_keys=True)


def main(argv: Sequence[str] | None = None, stdin: TextIO | None = None, stdout: TextIO | None = None, stderr: TextIO | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate a Notary release gate result JSON for CI.")
    parser.add_argument("result_json", help="Path to release gate result JSON, or '-' for stdin.")
    args = parser.parse_args(argv)

    input_stream = stdin if stdin is not None else sys.stdin
    output_stream = stdout if stdout is not None else sys.stdout
    error_stream = stderr if stderr is not None else sys.stderr

    try:
        result = load_result(args.result_json, input_stream)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error_code": "invalid_release_gate_result", "message": str(exc)}, sort_keys=True), file=error_stream)
        return ERROR_EXIT_CODE

    print(format_summary(result), file=output_stream)
    return exit_code_for_result(result)


if __name__ == "__main__":
    raise SystemExit(main())
