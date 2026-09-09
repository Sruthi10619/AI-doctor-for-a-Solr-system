# Deterministic Anomaly Detection Logic

## Overview
The anomaly detection engine in `src/detection/engine.py` operates on normalized events produced by the log parsers. Every anomaly is evaluated deterministically against configurable thresholds and produces a typed `Anomaly` model.

## Detection Rules Matrix

| Anomaly Type | Log Source | Detection Condition | Severity | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| `SOLR_QUERY_LATENCY_SPIKE` | Solr Log | `qtime_ms >= 5000ms` | `CRITICAL` | Severe latency risking upstream client HTTP 504 gateway timeouts. |
| `SOLR_QUERY_LATENCY_SPIKE` | Solr Log | `qtime_ms >= 1000ms` | `MEDIUM` | Elevated query execution time indicating resource or facet contention. |
| `SOLR_REPLICA_FAILURE` | Solr Log | Message contains `DOWN` or replica heartbeat lost | `HIGH` | Node replica is offline, degrading collection fault tolerance and search capacity. |
| `SOLR_ZOOKEEPER_DISCONNECT` | Solr Log | ZooKeeper session expired or connection lost | `CRITICAL` | Node lost coordination with ensemble, risking split-brain and cluster isolation. |
| `SOLR_ERROR_BURST` | Solr Log | Log severity `ERROR` or `FATAL` | `HIGH` | Solr internal failure during request execution or shard communication. |
| `JVM_LONG_GC_PAUSE` | GC Log | `pause_duration_ms >= 3000ms` | `CRITICAL` | Long Stop-The-World pause freezing all query processing and heartbeat threads. |
| `JVM_LONG_GC_PAUSE` | GC Log | `pause_duration_ms >= 1000ms` | `MEDIUM` | Elevated pause introducing noticeable query latency jitter. |
| `JVM_HIGH_HEAP_OCCUPANCY` | GC Log | `heap_occupancy_pct >= 92.0%` | `CRITICAL` | Old Generation saturated post-GC; high risk of `OutOfMemoryError` and GC thrashing. |
| `JVM_HIGH_HEAP_OCCUPANCY` | GC Log | `heap_occupancy_pct >= 80.0%` | `MEDIUM` | High heap occupancy reducing headroom for autowarmed caches and sorting buffers. |

## Why Deterministic Rules Instead of ML?
1. **Explainability**: SREs and engineers must understand exactly why an alert fired (e.g. `QTime (5120ms) >= 5000ms`).
2. **Cold-Start Resilience**: Machine learning models require clean historical baselines for each query type and node, which do not exist in a new deployment.
3. **Zero False-Positive Drift**: Fixed thresholds with clear severity tiers prevent spurious alerts caused by seasonal traffic variance.
