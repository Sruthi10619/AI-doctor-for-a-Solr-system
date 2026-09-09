from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from src.models.anomalies import AnomalySeverity
from src.models.ai import StructuredRCAResult, DeterministicRCACandidate


class IncidentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"
    REOPENED = "REOPENED"


class Incident(BaseModel):
    incident_id: str
    status: IncidentStatus = IncidentStatus.ACTIVE
    severity: AnomalySeverity
    title: str
    start_time: datetime
    end_time: datetime
    affected_nodes: List[str]
    affected_collections: List[str] = Field(default_factory=list)
    anomaly_ids: List[str]
    event_ids: List[str]
    deterministic_candidates: List[DeterministicRCACandidate] = Field(default_factory=list)
    rca_result: Optional[StructuredRCAResult] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data_source: str = "synthetic"
    environment: str = "prototype_demo"
