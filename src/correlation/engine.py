import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from src.config import settings
from src.models.events import NormalizedEvent
from src.models.anomalies import Anomaly, AnomalySeverity
from src.models.incidents import Incident, IncidentStatus
from src.rca.candidates import DeterministicRCAGenerator


class CorrelationEngine:
    """
    Correlates normalized events and anomalies across Solr and JVM GC sources
    using temporal sliding windows and cluster topology proximity.
    """

    def __init__(self, config=settings):
        self.config = config

    def correlate(self, anomalies: List[Anomaly], events: List[NormalizedEvent]) -> List[Incident]:
        if not anomalies:
            return []

        # Sort anomalies chronologically
        sorted_anomalies = sorted(anomalies, key=lambda a: a.timestamp)
        window_delta = timedelta(seconds=self.config.correlation_window_seconds)

        clusters: List[List[Anomaly]] = []
        current_cluster: List[Anomaly] = [sorted_anomalies[0]]

        for i in range(1, len(sorted_anomalies)):
            curr = sorted_anomalies[i]
            prev = current_cluster[-1]

            # Condition 1: Within time window
            in_window = (curr.timestamp - prev.timestamp) <= window_delta
            # Condition 2: Same node OR cross-node cluster event
            is_related_node = (curr.node_id == prev.node_id) or self.config.topology_shard_correlation

            if in_window and is_related_node:
                current_cluster.append(curr)
            else:
                clusters.append(current_cluster)
                current_cluster = [curr]

        if current_cluster:
            clusters.append(current_cluster)

        # Build Incident objects for each cluster
        incidents: List[Incident] = []
        for cluster in clusters:
            start_time = min(a.timestamp for a in cluster)
            end_time = max(a.timestamp for a in cluster)
            affected_nodes = sorted(list({a.node_id for a in cluster}))
            anomaly_ids = [a.anomaly_id for a in cluster]

            # Find matching events in time range for affected nodes
            matched_events = [
                e.event_id for e in events
                if (start_time - timedelta(seconds=5) <= e.timestamp <= end_time + timedelta(seconds=5))
                and (e.node_id in affected_nodes)
            ]

            # Highest severity in cluster determines incident severity
            severities = [a.severity for a in cluster]
            if AnomalySeverity.CRITICAL in severities:
                inc_severity = AnomalySeverity.CRITICAL
            elif AnomalySeverity.HIGH in severities:
                inc_severity = AnomalySeverity.HIGH
            elif AnomalySeverity.MEDIUM in severities:
                inc_severity = AnomalySeverity.MEDIUM
            else:
                inc_severity = AnomalySeverity.LOW

            # Generate Deterministic RCA Candidates
            candidates = DeterministicRCAGenerator.generate_candidates(cluster, affected_nodes)
            primary_hyp = candidates[0].primary_hypothesis if candidates else "Operational anomaly cluster"

            title = f"[{inc_severity.value}] {primary_hyp[:75]}... ({', '.join(affected_nodes)})"

            incident = Incident(
                incident_id=f"INC-{uuid.uuid4().hex[:8].upper()}",
                status=IncidentStatus.ACTIVE,
                severity=inc_severity,
                title=title,
                start_time=start_time,
                end_time=end_time,
                affected_nodes=affected_nodes,
                anomaly_ids=anomaly_ids,
                event_ids=matched_events,
                deterministic_candidates=candidates,
            )
            incidents.append(incident)

        return incidents
