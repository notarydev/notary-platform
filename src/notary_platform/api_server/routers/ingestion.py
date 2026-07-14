"""Routes for forensic snapshot ingestion."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


class IngestionRequest(BaseModel):
    """Payload accepted by the ingestion scaffold endpoint."""

    source: str = Field(..., description="Source system or collector identifier.")
    evidence_uri: str = Field(..., description="URI for the captured evidence bundle.")


@router.post("/snapshots", status_code=202)
def ingest_snapshot(payload: IngestionRequest) -> dict[str, str]:
    """Accept a forensic snapshot for later processing."""
    return {
        "status": "accepted",
        "source": payload.source,
        "evidence_uri": payload.evidence_uri,
    }
