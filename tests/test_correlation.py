from datetime import datetime, timedelta
from src.correlation.engine import CorrelationEngine
from src.rca.candidates import DeterministicRCAGenerator
from src.models.events import NormalizedEvent, LogSource, Severity
from src.models.anomalies import Anomaly, AnomalyType, AnomalySeverity
from src.models.ai import CausalityLevel


def test_cross_source_cascade_correlation():
    t0 = datetime(2026, 9, 8, 10, 0, 0)
    
    # 1. GC anomaly on solr-node-2
    gc_anomaly = Anomaly(
        anomaly_id="ANO-1",
        event_id="EV-1",
        node_id="solr-node-2",
        timestamp=t0,
        anomaly_type=AnomalyType.JVM_LONG_GC_PAUSE,
        severity=AnomalySeverity.CRITICAL,
        condition="GC pause 4.8s",
        trigger_metric="pause_duration_ms",
        trigger_value=4850.0,
        threshold_value=3000.0,
        reason="Stop the world",
    )

    # 2. Solr latency anomaly on solr-node-2, 5s later
    solr_anomaly = Anomaly(
        anomaly_id="ANO-2",
        event_id="EV-2",
        node_id="solr-node-2",
        timestamp=t0 + timedelta(seconds=5),
        anomaly_type=AnomalyType.SOLR_QUERY_LATENCY_SPIKE,
        severity=AnomalySeverity.CRITICAL,
        condition="QTime 5120ms",
        trigger_metric="qtime_ms",
        trigger_value=5120.0,
        threshold_value=5000.0,
        reason="Thread lock timeout",
    )

    events = [
        NormalizedEvent(
            event_id="EV-1",
            timestamp=t0,
            node_id="solr-node-2",
            source=LogSource.JVM_GC,
            severity=Severity.ERROR,
            event_type="JVM_FULL_GC",
            message="Full GC",
            raw_message="raw",
        ),
        NormalizedEvent(
            event_id="EV-2",
            timestamp=t0 + timedelta(seconds=5),
            node_id="solr-node-2",
            source=LogSource.SOLR,
            severity=Severity.ERROR,
            event_type="SOLR_REQUEST",
            message="timeout",
            raw_message="raw",
        ),
    ]

    engine = CorrelationEngine()
    incidents = engine.correlate([gc_anomaly, solr_anomaly], events)

    assert len(incidents) == 1
    inc = incidents[0]
    assert inc.affected_nodes == ["solr-node-2"]
    assert len(inc.deterministic_candidates) > 0
    
    # Primary candidate must be GC-induced query latency with likely causal rating
    primary = inc.deterministic_candidates[0]
    assert primary.rule_signature == "RULE_GC_INDUCED_QUERY_LATENCY"
    assert primary.causality_level == CausalityLevel.LIKELY_CAUSAL
    assert primary.confidence_score >= 0.90
