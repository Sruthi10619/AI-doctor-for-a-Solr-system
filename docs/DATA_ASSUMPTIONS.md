# Data Assumptions & Provenance

## Absence of Supplied Production Logs
The assignment did not provide production Solr or JVM GC log samples. Representative, deterministic synthetic fixtures were created in `data/synthetic/` to demonstrate the complete end-to-end architecture, verify rule thresholds, and provide reproducible testing.

All events ingested by the system are stamped with explicit provenance metadata:
```json
{
  "data_source": "synthetic",
  "environment": "prototype_demo"
}
```

## Synthetic Data Scenarios
1. **Scenario 1 — Healthy**:
   - Regular search traffic across 3 nodes.
   - Normal QTime (15ms - 39ms).
   - Minor Young Gen GCs (12ms - 21ms pause).
   - Zero errors, 100% cluster health.

2. **Scenario 2 — JVM Memory Pressure**:
   - Heavy facet queries escalating heap occupancy from 50% to 96%.
   - Full GC pauses escalating from 2.4s to 6.4s.
   - Stop-the-world pauses causing QTime degradation (> 5000ms) and timeouts.

3. **Scenario 3 — Solr Node Failure**:
   - ZooKeeper connection lost / session expired.
   - Overseer marking replica as `DOWN`.
   - Client requests throwing `SolrServerException: Connection refused`.

4. **Scenario 4 — Query Latency Spike**:
   - Unoptimized wildcard query (`*a*b*c*`) with deep paging (`start=50000`).
   - QTime escalating to 7000ms with normal GC behavior (pure query execution bottleneck).

5. **Scenario 5 — Mixed Incident (Cross-Source Cascade)**:
   - Node 2 experiences JVM memory buildup and a 4.85s Full GC pause.
   - Request handler on Node 2 times out waiting for thread lock.
   - ZooKeeper session expires during the GC pause.
   - Node 1 fails to query Node 2 replica (`SocketTimeoutException`).

## Heuristic Threshold Assumptions
All detection thresholds in `src/config.py` are illustrative heuristics for the prototype:
- `SOLR_QTIME_WARN_MS`: 1000ms
- `SOLR_QTIME_CRIT_MS`: 5000ms
- `GC_PAUSE_WARN_MS`: 1000ms
- `GC_PAUSE_CRIT_MS`: 3000ms
- `HEAP_USAGE_WARN_PCT`: 80.0%
- `HEAP_USAGE_CRIT_PCT`: 92.0%
- `CORRELATION_WINDOW_SECONDS`: 90 seconds

*Production note*: In real production deployments, thresholds must be dynamically tuned per collection based on historical percentiles (p95/p99) and client Service Level Objectives (SLOs).
