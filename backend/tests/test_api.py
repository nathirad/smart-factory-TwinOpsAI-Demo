import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import main  # noqa: E402


client = TestClient(main.app)


def reset_state():
    main.APP_MODE = "mock"
    main.CMMS_DISPATCH_WEBHOOK_URL = None
    main.WORK_ORDER_SYSTEM_NAME = "In-memory Work Order Queue"
    main.DASHBOARD_DATA_ENDPOINT = None
    main.ALERTS_DATA_ENDPOINT = None
    main.REPORTS_DATA_ENDPOINT = None
    main.app_state["is_anomaly_active"] = False
    main.app_state["anomaly_start_time"] = 0
    main.app_state["latest_ingested_data"] = None
    main.app_state["work_orders"] = {}
    main.app_state["next_work_order_sequence"] = 1


@pytest.fixture(autouse=True)
def clean_state():
    reset_state()
    yield
    reset_state()


def test_openapi_is_available():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/telemetry" in paths
    assert "/api/dashboard" in paths
    assert "/api/work-orders" in paths
    assert "/api/agent/trigger" in paths
    assert "/api/energy/insights" in paths


def test_ingest_telemetry_stores_latest_payload_and_triggers_anomaly():
    payload = {
        "device_id": "motor-A",
        "timestamp": "2026-05-11 10:24:30",
        "data": {
            "vibration": 3.4,
            "temperature": 78.2,
            "load": 91.0,
            "status": "Critical",
        },
    }

    response = client.post("/api/ingest-telemetry", json=payload)
    telemetry = client.get("/api/telemetry").json()

    assert response.status_code == 200
    assert response.json()["status"] == "received"
    assert main.app_state["is_anomaly_active"] is True
    assert telemetry["motor_A"]["status"] == "Critical"


def test_telemetry_returns_three_assets_in_normal_state():
    response = client.get("/api/telemetry")
    data = response.json()

    assert response.status_code == 200
    assert data["motor_A"]["status"] == "Normal"
    assert data["motor_B"]["status"] == "Normal"
    assert data["conveyor_C"]["status"] == "Normal"


def test_trigger_and_reset_anomaly_change_demo_state():
    trigger_response = client.post("/api/trigger-anomaly")
    critical_telemetry = client.get("/api/telemetry").json()

    reset_response = client.post("/api/reset-anomaly")
    normal_telemetry = client.get("/api/telemetry").json()

    assert trigger_response.status_code == 200
    assert critical_telemetry["motor_A"]["status"] == "Critical"
    assert reset_response.status_code == 200
    assert normal_telemetry["motor_A"]["status"] == "Normal"


def test_digital_twin_reflects_stable_and_critical_state():
    stable = client.get("/api/digital-twin").json()

    client.post("/api/trigger-anomaly")
    critical = client.get("/api/digital-twin").json()

    assert stable["line_status"] == "Stable"
    assert stable["failure_risk"] == "Low"
    assert critical["line_status"] == "Critical"
    assert critical["failure_risk"] == "High"
    assert critical["downstream_impact"]["Conveyor_C"] == "At Risk (Reduced Input)"


def test_analyze_returns_low_without_anomaly_and_high_with_anomaly():
    stable = client.get("/api/analyze").json()

    client.post("/api/trigger-anomaly")
    critical = client.get("/api/analyze").json()

    assert stable["risk_level"] == "Low"
    assert stable["recommended_actions"] == []
    assert critical["risk_level"] == "High"
    assert critical["retrieved_sop"]["document_id"]
    assert len(critical["recommended_actions"]) >= 1


def test_analyze_is_stable_within_an_active_anomaly_scenario():
    client.post("/api/trigger-anomaly")

    first = client.get("/api/analyze").json()
    main.app_state["latest_ingested_data"] = {
        "vibration": 3.8,
        "temperature": 82.0,
        "load": 95.0,
        "status": "Critical",
    }
    second = client.get("/api/analyze").json()

    assert second == first


def test_dashboard_alerts_oee_and_energy_in_normal_state():
    dashboard = client.get("/api/dashboard").json()
    alerts = client.get("/api/alerts").json()
    oee = client.get("/api/oee").json()
    energy = client.get("/api/energy").json()

    assert dashboard["line"]["status"] == "Stable"
    assert dashboard["oee"]["current"] == 87
    assert dashboard["energy"]["current_kw"] == 590
    assert dashboard["asset_health"][0]["status"] == "normal"
    assert alerts["alerts"][0]["severity"] == "Low"
    assert oee["oee"]["current"] == 87
    assert energy["energy"]["current_kw"] == 590


def test_dashboard_and_alerts_reflect_anomaly_state():
    client.post("/api/trigger-anomaly")

    dashboard = client.get("/api/dashboard").json()
    alerts = client.get("/api/alerts").json()["alerts"]

    assert dashboard["line"]["status"] == "Critical"
    assert dashboard["oee"]["current"] == 76
    assert dashboard["energy"]["current_kw"] == 735
    assert dashboard["asset_health"][0]["status"] == "critical"
    assert [alert["severity"] for alert in alerts] == ["High", "Medium"]


def test_dashboard_production_mode_uses_external_json_when_available(monkeypatch):
    main.APP_MODE = "production"
    external_dashboard = {
        "mode": "production",
        "source": "external",
        "line": {"status": "External"},
    }

    monkeypatch.setattr(main, "fetch_external_json", lambda endpoint: external_dashboard)
    main.DASHBOARD_DATA_ENDPOINT = "https://example.test/dashboard"

    response = client.get("/api/dashboard")

    assert response.status_code == 200
    assert response.json() == external_dashboard


