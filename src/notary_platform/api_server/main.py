"""FastAPI application for the Notary Platform."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from notary_platform.api_server.routers import certificates, dashboard, incidents, ingestion, viz
from notary_platform.config import SETTINGS

app = FastAPI(title="Notary Platform", version="0.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[SETTINGS.viz_origin],
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
