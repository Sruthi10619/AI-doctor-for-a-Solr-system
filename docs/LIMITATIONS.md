# System Limitations

1. **Synthetic Data**: The assignment did not provide real production Solr or JVM GC logs. Synthetic fixtures were used for verification.
2. **Heuristic Thresholds**: Detection thresholds (e.g. QTime > 1000ms, GC Pause > 1000ms) are prototype heuristics and must be calibrated to real production workloads.
3. **Business Impact Telemetry**: Business revenue loss or conversion impact cannot be calculated without access to business event streams.
4. **Log Format Variations**: Parsers support representative standard Solr and Hotspot/OpenJDK GC log formats; custom Log4j2 formats will require regex schema additions.
5. **Causality vs Correlation**: While rule signatures verify mechanism alignment, full causal proof requires kernel-level tracing (eBPF) or memory heap dump analysis.