def test_work_order_requires_active_anomaly():
    response = client.post("/api/work-orders")

    assert response.status_code == 409
    assert "No active anomaly" in response.json()["detail"]


def test_work_order_lifecycle_in_mock_mode():
    client.post("/api/trigger-anomaly")

    create_response = client.post(
        "/api/work-orders",
        json={
            "recommendation_id": 1,
            "action": "Inspect within 24 hours",
            "assignee": "Maintenance Team",
            "due": "Within 24 hours",
        },
    )
    created = create_response.json()
    work_order_id = created["id"]

    detail_response = client.get(f"/api/work-orders/{work_order_id}")
    approve_response = client.post(
        f"/api/work-orders/{work_order_id}/approve",
        json={"approved_by": "Shift Supervisor", "note": "Safety confirmed."},
    )
    dispatch_response = client.post(
        f"/api/work-orders/{work_order_id}/dispatch",
        json={"dispatched_by": "Maintenance Coordinator"},
    )
    queue_response = client.get("/api/work-orders")

    assert create_response.status_code == 200
    assert created["status"] == "Awaiting approval"
    assert created["dispatchStatus"] == "Not dispatched"
    assert detail_response.json()["id"] == work_order_id
    assert approve_response.json()["status"] == "Approved"
    assert dispatch_response.json()["status"] == "Dispatched"
    assert dispatch_response.json()["dispatchStatus"] == "Dispatched"
    assert len(queue_response.json()) == 1


def test_work_order_approval_callback_can_approve_or_reject():
    client.post("/api/trigger-anomaly")
    work_order = client.post("/api/work-orders").json()

    approved = client.post(
        f"/api/work-orders/{work_order['id']}/approval-callback",
        json={"decision": "approved", "approved_by": "Logic App"},
    )
    rejected = client.post(
        f"/api/work-orders/{work_order['id']}/approval-callback",
        json={"decision": "rejected", "approved_by": "Logic App", "note": "Need safety review"},
    )

    assert approved.status_code == 200
    assert approved.json()["status"] == "Approved"
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "Rejected"


def test_agent_trigger_and_energy_insights_have_fallbacks():
    trigger = client.post(
        "/api/agent/trigger",
        json={
            "sessionId": "session-test",
            "machineId": "motor-A",
            "severity": "High",
            "telemetry": {"vibration": 3.5, "temperature": 80.0, "load": 91.0, "status": "Critical"},
        },
    )
    decisions = client.get("/api/agent/decisions?sessionId=session-test").json()
    insights = client.get("/api/energy/insights").json()

    assert trigger.status_code == 200
    assert trigger.json()["foundryRuntimeCalled"] is False
    assert decisions["count"] >= 1
    assert insights["count"] >= 1


def test_dispatch_requires_approval():
    client.post("/api/trigger-anomaly")
    work_order = client.post("/api/work-orders").json()

    response = client.post(f"/api/work-orders/{work_order['id']}/dispatch")

    assert response.status_code == 409
    assert "approved before dispatch" in response.json()["detail"]


def test_work_order_production_mode_without_webhook_stays_pending_external_dispatch():
    main.APP_MODE = "production"
    main.WORK_ORDER_SYSTEM_NAME = "External CMMS"
    main.CMMS_DISPATCH_WEBHOOK_URL = None

    client.post("/api/trigger-anomaly")
    work_order = client.post("/api/work-orders").json()
    client.post(f"/api/work-orders/{work_order['id']}/approve")
    dispatched = client.post(f"/api/work-orders/{work_order['id']}/dispatch").json()

    assert dispatched["mode"] == "production"
    assert dispatched["status"] == "Approved"
    assert dispatched["dispatchStatus"] == "Pending external dispatch"
    assert dispatched["externalSystem"] == "External CMMS"


def test_reset_clears_work_order_queue():
    client.post("/api/trigger-anomaly")
    client.post("/api/work-orders")

    assert len(client.get("/api/work-orders").json()) == 1

    client.post("/api/reset-anomaly")

    assert client.get("/api/work-orders").json() == []


def test_reports_routes_return_expected_sections():
    full_report = client.get("/api/reports").json()
    business = client.get("/api/reports/business-value").json()
    roi = client.get("/api/reports/roi").json()
    architecture = client.get("/api/reports/azure-architecture").json()
    operating_model = client.get("/api/reports/operating-model").json()
    roadmap = client.get("/api/reports/roadmap").json()

    assert set(full_report.keys()) >= {
        "business_value",
        "roi",
        "azure_architecture",
        "operating_model",
        "roadmap",
    }
    assert len(business["metrics"]) == 4
    assert roi["summary"]["roi_percent"] == 312
    assert len(architecture["flow"]) == 7
    assert len(operating_model["stages"]) == 4
    assert len(roadmap["phases"]) == 4


def test_reports_production_mode_uses_external_json_when_available(monkeypatch):
    main.APP_MODE = "production"
    external_reports = {
        "mode": "production",
        "source": "external",
        "business_value": {"metrics": []},
    }

    monkeypatch.setattr(main, "fetch_external_json", lambda endpoint: external_reports)
    main.REPORTS_DATA_ENDPOINT = "https://example.test/reports"

    response = client.get("/api/reports")

    assert response.status_code == 200
    assert response.json() == external_reports
