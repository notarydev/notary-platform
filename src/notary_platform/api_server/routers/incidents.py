"""Routes for incident management."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/incidents", tags=["incidents"])


class IncidentSummary(BaseModel):
    """Minimal incident representation returned by scaffold endpoints."""

    incident_id: str = Field(..., description="Stable incident identifier.")
    status: str = Field(..., description="Current incident status.")


@router.get("/{incident_id}")
def get_incident(incident_id: str) -> IncidentSummary:
    """Return placeholder incident details."""
    return IncidentSummary(incident_id=incident_id, status="placeholder")
