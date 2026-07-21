from pathlib import Path

APP_JS = Path("static/app/app.js")
APP_CSS = Path("static/app/styles.css")


def test_platform_app_centers_harborline_golden_path() -> None:
    text = APP_JS.read_text(encoding="utf-8")
    assert "Meridian Credit Union" in text
    assert "Release Gate golden path" in text
    assert "/v1/demo/harborline-release-gate/seed" in text
    assert "Blocked Gate" in text
    assert "Passing Gate" in text


def test_release_gate_detail_surfaces_evidence_refs_and_scenario_results() -> None:
    text = APP_JS.read_text(encoding="utf-8")
    assert "Scenario Results" in text
    assert "Evidence References" in text
    assert "gate.scenario_run_id" in text
    assert "gate.evidence_refs" in text


def test_harborline_golden_path_has_mobile_layout() -> None:
    text = APP_CSS.read_text(encoding="utf-8")
    assert ".golden-path" in text
    assert "@media(max-width:900px)" in text
    assert ".golden-path{grid-template-columns:1fr" in text
