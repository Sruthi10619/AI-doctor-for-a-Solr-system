from datetime import datetime, timezone
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class HealthState(str, Enum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class NodeHealth(BaseModel):
    node_id: str
    state: HealthState
    health_score: float = Field(ge=0.0, le=100.0, description="100=perfect, 0=completely failing")
    error_count: int = 0
    warning_count: int = 0
    active_anomalies_count: int = 0
    avg_qtime_ms: float = 0.0
    max_gc_pause_ms: float = 0.0
    avg_heap_pct: float = 0.0
    primary_issues: List[str] = Field(default_factory=list)
    last_evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ClusterHealth(BaseModel):
    cluster_id: str = "solr-cluster-prod"
    state: HealthState
    overall_health_score: float = Field(ge=0.0, le=100.0)
    total_nodes: int
    healthy_nodes_count: int
    warning_nodes_count: int
    critical_nodes_count: int
    active_incidents_count: int
    primary_concern: str
    node_summaries: Dict[str, NodeHealth] = Field(default_factory=dict)
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
