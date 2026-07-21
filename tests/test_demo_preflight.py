from __future__ import annotations

from io import StringIO

from notary_platform.demo_preflight import format_text_report, main, run_harborline_preflight


def test_harborline_preflight_passes_and_reports_demo_anchors() -> None:
    result = run_harborline_preflight()

    assert result["status"] == "pass"
    assert result["summary"]["blocked_gate_status"] == "fail"
    assert result["summary"]["passing_gate_status"] == "pass"
    assert result["summary"]["verification_record_id"]
    assert result["summary"]["readiness_certificate_id"]
    assert all(check["passed"] is True for check in result["checks"])


def test_preflight_text_report_is_presenter_ready() -> None:
    result = run_harborline_preflight()
    report = format_text_report(result)

    assert "Northstar demo preflight: PASS" in report
    assert "Verification Record:" in report
    assert "Blocked Gate:" in report
    assert "Passing Gate:" in report
    assert "Claim scope:" in report

    # Verify the report references Northstar data, not Harborline.
    assert "Harborline demo preflight" not in report


def test_preflight_cli_json_mode_returns_success() -> None:
    out = StringIO()

    assert main(["--json"], stdout=out) == 0
    assert '"status": "pass"' in out.getvalue()
