from datetime import datetime
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Text, JSON, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from src.config import settings

Base = declarative_base()


class EventRecord(Base):
    __tablename__ = "events"

    event_id = Column(String(64), primary_key=True)
    timestamp = Column(DateTime, index=True, nullable=False)
    node_id = Column(String(64), index=True, nullable=False)
    cluster_id = Column(String(64), default="solr-cluster-prod")
    source = Column(String(32), index=True, nullable=False)
    severity = Column(String(16), nullable=False)
    event_type = Column(String(64), nullable=False)
    message = Column(Text, nullable=False)
    raw_message = Column(Text, nullable=False)
    parse_status = Column(String(32), default="PARSED")
    metrics_json = Column(JSON, default=dict)
    metadata_json = Column(JSON, default=dict)
    data_source = Column(String(32), default="synthetic")


class AnomalyRecord(Base):
    __tablename__ = "anomalies"

    anomaly_id = Column(String(64), primary_key=True)
    event_id = Column(String(64), index=True, nullable=False)
    node_id = Column(String(64), index=True, nullable=False)
    timestamp = Column(DateTime, index=True, nullable=False)
    anomaly_type = Column(String(64), nullable=False)
    severity = Column(String(16), nullable=False)
    condition = Column(Text, nullable=False)
    trigger_metric = Column(String(64), nullable=False)
    trigger_value = Column(Float, nullable=False)
    threshold_value = Column(Float, nullable=False)
    reason = Column(Text, nullable=False)
    metadata_json = Column(JSON, default=dict)


class IncidentRecord(Base):
    __tablename__ = "incidents"

    incident_id = Column(String(64), primary_key=True)
    status = Column(String(32), default="ACTIVE", index=True)
    severity = Column(String(16), nullable=False)
    title = Column(Text, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    affected_nodes_json = Column(JSON, default=list)
    anomaly_ids_json = Column(JSON, default=list)
    event_ids_json = Column(JSON, default=list)
    candidates_json = Column(JSON, default=list)
    rca_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


engine = create_engine(settings.database_url, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)
