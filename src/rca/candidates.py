import uuid
from typing import List, Dict
from src.models.anomalies import Anomaly, AnomalyType, AnomalySeverity
from src.models.ai import DeterministicRCACandidate, CausalityLevel


class DeterministicRCAGenerator:
    """
    Evaluates rule-based signatures over correlated anomaly clusters to produce
    grounded RCA hypotheses BEFORE invoking any LLM.
    """

    @classmethod
    def generate_candidates(cls, anomalies: List[Anomaly], node_ids: List[str]) -> List[DeterministicRCACandidate]:
        candidates: List[DeterministicRCACandidate] = []
        anomaly_types = {a.anomaly_type for a in anomalies}
        anomaly_ids = [a.anomaly_id for a in anomalies]

        has_long_gc = AnomalyType.JVM_LONG_GC_PAUSE in anomaly_types
        has_high_heap = AnomalyType.JVM_HIGH_HEAP_OCCUPANCY in anomaly_types
        has_qtime_spike = AnomalyType.SOLR_QUERY_LATENCY_SPIKE in anomaly_types
        has_zk_disconnect = AnomalyType.SOLR_ZOOKEEPER_DISCONNECT in anomaly_types
        has_replica_down = AnomalyType.SOLR_REPLICA_FAILURE in anomaly_types

        # Rule Signature 1: GC Pause Induced Latency Spike / Thread Starvation
        if has_long_gc and has_qtime_spike:
            candidates.append(
                DeterministicRCACandidate(
                    candidate_id=f"RCA-CAND-{uuid.uuid4().hex[:6]}",
                    primary_hypothesis="Stop-The-World JVM Garbage Collection pause induced Solr query latency spike & thread starvation.",
                    causality_level=CausalityLevel.LIKELY_CAUSAL,
                    confidence_score=0.92,
                    supporting_anomaly_ids=anomaly_ids,
                    inferred_mechanisms=[
                        "Long JVM GC pauses freeze all Java application threads (Stop-The-World).",
                        "Solr request handlers are unable to process in-flight query pipelines during pause duration.",
                        "Observed QTime spikes correlate temporally with prolonged GC pause events on the same node.",
                    ],
                    rule_signature="RULE_GC_INDUCED_QUERY_LATENCY",
                )
            )

        # Rule Signature 2: JVM OldGen Memory Pressure & Heap Saturation
        if has_high_heap and has_long_gc:
            candidates.append(
                DeterministicRCACandidate(
                    candidate_id=f"RCA-CAND-{uuid.uuid4().hex[:6]}",
                    primary_hypothesis="JVM Old Generation memory pressure causing frequent Full GC cycles and latency degradation.",
                    causality_level=CausalityLevel.LIKELY_CAUSAL,
                    confidence_score=0.88,
                    supporting_anomaly_ids=anomaly_ids,
                    inferred_mechanisms=[
                        "High post-GC heap occupancy indicates memory retention (large facet structures, heavy caches, or undersized heap).",
                        "JVM ergonomics trigger Full GC sweeps repeatedly attempting to reclaim space.",
                    ],
                    rule_signature="RULE_HEAP_PRESSURE_THRASHING",
                )
            )

        # Rule Signature 3: GC-Induced ZooKeeper Session Expiration & Replica Eviction
        if has_long_gc and (has_zk_disconnect or has_replica_down):
            candidates.append(
                DeterministicRCACandidate(
                    candidate_id=f"RCA-CAND-{uuid.uuid4().hex[:6]}",
                    primary_hypothesis="Prolonged JVM pause exceeded ZooKeeper session timeout (zkClientTimeout), causing ephemeral node expiration and replica state transition to DOWN.",
                    causality_level=CausalityLevel.LIKELY_CAUSAL,
                    confidence_score=0.90,
                    supporting_anomaly_ids=anomaly_ids,
                    inferred_mechanisms=[
                        "ZooKeeper client heartbeat pings are blocked during JVM Stop-The-World execution.",
                        "ZooKeeper ensemble assumes the node died and drops ephemeral session znodes.",
                        "Overseer marks node replicas as DOWN.",
                    ],
                    rule_signature="RULE_GC_ZK_EVICTION",
                )
            )

        # Rule Signature 4: Pure Query Complexity / Deep Paging (No GC pressure)
        if has_qtime_spike and not has_long_gc and not has_high_heap:
            candidates.append(
                DeterministicRCACandidate(
                    candidate_id=f"RCA-CAND-{uuid.uuid4().hex[:6]}",
                    primary_hypothesis="Heavy search query workload (unoptimized wildcards, deep pagination, or large facet cardinality) exceeding hardware core execution capacity.",
                    causality_level=CausalityLevel.LIKELY_CAUSAL,
                    confidence_score=0.85,
                    supporting_anomaly_ids=anomaly_ids,
                    inferred_mechanisms=[
                        "High QTime with normal JVM GC pauses indicates CPU/IO-bound query execution rather than garbage collection bottlenecks.",
                        "Lucene index traversal / doc values decompression overhead for complex search params.",
                    ],
                    rule_signature="RULE_QUERY_COMPLEXITY_SATURATION",
                )
            )

        # Rule Signature 5: ZooKeeper Network Partition / Direct Cluster Failure
        if (has_zk_disconnect or has_replica_down) and not has_long_gc:
            candidates.append(
                DeterministicRCACandidate(
                    candidate_id=f"RCA-CAND-{uuid.uuid4().hex[:6]}",
                    primary_hypothesis="ZooKeeper ensemble connectivity failure or network partition causing replica coordination breakdown.",
                    causality_level=CausalityLevel.LIKELY_CAUSAL,
                    confidence_score=0.80,
                    supporting_anomaly_ids=anomaly_ids,
                    inferred_mechanisms=[
                        "Loss of ZooKeeper quorum connection without preceding JVM GC pauses indicates network transport or ZooKeeper server issue.",
                    ],
                    rule_signature="RULE_ZK_NETWORK_PARTITION",
                )
            )

        # Fallback Candidate if no signature matched
        if not candidates and anomalies:
            candidates.append(
                DeterministicRCACandidate(
                    candidate_id=f"RCA-CAND-{uuid.uuid4().hex[:6]}",
                    primary_hypothesis="Multiple isolated operational anomalies detected without a single conclusive deterministic causal link.",
                    causality_level=CausalityLevel.CORRELATED,
                    confidence_score=0.50,
                    supporting_anomaly_ids=anomaly_ids,
                    inferred_mechanisms=["Anomalies occurred in proximity but do not match known cascade signatures."],
                    rule_signature="RULE_GENERIC_ANOMALY_CORRELATION",
                )
            )

        return candidates
