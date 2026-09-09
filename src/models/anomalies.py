from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AnomalySeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AnomalyType(str, Enum):
    SOLR_QUERY_LATENCY_SPIKE = "SOLR_QUERY_LATENCY_SPIKE"
    SOLR_ERROR_BURST = "SOLR_ERROR_BURST"
    SOLR_REPLICA_FAILURE = "SOLR_REPLICA_FAILURE"
    SOLR_ZOOKEEPER_DISCONNECT = "SOLR_ZOOKEEPER_DISCONNECT"
    JVM_LONG_GC_PAUSE = "JVM_LONG_GC_PAUSE"
    JVM_HIGH_HEAP_OCCUPANCY = "JVM_HIGH_HEAP_OCCUPANCY"
    JVM_FULL_GC_FREQUENCY = "JVM_FULL_GC_FREQUENCY"
    JVM_OUT_OF_MEMORY = "JVM_OUT_OF_MEMORY"


class Anomaly(BaseModel):
    anomaly_id: str
    event_id: str
    node_id: str
    timestamp: datetime
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    condition: str
    trigger_metric: str
    trigger_value: float
    threshold_value: float
    reason: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
