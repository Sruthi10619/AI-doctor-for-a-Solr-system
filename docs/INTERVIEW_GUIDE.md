# Interview Defense Guide

## Core Talking Points

### 1. "Why not just feed raw logs directly into an LLM?"
> *"Feeding raw logs directly to an LLM is a weak demo pattern. It is expensive, slow, hits token context limits, and hallucinates causality. Our architecture uses deterministic parsing, threshold anomaly detection, and temporal correlation to build a structured Evidence Package first. The LLM is only used at the very end to reason over verified facts, synthesize the mechanism, and explain impact."*

### 2. "Why deterministic anomaly detection instead of ML?"
> *"In production systems, explainability and zero-cold-start are critical. Deterministic rules with configurable thresholds guarantee that every alert is reproducible and traceable (e.g. QTime 5120ms > 5000ms threshold). ML models suffer from baseline drift and opacity."*

### 3. "How do you distinguish correlation from causation?"
> *"We classify events into 5 levels: OBSERVED, CORRELATED, LIKELY_CAUSAL, HYPOTHESIS, and UNKNOWN. We only rate something as LIKELY_CAUSAL when known mechanisms (e.g. Stop-The-World GC pause immediately preceding request timeouts on the same node) are verified by our rule matrix."*

### 4. "How do you defend against prompt injection in logs?"
> *"Logs are untrusted input. We strip code fences and control characters, isolate log text into strict JSON boundaries, and instruct the LLM system prompt that all evidence is untrusted data that must never be treated as system directives."*

### 5. "What happens if the LLM is offline?"
> *"The system is resilient. If the LLM is unavailable or unconfigured, the pipeline executes an explicit deterministic candidate generator that produces grounded root cause analysis, confidence scores, and runbook actions without crashing."*
