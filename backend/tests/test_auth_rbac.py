from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def test_rbac_matrix_for_core_endpoints():
    settings = get_settings()
    original = {
        "auth_enabled": settings.auth_enabled,
        "viewer_api_key": settings.viewer_api_key,
        "engineer_api_key": settings.engineer_api_key,
        "admin_api_key": settings.admin_api_key,
    }

    settings.auth_enabled = True
    settings.viewer_api_key = "viewer-key"
    settings.engineer_api_key = "engineer-key"
    settings.admin_api_key = "admin-key"

    try:
        with TestClient(app) as client:
            no_key = client.get("/api/dashboard")
            assert no_key.status_code == 401

            invalid_key = client.get("/api/dashboard", headers={"X-API-Key": "bad-key"})
            assert invalid_key.status_code == 401

            viewer_dashboard = client.get("/api/dashboard", headers={"X-API-Key": "viewer-key"})
            assert viewer_dashboard.status_code == 200

            viewer_execute = client.post(
                "/api/runs/execute",
                headers={"X-API-Key": "viewer-key"},
                json={"run_type": "manual", "triggered_by": "viewer", "only_risky": False},
            )
            assert viewer_execute.status_code == 403

            engineer_execute = client.post(
                "/api/runs/execute",
                headers={"X-API-Key": "engineer-key"},
                json={"run_type": "manual", "triggered_by": "engineer", "only_risky": False},
            )
            assert engineer_execute.status_code == 200

            engineer_scheduler = client.post(
                "/api/scheduler/run-nightly",
                headers={"X-API-Key": "engineer-key"},
            )
            assert engineer_scheduler.status_code == 403

            admin_scheduler = client.post(
                "/api/scheduler/run-nightly",
                headers={"X-API-Key": "admin-key"},
            )
            assert admin_scheduler.status_code == 200
    finally:
        settings.auth_enabled = original["auth_enabled"]
        settings.viewer_api_key = original["viewer_api_key"]
        settings.engineer_api_key = original["engineer_api_key"]
        settings.admin_api_key = original["admin_api_key"]
