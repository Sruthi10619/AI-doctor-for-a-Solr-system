import pytest
from fastapi.testclient import TestClient
from src.api.app import app
from src.pipeline import ObservabilityPipeline

client = TestClient(app)


def test_api_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "llm_mode" in data


@pytest.mark.asyncio
async def test_pipeline_all_scenarios():
    pipeline = ObservabilityPipeline()

    scenarios = ["healthy", "gc_pressure", "solr_failure", "query_latency", "mixed_incident"]
    for sc in scenarios:
        res = await pipeline.run_scenario(sc, run_llm=True)
        assert res["events_processed"] > 0
        assert "cluster_health" in res
        assert "incidents" in res

        # Specific scenario validation
        if sc == "healthy":
            assert res["cluster_health"]["state"] == "HEALTHY"
            assert res["anomalies_detected"] == 0
        elif sc == "mixed_incident":
            assert len(res["incidents"]) > 0
            assert res["cluster_health"]["state"] in ("WARNING", "CRITICAL")
            inc = res["incidents"][0]
            assert inc["rca_result"] is not None
            assert inc["rca_result"]["confidence"] >= 0.80


def test_api_scenario_runner():
    res = client.post("/api/pipeline/scenario/gc_pressure")
    assert res.status_code == 200
    data = res.json()
    assert data["events_processed"] > 0

    # Query cluster health
    h_res = client.get("/api/cluster/health")
    assert h_res.status_code == 200
    assert h_res.json()["warning_nodes_count"] > 0 or h_res.json()["critical_nodes_count"] > 0

    # Query incidents
    inc_res = client.get("/api/incidents")
    assert inc_res.status_code == 200
    incidents = inc_res.json()
    assert len(incidents) > 0
