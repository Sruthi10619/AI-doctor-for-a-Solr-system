import os
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.config import settings
from src.storage.db import SessionLocal, init_db
from src.storage.repository import ObservabilityRepository
from src.pipeline import ObservabilityPipeline
from src.ai.evidence import EvidencePackageBuilder
from src.ai.llm_provider import get_llm_provider
from src.health.engine import HealthEngine

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Solr AI Doctor & Observability API",
    description="Intelligent Log Observability, Anomaly Detection, Event Correlation & Root Cause Analysis for SolrCloud",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = ObservabilityPipeline()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "solr-ai-doctor",
        "llm_mode": settings.llm_mode,
        "gemini_model": settings.gemini_model_name,
    }


@app.post("/api/pipeline/scenario/{scenario_name}")
async def run_scenario_endpoint(scenario_name: str, run_llm: bool = True):
    """Loads and processes one of the 5 synthetic demonstration scenarios."""
    valid_scenarios = ["healthy", "gc_pressure", "solr_failure", "query_latency", "mixed_incident"]
    if scenario_name not in valid_scenarios:
        raise HTTPException(status_code=400, detail=f"Invalid scenario. Choose from: {valid_scenarios}")

    result = await pipeline.run_scenario(scenario_name, run_llm=run_llm)
    return result


class IngestPayload(BaseModel):
    solr_logs: Optional[str] = ""
    gc_logs: Optional[str] = ""
    node_id: str = "solr-node-1"
    run_llm: bool = True


@app.post("/api/pipeline/ingest")
async def ingest_logs_endpoint(payload: IngestPayload):
    """Ingests raw text logs and executes the complete analysis pipeline."""
    solr_lines = [l for l in payload.solr_logs.splitlines() if l.strip()]
    gc_lines = [l for l in payload.gc_logs.splitlines() if l.strip()]

    result = await pipeline.run_on_lines(
        solr_lines=solr_lines,
        gc_lines=gc_lines,
        default_node=payload.node_id,
        run_llm=payload.run_llm
    )
    return result


@app.get("/api/cluster/health")
def get_cluster_health(db: Session = Depends(get_db)):
    repo = ObservabilityRepository(db)
    events = repo.get_events(limit=500)
    anomalies = repo.get_anomalies(limit=200)
    incidents = repo.get_incidents()

    all_nodes = sorted(list({e.node_id for e in events} | {"solr-node-1", "solr-node-2", "solr-node-3"}))
    cluster_health = HealthEngine.evaluate_cluster_health(
        nodes=all_nodes,
        events=events,
        anomalies=anomalies,
        incidents=incidents
    )
    return cluster_health.model_dump()


@app.get("/api/incidents")
def list_incidents(db: Session = Depends(get_db)):
    repo = ObservabilityRepository(db)
    incidents = repo.get_incidents()
    return [inc.model_dump() for inc in incidents]


@app.get("/api/incidents/{incident_id}")
def get_incident_detail(incident_id: str, db: Session = Depends(get_db)):
    repo = ObservabilityRepository(db)
    incident = repo.get_incident_by_id(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident.model_dump()


@app.post("/api/incidents/{incident_id}/rca")
async def trigger_incident_rca(incident_id: str, db: Session = Depends(get_db)):
    repo = ObservabilityRepository(db)
    incident = repo.get_incident_by_id(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    events = repo.get_events(limit=500)
    anomalies = repo.get_anomalies(limit=200)

    evidence = EvidencePackageBuilder.build(incident, anomalies, events)
    primary_cand = incident.deterministic_candidates[0] if incident.deterministic_candidates else None
    inc_anomalies = [a for a in anomalies if a.anomaly_id in incident.anomaly_ids]

    llm_provider = get_llm_provider()
    rca_res = await llm_provider.analyze(evidence, inc_anomalies, primary_cand)

    incident.rca_result = rca_res
    repo.save_incident(incident)

    return rca_res.model_dump()


@app.get("/api/anomalies")
def list_anomalies(limit: int = 100, db: Session = Depends(get_db)):
    repo = ObservabilityRepository(db)
    anomalies = repo.get_anomalies(limit=limit)
    return [a.model_dump() for a in anomalies]


@app.get("/api/events")
def list_events(limit: int = 100, node_id: Optional[str] = None, db: Session = Depends(get_db)):
    repo = ObservabilityRepository(db)
    events = repo.get_events(limit=limit, node_id=node_id)
    return [e.model_dump() for e in events]


# Static Dashboard Mount
DASHBOARD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "dashboard")
if os.path.exists(DASHBOARD_DIR):
    app.mount("/static", StaticFiles(directory=DASHBOARD_DIR), name="static")


@app.get("/")
def serve_dashboard():
    index_path = os.path.join(DASHBOARD_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Solr AI Doctor Backend API Online. Dashboard directory not found."}
