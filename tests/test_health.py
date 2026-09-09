from datetime import datetime, timezone
from src.health.engine import HealthEngine
from src.models.events import NormalizedEvent, LogSource, Severity
from src.models.anomalies import Anomaly, AnomalyType, AnomalySeverity
from src.models.incidents import Incident, IncidentStatus
from src.models.health import HealthState


def test_node_health_scoring_deductions():
    now = datetime.now(timezone.utc)
    node_id = "solr-node-1"

    # Healthy node with 0 anomalies
    healthy_events = [
        NormalizedEvent(
            event_id="e1",
            timestamp=now,
            node_id=node_id,
            source=LogSource.SOLR,
            severity=Severity.INFO,
            event_type="SOLR_REQUEST",
            message="ok",
            raw_message="ok",
            metrics={"qtime_ms": 30.0},
        )
    ]
    node_health = HealthEngine.evaluate_node_health(node_id, healthy_events, [])
    assert node_health.state == HealthState.HEALTHY
    assert node_health.health_score == 100.0

    # Degraded node with critical anomaly
    crit_anomaly = Anomaly(
        anomaly_id="a1",
        event_id="e2",
        node_id=node_id,
        timestamp=now,
        anomaly_type=AnomalyType.JVM_LONG_GC_PAUSE,
        severity=AnomalySeverity.CRITICAL,
        condition="pause > 3000ms",
        trigger_metric="pause_duration_ms",
        trigger_value=4500.0,
        threshold_value=3000.0,
        reason="crit pause",
    )
    degraded_health = HealthEngine.evaluate_node_health(node_id, healthy_events, [crit_anomaly])
    assert degraded_health.state == HealthState.WARNING or degraded_health.state == HealthState.CRITICAL
    assert degraded_health.health_score < 80.0
