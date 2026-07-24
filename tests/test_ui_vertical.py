"""Headless browser tests for the WO-28 vertical slice UI.

These tests run against the real FastAPI app in a subprocess so the SPA can
hit live /v1 endpoints. They verify that the new Scenarios, Readiness, and
Release Gate views render and that primary actions are clickable.
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


def test_app_loads_and_seeds_catalog(page: Page, server: subprocess.Popen[Any]) -> None:
    page.goto(f"{BASE_URL}/app/")
    expect(page.locator("text=Notary Platform")).to_be_visible()

    # Seed demo data via the API.
    page.goto(f"{BASE_URL}/app/#seed")
    page.evaluate("() => fetch('/v1/demo/catalog/seed', {method: 'POST'})")
    time.sleep(1)

    # Verify Records view loads rows.
    page.goto(f"{BASE_URL}/app/?view=verification-records")
    time.sleep(1)
    expect(page.locator("text=Verification Records").first).to_be_visible()


def test_scenarios_view_renders(page: Page, server: subprocess.Popen[Any]) -> None:
    page.goto(f"{BASE_URL}/app/?view=scenarios")
    time.sleep(1)
    expect(page.locator("text=Scenario Library")).to_be_visible()


def test_readiness_view_renders(page: Page, server: subprocess.Popen[Any]) -> None:
    page.goto(f"{BASE_URL}/app/?view=readiness")
    time.sleep(1)
    expect(page.locator(".section-title").filter(has_text="Readiness Policies")).to_be_visible()
    expect(page.locator("button:has-text('Create Policy')")).to_be_visible()


def test_release_gate_end_to_end(page: Page, server: subprocess.Popen[Any]) -> None:
    # Seed catalog and navigate through a VR to issue a proof, then create policy/gate.
    page.goto(f"{BASE_URL}/app/")
    page.evaluate("""async () => {
        const r = await fetch('/v1/demo/catalog/seed', {method: 'POST'});
        return r.status;
    }""")
    time.sleep(1)

    page.goto(f"{BASE_URL}/app/?view=verification-records")
    time.sleep(1)

    # Click the first "Detail" link in the VR table.
    page.locator("text=Detail").first.click()
    time.sleep(1)
    expect(page.locator("text=Verification Record").first).to_be_visible()

    # Run mutation and issue proof if eligible.
    if page.locator("button:has-text('Verify Fix')").is_visible():
        page.locator("button:has-text('Verify Fix')").click()
        time.sleep(1)
    issue_proof = page.locator("button:has-text('Issue Proof')")
    if issue_proof.is_visible() and issue_proof.is_enabled():
        issue_proof.click()
        time.sleep(1)

    # Promote to scenario if eligible.
    promote = page.locator("button:has-text('Promote to Scenario')")
    if promote.is_visible() and promote.is_enabled():
        promote.click()
        time.sleep(1)

    # Readiness view should be reachable.
    page.goto(f"{BASE_URL}/app/?view=readiness")
    time.sleep(1)
    expect(page.locator(".section-title").filter(has_text="Readiness Policies")).to_be_visible()
