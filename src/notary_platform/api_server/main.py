"""Application entrypoint for the Notary Platform API server."""

from fastapi import FastAPI

from notary_platform.api_server.routers import certificates, incidents, ingestion

app = FastAPI(
    title="Notary Platform API",
    description="API server scaffold for forensic snapshot ingestion and evidence workflows.",
    version="0.1.0",
)

app.include_router(ingestion.router)
app.include_router(incidents.router)
app.include_router(certificates.router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Return a lightweight health response for load balancers and smoke tests."""
    return {"status": "ok"}
