import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from src.parsers.base import BaseLogParser
from src.models.events import NormalizedEvent, LogSource, Severity, ParseStatus


class GCLogParser(BaseLogParser):
    """
    Parser for HotSpot / OpenJDK JVM Garbage Collection logs.
    Handles standard patterns:
    - Minor GC: '2026-09-08T10:00:00.000+0000: [node] [GC (Allocation Failure) [PSYoungGen: ...] ... secs]'
    - Full GC: '2026-09-08T10:00:00.000+0000: [node] [Full GC (Ergonomics) ... [PSOldGen: ...] ... secs]'
    """

    GC_LINE_PATTERN = re.compile(
        r"^(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{4}|Z)?):?\s+"
        r"(?:\[(?P<node>[a-zA-Z0-9_-]+)\]\s+)?"
        r"\[(?P<gc_type>Full GC|GC)\s*(?:\((?P<cause>[^)]+)\))?\s*"
        r"(?P<details>.*)"
        r",\s*(?P<pause>[\d.]+)\s*secs\]"
    )

    TOTAL_HEAP_PATTERN = re.compile(r"(?P<before>\d+)K->(?P<after>\d+)K\((?P<total>\d+)K\)")
    NODE_BRACKET_PATTERN = re.compile(r"\[(?P<node>solr-node-\d+)\]")

    def parse_line(self, line: str, default_node_id: str = "solr-node-1") -> Optional[NormalizedEvent]:
        match = self.GC_LINE_PATTERN.search(line)
        if not match:
            # Fallback for non-standard GC format
            try:
                dt_match = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", line)
                ts = datetime.strptime(dt_match.group(1), "%Y-%m-%dT%H:%M:%S") if dt_match else datetime.now(timezone.utc)
            except Exception:
                ts = datetime.now(timezone.utc)

            return NormalizedEvent(
                event_id=NormalizedEvent.create_fingerprint(ts, default_node_id, LogSource.JVM_GC, line),
                timestamp=ts,
                node_id=default_node_id,
                source=LogSource.JVM_GC,
                severity=Severity.WARN,
                event_type="UNSTRUCTURED_GC_LOG",
                message=line[:250],
                raw_message=line,
                parse_status=ParseStatus.PARTIALLY_PARSED,
            )

        groups = match.groupdict()
        ts_str = groups["timestamp"]
        # Clean timezone offset for datetime parsing
        clean_ts = re.sub(r"[+-]\d{4}$|Z$", "", ts_str)
        try:
            if "." in clean_ts:
                ts = datetime.strptime(clean_ts, "%Y-%m-%dT%H:%M:%S.%f")
            else:
                ts = datetime.strptime(clean_ts, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            ts = datetime.utcnow()

        node_id = groups.get("node") or default_node_id
        if node_id == default_node_id:
            node_m = self.NODE_BRACKET_PATTERN.search(line)
            if node_m:
                node_id = node_m.group("node")

        gc_type = groups["gc_type"]
        is_full_gc = "Full" in gc_type
        pause_sec = float(groups["pause"])
        pause_ms = pause_sec * 1000.0

        metrics: Dict[str, float] = {
            "pause_duration_ms": pause_ms,
            "pause_duration_s": pause_sec,
            "is_full_gc": 1.0 if is_full_gc else 0.0,
        }

        # Extract overall heap utilization before and after
        heap_matches = self.TOTAL_HEAP_PATTERN.findall(line)
        if heap_matches:
            # The last match represents the total JVM heap transition
            last_heap = heap_matches[-1]
            before_k = float(last_heap[0])
            after_k = float(last_heap[1])
            total_k = float(last_heap[2])
            
            metrics["heap_before_mb"] = before_k / 1024.0
            metrics["heap_after_mb"] = after_k / 1024.0
            metrics["heap_total_mb"] = total_k / 1024.0
            metrics["heap_occupancy_pct"] = (after_k / total_k) * 100.0 if total_k > 0 else 0.0

        severity = Severity.INFO
        if is_full_gc and pause_ms > 2000:
            severity = Severity.ERROR
        elif is_full_gc or pause_ms > 800:
            severity = Severity.WARN

        event_type = "JVM_FULL_GC" if is_full_gc else "JVM_MINOR_GC"
        message = (
            f"{gc_type} ({groups.get('cause') or 'General'}) pause={pause_ms:.1f}ms "
            f"heap_after={metrics.get('heap_after_mb', 0):.1f}MB ({metrics.get('heap_occupancy_pct', 0):.1f}%)"
        )

        return NormalizedEvent(
            event_id=NormalizedEvent.create_fingerprint(ts, node_id, LogSource.JVM_GC, line),
            timestamp=ts,
            node_id=node_id,
            source=LogSource.JVM_GC,
            severity=severity,
            event_type=event_type,
            message=message,
            raw_message=line,
            parse_status=ParseStatus.PARSED,
            metrics=metrics,
            metadata={"cause": groups.get("cause"), "gc_type": gc_type},
        )
