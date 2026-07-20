import io
import json

from notary_platform.release_gate_cli import ERROR_EXIT_CODE, FAIL_EXIT_CODE, PASS_EXIT_CODE, exit_code_for_result, main


def test_exit_code_for_pass_fail_and_error_results() -> None:
    assert exit_code_for_result({"status": "pass"}) == PASS_EXIT_CODE
    assert exit_code_for_result({"status": "fail"}) == FAIL_EXIT_CODE
    assert exit_code_for_result({"status": "error"}) == ERROR_EXIT_CODE
    assert exit_code_for_result({"status": "not_started"}) == ERROR_EXIT_CODE
    assert exit_code_for_result({}) == ERROR_EXIT_CODE


def test_main_returns_zero_for_pass_result_from_stdin() -> None:
    stdout = io.StringIO()
    result = {
        "id": "rg-pass",
        "status": "pass",
        "readiness_check_id": "rc-1",
        "scenario_run_id": "sr-1",
        "evidence_refs": ["readiness_check:rc-1", "scenario_run:sr-1", "certificate:cert-1"],
    }

    code = main(["-"], stdin=io.StringIO(json.dumps(result)), stdout=stdout, stderr=io.StringIO())

    assert code == PASS_EXIT_CODE
    summary = json.loads(stdout.getvalue())
    assert summary["status"] == "pass"
    assert summary["release_gate_result_id"] == "rg-pass"
    assert summary["scenario_run_id"] == "sr-1"
    assert summary["evidence_refs"] == ["readiness_check:rc-1", "scenario_run:sr-1", "certificate:cert-1"]


def test_main_returns_one_for_fail_result_from_file(tmp_path) -> None:
    result_path = tmp_path / "release-gate.json"
    result_path.write_text(
        json.dumps(
            {
                "id": "rg-fail",
                "status": "fail",
                "failing_scenarios": ["scenario-a"],
                "errored_scenarios": [],
                "evidence_refs": ["scenario:scenario-a"],
            }
        ),
        encoding="utf-8",
    )
    stdout = io.StringIO()

    code = main([str(result_path)], stdin=io.StringIO(), stdout=stdout, stderr=io.StringIO())

    assert code == FAIL_EXIT_CODE
    summary = json.loads(stdout.getvalue())
    assert summary["status"] == "fail"
    assert summary["failing_scenarios"] == ["scenario-a"]
    assert summary["evidence_refs"] == ["scenario:scenario-a"]


def test_main_returns_two_for_error_result() -> None:
    stdout = io.StringIO()
    result = {"id": "rg-error", "status": "error", "error_code": "readiness_check_failed"}

    code = main(["-"], stdin=io.StringIO(json.dumps(result)), stdout=stdout, stderr=io.StringIO())

    assert code == ERROR_EXIT_CODE
    assert json.loads(stdout.getvalue())["error_code"] == "readiness_check_failed"


def test_main_returns_two_for_malformed_json() -> None:
    stderr = io.StringIO()

    code = main(["-"], stdin=io.StringIO("{not json"), stdout=io.StringIO(), stderr=stderr)

    assert code == ERROR_EXIT_CODE
    error = json.loads(stderr.getvalue())
    assert error["status"] == "error"
    assert error["error_code"] == "invalid_release_gate_result"
