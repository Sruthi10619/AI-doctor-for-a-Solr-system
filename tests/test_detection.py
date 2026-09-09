from datetime import datetime, timezone
from src.detection.engine import AnomalyDetectionEngine
from src.models.events import NormalizedEvent, LogSource, Severity
from src.models.anomalies import AnomalyType, AnomalySeverity


def test_qtime_anomaly_detection():
    detector = AnomalyDetectionEngine()
    now = datetime.now(timezone.utc)

    # Normal event (QTime = 50ms) -> No anomaly
    normal_event = NormalizedEvent(
        event_id="test-1",
        timestamp=now,
        node_id="solr-node-1",
        source=LogSource.SOLR,
        severity=Severity.INFO,
        event_type="SOLR_REQUEST",
        message="hits=10 QTime=50",
        raw_message="raw",
        metrics={"qtime_ms": 50.0},
    )
    assert len(detector.detect_anomalies_for_event(normal_event)) == 0

    # Critical QTime spike (QTime = 6500ms)
    spike_event = NormalizedEvent(
        event_id="test-2",
        timestamp=now,
        node_id="solr-node-1",
        source=LogSource.SOLR,
        severity=Severity.WARN,
        event_type="SOLR_REQUEST",
        message="hits=10 QTime=6500",
        raw_message="raw",
        metrics={"qtime_ms": 6500.0},
    )
    anomalies = detector.detect_anomalies_for_event(spike_event)
    assert len(anomalies) == 1
    assert anomalies[0].anomaly_type == AnomalyType.SOLR_QUERY_LATENCY_SPIKE
    assert anomalies[0].severity == AnomalySeverity.CRITICAL


def test_gc_pause_and_heap_anomaly_detection():
    detector = AnomalyDetectionEngine()
    now = datetime.now(timezone.utc)

    gc_event = NormalizedEvent(
        event_id="test-3",
        timestamp=now,
        node_id="solr-node-2",
        source=LogSource.JVM_GC,
        severity=Severity.ERROR,
        event_type="JVM_FULL_GC",
        message="Full GC pause=4500ms",
        raw_message="raw",
        metrics={"pause_duration_ms": 4500.0, "heap_occupancy_pct": 95.0},
    )
    anomalies = detector.detect_anomalies_for_event(gc_event)
    assert len(anomalies) == 2  # Long GC pause AND High heap occupancy
    types = {a.anomaly_type for a in anomalies}
    assert AnomalyType.JVM_LONG_GC_PAUSE in types
    assert AnomalyType.JVM_HIGH_HEAP_OCCUPANCY in types
