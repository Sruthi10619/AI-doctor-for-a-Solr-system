# Solr AI Doctor — Observability & Root Cause Analysis Platform

An intelligent, deterministic-first, AI-assisted observability and Root Cause Analysis (RCA) platform for distributed **Apache SolrCloud** clusters and **JVM Garbage Collection** environments.

---

## 🚀 Key Architecture Highlights

- **Deterministic-First Pipeline**: Log Ingestion $\to$ State Machine Regex Parsing $\to$ Canonical Normalization $\to$ Deterministic Anomaly Detection $\to$ Temporal & Topology Correlation $\to$ Deterministic RCA Candidates $\to$ Grounded LLM Synthesis.
- **Explainable Health Scoring**: Transparent, deduction-based Node & Cluster health scoring (0-100) with diagnostic breakdown.
- **Explicit AI & Prompt Defense**: Dual-mode LLM engine (Google Gemini API + Deterministic Mock Fallback) with strict anti-prompt-injection boundaries.
- **Glassmorphism UI**: Interactive dark-mode dashboard with cluster health gauges, incident inspection drawer, and cross-source cascade timeline.

---

## 📦 Quick Start & Demo Replay

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Automated Test Suite
```bash
python -m pytest tests/ -v
```

### 3. Start the Application & UI
```bash
uvicorn src.api.app:app --reload --port 8000
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser.

---

## 🎯 Included Synthetic Scenarios
1. **Healthy Cluster**: Baseline query traffic, minor GC pauses (< 20ms), 100% health.
2. **JVM GC Memory Pressure**: Escalating heap utilization $\to$ Full GC Stop-The-World pauses (2.4s - 6.4s) $\to$ query timeouts.
3. **Solr Node Failure**: ZooKeeper session expiration $\to$ replica marked DOWN $\to$ cross-node connection refused errors.
4. **Query Latency Spike**: Unoptimized leading wildcard queries (`*a*b*c*`) causing latency threshold breaches (QTime > 5000ms).
5. **Mixed Incident (Cascade Failure)**: Node 2 suffers a 4.85s Full GC pause $\to$ query thread timeout $\to$ ZK heartbeat loss $\to$ Node 1 replica read failure.

---

## 📚 Documentation Index
- [docs/CASE_STUDY_ANALYSIS.md](docs/CASE_STUDY_ANALYSIS.md) — Problem statement, requirements matrix, and evaluation criteria.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — Complete end-to-end component architecture and data flow.
- [docs/DETECTION_LOGIC.md](docs/DETECTION_LOGIC.md) — Deterministic anomaly detection conditions and thresholds.
- [docs/CORRELATION.md](docs/CORRELATION.md) — Multi-dimensional temporal & topology correlation and RCA candidate rules.
- [docs/AI_DESIGN.md](docs/AI_DESIGN.md) — Grounded LLM reasoning, evidence packaging, and anti-hallucination controls.
- [docs/SECURITY.md](docs/SECURITY.md) — Prompt injection defense and untrusted log boundary isolation.
- [docs/TRADE_OFFS.md](docs/TRADE_OFFS.md) — Detailed rationale behind engineering design decisions.
- [docs/LIMITATIONS.md](docs/LIMITATIONS.md) — Known constraints and assumptions.
- [docs/PRODUCTION_SCALING.md](docs/PRODUCTION_SCALING.md) — Production architecture roadmap (Kafka, Flink, ClickHouse).
- [docs/INTERVIEW_GUIDE.md](docs/INTERVIEW_GUIDE.md) — Comprehensive technical Q&A and architecture defense guide.
