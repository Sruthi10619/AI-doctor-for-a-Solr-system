import hashlib
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LogSource(str, Enum):
    SOLR = "SOLR"
    JVM_GC = "JVM_GC"


class Severity(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"


class ParseStatus(str, Enum):
    PARSED = "PARSED"
    PARTIALLY_PARSED = "PARTIALLY_PARSED"
    UNPARSED = "UNPARSED"


class NormalizedEvent(BaseModel):
    event_id: str = Field(description="Unique deterministic SHA-256 fingerprint of the event")
    timestamp: datetime
    node_id: str
    cluster_id: str = "solr-cluster-prod"
    source: LogSource
    severity: Severity
    event_type: str
    message: str
    raw_message: str
    parse_status: ParseStatus = ParseStatus.PARSED
    metrics: Dict[str, float] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    data_source: str = "synthetic"
    environment: str = "prototype_demo"

    @classmethod
    def create_fingerprint(cls, timestamp: datetime, node_id: str, source: LogSource, raw_message: str) -> str:
        """Generates an idempotent deterministic SHA-256 hash for deduplication."""
        seed = f"{timestamp.isoformat()}|{node_id}|{source.value}|{raw_message.strip()}"
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
