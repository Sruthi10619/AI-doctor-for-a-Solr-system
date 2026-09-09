from typing import List, Dict, Any
from pydantic import BaseModel, Field
from src.models.events import NormalizedEvent
from src.models.anomalies import Anomaly
from src.models.incidents import Incident
from src.models.ai import DeterministicRCACandidate


class EvidencePackage(BaseModel):
    incident_id: str
    affected_nodes: List[str]
    time_window: str
    observed_anomalies: List[Dict[str, Any]]
    representative_events: List[Dict[str, Any]]
    deterministic_rca_candidates: List[Dict[str, Any]]
    known_facts: List[str]
    uncertainties: List[str]
    data_provenance: Dict[str, str] = Field(
        default_factory=lambda: {"data_source": "synthetic", "environment": "prototype_demo"}
    )


class EvidencePackageBuilder:
    """
    Constructs a structured, sanitized Evidence Package for LLM reasoning.
    Defends against prompt injection by isolating raw text into strict data boundaries.
    """

    @classmethod
    def sanitize_untrusted_text(cls, text: str) -> str:
        """Sanitizes raw log lines to neutralize prompt injection attempts."""
        if not text:
            return ""
        # Neutralize common prompt injection markers
        clean = text.replace("```", "'''").replace("<system>", "[system]").replace("</system>", "[/system]")
        return clean[:300]

    @classmethod
    def build(
        cls,
        incident: Incident,
        anomalies: List[Anomaly],
        events: List[NormalizedEvent]
    ) -> EvidencePackage:
        # Match anomalies for this incident
        inc_anomalies = [a for a in anomalies if a.anomaly_id in incident.anomaly_ids]
        inc_events = [e for e in events if e.event_id in incident.event_ids]

        anomaly_summaries = []
        for a in inc_anomalies:
            anomaly_summaries.append({
                "anomaly_id": a.anomaly_id,
                "node_id": a.node_id,
                "timestamp": a.timestamp.isoformat(),
                "type": a.anomaly_type.value,
                "severity": a.severity.value,
                "condition": a.condition,
                "trigger_metric": a.trigger_metric,
                "trigger_value": a.trigger_value,
                "threshold_value": a.threshold_value,
            })

        event_summaries = []
        # Sample representative events (up to 15) to keep context compact and clean
        for e in inc_events[:15]:
            event_summaries.append({
                "event_id": e.event_id,
                "timestamp": e.timestamp.isoformat(),
                "node_id": e.node_id,
                "source": e.source.value,
                "severity": e.severity.value,
                "event_type": e.event_type,
                "message": cls.sanitize_untrusted_text(e.message),
                "metrics": e.metrics,
            })

        candidate_summaries = []
        for c in incident.deterministic_candidates:
            candidate_summaries.append({
                "candidate_id": c.candidate_id,
                "primary_hypothesis": c.primary_hypothesis,
                "causality_level": c.causality_level.value,
                "confidence_score": c.confidence_score,
                "rule_signature": c.rule_signature,
                "inferred_mechanisms": c.inferred_mechanisms,
            })

        known_facts = [
            f"Incident spans nodes: {', '.join(incident.affected_nodes)}",
            f"Detected {len(inc_anomalies)} deterministic anomalies between {incident.start_time.isoformat()} and {incident.end_time.isoformat()}",
            f"Evaluated {len(incident.deterministic_candidates)} deterministic RCA candidate signatures",
        ]

        uncertainties = [
            "Operating system hardware metrics (CPU load, disk I/O, paging) are not present in provided logs.",
            "Solr cluster-wide ZooKeeper ensemble logs are external to individual node logs.",
            "Business impact and financial metrics cannot be derived from raw technical logs.",
        ]

        return EvidencePackage(
            incident_id=incident.incident_id,
            affected_nodes=incident.affected_nodes,
            time_window=f"{incident.start_time.isoformat()} to {incident.end_time.isoformat()}",
            observed_anomalies=anomaly_summaries,
            representative_events=event_summaries,
            deterministic_rca_candidates=candidate_summaries,
            known_facts=known_facts,
            uncertainties=uncertainties,
        )
