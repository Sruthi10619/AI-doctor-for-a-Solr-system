# Synthetic Data Provenance & Structure

## Provenance Declaration
**IMPORTANT**: The case study does NOT provide real production Solr or JVM GC logs.
All datasets in this directory are **strictly synthetic and deterministically generated** for testing the complete Solr AI Doctor pipeline.

Provenance metadata attached to all ingested events:
```json
{
  "data_source": "synthetic",
  "environment": "prototype_demo"
}
```

## Scenarios
1. `healthy/`: Baseline healthy cluster operation (low QTime, minor GC pauses < 20ms, zero errors).
2. `gc_pressure/`: Heavy memory utilization leading to Stop-The-World Full GCs (2.4s - 6.4s) and subsequent Solr request timeouts.
3. `solr_failure/`: ZooKeeper connection loss, replica marked down, cross-node connection refused errors.
4. `query_latency/`: Unoptimized wildcard search queries causing latency threshold breaches (QTime > 5000ms).
5. `mixed_incident/`: Cross-source cascade failure where `solr-node-2` undergoes a 4.85s Full GC pause, triggering query timeouts and replica read timeouts from `solr-node-1`.
