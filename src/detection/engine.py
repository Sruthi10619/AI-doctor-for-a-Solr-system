from typing import List, Optional
import uuid
from src.config import settings
from src.models.events import NormalizedEvent, LogSource, Severity
from src.models.anomalies import Anomaly, AnomalySeverity, AnomalyType


class AnomalyDetectionEngine:
    """
    Deterministic rule-based anomaly detector using configurable thresholds.
    Ensures 100% explainable, reproducible, and verifiable detection.
    """

    def __init__(self, config=settings):
        self.config = config

    def detect_anomalies_for_event(self, event: NormalizedEvent) -> List[Anomaly]:
        anomalies: List[Anomaly] = []

        if event.source == LogSource.SOLR:
            # 1. Solr Query Latency Spike Detection
            qtime = event.metrics.get("qtime_ms")
            if qtime is not None:
                if qtime >= self.config.solr_qtime_crit_ms:
                    anomalies.append(
                        Anomaly(
                            anomaly_id=f"ANO-LAT-{uuid.uuid4().hex[:8]}",
                            event_id=event.event_id,
                            node_id=event.node_id,
                            timestamp=event.timestamp,
                            anomaly_type=AnomalyType.SOLR_QUERY_LATENCY_SPIKE,
                            severity=AnomalySeverity.CRITICAL,
                            condition=f"QTime ({qtime:.0f}ms) >= critical threshold ({self.config.solr_qtime_crit_ms:.0f}ms)",
                            trigger_metric="qtime_ms",
                            trigger_value=qtime,
                            threshold_value=self.config.solr_qtime_crit_ms,
                            reason="Severe query latency degradation risking application-level client timeouts.",
                        )
                    )
                elif qtime >= self.config.solr_qtime_warn_ms:
                    anomalies.append(
                        Anomaly(
                            anomaly_id=f"ANO-LAT-{uuid.uuid4().hex[:8]}",
                            event_id=event.event_id,
                            node_id=event.node_id,
                            timestamp=event.timestamp,
                            anomaly_type=AnomalyType.SOLR_QUERY_LATENCY_SPIKE,
                            severity=AnomalySeverity.MEDIUM,
                            condition=f"QTime ({qtime:.0f}ms) >= warning threshold ({self.config.solr_qtime_warn_ms:.0f}ms)",
                            trigger_metric="qtime_ms",
                            trigger_value=qtime,
                            threshold_value=self.config.solr_qtime_warn_ms,
                            reason="Elevated query execution time indicating resource contention or complex query load.",
                        )
                    )

            # 2. Solr Communication / Replica Failure
            if event.event_type == "SOLR_CLUSTER_STATE" or "DOWN" in event.message:
                anomalies.append(
                    Anomaly(
                        anomaly_id=f"ANO-REP-{uuid.uuid4().hex[:8]}",
                        event_id=event.event_id,
                        node_id=event.node_id,
                        timestamp=event.timestamp,
                        anomaly_type=AnomalyType.SOLR_REPLICA_FAILURE,
                        severity=AnomalySeverity.HIGH,
                        condition="Replica state transitioned to DOWN or lost heartbeat",
                        trigger_metric="replica_state",
                        trigger_value=1.0,
                        threshold_value=0.0,
                        reason="Replica is offline, reducing cluster fault-tolerance and query throughput.",
                    )
                )

            # 3. Solr ZooKeeper Disconnect
            if event.event_type == "SOLR_ZOOKEEPER" and ("expired" in event.message.lower() or "lost" in event.message.lower()):
                anomalies.append(
                    Anomaly(
                        anomaly_id=f"ANO-ZK-{uuid.uuid4().hex[:8]}",
                        event_id=event.event_id,
                        node_id=event.node_id,
                        timestamp=event.timestamp,
                        anomaly_type=AnomalyType.SOLR_ZOOKEEPER_DISCONNECT,
                        severity=AnomalySeverity.CRITICAL,
                        condition="ZooKeeper session expiration / connection lost",
                        trigger_metric="zk_session_loss",
                        trigger_value=1.0,
                        threshold_value=0.0,
                        reason="Node lost coordination with ZooKeeper, risking split-brain or replica eviction.",
                    )
                )

            # 4. Solr Fatal/Error Burst
            if event.severity in (Severity.ERROR, Severity.FATAL) and not anomalies:
                anomalies.append(
                    Anomaly(
                        anomaly_id=f"ANO-ERR-{uuid.uuid4().hex[:8]}",
                        event_id=event.event_id,
                        node_id=event.node_id,
                        timestamp=event.timestamp,
                        anomaly_type=AnomalyType.SOLR_ERROR_BURST,
                        severity=AnomalySeverity.HIGH,
                        condition=f"Solr logged error/fatal event: {event.message[:80]}",
                        trigger_metric="error_event",
                        trigger_value=1.0,
                        threshold_value=0.0,
                        reason="Solr internal error during request or background coordination execution.",
                    )
                )

        elif event.source == LogSource.JVM_GC:
            # 5. JVM GC Pause Duration Spike
            pause_ms = event.metrics.get("pause_duration_ms", 0.0)
            if pause_ms >= self.config.gc_pause_crit_ms:
                anomalies.append(
                    Anomaly(
                        anomaly_id=f"ANO-GC-{uuid.uuid4().hex[:8]}",
                        event_id=event.event_id,
                        node_id=event.node_id,
                        timestamp=event.timestamp,
                        anomaly_type=AnomalyType.JVM_LONG_GC_PAUSE,
                        severity=AnomalySeverity.CRITICAL,
                        condition=f"GC Pause ({pause_ms:.0f}ms) >= critical threshold ({self.config.gc_pause_crit_ms:.0f}ms)",
                        trigger_metric="pause_duration_ms",
                        trigger_value=pause_ms,
                        threshold_value=self.config.gc_pause_crit_ms,
                        reason="Stop-The-World pause blocks all Solr search threads and ZooKeeper heartbeat pings.",
                    )
                )
            elif pause_ms >= self.config.gc_pause_warn_ms:
                anomalies.append(
                    Anomaly(
                        anomaly_id=f"ANO-GC-{uuid.uuid4().hex[:8]}",
                        event_id=event.event_id,
                        node_id=event.node_id,
                        timestamp=event.timestamp,
                        anomaly_type=AnomalyType.JVM_LONG_GC_PAUSE,
                        severity=AnomalySeverity.MEDIUM,
                        condition=f"GC Pause ({pause_ms:.0f}ms) >= warning threshold ({self.config.gc_pause_warn_ms:.0f}ms)",
                        trigger_metric="pause_duration_ms",
                        trigger_value=pause_ms,
                        threshold_value=self.config.gc_pause_warn_ms,
                        reason="Elevated GC pause causes intermittent query response jitter.",
                    )
                )

            # 6. JVM Heap Utilization Threshold Breach
            heap_pct = event.metrics.get("heap_occupancy_pct", 0.0)
            if heap_pct >= self.config.heap_usage_crit_pct:
                anomalies.append(
                    Anomaly(
                        anomaly_id=f"ANO-HEAP-{uuid.uuid4().hex[:8]}",
                        event_id=event.event_id,
                        node_id=event.node_id,
                        timestamp=event.timestamp,
                        anomaly_type=AnomalyType.JVM_HIGH_HEAP_OCCUPANCY,
                        severity=AnomalySeverity.CRITICAL,
                        condition=f"Post-GC Heap Occupancy ({heap_pct:.1f}%) >= critical threshold ({self.config.heap_usage_crit_pct:.1f}%)",
                        trigger_metric="heap_occupancy_pct",
                        trigger_value=heap_pct,
                        threshold_value=self.config.heap_usage_crit_pct,
                        reason="JVM Old Generation nearly exhausted; high risk of OutOfMemoryError and GC thrashing.",
                    )
                )
            elif heap_pct >= self.config.heap_usage_warn_pct:
                anomalies.append(
                    Anomaly(
                        anomaly_id=f"ANO-HEAP-{uuid.uuid4().hex[:8]}",
                        event_id=event.event_id,
                        node_id=event.node_id,
                        timestamp=event.timestamp,
                        anomaly_type=AnomalyType.JVM_HIGH_HEAP_OCCUPANCY,
                        severity=AnomalySeverity.MEDIUM,
                        condition=f"Post-GC Heap Occupancy ({heap_pct:.1f}%) >= warning threshold ({self.config.heap_usage_warn_pct:.1f}%)",
                        trigger_metric="heap_occupancy_pct",
                        trigger_value=heap_pct,
                        threshold_value=self.config.heap_usage_warn_pct,
                        reason="Elevated heap occupancy reduces headroom for caching and in-flight facet/sorting buffers.",
                    )
                )

        return anomalies

    def detect_anomalies(self, events: List[NormalizedEvent]) -> List[Anomaly]:
        all_anomalies = []
        for ev in events:
            all_anomalies.extend(self.detect_anomalies_for_event(ev))
        return all_anomalies
