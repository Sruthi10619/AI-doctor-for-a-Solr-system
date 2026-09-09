from typing import List, Dict
from datetime import timezone
from datetime import datetime
from src.models.events import NormalizedEvent, Severity
from src.models.anomalies import Anomaly, AnomalySeverity
from src.models.incidents import Incident, IncidentStatus
from src.models.health import NodeHealth, ClusterHealth, HealthState


class HealthEngine:
    """
    Evaluates explainable Node-level and Cluster-level health scores (0 - 100)
    using weighted deduction rules based on observed telemetry and anomalies.
    """

    @classmethod
    def evaluate_node_health(
        cls,
        node_id: str,
        events: List[NormalizedEvent],
        anomalies: List[Anomaly]
    ) -> NodeHealth:
        node_events = [e for e in events if e.node_id == node_id]
        node_anomalies = [a for a in anomalies if a.node_id == node_id]

        error_count = sum(1 for e in node_events if e.severity in (Severity.ERROR, Severity.FATAL))
        warning_count = sum(1 for e in node_events if e.severity == Severity.WARN)

        qtimes = [e.metrics["qtime_ms"] for e in node_events if "qtime_ms" in e.metrics]
        avg_qtime = sum(qtimes) / len(qtimes) if qtimes else 0.0

        gc_pauses = [e.metrics["pause_duration_ms"] for e in node_events if "pause_duration_ms" in e.metrics]
        max_gc_pause = max(gc_pauses) if gc_pauses else 0.0

        heap_pcts = [e.metrics["heap_occupancy_pct"] for e in node_events if "heap_occupancy_pct" in e.metrics]
        avg_heap_pct = sum(heap_pcts) / len(heap_pcts) if heap_pcts else 0.0

        # Health Scoring (Start at 100.0)
        score = 100.0
        primary_issues = []

        # Deductions for Anomaly Severity
        for a in node_anomalies:
            if a.severity == AnomalySeverity.CRITICAL:
                score -= 30.0
                primary_issues.append(f"CRITICAL: {a.condition}")
            elif a.severity == AnomalySeverity.HIGH:
                score -= 15.0
                primary_issues.append(f"HIGH: {a.condition}")
            elif a.severity == AnomalySeverity.MEDIUM:
                score -= 8.0
                primary_issues.append(f"MEDIUM: {a.condition}")

        # Deductions for Errors
        if error_count > 0:
            score -= min(error_count * 5.0, 25.0)

        # Clamp score between 0.0 and 100.0
        score = max(0.0, min(100.0, score))

        # Classification
        if score >= 80.0:
            state = HealthState.HEALTHY
        elif score >= 50.0:
            state = HealthState.WARNING
        else:
            state = HealthState.CRITICAL

        if not primary_issues and state == HealthState.HEALTHY:
            primary_issues.append("All metrics operating within baseline bounds.")

        return NodeHealth(
            node_id=node_id,
            state=state,
            health_score=round(score, 1),
            error_count=error_count,
            warning_count=warning_count,
            active_anomalies_count=len(node_anomalies),
            avg_qtime_ms=round(avg_qtime, 1),
            max_gc_pause_ms=round(max_gc_pause, 1),
            avg_heap_pct=round(avg_heap_pct, 1),
            primary_issues=primary_issues[:4],
            last_evaluated_at=datetime.now(timezone.utc),
        )

    @classmethod
    def evaluate_cluster_health(
        cls,
        nodes: List[str],
        events: List[NormalizedEvent],
        anomalies: List[Anomaly],
        incidents: List[Incident]
    ) -> ClusterHealth:
        node_summaries: Dict[str, NodeHealth] = {}
        for node in nodes:
            node_summaries[node] = cls.evaluate_node_health(node, events, anomalies)

        total_nodes = len(nodes)
        healthy_count = sum(1 for nh in node_summaries.values() if nh.state == HealthState.HEALTHY)
        warning_count = sum(1 for nh in node_summaries.values() if nh.state == HealthState.WARNING)
        critical_count = sum(1 for nh in node_summaries.values() if nh.state == HealthState.CRITICAL)

        active_incidents = [inc for inc in incidents if inc.status == IncidentStatus.ACTIVE]

        # Overall Cluster Health Score is weighted average of node scores with active incident penalty
        avg_node_score = sum(nh.health_score for nh in node_summaries.values()) / total_nodes if total_nodes > 0 else 100.0
        incident_penalty = len(active_incidents) * 10.0
        cluster_score = max(0.0, min(100.0, avg_node_score - incident_penalty))

        if critical_count > 0 or cluster_score < 50.0:
            cluster_state = HealthState.CRITICAL
            concern = f"{critical_count} critical node(s) with severe active degradation."
        elif warning_count > 0 or cluster_score < 80.0:
            cluster_state = HealthState.WARNING
            concern = f"{warning_count} warning node(s) showing elevated latency or GC pressure."
        else:
            cluster_state = HealthState.HEALTHY
            concern = "All SolrCloud nodes and shards operating normally."

        return ClusterHealth(
            cluster_id="solr-cluster-prod",
            state=cluster_state,
            overall_health_score=round(cluster_score, 1),
            total_nodes=total_nodes,
            healthy_nodes_count=healthy_count,
            warning_nodes_count=warning_count,
            critical_nodes_count=critical_count,
            active_incidents_count=len(active_incidents),
            primary_concern=concern,
            node_summaries=node_summaries,
            evaluated_at=datetime.now(timezone.utc),
        )
