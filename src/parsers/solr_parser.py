import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from src.parsers.base import BaseLogParser
from src.models.events import NormalizedEvent, LogSource, Severity, ParseStatus


class SolrLogParser(BaseLogParser):
    """
    Parser for Apache Solr logs.
    Handles standard patterns:
    'YYYY-MM-DD HH:MM:SS.mmm LEVEL (thread) [node_context] Class message [params...] QTime=... hits=...'
    """

    SOLR_PATTERN = re.compile(
        r"^(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+"
        r"(?P<severity>INFO|WARN|ERROR|DEBUG|FATAL)\s+"
        r"(?:\((?P<thread>[^)]+)\)\s+)?"
        r"(?:\[(?P<context>[^\]]+)\]\s+)?"
        r"(?P<logger>[a-zA-Z0-9_.$]+)\s+"
        r"(?P<message>.*)$"
    )

    QTIME_PATTERN = re.compile(r"QTime=(?P<qtime>\d+)")
    HITS_PATTERN = re.compile(r"hits=(?P<hits>\d+)")
    STATUS_PATTERN = re.compile(r"status=(?P<status>\d+)")
    COLLECTION_PATTERN = re.compile(r"\[(?P<collection>[a-zA-Z0-9_-]+)\]")
    NODE_PATTERN = re.compile(r"(?P<node>[a-zA-Z0-9_-]+):\d+_solr")

    def parse_line(self, line: str, default_node_id: str = "solr-node-1") -> Optional[NormalizedEvent]:
        match = self.SOLR_PATTERN.match(line)
        if not match:
            try:
                dt_match = re.match(r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})", line)
                ts = datetime.strptime(dt_match.group(1), "%Y-%m-%d %H:%M:%S") if dt_match else datetime.now(timezone.utc)
            except Exception:
                ts = datetime.now(timezone.utc)

            return NormalizedEvent(
                event_id=NormalizedEvent.create_fingerprint(ts, default_node_id, LogSource.SOLR, line),
                timestamp=ts,
                node_id=default_node_id,
                source=LogSource.SOLR,
                severity=Severity.WARN,
                event_type="UNSTRUCTURED_SOLR_LOG",
                message=line[:250],
                raw_message=line,
                parse_status=ParseStatus.PARTIALLY_PARSED,
            )

        groups = match.groupdict()
        ts_str = groups["timestamp"]
        try:
            if "." in ts_str:
                ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S.%f")
            else:
                ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            ts = datetime.utcnow()

        severity_str = groups["severity"].upper()
        severity = Severity[severity_str] if severity_str in Severity.__members__ else Severity.INFO

        context = groups.get("context") or ""
        node_id = default_node_id
        node_match = self.NODE_PATTERN.search(context)
        if node_match:
            node_id = node_match.group("node")

        message = groups["message"]
        metrics: Dict[str, float] = {}

        qtime_m = self.QTIME_PATTERN.search(message)
        if qtime_m:
            metrics["qtime_ms"] = float(qtime_m.group("qtime"))

        hits_m = self.HITS_PATTERN.search(message)
        if hits_m:
            metrics["hits"] = float(hits_m.group("hits"))

        status_m = self.STATUS_PATTERN.search(message)
        if status_m:
            metrics["status"] = float(status_m.group("status"))

        metadata: Dict[str, Any] = {
            "logger": groups.get("logger"),
            "thread": groups.get("thread"),
            "context": context,
        }

        # Event type classification: Prioritize severity errors
        if severity in (Severity.ERROR, Severity.FATAL):
            event_type = "SOLR_ERROR"
        elif "ZooKeeper" in message or "ZkController" in message or "ConnectionManager" in message:
            event_type = "SOLR_ZOOKEEPER"
        elif "Replica" in message or "Overseer" in message or "marking replica" in message.lower():
            event_type = "SOLR_CLUSTER_STATE"
        elif "SolrServerException" in message or "SocketTimeoutException" in message or "Connection refused" in message:
            event_type = "SOLR_COMMUNICATION_ERROR"
        elif "Request" in message or "webapp=/solr" in message or "path=/select" in message:
            event_type = "SOLR_REQUEST"
        else:
            event_type = "SOLR_LOG"

        return NormalizedEvent(
            event_id=NormalizedEvent.create_fingerprint(ts, node_id, LogSource.SOLR, line),
            timestamp=ts,
            node_id=node_id,
            source=LogSource.SOLR,
            severity=severity,
            event_type=event_type,
            message=message,
            raw_message=line,
            parse_status=ParseStatus.PARSED,
            metrics=metrics,
            metadata=metadata,
        )
