import os

from fastapi.testclient import TestClient

# Force a local SQLite DB for test stability.
os.environ["DATABASE_URL"] = "sqlite:///./autotest_e2e.db"
os.environ["AUTH_ENABLED"] = "false"

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_api_end_to_end_flow():
    _reset_db()

    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        # Seed data runs in lifespan; requirements should be present.
        requirements = client.get("/api/requirements")
        assert requirements.status_code == 200
        requirements_payload = requirements.json()
        assert len(requirements_payload) >= 4

        generated = client.post(
            "/api/scenarios/generate",
            params={"scenario_type": "intersection", "count": 3, "seed": 99},
        )
        assert generated.status_code == 200
        generated_payload = generated.json()
        assert len(generated_payload) == 3
        assert generated_payload[0]["scenario_type"] == "intersection"

        run_result = client.post(
            "/api/runs/execute",
            json={"run_type": "manual", "triggered_by": "pytest", "only_risky": False},
        )
        assert run_result.status_code == 200
        run_payload = run_result.json()
        assert run_payload["total"] >= 1
        assert run_payload["passed"] + run_payload["failed"] == run_payload["total"]

        traceability = client.get("/api/traceability")
        assert traceability.status_code == 200
        trace_payload = traceability.json()
        assert len(trace_payload) >= 1
        assert "requirement_key" in trace_payload[0]
        assert "tests" in trace_payload[0]

        dashboard = client.get("/api/dashboard")
        assert dashboard.status_code == 200
        dashboard_payload = dashboard.json()
        assert "requirement_coverage" in dashboard_payload
        assert "regression_trends" in dashboard_payload
        assert "failure_categories" in dashboard_payload
        assert "test_completeness" in dashboard_payload
        assert "scenario_diversity" in dashboard_payload
        assert "coverage_gaps" in dashboard_payload
        assert "risk_flags" in dashboard_payload
