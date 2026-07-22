"""FastAPI application for the Notary Platform."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from notary_platform.api_server.routers import certificates, incidents, ingestion, platform, release_gate, setup, verification, viz
from notary_platform.config import SETTINGS

app = FastAPI(title="Notary Platform", version="0.0.1")

# Allow a comma-separated list of viz origins so local + deployed Command Center
# can both be permitted, and shared deployments can lock CORS to known origins.
_viz_origins = [o.strip() for o in SETTINGS.viz_origin.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_viz_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingestion.router, prefix="/v1")
app.include_router(incidents.router, prefix="/v1")
app.include_router(certificates.router, prefix="/v1")
app.include_router(verification.router, prefix="/v1")
app.include_router(platform.router, prefix="/v1")
app.include_router(release_gate.router, prefix="/v1")
app.include_router(viz.router, prefix="/v1")
app.include_router(setup.router, prefix="/v1")
# Redirect root to the platform SPA (must be before dashboard router).
@app.get("/", include_in_schema=False)
def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/app/", status_code=302)

# Serve the notary-viz Command Center SPA at /cc.
_static_root = Path(__file__).resolve().parent.parent.parent.parent / "static" / "cc"
if _static_root.exists() and (_static_root / "index.html").exists():
    app.mount("/cc", StaticFiles(directory=str(_static_root), html=True), name="command_center")

# Serve the Notary Platform SPA at /app.
_platform_root = Path(__file__).resolve().parent.parent.parent.parent / "static" / "app"
if _platform_root.exists() and (_platform_root / "index.html").exists():
    app.mount("/app", StaticFiles(directory=str(_platform_root), html=True), name="platform")


@app.on_event("startup")
def _register_demo_agent() -> None:
    """Register the demo replay runner and seed demo org into storage."""
    from notary_platform.api_server.routers.dashboard import _scenario_agent_factory  # keep available for demo agent factory
    from notary_platform.api_server.routers.incidents import set_demo_agent
    from notary_platform.api_server.routers.ingestion import set_replay_runner, storage
    from notary_platform.services import DemoReplayRunner

    agent = _scenario_agent_factory("lending-denial")
    set_demo_agent(agent)

    # Register DemoReplayRunner for the service registry
    _demo_runner = DemoReplayRunner(scenario_id="lending-denial")
    set_replay_runner(_demo_runner)

    # Seed demo organization into storage
    from notary_platform.platform_data import seed as get_seed

    data = get_seed()
    org = data.get("organization")
    if org is not None and hasattr(org, "id"):
        storage.create_org(org)
        for env in data.get("environments", []):
            if hasattr(env, "id"):
                storage.create_env(env)
        for ag in data.get("agents", []):
            if hasattr(ag, "id"):
                storage.create_agent(ag)
        for sys_conn in data.get("systems", []):
            if hasattr(sys_conn, "id"):
                storage.create_system_conn(sys_conn)
        for pol in data.get("policies", []):
            if hasattr(pol, "id"):
                storage.create_policy(pol)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
