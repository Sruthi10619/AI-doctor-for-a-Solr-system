# Case Study Analysis: Solr Observability & Grounded AI RCA

## 1. Problem Statement
The client operates a distributed **SolrCloud cluster** across multiple Linux servers. 
Currently, engineers investigate production issues by manually reading raw **Solr logs** and **JVM Garbage Collection (GC) logs**. This reactive manual approach is:
- **Slow and unscalable**: Triaging cascades during multi-node incidents takes hours.
- **Cognitively heavy**: Requires mental cross-referencing of asynchronous timestamps across heterogeneous log formats.
- **Prone to misdiagnosis**: Symptoms (e.g. query timeouts) are routinely confused with root causes (e.g. Stop-The-World Full GC pauses or ZooKeeper session drops).

## 2. Requirements Matrix

| Requirement | Operational Interpretation | Technical Implementation in Solr AI Doctor |
| :--- | :--- | :--- |
| **Solr log parsing** | Extract queries, QTimes, errors, replica state transitions, and context | `SolrLogParser` with explicit `PARSED`/`PARTIALLY_PARSED`/`UNPARSED` states |
| **JVM GC parsing** | Extract GC event type (Minor/Full), pause durations, and memory before/after | `GCLogParser` calculating heap occupancy % and pause metrics in milliseconds |
| **Event Normalization** | Create canonical representation across heterogeneous sources | `NormalizedEvent` with idempotent SHA-256 fingerprinting |
| **Anomaly Detection** | Identify meaningful threshold breaches without false positive alarms | `AnomalyDetectionEngine` with configurable thresholds in `src/config.py` |
| **Event Correlation** | Connect related events across time windows and cluster topology | `CorrelationEngine` using sliding temporal window (90s) & node/shard mapping |
| **Deterministic RCA** | Formulate grounded root cause hypotheses prior to any AI call | `DeterministicRCAGenerator` evaluating rule signatures across anomaly clusters |
| **Node Health** | Evaluate individual node condition with transparent scoring | `HealthEngine.evaluate_node_health()` calculating score (0-100) & primary issues |
| **Cluster Health** | Aggregate node conditions into an executive cluster status | `HealthEngine.evaluate_cluster_health()` roll-up with primary concern diagnosis |
| **Grounded AI / RCA** | Reason over structured evidence, explain mechanisms, and avoid hallucinations | `GeminiLLMProvider` / `DeterministicMockLLMProvider` with strict Pydantic JSON schema |
| **Impact & Remediation**| Provide realistic operational impact and runbook actions | `RemediationEngine` mapping incident signatures to vetted immediate & preventative steps |
| **Dashboard / API** | Present health, timeline, and incident deep-dives in real time | FastAPI backend + Vanilla JS/HTML5 Dark Glassmorphism Dashboard |

## 3. Inputs, Outputs & Constraints
- **Inputs**: Raw Solr application logs and Hotspot/OpenJDK JVM GC logs.
- **Outputs**: Normalized events, detected anomalies, clustered incidents, node/cluster health cards, structured RCA evidence package, runbook actions, and interactive UI.
- **Constraints**:
  1. No client logs provided $\to$ Deterministic synthetic fixtures generated.
  2. Same-day prototype $\to$ Zero unnecessary infrastructure (no Kafka, Redis, Elasticsearch, or heavy ML setups).
  3. LLM is not ground truth $\to$ Deterministic-first architecture with transparent provenance.
