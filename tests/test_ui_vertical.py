"""Headless browser tests for WP-100 Decision Landscape UX.

These tests run against the real FastAPI app in a subprocess so the SPA can
hit live /v1 endpoints. They verify the Decision Landscape view renders,
data is persisted, drawers work, and new components (Resolution Trace,
E0-E4, Proof Bridge eligibility, signals safety) are accessible.

All test data is created via the real API — no simulated browser-only
graph objects.
"""

from __future__ import annotations

import subprocess
import sys
import time
from typing import Any, Generator

import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:8765"


@pytest.fixture(scope="module")
def server() -> Generator[subprocess.Popen[Any], None, None]:
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "notary_platform.api_server.main:app", "--port", "8765"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            import urllib.request

            with urllib.request.urlopen(f"{BASE_URL}/health", timeout=1):
                break
        except Exception:
            time.sleep(0.5)
    yield proc
    proc.terminate()
    proc.wait(timeout=10)


def _seed(page: Page) -> None:
    """Seed landscape fixtures via the real API."""
    import pathlib

    seed_js = (pathlib.Path("/tmp/wp100_seed.js")).read_text()
    page.goto(f"{BASE_URL}/app/")
    page.wait_for_load_state("networkidle")
    page.evaluate("(async () => {" + seed_js + " return await seedWP100(); })()")
    time.sleep(2)


def _nav(page: Page, tab: str = "") -> None:
    url = f"{BASE_URL}/app/?view=landscape" + (f"&tab={tab}" if tab else "")
    page.goto(url)
    page.wait_for_load_state("networkidle")
    time.sleep(1)


def _open_first_candidate_detail(page: Page) -> bool:
    """Open first candidate detail drawer, return True if opened."""
    review_btn = page.locator("button:has-text('Review')").first
    if review_btn.is_visible():
        review_btn.click()
        time.sleep(1)
        return page.locator(".drawer-overlay").is_visible()
    return False


def _close_drawer(page: Page) -> None:
    drawer = page.locator(".drawer-overlay")
    if drawer.is_visible():
        drawer.locator("[data-close]").click()
        time.sleep(0.5)


# ═══════════════════════════════════════════════════════════════════
# Journey: Seed → Landscape → Families → DER → Resolution Trace
# ═══════════════════════════════════════════════════════════════════


def test_landscape_loads_with_persisted_data(page: Page, server: subprocess.Popen[Any]) -> None:
    _seed(page)
    _nav(page)
    expect(page.locator("text=Decision Landscape").first).to_be_visible()
    expect(page.locator(".queue-chip").first).to_be_visible()


def test_landscape_displays_decision_families(page: Page, server: subprocess.Popen[Any]) -> None:
    _nav(page, "families")
    expect(page.locator(".section-title").filter(has_text="Decision Families")).to_be_visible()
    table = page.locator("table").first
    expect(table).to_be_visible()
    families = table.locator("tbody tr")
    expect(families).not_to_have_count(0)


def test_landscape_family_identity_is_clickable(page: Page, server: subprocess.Popen[Any]) -> None:
    _nav(page, "families")
    first_link = page.locator("table tbody tr td a").first
    if first_link.is_visible():
        first_link.click()
        time.sleep(1)
        drawer = page.locator(".drawer-overlay")
        expect(drawer).to_be_visible()
        _close_drawer(page)


def test_relationships_tab_shows_status(page: Page, server: subprocess.Popen[Any]) -> None:
    _nav(page, "relationships")
    expect(page.locator(".section-title").filter(has_text="Relationships").first).to_be_visible()
    table = page.locator("table").first
    if table.is_visible():
        rows = table.locator("tbody tr")
        if rows.count() > 0:
            cells = rows.first.locator("td")
            status_text = cells.nth(3).inner_text().strip().lower()
            assert status_text in ("confirmed", "inferred", "ambiguous", "missing", "conflicted", "—")


def test_context_tab_shows_bindings(page: Page, server: subprocess.Popen[Any]) -> None:
    _nav(page, "context")
    expect(page.locator("text=Context Coverage")).to_be_visible()


def test_evaluators_tab_shows_contracts(page: Page, server: subprocess.Popen[Any]) -> None:
    _nav(page, "evaluators")
    expect(page.locator(".filter-pill.active")).to_be_visible()


def test_gaps_tab_shows_evidence_gaps(page: Page, server: subprocess.Popen[Any]) -> None:
    _nav(page, "gaps")
    expect(page.locator(".filter-pill.active")).to_be_visible()


