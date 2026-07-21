from pathlib import Path

APP_JS = Path("static/app/app.js")
APP_CSS = Path("static/app/styles.css")


def test_platform_app_centers_northstar_golden_path() -> None:
    text = APP_JS.read_text(encoding="utf-8")
    assert "Northstar Air" in text
    assert "From AI failure to release gate" in text
    assert "/v1/demo/northstar/seed" in text
    assert "renderDemo" in text
    assert "ESCALATE_TO_HUMAN" in text


def test_release_gate_detail_surfaces_evidence_refs_and_scenario_results() -> None:
    text = APP_JS.read_text(encoding="utf-8")
    assert "Scenario Results" in text
    assert "Evidence References" in text
    assert "gate.scenario_run_id" in text
    assert "gate.evidence_refs" in text


def test_northstar_golden_path_has_mobile_layout() -> None:
    text = APP_CSS.read_text(encoding="utf-8")
    assert ".golden-path" in text
    assert "@media(max-width:900px)" in text
    assert ".golden-path{grid-template-columns:1fr" in text
