# System Architecture: Solr AI Doctor

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           1. INGESTION & PARSING                                │
│                                                                                 │
│   Solr Application Logs                         HotSpot / OpenJDK GC Logs       │
│          │                                                  │                   │
│          ▼                                                  ▼                   │
│   ┌───────────────┐                                  ┌───────────────┐          │
│   │ SolrLogParser │                                  │  GCLogParser  │          │
│   └───────┬───────┘                                  └───────┬───────┘          │
└───────────┼──────────────────────────────────────────────────┼──────────────────┘
            │                                                  │
            ▼                                                  ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           2. EVENT NORMALIZATION                                │
│                                                                                 │
│   NormalizedEvent Model (event_id: SHA256 Fingerprint, source, severity,         │
│                          metrics: [qtime, pause_ms, heap_pct], metadata)        │
│   ──► Persisted to SQLite (Idempotent Deduplication)                            │
└───────────────────────────────────┬─────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      3. DETERMINISTIC ANOMALY DETECTION                         │
│                                                                                 │
│   AnomalyDetectionEngine: Evaluates configurable thresholds                     │
│   - Solr QTime > 1000ms (WARN), > 5000ms (CRITICAL)                             │
│   - JVM GC Pause > 1000ms (WARN), > 3000ms (CRITICAL)                           │
│   - Heap Occupancy > 80% (WARN), > 92% (CRITICAL)                               │
│   - Replica state transitions & ZooKeeper disconnects                           │
│   ──► Persisted to SQLite                                                       │
└───────────────────────────────────┬─────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                 4. TEMPORAL & TOPOLOGY CORRELATION ENGINE                       │
│                                                                                 │
│   Sliding Time Window (90s) + Topology (Node / Shard Proximity)                │
│   ──► Multi-anomaly clustering                                                  │
│   ──► Deterministic RCA Candidate Generator (Rule Matrix Evaluation)            │
│   ──► Incident Construction & Lifecycle (ACTIVE / RESOLVED / REOPENED)          │
└───────────────────┬───────────────────────────────────────┬─────────────────────┘
                    │                                       │
                    ▼                                       ▼
┌───────────────────────────────────┐   ┌─────────────────────────────────────────┐
│   5. NODE & CLUSTER HEALTH        │   │        6. STRUCTURED EVIDENCE           │
│                                   │   │                                         │
│   - NodeHealth: Score (0 - 100)   │   │   EvidencePackageBuilder                │
│     with transparent deductions   │   │   - Sanitized observed facts            │
│   - ClusterHealth: Roll-up score  │   │   - Telemetry metrics & timeline        │
│     and primary concern summary   │   │   - Deterministic RCA Candidates        │
│                                   │   │   - Anti-prompt-injection wrappers      │
└───────────────────────────────────┘   └───────────────────┬─────────────────────┘
                                                            │
                                                            ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          7. GROUNDED AI / RCA ENGINE                            │
│                                                                                 │
│   BaseLLMProvider                                                               │
│   ├── GeminiLLMProvider (Live Gemini model with strict JSON schema)             │
│   └── DeterministicMockLLMProvider (Explicit offline fallback for test/CI)      │
│                                                                                 │
│   Output: Root cause, Confidence + Reason, Causality assessment,                │
│           Inferred mechanisms, Vetted runbook remediations                      │
└───────────────────────────────────┬─────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          8. REST API & DASHBOARD                                │
│                                                                                 │
│   FastAPI Endpoints (Ingest, Scenario replay, Health, Incidents, Detail RCA)   │
│   Vanilla JS/HTML5 Dark Glassmorphism UI (Health gauges, Incident drawer,       │
│                                           Cascade timeline)                     │
└─────────────────────────────────────────────────────────────────────────────────┘
```
