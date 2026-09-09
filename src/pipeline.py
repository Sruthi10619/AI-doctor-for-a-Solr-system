import time
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.parsers.solr_parser import SolrLogParser
from src.parsers.gc_parser import GCLogParser
from src.detection.engine import AnomalyDetectionEngine
from src.correlation.engine import CorrelationEngine
from src.health.engine import HealthEngine
from src.ai.evidence import EvidencePackageBuilder
from src.ai.llm_provider import get_llm_provider
from src.storage.db import SessionLocal, init_db
from src.storage.repository import ObservabilityRepository
from src.models.events import NormalizedEvent
from src.models.anomalies import Anomaly
from src.models.incidents import Incident
from src.models.health import ClusterHealth, NodeHealth


class ObservabilityPipeline:
    def __init__(self):
        init_db()
        self.solr_parser = SolrLogParser()
        self.gc_parser = GCLogParser()
        self.anomaly_detector = AnomalyDetectionEngine()
        self.correlation_engine = CorrelationEngine()
        self.llm_provider = get_llm_provider()

    async def run_on_lines(
        self,
        solr_lines: List[str],
        gc_lines: List[str],
        default_node: str = "solr-node-1",
        run_llm: bool = True
    ) -> Dict[str, Any]:
        start_time = time.time()
        db = SessionLocal()
        repo = ObservabilityRepository(db)

        try:
            # 1. Parsing & Normalization
            events: List[NormalizedEvent] = []
            if solr_lines:
                events.extend(self.solr_parser.parse_lines(solr_lines, default_node))
            if gc_lines:
                events.extend(self.gc_parser.parse_lines(gc_lines, default_node))

            # 2. Persist Events
            events_saved = repo.save_events(events)

            # 3. Anomaly Detection
            anomalies: List[Anomaly] = self.anomaly_detector.detect_anomalies(events)
            anomalies_saved = repo.save_anomalies(anomalies)

            # 4. Correlation & Incident Construction with Deterministic RCA Candidates
            incidents: List[Incident] = self.correlation_engine.correlate(anomalies, events)

            # 5. Optional / Configured LLM RCA Execution
            if run_llm:
                for inc in incidents:
                    evidence = EvidencePackageBuilder.build(inc, anomalies, events)
                    primary_cand = inc.deterministic_candidates[0] if inc.deterministic_candidates else None
                    inc_anomalies = [a for a in anomalies if a.anomaly_id in inc.anomaly_ids]
                    
                    rca_res = await self.llm_provider.analyze(
                        evidence=evidence,
                        anomalies=inc_anomalies,
                        primary_candidate=primary_cand
                    )
                    inc.rca_result = rca_res
                    repo.save_incident(inc)
            else:
                for inc in incidents:
                    repo.save_incident(inc)

            # 6. Health Scoring
            all_nodes = sorted(list({e.node_id for e in events} | {"solr-node-1", "solr-node-2", "solr-node-3"}))
            cluster_health: ClusterHealth = HealthEngine.evaluate_cluster_health(
                nodes=all_nodes,
                events=events,
                anomalies=anomalies,
                incidents=incidents
            )

            elapsed_ms = (time.time() - start_time) * 1000.0

            return {
                "pipeline_execution_ms": round(elapsed_ms, 2),
                "events_processed": len(events),
                "events_saved": events_saved,
                "anomalies_detected": len(anomalies),
                "incidents_created": len(incidents),
                "cluster_health": cluster_health.model_dump(),
                "incidents": [inc.model_dump() for inc in incidents],
                "parser_stats": {
                    "solr": self.solr_parser.stats.model_dump(),
                    "gc": self.gc_parser.stats.model_dump(),
                },
            }
        finally:
            db.close()

    async def run_scenario(self, scenario_name: str, run_llm: bool = True) -> Dict[str, Any]:
        base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "synthetic", scenario_name)
        solr_path = os.path.join(base_dir, "solr.log")
        gc_path = os.path.join(base_dir, "jvm_gc.log")

        solr_lines = []
        if os.path.exists(solr_path):
            with open(solr_path, "r", encoding="utf-8") as f:
                solr_lines = f.readlines()

        gc_lines = []
        if os.path.exists(gc_path):
            with open(gc_path, "r", encoding="utf-8") as f:
                gc_lines = f.readlines()

        # Clear previous run to provide clean demo state
        db = SessionLocal()
        ObservabilityRepository(db).clear_all()
        db.close()

        return await self.run_on_lines(solr_lines, gc_lines, run_llm=run_llm)
