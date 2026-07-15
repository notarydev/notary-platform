"""FastAPI application for the Notary Platform."""

from __future__ import annotations

from fastapi import FastAPI

from notary_platform.api_server.routers import dashboard, incidents, ingestion

app = FastAPI(title="Notary Platform", version="0.0.1")

app.include_router(ingestion.router, prefix="/v1")
app.include_router(incidents.router, prefix="/v1")
app.include_router(dashboard.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