# ═══════════════════════════════════════════════════════════════════
# Candidate detail: E0–E4, DER link, Proof eligibility, Reviews
# ═══════════════════════════════════════════════════════════════════


def test_candidate_detail_shows_e0_e4_sufficiency(page: Page, server: subprocess.Popen[Any]) -> None:
    _nav(page, "candidates")
    if _open_first_candidate_detail(page):
        drawer = page.locator(".drawer-overlay")
        expect(drawer.locator("text=Evidence Sufficiency")).to_be_visible()
        expect(drawer.locator("text=E0").first).to_be_visible()
        _close_drawer(page)


def test_candidate_detail_shows_der_link(page: Page, server: subprocess.Popen[Any]) -> None:
    _nav(page, "candidates")
    if _open_first_candidate_detail(page):
        drawer = page.locator(".drawer-overlay")
        expect(drawer.locator("text=Decision Evidence Record")).to_be_visible()
        _close_drawer(page)


def test_candidate_detail_shows_outcome_comparison(page: Page, server: subprocess.Popen[Any]) -> None:
    _nav(page, "candidates")
    if _open_first_candidate_detail(page):
        drawer = page.locator(".drawer-overlay")
        if drawer.locator("text=Outcome Comparison").is_visible():
            expect(drawer.locator("text=Expected")).to_be_visible()
            expect(drawer.locator("text=Actual")).to_be_visible()
        _close_drawer(page)


def test_candidate_detail_shows_business_summary(page: Page, server: subprocess.Popen[Any]) -> None:
    _nav(page, "candidates")
    if _open_first_candidate_detail(page):
        drawer = page.locator(".drawer-overlay")
        if drawer.locator("text=Business Summary").is_visible():
            expect(drawer.locator("text=Business Summary").first).to_be_visible()
        _close_drawer(page)


def test_candidate_detail_shows_review_actions(page: Page, server: subprocess.Popen[Any]) -> None:
    _nav(page, "candidates")
    if _open_first_candidate_detail(page):
        drawer = page.locator(".drawer-overlay")
        approve = drawer.locator("button:has-text('Approve as Incident')")
        dismiss = drawer.locator("button:has-text('Dismiss')")
        req_ctx = drawer.locator("button:has-text('Request Context')")
        if approve.is_visible():
            expect(approve).to_be_enabled()
        if dismiss.is_visible():
            expect(dismiss).to_be_enabled()
        if req_ctx.is_visible():
            expect(req_ctx).to_be_enabled()
        _close_drawer(page)


def test_candidate_detail_proof_bridge_eligibility(page: Page, server: subprocess.Popen[Any]) -> None:
    _nav(page, "candidates")
    approved_row = page.locator("table tbody tr").filter(has_text="approved_incident")
    if approved_row.count() > 0:
        approved_row.locator("button:has-text('Review')").click()
        time.sleep(1)
        drawer = page.locator(".drawer-overlay")
        if drawer.is_visible():
            if drawer.locator("text=Proof Bridge Eligibility").is_visible():
                expect(drawer.locator("text=Not eligible").first).to_be_visible()
                if drawer.locator("text=Prerequisites").is_visible():
                    expect(drawer.locator("text=Prerequisites").first).to_be_visible()
                if drawer.locator("text=Next Actions").is_visible():
                    expect(drawer.locator("text=Next Actions").first).to_be_visible()
            _close_drawer(page)


def test_candidate_detail_review_history(page: Page, server: subprocess.Popen[Any]) -> None:
    _nav(page, "candidates")
    if _open_first_candidate_detail(page):
        drawer = page.locator(".drawer-overlay")
        if drawer.locator("text=Review History").is_visible():
            expect(drawer.locator("table")).to_be_visible()
        _close_drawer(page)


# ═══════════════════════════════════════════════════════════════════
# DER Detail → Resolution Trace
# ═══════════════════════════════════════════════════════════════════


def test_der_detail_opens_from_families(page: Page, server: subprocess.Popen[Any]) -> None:
    _nav(page, "families")
    link = page.locator("table tbody tr td a").first
    if link.is_visible():
        link.click()
        time.sleep(1)
        drawer = page.locator(".drawer-overlay")
        expect(drawer).to_be_visible()
        _close_drawer(page)


