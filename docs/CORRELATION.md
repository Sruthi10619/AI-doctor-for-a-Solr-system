# Event Correlation & Deterministic RCA Generation

## Multi-Dimensional Correlation Strategy
The correlation engine (`src/correlation/engine.py`) groups raw anomalies into structured incidents across two primary dimensions:
1. **Temporal Proximity**: Sliding time window ($\Delta t \le 90\text{s}$) capturing cascades as they unfold.
2. **Topology Proximity**: Grouping by `node_id`, collection, and inter-replica shard communication paths.

## Causality Classification
Correlation does not automatically imply causation. The system classifies relationships into 5 explicit levels:
- `OBSERVED`: Direct telemetry data explicitly recorded in log text.
- `CORRELATED`: Events occurring within the same time window and topology context.
- `LIKELY_CAUSAL`: Strong mechanisms verified by rule signatures (e.g. Stop-The-World GC pause immediately preceding request timeouts on the same node).
- `HYPOTHESIS`: Probable explanation supported by telemetry patterns but requiring external confirmation (e.g. heap dump or OS metrics).
- `UNKNOWN`: Insufficient evidence to establish a link.

## Deterministic RCA Candidate Signatures

| Signature Name | Trigger Conditions | Inferred Mechanism | Causality |
| :--- | :--- | :--- | :--- |
| `RULE_GC_INDUCED_QUERY_LATENCY` | `JVM_LONG_GC_PAUSE` + `SOLR_QUERY_LATENCY_SPIKE` on same node | Stop-The-World GC freezes Solr search threads; queries queue up and timeout. | `LIKELY_CAUSAL` (0.92) |
| `RULE_HEAP_PRESSURE_THRASHING` | `JVM_HIGH_HEAP_OCCUPANCY` + `JVM_FULL_GC_FREQUENCY` | Old Generation memory retention triggers continuous Full GC sweeps. | `LIKELY_CAUSAL` (0.88) |
| `RULE_GC_ZK_EVICTION` | `JVM_LONG_GC_PAUSE` + (`SOLR_ZOOKEEPER_DISCONNECT` \| `SOLR_REPLICA_FAILURE`) | JVM pause blocks ZK heartbeat pings; ephemeral znode expires; replica marked DOWN. | `LIKELY_CAUSAL` (0.90) |
| `RULE_QUERY_COMPLEXITY_SATURATION` | `SOLR_QUERY_LATENCY_SPIKE` without GC pause or heap pressure | Unoptimized queries (deep paging, regex, wildcards) saturating CPU/IO cores. | `LIKELY_CAUSAL` (0.85) |
| `RULE_ZK_NETWORK_PARTITION` | `SOLR_ZOOKEEPER_DISCONNECT` without preceding GC pause | Network partition or ZooKeeper ensemble host failure. | `LIKELY_CAUSAL` (0.80) |
