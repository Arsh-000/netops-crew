from pydantic import BaseModel, Field
from typing import Optional


class InterfaceQueryInput(BaseModel):
    interface: Optional[str] = None


class ConfigHistoryInput(BaseModel):
    pass


class Incident(BaseModel):
    """The shared object that gets handed off between agents."""
    interface: str
    detected_by: str = "monitor_agent"
    raw_status: dict = Field(default_factory=dict)


class Diagnosis(BaseModel):
    incident: Incident
    root_cause: str
    confidence: str
    recommended_action: str


class IncidentReport(BaseModel):
    diagnosis: Diagnosis
    ticket_title: str
    ticket_body: str
