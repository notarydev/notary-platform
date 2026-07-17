"""FastAPI application for the Notary Platform."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from notary_platform.api_server.routers import certificates, dashboard, incidents, ingestion, viz
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
app.include_router(viz.router, prefix="/v1")
app.include_router(dashboard.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
