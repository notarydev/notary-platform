"""Dashboard router — minimal HTML dashboard for the prototype demo."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from notary_platform.api_server.routers.incidents import storage
from notary_platform.replay_engine.cassette import ResponseCassette
from notary_platform.snapshot import (
    CapturedElement,
    _compute_root_hash,
    _seal_element,
)

router = APIRouter(tags=["dashboard"])

_DEMO_SECRET = b"demo-secret-key-32-bytes-long!!!"
_DEMO_SCORE = 650


def _lending_agent(cassette: ResponseCassette, threshold: int = 700) -> str:
    result = cassette.lookup("POST", "https://api.example.com/credit-check")
    if result is None:
        return "UNKNOWN"
    score = result.get("response", {}).get("score", 0)
    return "APPROVE" if score >= threshold else "DENY"


def _make_demo_snapshot() -> dict[str, Any]:
    elements: list[dict[str, Any]] = [
        {
            "kind": "http",
            "payload": {
                "request": {
                    "method": "POST",
                    "url": "https://api.example.com/credit-check",
                },
                "response": {"score": _DEMO_SCORE},
                "status": 200,
            },
        },
        {"kind": "decision", "payload": {"decision": "DENY"}},
    ]
    prev_hash = b"\x00" * 32
    elem_hashes: list[bytes] = []
    sealed: list[dict[str, Any]] = []
    for e in elements:
        ce = CapturedElement(kind=e["kind"], payload=e.get("payload", {}))
        h = _seal_element(prev_hash, ce.canonical_bytes(), _DEMO_SECRET)
        elem_hashes.append(h)
        sealed.append({"kind": ce.kind, "payload": ce.payload, "element_hash": h.hex()})
        prev_hash = h
    root = _compute_root_hash(elem_hashes)
    return {
        "schema_version": 1,
        "timestamp": "2025-07-15T00:00:00Z",
        "elements": sealed,
        "merkle_chain": [h.hex() for h in elem_hashes],
        "root_hash": root,
    }


def _incident_row(inc: object) -> str:
    inc_d = inc.to_dict()  # type: ignore[attr-defined]
    inc_id = inc_d["incident_id"]
    status = inc_d["status"]
    elem_count = inc_d["snapshot_summary"].get("element_count", "?")
    root = inc_d["snapshot_summary"].get("root_hash", "")[:16]

    actions = ""
    if status == "ingested":
        actions = (
            f"<form method='post' action='/v1/incidents/{inc_id}/replay' style='display:inline'>"
            f"<button type='submit'>Replay</button></form>"
        )
    elif status == "replayed":
        actions = (
            f"<form method='post' action='/v1/incidents/{inc_id}/mutation' "
            f"enctype='application/json' style='display:inline'>"
            f"<input type='hidden' name='fix_config' value='{{\"threshold\":620}}'>"
            f"<button type='submit'>Apply Fix</button></form>"
        )
    elif status == "mitigated":
        actions = (
            f"<form method='post' action='/v1/certificates/{inc_id}' style='display:inline'>"
            f"<button type='submit'>Issue Certificate</button></form>"
        )
    elif status == "certified":
        actions = (
            f"<a href='/v1/certificates/{inc_id}'>View Certificate</a> "
            f"<a href='/v1/certificates/{inc_id}/verify'>Verify Signature</a>"
        )

    return (
        f"<tr>"
        f"<td>{inc_id}</td>"
        f"<td>{status}</td>"
        f"<td>{elem_count}</td>"
        f"<td>{root}...</td>"
        f"<td>{actions}</td>"
        f"</tr>"
    )


@router.get("/", response_class=HTMLResponse)
def index() -> str:
    return (
        "<html><head><title>Notary Platform</title></head><body>"
        "<h1>Notary Platform</h1>"
        "<ul>"
        "<li><a href='/dashboard'>Dashboard</a></li>"
        "<li><a href='/health'>Health</a></li>"
        "<li><a href='/v1/incidents'>Incidents API</a></li>"
        "</ul>"
        "<h2>Demo</h2>"
        "<form method='post' action='/v1/demo/lending-seed'>"
        "<button type='submit'>Seed Lending Demo Incident</button>"
        "</form>"
        "</body></html>"
    )


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> str:
    incidents = storage.list_incidents()
    rows = "".join(_incident_row(i) for i in incidents)
    return (
        "<html><head><title>Notary Dashboard</title></head><body>"
        "<h1>Incident Dashboard</h1>"
        "<form method='post' action='/v1/demo/lending-seed' style='margin-bottom:16px'>"
        "<button type='submit'>Seed Lending Demo</button>"
        "</form>"
        "<table border='1' cellpadding='4'>"
        "<tr><th>ID</th><th>Status</th><th>Elements</th><th>Root Hash</th><th>Actions</th></tr>"
        f"{rows}"
        "</table>"
        "<p><a href='/'>Home</a></p>"
        "</body></html>"
    )


@router.post("/v1/demo/lending-seed", response_class=HTMLResponse)
def seed_lending_demo() -> HTMLResponse:
    snap = _make_demo_snapshot()
    storage.create_incident(snap)
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/dashboard", status_code=303)  # type: ignore[return-value]
