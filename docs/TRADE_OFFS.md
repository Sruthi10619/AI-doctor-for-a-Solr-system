# Architectural Trade-Offs

## 1. Deterministic Rules vs Deep Learning Anomaly Detection
- **Decision**: Used deterministic configurable threshold rules.
- **Trade-off**: Requires initial threshold configuration, but provides 100% explainability, sub-millisecond execution, zero training overhead, and eliminates false-alarm hallucination.
- **Alternative Rejected**: Unsupervised LSTM/Autoencoders rejected due to cold-start issues, opacity to SREs, and high compute overhead.

## 2. Sliding Window vs Graph Database Correlation
- **Decision**: In-memory temporal window (90s) + node topology clustering.
- **Trade-off**: Does not store infinite historical graph links, but handles cascade clustering in $O(N \log N)$ time with zero external infrastructure.
- **Alternative Rejected**: Neo4j / Graph DBs rejected for prototype due to operational complexity and maintenance overhead.

## 3. SQLite + Repository Pattern vs Distributed Elasticsearch
- **Decision**: SQLite with SQLAlchemy ORM using clean Repository abstraction.
- **Trade-off**: Limited to single-node storage for the prototype, but provides zero-dependency setup with complete portability to PostgreSQL or ClickHouse.
- **Alternative Rejected**: Elasticsearch rejected because running an external search engine just to observe a search engine is recursive overhead for a prototype.

## 4. Vanilla Glassmorphism UI vs Heavy Frontend Framework
- **Decision**: Vanilla HTML5 / CSS3 / ES6 JavaScript.
- **Trade-off**: No React component lifecycle ecosystem, but zero build step (`npm run build`), instant hot reloading, and native embedding in FastAPI static routes.
