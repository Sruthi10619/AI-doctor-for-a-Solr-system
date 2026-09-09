# Production Scaling & Evolution Plan

```
PROTOTYPE                                             PRODUCTION
┌─────────────────────────┐                           ┌───────────────────────────────┐
│ Synthetic Log Files     │                           │ Fluentbit / Vector Log Agents │
└───────────┬─────────────┘                           └───────────────┬───────────────┘
            │                                                         │
            ▼                                                         ▼
┌─────────────────────────┐                           ┌───────────────────────────────┐
│ Local Python Process    │                           │ Apache Kafka / Redpanda Stream│
└───────────┬─────────────┘                           └───────────────┬───────────────┘
            │                                                         │
            ▼                                                         ▼
┌─────────────────────────┐                           ┌───────────────────────────────┐
│ In-Memory Sliding Window│                           │ Apache Flink Stream Processor │
└───────────┬─────────────┘                           └───────────────┬───────────────┘
            │                                                         │
            ▼                                                         ▼
┌─────────────────────────┐                           ┌───────────────────────────────┐
│ SQLite DB               │                           │ ClickHouse (Logs) + Postgres  │
└───────────┬─────────────┘                           └───────────────┬───────────────┘
            │                                                         │
            ▼                                                         ▼
┌─────────────────────────┐                           ┌───────────────────────────────┐
│ Single LLM Call         │                           │ LLM Gateway (Rate limit/Cache)│
└─────────────────────────┘                           └───────────────────────────────┘
```

## Scaling Enhancements for High-Volume Production
1. **Streaming Ingestion**: Deploy lightweight Vector / Fluentbit daemons on each Solr node shipping structured JSON to Kafka.
2. **Distributed Stream Correlation**: Use Apache Flink to run sliding temporal windows over millions of events/sec across hundreds of Solr collections.
3. **Hybrid Columnar Storage**: Store high-frequency log metrics in ClickHouse and incident metadata in PostgreSQL.
4. **LLM Cost & Latency Optimization**: Cache identical incident signatures using semantic/exact hash caching to prevent redundant LLM invocations during sustained incidents.