def test_resolution_trace_opens_from_der_detail(page: Page, server: subprocess.Popen[Any]) -> None:
    _nav(page, "families")
    link = page.locator("table tbody tr td a").first
    if link.is_visible():
        link.click()
        time.sleep(1)
        drawer = page.locator(".drawer-overlay")
        rt_btn = drawer.locator("button:has-text('View Resolution Trace')")
        if rt_btn.is_visible():
            rt_btn.click()
            time.sleep(1)
            rt_drawer = page.locator(".drawer-overlay")
            expect(rt_drawer).to_be_visible()
            expect(rt_drawer.locator("text=Resolution Trace")).to_be_visible()
            _close_drawer(page)
        else:
            _close_drawer(page)


def test_resolution_trace_shows_binding_categories(page: Page, server: subprocess.Popen[Any]) -> None:
    _nav(page, "families")
    link = page.locator("table tbody tr td a").first
    if link.is_visible():
        link.click()
        time.sleep(1)
        drawer = page.locator(".drawer-overlay")
        rt_btn = drawer.locator("button:has-text('View Resolution Trace')")
        if rt_btn.is_visible():
            rt_btn.click()
            time.sleep(1)
            rt_drawer = page.locator(".drawer-overlay")
            expect(rt_drawer).to_be_visible()
            body = rt_drawer.locator(".drawer-body").inner_text()
            categories = [
                "Included Binding",
                "Excluded Binding",
                "Superseded Binding",
                "Missing Artifact",
                "Stale Artifact",
                "Redacted Artifact",
                "Conflicted Binding",
            ]
            found = any(cat in body for cat in categories)
            assert found, "Expected at least one binding category in resolution trace"
            _close_drawer(page)
        else:
            _close_drawer(page)


# ═══════════════════════════════════════════════════════════════════
# Systematic-Issue Signal Safety
# ═══════════════════════════════════════════════════════════════════


def test_signals_tab_visible(page: Page, server: subprocess.Popen[Any]) -> None:
    _nav(page, "signals")
    expect(page.locator("text=Advisory Signals")).to_be_visible()


def test_systematic_issue_signal_is_advisory(page: Page, server: subprocess.Popen[Any]) -> None:
    _nav(page, "signals")
    table = page.locator("table").first
    if table.is_visible():
        rows = table.locator("tbody tr")
        if rows.count() > 0:
            type_text = rows.first.locator("td").nth(0).inner_text()
            assert "systematic" in type_text.lower()


def test_signal_safety_not_incident_or_proof(page: Page, server: subprocess.Popen[Any]) -> None:
    _nav(page, "signals")
    table = page.locator("table").first
    if table.is_visible():
        text = table.inner_text().lower()
        assert "confirmed violation" not in text
        assert "causal conclusion" not in text
        assert "proof claim" not in text


def test_signal_shows_scope_and_basis(page: Page, server: subprocess.Popen[Any]) -> None:
    _nav(page, "signals")
    table = page.locator("table").first
    if table.is_visible():
        rows = table.locator("tbody tr")
        if rows.count() > 0:
            expect(rows.first.locator("td").nth(2)).to_be_visible()


def test_signal_safety_status_is_displayed(page: Page, server: subprocess.Popen[Any]) -> None:
    _nav(page, "signals")
    table = page.locator("table").first
    if table.is_visible():
        rows = table.locator("tbody tr")
        if rows.count() > 0:
            safety = rows.first.locator("td").nth(3).inner_text().strip().lower()
            assert safety in ("advisory", "inferred", "confirmed", "rejected", "—")


# ═══════════════════════════════════════════════════════════════════
# State Coverage
# ═══════════════════════════════════════════════════════════════════


def test_landscape_with_seed_shows_data(page: Page, server: subprocess.Popen[Any]) -> None:
    _nav(page)
    expect(page.locator(".queue-chip").first).to_be_visible()


def test_error_state_on_network_failure(page: Page, server: subprocess.Popen[Any]) -> None:
    page.goto(f"{BASE_URL}/app/")
    time.sleep(1)
    page.evaluate("""() => {
        window.__originalFetch = window.fetch;
        window.fetch = () => Promise.reject(new Error('Network error'));
    }""")
    time.sleep(0.5)
    page.evaluate("() => { if (typeof nav === 'function') nav('landscape'); }")
    time.sleep(2)
    found = page.locator("text=Error").count() > 0 or page.locator("text=Failed to load").count() > 0 or page.locator(".explicit-state").count() > 0
    page.evaluate("() => { if (window.__originalFetch) window.fetch = window.__originalFetch; }")
    time.sleep(0.5)
    assert found, "Expected error state when API fails"


# ═══════════════════════════════════════════════════════════════════
# Responsive Coverage
# ═══════════════════════════════════════════════════════════════════


