from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from src.storage.db import EventRecord, AnomalyRecord, IncidentRecord
from src.models.events import NormalizedEvent, LogSource, Severity, ParseStatus
from src.models.anomalies import Anomaly, AnomalySeverity, AnomalyType
from src.models.incidents import Incident, IncidentStatus
from src.models.ai import StructuredRCAResult, DeterministicRCACandidate


class ObservabilityRepository:
    def __init__(self, db: Session):
        self.db = db

    def save_events(self, events: List[NormalizedEvent]) -> int:
        count = 0
        for ev in events:
            # Idempotent insert: skip if already exists
            existing = self.db.query(EventRecord).filter_by(event_id=ev.event_id).first()
            if not existing:
                rec = EventRecord(
                    event_id=ev.event_id,
                    timestamp=ev.timestamp,
                    node_id=ev.node_id,
                    cluster_id=ev.cluster_id,
                    source=ev.source.value,
                    severity=ev.severity.value,
                    event_type=ev.event_type,
                    message=ev.message,
                    raw_message=ev.raw_message,
                    parse_status=ev.parse_status.value,
                    metrics_json=ev.metrics,
                    metadata_json=ev.metadata,
                    data_source=ev.data_source,
                )
                self.db.add(rec)
                count += 1
        self.db.commit()
        return count

    def get_events(self, limit: int = 100, node_id: Optional[str] = None) -> List[NormalizedEvent]:
        query = self.db.query(EventRecord).order_by(EventRecord.timestamp.desc())
        if node_id:
            query = query.filter(EventRecord.node_id == node_id)
        records = query.limit(limit).all()

        events = []
        for r in records:
            events.append(
                NormalizedEvent(
                    event_id=r.event_id,
                    timestamp=r.timestamp,
                    node_id=r.node_id,
                    cluster_id=r.cluster_id,
                    source=LogSource(r.source),
                    severity=Severity(r.severity),
                    event_type=r.event_type,
                    message=r.message,
                    raw_message=r.raw_message,
                    parse_status=ParseStatus(r.parse_status),
                    metrics=r.metrics_json or {},
                    metadata=r.metadata_json or {},
                    data_source=r.data_source or "synthetic",
                )
            )
        return events

    def save_anomalies(self, anomalies: List[Anomaly]) -> int:
        count = 0
        for a in anomalies:
            existing = self.db.query(AnomalyRecord).filter_by(anomaly_id=a.anomaly_id).first()
            if not existing:
                rec = AnomalyRecord(
                    anomaly_id=a.anomaly_id,
                    event_id=a.event_id,
                    node_id=a.node_id,
                    timestamp=a.timestamp,
                    anomaly_type=a.anomaly_type.value,
                    severity=a.severity.value,
                    condition=a.condition,
                    trigger_metric=a.trigger_metric,
                    trigger_value=a.trigger_value,
                    threshold_value=a.threshold_value,
                    reason=a.reason,
                    metadata_json=a.metadata,
                )
                self.db.add(rec)
                count += 1
        self.db.commit()
        return count

    def get_anomalies(self, limit: int = 100) -> List[Anomaly]:
        records = self.db.query(AnomalyRecord).order_by(AnomalyRecord.timestamp.desc()).limit(limit).all()
        anomalies = []
        for r in records:
            anomalies.append(
                Anomaly(
                    anomaly_id=r.anomaly_id,
                    event_id=r.event_id,
                    node_id=r.node_id,
                    timestamp=r.timestamp,
                    anomaly_type=AnomalyType(r.anomaly_type),
                    severity=AnomalySeverity(r.severity),
                    condition=r.condition,
                    trigger_metric=r.trigger_metric,
                    trigger_value=r.trigger_value,
                    threshold_value=r.threshold_value,
                    reason=r.reason,
                    metadata=r.metadata_json or {},
                )
            )
        return anomalies

    def save_incident(self, incident: Incident) -> None:
        rec = self.db.query(IncidentRecord).filter_by(incident_id=incident.incident_id).first()
        cand_data = [c.model_dump() for c in incident.deterministic_candidates]
        rca_data = incident.rca_result.model_dump() if incident.rca_result else None

        if not rec:
            rec = IncidentRecord(
                incident_id=incident.incident_id,
                status=incident.status.value,
                severity=incident.severity.value,
                title=incident.title,
                start_time=incident.start_time,
                end_time=incident.end_time,
                affected_nodes_json=incident.affected_nodes,
                anomaly_ids_json=incident.anomaly_ids,
                event_ids_json=incident.event_ids,
                candidates_json=cand_data,
                rca_json=rca_data,
                created_at=incident.created_at,
                updated_at=incident.updated_at,
            )
            self.db.add(rec)
        else:
            rec.status = incident.status.value
            rec.severity = incident.severity.value
            rec.title = incident.title
            rec.rca_json = rca_data
            rec.candidates_json = cand_data
            rec.updated_at = incident.updated_at

        self.db.commit()

    def get_incidents(self) -> List[Incident]:
        records = self.db.query(IncidentRecord).order_by(IncidentRecord.start_time.desc()).all()
        incidents = []
        for r in records:
            candidates = [DeterministicRCACandidate.model_validate(c) for c in (r.candidates_json or [])]
            rca_res = StructuredRCAResult.model_validate(r.rca_json) if r.rca_json else None
            incidents.append(
                Incident(
                    incident_id=r.incident_id,
                    status=IncidentStatus(r.status),
                    severity=AnomalySeverity(r.severity),
                    title=r.title,
                    start_time=r.start_time,
                    end_time=r.end_time,
                    affected_nodes=r.affected_nodes_json or [],
                    anomaly_ids=r.anomaly_ids_json or [],
                    event_ids=r.event_ids_json or [],
                    deterministic_candidates=candidates,
                    rca_result=rca_res,
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                )
            )
        return incidents

    def get_incident_by_id(self, incident_id: str) -> Optional[Incident]:
        r = self.db.query(IncidentRecord).filter_by(incident_id=incident_id).first()
        if not r:
            return None
        candidates = [DeterministicRCACandidate.model_validate(c) for c in (r.candidates_json or [])]
        rca_res = StructuredRCAResult.model_validate(r.rca_json) if r.rca_json else None
        return Incident(
            incident_id=r.incident_id,
            status=IncidentStatus(r.status),
            severity=AnomalySeverity(r.severity),
            title=r.title,
            start_time=r.start_time,
            end_time=r.end_time,
            affected_nodes=r.affected_nodes_json or [],
            anomaly_ids=r.anomaly_ids_json or [],
            event_ids=r.event_ids_json or [],
            deterministic_candidates=candidates,
            rca_result=rca_res,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )

    def clear_all(self):
        """Clears all records for clean scenario switching."""
        self.db.query(IncidentRecord).delete()
        self.db.query(AnomalyRecord).delete()
        self.db.query(EventRecord).delete()
        self.db.commit()
