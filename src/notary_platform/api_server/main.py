"""FastAPI application for the Notary Platform."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from notary_platform.api_server.routers import certificates, incidents, ingestion, platform, viz
from notary_platform.config import SETTINGS

app = FastAPI(title="Notary Platform", version="0.0.1")

# Allow a comma-separated list of viz origins so local + deployed Command Center
# can both be permitted, and shared deployments can lock CORS to known origins.
_viz_origins = [o.strip() for o in SETTINGS.viz_origin.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_viz_origins,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(ingestion.router, prefix="/v1")
app.include_router(incidents.router, prefix="/v1")
app.include_router(certificates.router, prefix="/v1")
app.include_router(platform.router, prefix="/v1")
app.include_router(viz.router, prefix="/v1")

# Serve the internal Command Center SPA (static build from notary-viz) at /cc.
# The build is included in the container image at /app/static/cc.
_static_root = Path(__file__).resolve().parent.parent.parent.parent / "static" / "cc"
if _static_root.exists() and (_static_root / "index.html").exists():
    app.mount("/cc", StaticFiles(directory=str(_static_root), html=True), name="command_center")

# Serve the Notary Platform SPA at /app.
_platform_root = Path(__file__).resolve().parent.parent.parent.parent / "static" / "app"
if _platform_root.exists() and (_platform_root / "index.html").exists():
    app.mount("/app", StaticFiles(directory=str(_platform_root), html=True), name="platform")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
