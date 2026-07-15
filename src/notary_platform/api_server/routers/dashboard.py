"""Dashboard router — minimal HTML dashboard for the prototype demo."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from notary_platform.api_server.routers.ingestion import storage

router = APIRouter(tags=["dashboard"])


def _incident_row(inc: object) -> str:
    inc_d = inc.to_dict()  # type: ignore[attr-defined]
    return (
        f"<tr>"
        f"<td>{inc_d['incident_id']}</td>"
        f"<td>{inc_d['status']}</td>"
        f"<td>{inc_d['snapshot_summary'].get('element_count', '?')}</td>"
        f"<td>{inc_d['snapshot_summary'].get('root_hash', '')[:16]}...</td>"
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
        "</body></html>"
    )


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> str:
    incidents = storage.list_incidents()
    rows = "".join(_incident_row(i) for i in incidents)
    return (
        "<html><head><title>Notary Dashboard</title></head><body>"
        "<h1>Incident Dashboard</h1>"
        "<table border='1' cellpadding='4'>"
        "<tr><th>ID</th><th>Status</th><th>Elements</th><th>Root Hash</th></tr>"
        f"{rows}"
        "</table>"
        "<p><a href='/'>Home</a></p>"
        "</body></html>"
    )