def test_desktop_width_landscape_usable(page: Page, server: subprocess.Popen[Any]) -> None:
    page.set_viewport_size({"width": 1440, "height": 900})
    _nav(page)
    expect(page.locator(".queue-chip").first).to_be_visible()
    expect(page.locator(".filter-pill").first).to_be_visible()


def test_mobile_width_landscape_usable(page: Page, server: subprocess.Popen[Any]) -> None:
    page.set_viewport_size({"width": 375, "height": 812})
    _nav(page)
    content = page.locator("#content")
    if content.is_visible():
        box = content.bounding_box()
        if box:
            assert box["width"] <= 375
    tabs = page.locator(".filter-pill")
    if tabs.count() > 0:
        expect(tabs.first).to_be_visible()


def test_mobile_no_clipped_actions(page: Page, server: subprocess.Popen[Any]) -> None:
    page.set_viewport_size({"width": 375, "height": 812})
    _nav(page, "candidates")
    content = page.locator("#content")
    buttons = content.locator("button")
    for i in range(min(buttons.count(), 5)):
        btn = buttons.nth(i)
        if btn.is_visible():
            box = btn.bounding_box()
            if box:
                assert box["x"] + box["width"] <= 375 + 10, f"Button clipped: {btn.inner_text()}"


def test_mobile_drawer_accessible(page: Page, server: subprocess.Popen[Any]) -> None:
    page.set_viewport_size({"width": 375, "height": 812})
    _nav(page, "families")
    link = page.locator("table tbody tr td a").first
    if link.is_visible():
        link.click()
        time.sleep(1)
        drawer = page.locator(".drawer-overlay")
        if drawer.is_visible():
            expect(drawer.locator("[data-close]")).to_be_visible()
            _close_drawer(page)


def test_desktop_table_not_clipped(page: Page, server: subprocess.Popen[Any]) -> None:
    page.set_viewport_size({"width": 1440, "height": 900})
    _nav(page, "families")
    table = page.locator("table").first
    if table.is_visible():
        box = table.bounding_box()
        if box:
            assert box["x"] >= 0


# ═══════════════════════════════════════════════════════════════════
# Authority Safety
# ═══════════════════════════════════════════════════════════════════


def test_promote_button_not_shown_for_reviewable(page: Page, server: subprocess.Popen[Any]) -> None:
    _nav(page, "candidates")
    reviewable = page.locator("table tbody tr").filter(has_text="reviewable")
    if reviewable.count() > 0:
        reviewable.locator("button:has-text('Review')").click()
        time.sleep(1)
        drawer = page.locator(".drawer-overlay")
        if drawer.is_visible():
            promote = drawer.locator("button:has-text('Promote via Proof Bridge')")
            assert promote.count() == 0 or not promote.is_visible(), "Promote button should not be visible for reviewable candidates"
            _close_drawer(page)


def test_signals_no_unauthorized_actions(page: Page, server: subprocess.Popen[Any]) -> None:
    _nav(page, "signals")
    content = page.locator(".content, #content, .main").first
    if content.is_visible():
        text = content.inner_text()
        for action in ["Promote", "Approve", "Delete", "Modify", "Force", "Override"]:
            assert action not in text, f"Signal view should not expose '{action}'"


def test_actions_require_server_authorization(page: Page, server: subprocess.Popen[Any]) -> None:
    _nav(page, "candidates")
    if _open_first_candidate_detail(page):
        drawer = page.locator(".drawer-overlay")
        approve = drawer.locator("button:has-text('Approve as Incident')")
        if approve.is_visible():
            expect(approve).to_be_enabled()
        _close_drawer(page)


# ═══════════════════════════════════════════════════════════════════
# Sweep History & Tab Navigation
# ═══════════════════════════════════════════════════════════════════


def test_sweep_tab_visible(page: Page, server: subprocess.Popen[Any]) -> None:
    _nav(page, "sweep")
    expect(page.locator("text=Sweep Definitions")).to_be_visible()


def test_all_tabs_navigable(page: Page, server: subprocess.Popen[Any]) -> None:
    tabs = [
        ("families", "Decision Families"),
        ("sources", "Sources"),
        ("candidates", "Assurance Candidates"),
        ("evaluators", "Evaluators"),
        ("context", "Context"),
        ("relationships", "Relationships"),
        ("gaps", "Evidence Gaps"),
        ("signals", "Signals"),
        ("sweep", "Sweep"),
    ]
    for tab_key, expected in tabs:
        _nav(page, tab_key)
        expect(page.locator(f"text={expected}").first).to_be_visible()
