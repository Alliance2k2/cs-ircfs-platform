"""System/health schemas."""
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
