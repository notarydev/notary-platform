"""Routes for evidence certificate workflows."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/certificates", tags=["certificates"])


class CertificateRequest(BaseModel):
    """Payload for creating a placeholder evidence certificate."""

    incident_id: str = Field(..., description="Incident associated with the certificate.")
    evidence_hash: str = Field(..., description="Digest of the evidence bundle.")


@router.post("/", status_code=202)
def create_certificate(payload: CertificateRequest) -> dict[str, str]:
    """Queue a placeholder evidence certificate request."""
    return {
        "status": "queued",
        "incident_id": payload.incident_id,
        "evidence_hash": payload.evidence_hash,
    }
