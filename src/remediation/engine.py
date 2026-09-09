from typing import List, Tuple
from src.models.ai import RemediationItem, CausalityLevel
from src.models.anomalies import Anomaly, AnomalyType


class RemediationEngine:
    """
    Maps deterministic incident signatures and anomalies to vetted operational runbook actions.
    """

    @classmethod
    def get_grounded_remediations(
        cls,
        anomalies: List[Anomaly],
        primary_hypothesis: str
    ) -> Tuple[List[RemediationItem], List[RemediationItem]]:
        immediate: List[RemediationItem] = []
        preventative: List[RemediationItem] = []
        types = {a.anomaly_type for a in anomalies}

        if AnomalyType.JVM_LONG_GC_PAUSE in types or AnomalyType.JVM_HIGH_HEAP_OCCUPANCY in types:
            immediate.append(
                RemediationItem(
                    action="Capture JVM thread dump and heap histogram (`jcmd <pid> GC.class_histogram`) before restarting node.",
                    priority="IMMEDIATE",
                    rationale="Preserves diagnostic evidence of which objects/caches occupy the Old Generation.",
                    risk="LOW",
                )
            )
            immediate.append(
                RemediationItem(
                    action="Gracefully restart degraded Solr node or failover leader replica to healthy node.",
                    priority="IMMEDIATE",
                    rationale="Clears accumulated JVM memory pressure and restores immediate query responsiveness.",
                    risk="MEDIUM",
                )
            )
            preventative.append(
                RemediationItem(
                    action="Inspect and tune Solr Cache sizes (filterCache, queryResultCache, documentCache) in solrconfig.xml.",
                    priority="SHORT_TERM",
                    rationale="Oversized autowarmed caches are a primary cause of OldGen memory retention.",
                    risk="LOW",
                )
            )
            preventative.append(
                RemediationItem(
                    action="Evaluate G1GC collector tuning or increase JVM -Xmx heap headroom with adequate OS page cache margin.",
                    priority="LONG_TERM",
                    rationale="Ensures GC pauses remain under 500ms even under heavy indexing/query concurrency.",
                    risk="MEDIUM",
                )
            )

        if AnomalyType.SOLR_QUERY_LATENCY_SPIKE in types:
            immediate.append(
                RemediationItem(
                    action="Inspect currently running queries via `/solr/admin/collections?action=REQUESTSTATUS` and abort runaway queries.",
                    priority="IMMEDIATE",
                    rationale="Stops resource starvation caused by heavy regex/leading wildcard search requests.",
                    risk="LOW",
                )
            )
            preventative.append(
                RemediationItem(
                    action="Implement `timeAllowed` query limits in solrconfig.xml and enforce max facet cardinality restrictions.",
                    priority="SHORT_TERM",
                    rationale="Guarantees queries timeout gracefully before saturating cluster worker threads.",
                    risk="LOW",
                )
            )

        if AnomalyType.SOLR_ZOOKEEPER_DISCONNECT in types or AnomalyType.SOLR_REPLICA_FAILURE in types:
            immediate.append(
                RemediationItem(
                    action="Verify ZooKeeper ensemble quorum health (`echo mntr | nc zk-host 2181`) and client network connectivity.",
                    priority="IMMEDIATE",
                    rationale="Determines whether ZK session loss is localized to this node or a broader cluster partition.",
                    risk="LOW",
                )
            )
            preventative.append(
                RemediationItem(
                    action="Review and adjust `zkClientTimeout` (recommended: 30000ms) to tolerate transient GC pauses.",
                    priority="SHORT_TERM",
                    rationale="Prevents premature ephemeral node eviction during standard maintenance operations.",
                    risk="LOW",
                )
            )

        if not immediate:
            immediate.append(
                RemediationItem(
                    action="Review system resource utilization (CPU, disk I/O, network) on affected nodes.",
                    priority="IMMEDIATE",
                    rationale="Investigate potential underlying host-level resource bottlenecks.",
                    risk="LOW",
                )
            )

        return immediate, preventative
