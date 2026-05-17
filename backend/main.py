import glob
import json
import os
import random
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Literal
from urllib.error import URLError
from urllib.request import Request as UrlRequest, urlopen
from services.adt_service import get_mock_twin_dependencies, get_twin_dependencies, seed_demo_graph
from fastapi.responses import StreamingResponse
from services.anomaly_service import detect_anomaly_from_telemetry
from services.fabric_kql import (
    get_latest_telemetry as get_fabric_latest_telemetry,
    get_latest_anomalies as get_fabric_latest_anomalies,
)
from services.iot_hub_service import (
    set_telemetry_handler,
    start_iot_hub_listener,
    stop_iot_hub_listener,
    get_latest_telemetry as get_iot_latest_telemetry,
)

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from services.cosmos_service import (
    cosmos_enabled,
    cosmos_state_status,
    get_work_order as get_cosmos_work_order,
    list_agent_decisions,
    list_anomaly_results,
    list_energy_insights,
    list_work_orders as list_cosmos_work_orders,
    save_agent_decision,
    save_anomaly_result,
    save_energy_insight,
    upsert_work_order,
)
from features.agents_api import register_agents_routes
from services.key_vault_service import key_vault_status

try:
    from openai import AzureOpenAI, OpenAI
except ImportError:
    AzureOpenAI = None
    OpenAI = None

try:
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient
except ImportError:
    AzureKeyCredential = None
    SearchClient = None


load_dotenv()

APP_MODE = os.getenv("APP_MODE", "mock").lower()
WORK_ORDER_SYSTEM_NAME = os.getenv(
    "WORK_ORDER_SYSTEM_NAME",
    "In-memory Work Order Queue" if APP_MODE == "mock" else "External CMMS",
)
CMMS_DISPATCH_WEBHOOK_URL = os.getenv("CMMS_DISPATCH_WEBHOOK_URL")
CMMS_DISPATCH_BEARER_TOKEN = os.getenv("CMMS_DISPATCH_BEARER_TOKEN")
APPROVAL_CALLBACK_TOKEN = os.getenv("APPROVAL_CALLBACK_TOKEN")
DASHBOARD_DATA_ENDPOINT = os.getenv("DASHBOARD_DATA_ENDPOINT")
ALERTS_DATA_ENDPOINT = os.getenv("ALERTS_DATA_ENDPOINT")
REPORTS_DATA_ENDPOINT = os.getenv("REPORTS_DATA_ENDPOINT")
EXTERNAL_API_BEARER_TOKEN = os.getenv("EXTERNAL_API_BEARER_TOKEN")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
print(f"Starting SmartFactory TwinOps API in {APP_MODE.upper()} mode")


@asynccontextmanager
async def lifespan(_: FastAPI):
    set_telemetry_handler(handle_live_telemetry)
    await start_iot_hub_listener()
    try:
        yield
    finally:
        await stop_iot_hub_listener()


app = FastAPI(title="SmartFactory TwinOps API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


openai_key = os.getenv("OPENAI_API_KEY")
openai_client = None
openai_model = OPENAI_MODEL
if AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY and AZURE_OPENAI_DEPLOYMENT and AzureOpenAI:
    openai_client = AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
    )
    openai_model = AZURE_OPENAI_DEPLOYMENT
elif openai_key and OpenAI:
    openai_client = OpenAI(api_key=openai_key)

search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
search_key = os.getenv("AZURE_SEARCH_KEY")
search_index = os.getenv("AZURE_SEARCH_INDEX")

search_client = None
if search_endpoint and search_key and search_index and SearchClient and AzureKeyCredential:
    try:
        search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=search_index,
            credential=AzureKeyCredential(search_key),
        )
    except Exception as exc:
        print(f"Failed to initialize Azure Search Client: {exc}")


def load_sop_knowledge_base():
    sop_content = ""
    folder_path = os.path.join(os.path.dirname(__file__), "mock-data", "SOP-Mocking")
    file_pattern = os.path.join(folder_path, "*.txt")
    files = glob.glob(file_pattern)

    if not files:
        return """
            [SOP-MA-102] Bearing Inspection
            - Criteria: vibration > 3.0 mm/s or temperature > 75 C
            - Actions: reduce load by 15% immediately and inspect bearing.
        """

    for file_path in files:
        with open(file_path, "r", encoding="utf-8") as file:
            sop_content += f"\n[{os.path.basename(file_path)}]\n{file.read()}\n"

    return sop_content


MOCK_KNOWLEDGE_BASE = load_sop_knowledge_base()


class TelemetryMetrics(BaseModel):
    vibration: float
    temperature: float
    load: float
    status: str


class IngestPayload(BaseModel):
    device_id: str
    timestamp: str
    data: TelemetryMetrics


class WorkOrderCreateRequest(BaseModel):
    recommendation_id: int | None = None
    action: str | None = None
    assignee: str | None = None
    due: str | None = None


class WorkOrderApprovalRequest(BaseModel):
    approved_by: str | None = None
    note: str | None = None


class WorkOrderDispatchRequest(BaseModel):
    dispatched_by: str | None = None
    note: str | None = None


class WorkOrderApprovalCallback(BaseModel):
    decision: Literal["approved", "rejected"]
    approved_by: str | None = None
    note: str | None = None
    externalApprovalId: str | None = None
    token: str | None = None


class AgentTriggerRequest(BaseModel):
    sessionId: str | None = None
    anomalyId: str | None = None
    machineId: str = "motor-A"
    severity: str = "High"
    source: str = "cosmos-trigger"
    telemetry: dict | None = None


WorkOrderStatus = Literal["Draft", "Awaiting approval", "Approved", "Rejected", "Dispatched"]
WorkOrderPriority = Literal["High", "Medium", "Low"]
DispatchStatus = Literal["Not dispatched", "Pending external dispatch", "Dispatched", "Failed"]


class WorkOrderHistoryItem(BaseModel):
    time: str
    event: str


class WorkOrder(BaseModel):
    id: str
    assetId: str
    assetName: str
    priority: WorkOrderPriority
    status: WorkOrderStatus
    assignee: str
    due: str
    title: str
    checklist: list[str]
    history: list[WorkOrderHistoryItem]
    recommendation_id: int | None = None
    source: str = "backend"
    mode: str = "mock"
    externalSystem: str | None = None
    externalId: str | None = None
    dispatchStatus: DispatchStatus = "Not dispatched"
    dispatchError: str | None = None


app_state = {
    "is_anomaly_active": False,
    "anomaly_start_time": 0,
    "latest_ingested_data": None,
    # Agents API feature: stores the simulated Azure multi-agent cascade state in memory for the demo.
    "agent_cascade_started": False,
    "agent_cascade_last_run": None,
    "work_orders": {},
    "next_work_order_sequence": 1,
    "recommendation_cache": None,
    "recommendation_cache_key": None,
}


def now_string():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normal_motor_b():
    return {
        "vibration": round(random.uniform(1.1, 1.5), 2),
        "temperature": round(random.uniform(59.0, 62.0), 1),
        "load": round(random.uniform(65.0, 70.0), 1),
        "status": "Normal",
    }


def normal_conveyor_c():
    return {
        "vibration": round(random.uniform(0.9, 1.2), 2),
        "temperature": round(random.uniform(54.0, 56.0), 1),
        "load": round(random.uniform(60.0, 65.0), 1),
        "status": "Normal",
    }


def normal_motor_a():
    return {
        "vibration": round(random.uniform(1.0, 1.4), 2),
        "temperature": round(random.uniform(60.0, 63.0), 1),
        "load": round(random.uniform(68.0, 73.0), 1),
        "status": "Normal",
    }


def critical_motor_a():
    return {
        "vibration": round(random.uniform(3.0, 3.8), 2),
        "temperature": round(random.uniform(75.0, 82.0), 1),
        "load": round(random.uniform(88.0, 95.0), 1),
        "status": "Critical",
    }


def fetch_external_json(endpoint: str | None):
    if not endpoint:
        return None

    headers = {"Accept": "application/json"}
    if EXTERNAL_API_BEARER_TOKEN:
        headers["Authorization"] = f"Bearer {EXTERNAL_API_BEARER_TOKEN}"

    request = UrlRequest(endpoint, headers=headers, method="GET")

    try:
        with urlopen(request, timeout=10) as response:
            response_body = response.read().decode("utf-8")
            return json.loads(response_body) if response_body else None
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"External data fetch failed for {endpoint}: {exc}")
        return None


def update_anomaly_state_from_metrics(metrics: dict, timestamp: str | None = None):
    app_state["latest_ingested_data"] = metrics

    if metrics.get("status") == "Critical":
        app_state["is_anomaly_active"] = True
        app_state["anomaly_start_time"] = timestamp or now_string()
        app_state["agent_cascade_started"] = True
        app_state["agent_cascade_last_run"] = now_string()


def normalize_live_telemetry(raw: dict):
    payload = raw.get("data") if isinstance(raw.get("data"), dict) else raw
    if not isinstance(payload, dict):
        return None

    try:
        vibration = float(payload.get("vibration", payload.get("vibration_mm_s")))
        temperature = float(payload.get("temperature", payload.get("temperature_c")))
        load = float(payload.get("load", payload.get("energyLoad", payload.get("load_percent"))))
    except (TypeError, ValueError):
        return None

    status = str(payload.get("status") or ("Critical" if vibration >= 3.0 or temperature >= 75 else "Normal"))
    if status.lower() in {"critical", "fault", "error"}:
        status = "Critical"
    elif status.lower().startswith("warn"):
        status = "Warning"
    else:
        status = "Normal"

    timestamp = raw.get("timestamp") or payload.get("timestamp") or raw.get("enqueuedTime")
    return {
        "vibration": round(vibration, 2),
        "temperature": round(temperature, 1),
        "load": round(load, 1),
        "status": status,
    }, timestamp


def handle_live_telemetry(raw: dict):
    normalized = normalize_live_telemetry(raw)
    if normalized is None:
        print(f"Live telemetry skipped because payload does not match TwinOps metrics: {raw}")
        return

    metrics, timestamp = normalized
    update_anomaly_state_from_metrics(metrics, timestamp)


def configured(value: str | None) -> bool:
    return bool(value and value.strip())


def build_integrations_status():
    return {
        "mode": APP_MODE,
        "generated_at": now_string(),
        "integrations": {
            "iot_hub": {
                "enabled": os.getenv("USE_AZURE", "false").lower() == "true",
                "configured": configured(os.getenv("IOTHUB_EVENTHUB_CONNECTION_STRING")),
                "consumer_group": os.getenv("IOTHUB_CONSUMER_GROUP", "twinops-cg"),
            },
            "azure_digital_twins": {
                "configured": configured(os.getenv("ADT_URL") or os.getenv("ADT_ENDPOINT")),
                "fallback": "mock-digital-twins",
            },
            "azure_ml": {
                "configured": configured(os.getenv("AZURE_ML_SCORING_URI") or os.getenv("AZURE_ML_ANOMALY_ENDPOINT")),
                "deployment": os.getenv("AZURE_ML_DEPLOYMENT_NAME"),
                "fallback": "local-rule-detector",
            },
            "cosmos_db": {
                "configured": configured(os.getenv("COSMOS_ENDPOINT")) and configured(os.getenv("COSMOS_KEY")),
                "database": os.getenv("COSMOS_DB", "twinopsai-anomaly-db"),
                "container": os.getenv("COSMOS_CONTAINER", "anomaly-results"),
                "stateStore": cosmos_state_status(),
            },
            "fabric_kql": {
                "configured": configured(os.getenv("FABRIC_KQL_CLUSTER_URI")),
                "database": os.getenv("FABRIC_KQL_DATABASE", "twinopsai_kql_db"),
                "table": os.getenv("FABRIC_KQL_TABLE", "telemetry_v2"),
            },
            "azure_ai_search": {
                "configured": all([configured(search_endpoint), configured(search_key), configured(search_index)]),
                "index": search_index,
                "fallback": "local-sop-files",
            },
            "openai": {
                "configured": configured(openai_key) or all([
                    configured(AZURE_OPENAI_ENDPOINT),
                    configured(AZURE_OPENAI_API_KEY),
                    configured(AZURE_OPENAI_DEPLOYMENT),
                ]),
                "azure_openai_configured": all([
                    configured(AZURE_OPENAI_ENDPOINT),
                    configured(AZURE_OPENAI_API_KEY),
                    configured(AZURE_OPENAI_DEPLOYMENT),
                ]),
                "model_or_deployment": openai_model,
                "fallback": "system-recommendation",
            },
            "dashboard_external_api": {"configured": configured(DASHBOARD_DATA_ENDPOINT)},
            "alerts_external_api": {"configured": configured(ALERTS_DATA_ENDPOINT)},
            "reports_external_api": {"configured": configured(REPORTS_DATA_ENDPOINT)},
            "cmms_dispatch": {
                "configured": configured(CMMS_DISPATCH_WEBHOOK_URL),
                "system_name": WORK_ORDER_SYSTEM_NAME,
                "auth_configured": configured(CMMS_DISPATCH_BEARER_TOKEN),
                "approvalCallbackTokenConfigured": configured(APPROVAL_CALLBACK_TOKEN),
            },
            "key_vault": key_vault_status(),
            "managed_identity": {
                "configured": configured(os.getenv("AZURE_CLIENT_ID")) or configured(os.getenv("IDENTITY_ENDPOINT")),
                "authModel": "DefaultAzureCredential",
            },
        },
    }


def build_telemetry_snapshot():
    motor_a_data = app_state["latest_ingested_data"] or normal_motor_a()

    if app_state["is_anomaly_active"]:
        motor_a_data = critical_motor_a()

    return {
        "timestamp": now_string(),
        "motor_A": motor_a_data,
        "motor_B": normal_motor_b(),
        "conveyor_C": normal_conveyor_c(),
    }


def asset_health_from_metric(metric: dict, baseline: int, critical_floor: int = 42):
    if metric["status"] == "Critical":
        return max(
            critical_floor,
            round(68 - (metric["vibration"] - 3) * 6 - max(0, metric["temperature"] - 75) * 0.35),
        )

    return min(
        99,
        round(
            baseline
            + (1.35 - metric["vibration"]) * 10
            + (62 - metric["temperature"]) * 0.35
            + (72 - metric["load"]) * 0.05
        ),
    )


def build_asset_health(telemetry: dict):
    motor_a = telemetry["motor_A"]
    motor_b = telemetry["motor_B"]
    conveyor_c = telemetry["conveyor_C"]
    anomaly_active = app_state["is_anomaly_active"]

    return [
        {
            "id": "motor-a",
            "name": "Motor A",
            "role": "Main drive motor",
            "status": "critical" if anomaly_active else "normal",
            "healthScore": asset_health_from_metric(motor_a, 94),
            "vibration": motor_a["vibration"],
            "temperature": motor_a["temperature"],
            "load": motor_a["load"],
            "oee": 76 if anomaly_active else 92,
        },
        {
            "id": "motor-b",
            "name": "Motor B",
            "role": "Secondary drive motor",
            "status": "normal",
            "healthScore": asset_health_from_metric(motor_b, 95),
            "vibration": motor_b["vibration"],
            "temperature": motor_b["temperature"],
            "load": motor_b["load"],
            "oee": 91,
        },
        {
            "id": "conveyor-c",
            "name": "Conveyor C",
            "role": "Line transfer conveyor",
            "status": "warning" if anomaly_active else "normal",
            "healthScore": asset_health_from_metric(conveyor_c, 96) - (8 if anomaly_active else 0),
            "vibration": conveyor_c["vibration"],
            "temperature": conveyor_c["temperature"],
            "load": conveyor_c["load"],
            "oee": 86 if anomaly_active else 94,
        },
    ]


def build_oee_history():
    values = [79, 82, 85, 86, 88, 87, 87]
    if app_state["is_anomaly_active"]:
        values[-1] = 76

    return [
        {"day": "May 11", "value": values[0]},
        {"day": "May 12", "value": values[1]},
        {"day": "May 13", "value": values[2]},
        {"day": "May 14", "value": values[3]},
        {"day": "May 15", "value": values[4]},
        {"day": "May 16", "value": values[5]},
        {"day": "May 17", "value": values[6]},
    ]


def build_energy_usage():
    values = [320, 440, 380, 410, 625, 590, 560, 690, 540, 590, 470, 390]
    if app_state["is_anomaly_active"]:
        values[4] = 710
        values[5] = 735
        values[6] = 690

    times = ["00:00", "02:00", "04:00", "06:00", "08:00", "10:00", "12:00", "14:00", "16:00", "18:00", "20:00", "22:00"]
    return [{"time": time, "value": value} for time, value in zip(times, values)]


def build_alert_queue(telemetry: dict):
    if app_state["is_anomaly_active"]:
        motor_a = telemetry["motor_A"]
        return [
            {
                "id": "alert-motor-a-bearing-risk",
                "title": "Bearing wear risk detected",
                "assetId": "motor-a",
                "assetName": "Motor A",
                "severity": "High",
                "timestamp": telemetry["timestamp"],
                "details": "Motor A vibration and temperature moved above baseline together.",
                "status": "Active",
                "recommendedAction": "Inspect Motor A bearing and reduce load by 15%.",
                "metrics": [
                    {"label": "Vibration", "value": f"{motor_a['vibration']} mm/s", "delta": "Elevated vs baseline"},
                    {"label": "Temperature", "value": f"{motor_a['temperature']} C", "delta": "Elevated vs baseline"},
                    {"label": "Load", "value": f"{motor_a['load']}%", "delta": "Operating load"},
                ],
            },
            {
                "id": "alert-conveyor-c-impact",
                "title": "Downstream impact risk",
                "assetId": "conveyor-c",
                "assetName": "Conveyor C",
                "severity": "Medium",
                "timestamp": telemetry["timestamp"],
                "details": "Conveyor C may receive reduced or unstable input if Motor A remains critical.",
                "status": "Active",
                "recommendedAction": "Monitor downstream throughput and prepare maintenance window.",
                "metrics": [
                    {"label": "Dependency", "value": "Motor A -> Conveyor C", "delta": "At risk"},
                    {"label": "Line throughput", "value": "-18% to -25%", "delta": "Estimated impact"},
                ],
            },
        ]

    return [
        {
            "id": "alert-line-stable",
            "title": "No active anomaly",
            "assetId": "motor-a",
            "assetName": "Packaging Line 1",
            "severity": "Low",
            "timestamp": telemetry["timestamp"],
            "details": "Line is operating within baseline. Monitoring continues.",
            "status": "Informational",
            "recommendedAction": "Continue monitoring.",
            "metrics": [
                {"label": "Line status", "value": "Stable", "delta": "Within baseline"},
            ],
        }
    ]


def build_kpis(asset_health: list[dict], alerts: list[dict]):
    anomaly_active = app_state["is_anomaly_active"]
    avg_health = round(sum(asset["healthScore"] for asset in asset_health) / len(asset_health))
    active_alerts = len([alert for alert in alerts if alert["status"] == "Active"])

    return [
        {
            "id": "line-health",
            "label": "Line Health",
            "value": f"{avg_health}%",
            "trend": "-12%" if anomaly_active else "+3%",
            "status": "Critical" if anomaly_active else "Stable",
        },
        {
            "id": "oee",
            "label": "OEE",
            "value": "76%" if anomaly_active else "87%",
            "trend": "-11 pts" if anomaly_active else "+2 pts",
            "status": "At Risk" if anomaly_active else "On Track",
        },
        {
            "id": "energy",
            "label": "Energy Usage",
            "value": "735 kW" if anomaly_active else "590 kW",
            "trend": "+24%" if anomaly_active else "-4%",
            "status": "Elevated" if anomaly_active else "Normal",
        },
        {
            "id": "alerts",
            "label": "Active Alerts",
            "value": str(active_alerts),
            "trend": "+2" if anomaly_active else "0",
            "status": "Action Required" if anomaly_active else "Clear",
        },
    ]


def azure_service_status():
    status = "Connected" if APP_MODE == "production" else "Mocked"
    return [
        {"id": "iot", "name": "IoT Hub", "status": status, "detail": "Telemetry ingress from PLC, OPC UA, and MQTT"},
        {"id": "adt", "name": "Azure Digital Twins", "status": status, "detail": "Asset graph and dependency context"},
        {"id": "fabric", "name": "Microsoft Fabric", "status": status, "detail": "Operational history and reporting lake"},
        {"id": "foundry", "name": "Foundry Agent Service", "status": status, "detail": "Multi-agent orchestration and actions"},
    ]


def build_dashboard_summary():
    telemetry = build_telemetry_snapshot()
    asset_health = build_asset_health(telemetry)
    alerts = build_alert_queue(telemetry)

    return {
        "mode": APP_MODE,
        "source": "mock" if APP_MODE == "mock" else "production-fallback",
        "generated_at": now_string(),
        "line": {
            "id": "packaging-line-1",
            "name": "Packaging Line 1",
            "status": "Critical" if app_state["is_anomaly_active"] else "Stable",
        },
        "kpis": build_kpis(asset_health, alerts),
        "oee": {
            "current": 76 if app_state["is_anomaly_active"] else 87,
            "target": 90,
            "unit": "%",
            "history": build_oee_history(),
        },
        "energy": {
            "current_kw": 735 if app_state["is_anomaly_active"] else 590,
            "baseline_kw": 590,
            "unit": "kW",
            "history": build_energy_usage(),
        },
        "asset_health": asset_health,
        "latest_telemetry": telemetry,
        "alerts": alerts,
        "azure_services": azure_service_status(),
    }


def reports_source():
    return "mock" if APP_MODE == "mock" else "production-fallback"


def build_business_value_report():
    return {
        "mode": APP_MODE,
        "source": reports_source(),
        "generated_at": now_string(),
        "metrics": [
            {"id": "downtime", "label": "Downtime Reduction", "value": "10-20%", "detail": "Reduced unplanned downtime", "tone": "red"},
            {"id": "energy", "label": "Energy Reduction", "value": "5-10%", "detail": "Reduced energy consumption", "tone": "green"},
            {"id": "oee", "label": "Real-Time OEE", "value": "Live", "detail": "Asset-level visibility", "tone": "blue"},
            {"id": "triage", "label": "Faster Triage", "value": "AI", "detail": "AI-assisted response time", "tone": "orange"},
        ],
        "pain_point_mapping": [
            {"problem": "Limited risk visibility", "response": "Line Health & Risk Summary", "kpi": "OEE, Downtime"},
            {"problem": "Too many alarms and slow root-cause analysis", "response": "Likely Cause and Evidence", "kpi": "MTTR, MTBF"},
            {"problem": "Siloed machine data", "response": "Digital Twin Dependency", "kpi": "Line Throughput"},
            {"problem": "Manual SOP search", "response": "RAG-based recommendations", "kpi": "Faster Triage"},
        ],
    }


def build_roi_report():
    return {
        "mode": APP_MODE,
        "source": reports_source(),
        "generated_at": now_string(),
        "currency": "USD",
        "summary": {
            "annual_cost_avoidance": 1840000,
            "roi_percent": 312,
            "payback_months": 4.2,
            "risk_exposure_per_hour": 2300000,
        },
        "assumptions": [
            {"driver": "Unplanned downtime", "assumption": "10-20% reduction from predictive maintenance", "annualImpact": 1350000},
            {"driver": "Energy waste", "assumption": "5-10% reduction from load and anomaly insight", "annualImpact": 310000},
            {"driver": "Manual triage delay", "assumption": "Agent-assisted RCA with SOP evidence", "annualImpact": 180000},
        ],
        "notes": [
            "Pilot assumptions are directional and should be validated with plant-specific downtime, energy, and maintenance data.",
            "Production mode should calculate this from Fabric operational history and finance assumptions.",
        ],
    }


def build_azure_architecture_report():
    return {
        "mode": APP_MODE,
        "source": reports_source(),
        "generated_at": now_string(),
        "flow": [
            {"order": 1, "name": "Factory Edge", "role": "PLC, SCADA, OPC UA, MQTT, and local gateway sources"},
            {"order": 2, "name": "IoT Hub", "role": "Telemetry ingress and device messaging"},
            {"order": 3, "name": "Fabric Real-Time", "role": "Operational event stream and historical reporting"},
            {"order": 4, "name": "Azure Digital Twins", "role": "Asset graph and dependency context"},
            {"order": 5, "name": "Azure ML", "role": "Anomaly models and predictive signals"},
            {"order": 6, "name": "Foundry Agents", "role": "Agent orchestration and action generation"},
            {"order": 7, "name": "Tools & Work Orders", "role": "Supervisor approval and CMMS dispatch"},
        ],
        "service_roles": azure_service_status(),
    }


def build_operating_model_report():
    return {
        "mode": APP_MODE,
        "source": reports_source(),
        "generated_at": now_string(),
        "equation": "Telemetry + Digital Twin Context + AI Agent Intelligence = Actionable Operations",
        "stages": [
            {"name": "Raw Telemetry", "detail": "Sensor, PLC, SCADA"},
            {"name": "Digital Twin Context", "detail": "Asset graph and dependencies"},
            {"name": "AI Agent Intelligence", "detail": "SOP/manual RAG and multi-agent reasoning"},
            {"name": "Actionable Ops", "detail": "Recommended action, approval, and work order dispatch"},
        ],
        "paradigm_shift": {
            "traditional": ["Reactive maintenance", "Manual inspection", "Siloed machine data", "Static dashboard", "Manual SOP search"],
            "ai_driven": ["Predictive maintenance", "Real-time monitoring", "Connected factory intelligence", "Agent-assisted operations", "RAG-based recommendations"],
        },
    }


def build_roadmap_report():
    return {
        "mode": APP_MODE,
        "source": reports_source(),
        "generated_at": now_string(),
        "phases": [
            {"id": "p1", "title": "Phase 1 - Simulated dashboard", "description": "Anomaly demo and executive visibility for one line.", "risk": "Legacy tech isolated from pilot data."},
            {"id": "p2", "title": "Phase 2 - Connect machines", "description": "Azure IoT Hub connection with OPC UA or MQTT ingestion.", "risk": "Secure gateway and telemetry validation required."},
            {"id": "p3", "title": "Phase 3 - Train anomaly model", "description": "Add RAG from SOPs, manuals, and historical maintenance logs.", "risk": "AI hallucination managed with approval and source evidence."},
            {"id": "p4", "title": "Phase 4 - Multi-line twin", "description": "Scale dependency graph, work orders, and reporting across factories.", "risk": "Cybersecurity via Azure Defender for IoT and Entra ID."},
        ],
    }
def append_work_order_history(work_order: dict, event: str):
    work_order["history"].append({
        "time": now_string(),
        "event": event,
    })


def get_work_order_or_404(work_order_id: str):
    work_order = app_state["work_orders"].get(work_order_id)
    if not work_order and APP_MODE == "production":
        work_order = get_cosmos_work_order(work_order_id)
        if work_order:
            app_state["work_orders"][work_order_id] = work_order

    if not work_order:
        raise HTTPException(status_code=404, detail=f"Work order {work_order_id} not found")
    return work_order


def persist_work_order(work_order: dict):
    app_state["work_orders"][work_order["id"]] = work_order
    if APP_MODE == "production":
        saved = upsert_work_order(work_order)
        if saved.get("cosmosSaved"):
            work_order["cosmosSaved"] = True
        elif saved.get("cosmosError"):
            work_order["cosmosSaved"] = False
            work_order["cosmosError"] = saved.get("cosmosError")
    return work_order


def build_work_order_id():
    sequence = app_state["next_work_order_sequence"]
    app_state["next_work_order_sequence"] = sequence + 1
    return f"WO-{datetime.now().strftime('%Y%m%d')}-{sequence:04d}"


def build_work_order_from_recommendation(payload: WorkOrderCreateRequest):
    action = payload.action or "Inspect within 24 hours"
    due = payload.due or "Within 24 hours"
    assignee = payload.assignee or "Maintenance Team"
    work_order_id = build_work_order_id()

    return {
        "id": work_order_id,
        "assetId": "motor-a",
        "assetName": "Motor A",
        "priority": "High",
        "status": "Awaiting approval",
        "assignee": assignee,
        "due": due,
        "title": "Bearing inspection and lubrication check",
        "checklist": [
            "Verify lockout/tagout before inspection.",
            "Inspect Motor A bearing housing and lubrication level.",
            "Check vibration trend after temporary load reduction.",
            "Record findings and attach photos to maintenance history.",
        ],
        "history": [
            {
                "time": now_string(),
                "event": "Work order generated from AI recommendation.",
            },
            {
                "time": now_string(),
                "event": f"Recommended action attached: {action}",
            },
        ],
        "recommendation_id": payload.recommendation_id,
        "source": "mock" if APP_MODE == "mock" else "production",
        "mode": APP_MODE,
        "externalSystem": WORK_ORDER_SYSTEM_NAME,
        "externalId": None,
        "dispatchStatus": "Not dispatched",
        "dispatchError": None,
    }


def dispatch_to_external_system(work_order: dict):
    if not CMMS_DISPATCH_WEBHOOK_URL:
        work_order["dispatchStatus"] = "Pending external dispatch"
        append_work_order_history(
            work_order,
            f"Production dispatch prepared for {WORK_ORDER_SYSTEM_NAME}; no CMMS_DISPATCH_WEBHOOK_URL configured.",
        )
        return persist_work_order(work_order)

    payload = json.dumps(work_order).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if CMMS_DISPATCH_BEARER_TOKEN:
        headers["Authorization"] = f"Bearer {CMMS_DISPATCH_BEARER_TOKEN}"

    request = UrlRequest(
        CMMS_DISPATCH_WEBHOOK_URL,
        data=payload,
        headers=headers,
        method="POST",
    )

    try:
        with urlopen(request, timeout=10) as response:
            response_body = response.read().decode("utf-8")
            external_response = json.loads(response_body) if response_body else {}
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        work_order["dispatchStatus"] = "Failed"
        work_order["dispatchError"] = str(exc)
        append_work_order_history(work_order, f"External dispatch failed: {exc}")
        return persist_work_order(work_order)

    work_order["status"] = "Dispatched"
    work_order["dispatchStatus"] = "Dispatched"
    work_order["dispatchError"] = None
    work_order["externalId"] = (
        external_response.get("external_id")
        or external_response.get("work_order_id")
        or external_response.get("id")
    )
    append_work_order_history(work_order, f"Work order dispatched to {WORK_ORDER_SYSTEM_NAME}.")
    return persist_work_order(work_order)


@app.post("/api/ingest-telemetry")
async def ingest_telemetry(payload: IngestPayload):
    update_anomaly_state_from_metrics(payload.data.model_dump(), payload.timestamp)

    return {
        "status": "received",
        "server_received_time": now_string(),
    }

@app.post("/api/adt/events")
async def receive_adt_events(request: Request):
    events = await request.json()

    if isinstance(events, dict):
        events = [events]

    if not isinstance(events, list):
        raise HTTPException(status_code=400, detail="Invalid Event Grid payload")

    # 1) Event Grid validation handshake
    for event in events:
        if event.get("eventType") == "Microsoft.EventGrid.SubscriptionValidationEvent":
            validation_code = event.get("data", {}).get("validationCode")

            if not validation_code:
                raise HTTPException(status_code=400, detail="Missing validationCode")

            return {
                "validationResponse": validation_code
            }

    # 2) Normal Azure Digital Twins events
    for event in events:
        print("Received ADT Event Grid event:")
        print(event)
        event_data = event.get("data", {})
        telemetry_candidate = event_data.get("patch") or event_data
        if isinstance(telemetry_candidate, dict):
            handle_live_telemetry(telemetry_candidate)

    return {
        "status": "ok",
        "source": "azure-digital-twins-event-grid",
        "received": len(events)
    }

@app.get("/api/telemetry")
async def get_telemetry():
    motor_a_data = app_state["latest_ingested_data"] or normal_motor_a()

    if app_state["is_anomaly_active"]:
        motor_a_data = critical_motor_a()

    return {
        "timestamp": now_string(),
        "motor_A": motor_a_data,
        "motor_B": normal_motor_b(),
        "conveyor_C": normal_conveyor_c(),
    }


@app.post("/api/trigger-anomaly")
async def trigger_anomaly():
    app_state["is_anomaly_active"] = True
    app_state["anomaly_start_time"] = now_string()
    app_state["latest_ingested_data"] = critical_motor_a()
    app_state["recommendation_cache"] = None
    app_state["recommendation_cache_key"] = None
    # Agents API feature: manual anomaly trigger also starts the simulated Azure agent cascade.
    app_state["agent_cascade_started"] = True
    app_state["agent_cascade_last_run"] = app_state["anomaly_start_time"]

    return {
        "Message": "Anomaly simulation triggered. Dashboard will spike.",
    }


@app.post("/api/reset-anomaly")
async def reset_anomaly():
    app_state["is_anomaly_active"] = False
    app_state["anomaly_start_time"] = 0
    app_state["latest_ingested_data"] = None
    # Agents API feature: reset clears only the agent cascade demo state; no existing telemetry logic is removed.
    app_state["agent_cascade_started"] = False
    app_state["agent_cascade_last_run"] = None
    app_state["work_orders"] = {}
    app_state["next_work_order_sequence"] = 1
    app_state["recommendation_cache"] = None
    app_state["recommendation_cache_key"] = None

    return {
        "Message": "Anomaly simulation reset to normal state.",
    }


# Agents API feature: registers isolated routes for the simulated Microsoft Azure multi-agent cascade.
register_agents_routes(app, app_state)

@app.get("/api/integrations/status")
async def get_integrations_status():
    return build_integrations_status()

@app.get("/api/twins/{twin_id}/dependencies")
async def get_twin_dependencies_api(twin_id: str):
    try:
        return get_twin_dependencies(twin_id)
    except Exception as exc:
        print(f"Azure Digital Twins dependency lookup failed: {exc}. Returning mock dependency graph.")
        return get_mock_twin_dependencies(twin_id)


@app.post("/api/twins/seed-demo-graph")
async def seed_twin_demo_graph():
    try:
        result = seed_demo_graph()
        return {
            "status": "ok",
            "mode": APP_MODE,
            **result,
        }
    except Exception as exc:
        return {
            "status": "fallback",
            "mode": APP_MODE,
            "source": "mock-digital-twins",
            "message": "Azure Digital Twins seed was not applied. Returning the mock graph shape for local/demo use.",
            "error": str(exc),
            "mockGraph": get_mock_twin_dependencies("motor-A"),
        }


@app.get("/api/digital-twin")
async def get_digital_twin():
    if app_state["is_anomaly_active"]:
        return {
            "line_status": "Critical",
            "failure_risk": "High",
            "affected_asset": "Motor A",
            "potential_impact": "Degradation at Motor A may reduce throughput capacity of Line 1 by 18-25% if unaddressed.",
            "downstream_impact": {
                "Motor_B": "Normal",
                "Conveyor_C": "At Risk (Reduced Input)",
            },
        }

    return {
        "line_status": "Stable",
        "failure_risk": "Low",
        "affected_asset": "None",
        "potential_impact": "Normal production",
        "downstream_impact": {
            "Motor_B": "Normal",
            "Conveyor_C": "Normal",
        },
    }


@app.get("/api/dashboard")
async def get_dashboard():
    if APP_MODE == "production":
        external_data = fetch_external_json(DASHBOARD_DATA_ENDPOINT)
        if external_data:
            return external_data

    return build_dashboard_summary()


@app.get("/api/alerts")
async def get_alerts():
    if APP_MODE == "production":
        external_data = fetch_external_json(ALERTS_DATA_ENDPOINT)
        if external_data:
            return external_data

    dashboard = build_dashboard_summary()
    return {
        "mode": APP_MODE,
        "source": dashboard["source"],
        "generated_at": dashboard["generated_at"],
        "alerts": dashboard["alerts"],
    }


@app.get("/api/oee")
async def get_oee():
    return {
        "mode": APP_MODE,
        "source": "mock" if APP_MODE == "mock" else "production-fallback",
        "generated_at": now_string(),
        "oee": build_dashboard_summary()["oee"],
    }


@app.get("/api/energy")
async def get_energy():
    return {
        "mode": APP_MODE,
        "source": "mock" if APP_MODE == "mock" else "production-fallback",
        "generated_at": now_string(),
        "energy": build_dashboard_summary()["energy"],
    }


@app.get("/api/analyze")
async def get_ai_recommendations():
    if not app_state["is_anomaly_active"]:
        return {
            "insight": "No active anomaly",
            "confidence_score": "12%",
            "risk_level": "Low",
            "recommended_actions": [],
        }

    current_data = app_state.get("latest_ingested_data") or {
        "vibration": 3.6,
        "temperature": 80.0,
        "load": 70.0,
        "status": "Critical",
    }
    cache_key = app_state.get("anomaly_start_time") or "active-anomaly"
    if app_state.get("recommendation_cache_key") == cache_key and app_state.get("recommendation_cache"):
        return app_state["recommendation_cache"]

    retrieved_context = MOCK_KNOWLEDGE_BASE

    if APP_MODE == "production" and search_client:
        try:
            search_query = f"High vibration {current_data.get('vibration')} and temperature {current_data.get('temperature')}"
            results = search_client.search(search_text=search_query, top=2)
            search_context = ""

            for result in results:
                search_context += f"\n[Document ID: {result.get('id', 'Unknown')}]\n{result.get('content', '')}\n"

            if search_context.strip():
                retrieved_context = search_context
        except Exception as exc:
            print(f"Azure Search failed: {exc}. Falling back to local files.")

    fallback_response = {
        "insight": "Anomaly detected at Motor A (System Fallback)",
        "confidence_score": "88%",
        "risk_level": "High",
        "retrieved_sop": {
            "document_id": "SOP-MA-102: Bearing Inspection & Replacement",
            "match_score": "92%",
            "excerpts": ["Check bearings immediately."],
        },
        "recommended_actions": [
            {"id": 1, "action": "Inspect within 24 hours", "impact": "High Impact"},
            {"id": 2, "action": "Reduce operating load by 15%", "impact": "Medium Impact"},
        ],
    }

    if APP_MODE == "mock" or not openai_client:
        app_state["recommendation_cache"] = fallback_response
        app_state["recommendation_cache_key"] = cache_key
        return fallback_response

    system_prompt = f"""
        You are 'TwinOps AI', an expert maintenance assistant for a Smart Factory.
        Analyze the incoming sensor data and provide recommendations strictly based on the provided SOP database.

        [SOP DATABASE]
        {retrieved_context}

        [INSTRUCTIONS]
        1. Compare the sensor data against the SOP thresholds.
        2. Determine the risk level (High, Medium, Low).
        3. Extract the relevant SOP document ID and exact matched excerpts.
        4. Formulate actionable recommended actions based only on the SOP.

        [OUTPUT FORMAT]
        Return only a valid JSON object matching exactly this structure:
        {{
            "insight": "Short string explaining the diagnosis",
            "confidence_score": "Percentage string e.g. 92%",
            "risk_level": "High or Medium or Low",
            "retrieved_sop": {{
                "document_id": "Matched SOP ID",
                "match_score": "Percentage string",
                "excerpts": ["string list of matching SOP rules"]
            }},
            "recommended_actions": [
                {{"id": 1, "action": "string", "impact": "High Impact or Medium Impact"}}
            ]
        }}
    """

    user_prompt = (
        f"Motor A Sensor Data: Vibration = {current_data.get('vibration')} mm/s, "
        f"Temperature = {current_data.get('temperature')} C."
    )

    try:
        response = openai_client.chat.completions.create(
            model=openai_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
        )

        generated = json.loads(response.choices[0].message.content)
        app_state["recommendation_cache"] = generated
        app_state["recommendation_cache_key"] = cache_key
        return generated
    except Exception as exc:
        print(f"OpenAI generation failed: {exc}. Returning fallback response.")
        app_state["recommendation_cache"] = fallback_response
        app_state["recommendation_cache_key"] = cache_key
        return fallback_response

@app.get("/api/telemetry/live")
async def get_live_telemetry():
    telemetry = get_iot_latest_telemetry()

    if telemetry is None:
        return {
            "source": "azure-iot-hub",
            "status": "waiting",
            "message": "No telemetry received yet. Start the device simulator first.",
            "data": None,
        }

    return {
        "source": "azure-iot-hub",
        "status": "ok",
        "data": telemetry,
    }

@app.get("/api/telemetry/stream")
async def stream_live_telemetry():
    async def event_generator():
        while True:
            telemetry = get_iot_latest_telemetry()

            if telemetry is None:
                payload = {
                    "source": "azure-iot-hub",
                    "status": "waiting",
                    "message": "No telemetry received yet. Start the device simulator first.",
                    "data": None,
                }
            else:
                payload = {
                    "source": "azure-iot-hub",
                    "status": "ok",
                    "data": telemetry,
                }

            yield f"data: {json.dumps(payload, default=str)}\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )

@app.get("/api/reports")
async def get_reports():
    if APP_MODE == "production":
        external_data = fetch_external_json(REPORTS_DATA_ENDPOINT)
        if external_data:
            return external_data

    return {
        "mode": APP_MODE,
        "source": reports_source(),
        "generated_at": now_string(),
        "business_value": build_business_value_report(),
        "roi": build_roi_report(),
        "azure_architecture": build_azure_architecture_report(),
        "operating_model": build_operating_model_report(),
        "roadmap": build_roadmap_report(),
    }


@app.get("/api/reports/business-value")
async def get_business_value_report():
    return build_business_value_report()


@app.get("/api/reports/roi")
async def get_roi_report():
    return build_roi_report()


@app.get("/api/reports/azure-architecture")
async def get_azure_architecture_report():
    return build_azure_architecture_report()


@app.get("/api/reports/operating-model")
async def get_operating_model_report():
    return build_operating_model_report()


@app.get("/api/reports/roadmap")
async def get_roadmap_report():
    return build_roadmap_report()


@app.get("/api/work-orders", response_model=list[WorkOrder])
async def list_work_orders():
    if APP_MODE == "production":
        cosmos_orders = list_cosmos_work_orders()
        if cosmos_orders:
            for item in cosmos_orders:
                app_state["work_orders"][item["id"]] = item
            return cosmos_orders

    return list(app_state["work_orders"].values())


@app.post("/api/work-orders", response_model=WorkOrder)
async def create_work_order(payload: WorkOrderCreateRequest | None = None):
    if not app_state["is_anomaly_active"]:
        raise HTTPException(
            status_code=409,
            detail="No active anomaly. Generate a work order after an AI recommendation is available.",
        )

    request_payload = payload or WorkOrderCreateRequest()
    work_order = build_work_order_from_recommendation(request_payload)

    return persist_work_order(work_order)


@app.get("/api/work-orders/{work_order_id}", response_model=WorkOrder)
async def get_work_order(work_order_id: str):
    return get_work_order_or_404(work_order_id)


@app.post("/api/work-orders/{work_order_id}/approve", response_model=WorkOrder)
async def approve_work_order(work_order_id: str, payload: WorkOrderApprovalRequest | None = None):
    work_order = get_work_order_or_404(work_order_id)

    if work_order["status"] == "Dispatched":
        raise HTTPException(status_code=409, detail="Dispatched work orders cannot be approved again")

    work_order["status"] = "Approved"
    request_payload = payload or WorkOrderApprovalRequest()
    approver = request_payload.approved_by or "Supervisor"
    note = f" Note: {request_payload.note}" if request_payload.note else ""
    append_work_order_history(work_order, f"{approver} approved the maintenance action.{note}")

    return persist_work_order(work_order)


@app.post("/api/work-orders/{work_order_id}/dispatch", response_model=WorkOrder)
async def dispatch_work_order(work_order_id: str, payload: WorkOrderDispatchRequest | None = None):
    work_order = get_work_order_or_404(work_order_id)

    if work_order["status"] != "Approved":
        raise HTTPException(status_code=409, detail="Work order must be approved before dispatch")

    request_payload = payload or WorkOrderDispatchRequest()
    dispatcher = request_payload.dispatched_by or "Maintenance Coordinator"
    note = f" Note: {request_payload.note}" if request_payload.note else ""
    append_work_order_history(work_order, f"{dispatcher} requested maintenance dispatch.{note}")

    if APP_MODE == "production":
        return dispatch_to_external_system(work_order)

    work_order["status"] = "Dispatched"
    work_order["dispatchStatus"] = "Dispatched"
    work_order["dispatchError"] = None
    append_work_order_history(work_order, "Work order dispatched to the mock maintenance team.")

    return persist_work_order(work_order)


@app.post("/api/work-orders/{work_order_id}/approval-callback", response_model=WorkOrder)
async def work_order_approval_callback(work_order_id: str, payload: WorkOrderApprovalCallback):
    if APPROVAL_CALLBACK_TOKEN and payload.token != APPROVAL_CALLBACK_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid approval callback token")

    work_order = get_work_order_or_404(work_order_id)
    approver = payload.approved_by or "External approver"
    note = f" Note: {payload.note}" if payload.note else ""
    external_id = f" External approval id: {payload.externalApprovalId}." if payload.externalApprovalId else ""

    if payload.decision == "approved":
        work_order["status"] = "Approved"
        append_work_order_history(work_order, f"{approver} approved via external approval callback.{external_id}{note}")
    else:
        work_order["status"] = "Rejected"
        work_order["dispatchStatus"] = "Not dispatched"
        append_work_order_history(work_order, f"{approver} rejected via external approval callback.{external_id}{note}")

    return persist_work_order(work_order)


@app.post("/api/agent/trigger")
async def trigger_agent_workflow(payload: AgentTriggerRequest | None = None):
    request_payload = payload or AgentTriggerRequest()
    session_id = request_payload.sessionId or f"session-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    telemetry = request_payload.telemetry or build_telemetry_snapshot().get("motor_A", {})

    app_state["agent_cascade_started"] = True
    app_state["agent_cascade_last_run"] = now_string()

    decision = {
        "sessionId": session_id,
        "anomalyId": request_payload.anomalyId,
        "machineId": request_payload.machineId,
        "severity": request_payload.severity,
        "source": request_payload.source,
        "status": "queued",
        "orchestrator": "backend-simulated-orchestrator",
        "foundryRuntimeCalled": False,
        "recommendedNextAction": "Run /api/agents or /api/analyze, then create a work order if supervisor approval is needed.",
        "telemetry": telemetry,
    }
    saved_decision = save_agent_decision(session_id, decision)

    return {
        "status": "accepted",
        "mode": APP_MODE,
        "sessionId": session_id,
        "foundryRuntimeCalled": False,
        "message": "Agent trigger accepted. Foundry runtime is intentionally not called in this scope.",
        "decision": saved_decision,
    }


@app.get("/api/agent/decisions")
async def get_agent_decisions(sessionId: str | None = None, limit: int = 20):
    decisions = list_agent_decisions(session_id=sessionId, limit=limit)
    if not decisions and app_state.get("agent_cascade_started"):
        decisions = [
            {
                "id": "local-agent-cascade",
                "sessionId": app_state.get("agent_cascade_last_run") or "local",
                "source": "local-memory",
                "status": "completed",
                "foundryRuntimeCalled": False,
                "recommendedNextAction": "Review AI recommendation and create work order.",
            }
        ]

    return {
        "status": "ok",
        "source": "cosmos-db" if decisions and decisions[0].get("cosmosSaved") else "local-fallback",
        "count": len(decisions),
        "decisions": decisions,
    }


@app.get("/api/energy/insights")
async def get_energy_insights(deviceId: str | None = None, limit: int = 20):
    insights = list_energy_insights(device_id=deviceId, limit=limit)
    if not insights:
        current = build_telemetry_snapshot().get("motor_A", {})
        insights = [
            {
                "id": "local-energy-insight",
                "deviceId": "motor-A",
                "source": "local-fallback",
                "energyLoad": current.get("load") or current.get("energyLoad"),
                "correlation": "Energy load is correlated with the active Motor A anomaly scenario." if app_state["is_anomaly_active"] else "No active energy anomaly detected.",
                "createdAt": now_string(),
            }
        ]

    return {
        "status": "ok",
        "source": "cosmos-db" if insights and insights[0].get("cosmosSaved") else "local-fallback",
        "count": len(insights),
        "insights": insights,
    }
@app.get("/api/anomaly/results")
async def get_anomaly_results(machineId: str | None = None, limit: int = 20):
    results = list_anomaly_results(machine_id=machineId, limit=limit)
    return {
        "source": "cosmos-db" if cosmos_enabled() else "local-disabled",
        "status": "ok",
        "count": len(results),
        "results": results,
    }


@app.post("/api/anomaly/detect")
async def detect_anomaly():
    try:
        telemetry = build_telemetry_snapshot()

        detection = detect_anomaly_from_telemetry(telemetry)

        motor_a = telemetry.get("motor_A", {})

        result = save_anomaly_result(
            machine_id="motor-A",
            telemetry=motor_a,
            is_anomaly=detection.get("isAnomaly", False),
            severity=detection.get("severity", "Low"),
            contributing_factors=detection.get("contributingFactors", []),
            source=detection.get("source", "azure-ml-managed-endpoint"),
            agent_triggered=detection.get("isAnomaly", False),
        )

        energy_insight = save_energy_insight(
            device_id="motor-A",
            insight={
                "machineId": "motor-A",
                "severity": detection.get("severity", "Low"),
                "isAnomaly": detection.get("isAnomaly", False),
                "energyLoad": motor_a.get("load") or motor_a.get("energyLoad"),
                "correlation": "Energy load is elevated during Motor A anomaly detection."
                if detection.get("isAnomaly", False)
                else "Energy load is within expected range.",
                "source": detection.get("source", "azure-ml-managed-endpoint"),
            },
        )

        agent_decision = save_agent_decision(
            session_id=result["id"],
            decision={
                "anomalyId": result["id"],
                "machineId": "motor-A",
                "severity": detection.get("severity", "Low"),
                "source": "anomaly-detect-api",
                "status": "queued" if detection.get("isAnomaly", False) else "not-required",
                "foundryRuntimeCalled": False,
                "recommendedNextAction": "Start agent cascade and prepare maintenance recommendation."
                if detection.get("isAnomaly", False)
                else "Continue monitoring.",
            },
        )

        if detection.get("isAnomaly", False):
            update_anomaly_state_from_metrics({
                "vibration": float(motor_a.get("vibration", 3.6)),
                "temperature": float(motor_a.get("temperature", 80.0)),
                "load": float(motor_a.get("load", motor_a.get("energyLoad", 90.0))),
                "status": "Critical",
            }, telemetry.get("timestamp"))

        return {
            "status": "ok",
            "cosmosEnabled": cosmos_enabled(),
            "detection": detection,
            "result": result,
            "energyInsight": energy_insight,
            "agentDecision": agent_decision,
            "agentTrigger": {
                "enabled": detection.get("isAnomaly", False),
                "target": "phase-5-agent-orchestrator",
                "reason": "anomaly detected" if detection.get("isAnomaly", False) else "normal telemetry",
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Anomaly detection failed: {type(e).__name__}: {str(e)}",
        )

@app.get("/api/fabric/telemetry/latest")
async def fabric_telemetry_latest(
    limit: int = Query(default=20, ge=1, le=100),
    minutes: int = Query(default=30, ge=1, le=1440),
):
    try:
        data = get_fabric_latest_telemetry(limit=limit, minutes=minutes)

        return {
            "status": "ok",
            "source": "microsoft-fabric-kql",
            "database": "twinopsai_kql_db",
            "table": "telemetry_v2",
            "count": len(data),
            "data": data,
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "source": "microsoft-fabric-kql",
                "message": str(error),
            },
        )


@app.get("/api/fabric/anomalies/latest")
async def fabric_anomalies_latest(
    limit: int = Query(default=20, ge=1, le=100),
    minutes: int = Query(default=30, ge=1, le=1440),
):
    try:
        anomalies = get_fabric_latest_anomalies(limit=limit, minutes=minutes)

        return {
            "status": "ok",
            "source": "microsoft-fabric-kql",
            "table": "telemetry_v2",
            "count": len(anomalies),
            "anomalyCount": len(anomalies),
            "anomalies": anomalies,
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "source": "microsoft-fabric-kql",
                "message": str(error),
            },
        )


@app.get("/api/fabric/anomaly/latest")
async def get_fabric_anomaly_latest(
    limit: int = Query(default=20, ge=1, le=100),
    minutes: int = Query(default=120, ge=1, le=1440),
):
    try:
        rows = get_fabric_latest_telemetry(limit=limit, minutes=minutes)
        alerts = []

        for row in rows:
            temperature = float(row.get("temperature") or 0)
            vibration = float(row.get("vibration") or 0)
            energy_load = float(row.get("energyLoad") or 0)
            status = str(row.get("status") or "").upper()

            reasons = []

            if temperature > 76:
                reasons.append(f"temperature high: {temperature}")

            if vibration > 3.5:
                reasons.append(f"vibration high: {vibration}")

            if energy_load > 20:
                reasons.append(f"energyLoad high: {energy_load}")

            if status == "WARN":
                reasons.append("device status is WARN")

            if reasons:
                severity = "CRITICAL" if (
                    temperature > 76
                    or vibration > 3.5
                    or energy_load > 20
                    or status == "WARN"
                ) else "WARNING"

                alerts.append({
                    "timestamp": row.get("timestamp"),
                    "machineId": row.get("machineId"),
                    "deviceId": row.get("deviceId"),
                    "severity": severity,
                    "status": status,
                    "temperature": temperature,
                    "vibration": vibration,
                    "energyLoad": energy_load,
                    "reasons": reasons,
                    "recommendedAction": "Inspect motor-A and create maintenance work order",
                })

        return {
            "status": "ok",
            "source": "microsoft-fabric-kql",
            "table": "telemetry_v2",
            "count": len(alerts),
            "alerts": alerts,
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "source": "microsoft-fabric-kql",
                "message": str(error),
            },
        )

@app.get("/api/fabric/dashboard")
async def fabric_dashboard(
    limit: int = Query(default=20, ge=1, le=100),
    minutes: int = Query(default=120, ge=1, le=1440),
):
    try:
        telemetry = get_fabric_latest_telemetry(limit=limit, minutes=minutes)
        anomalies = get_fabric_latest_anomalies(limit=limit, minutes=minutes)

        latest = telemetry[0] if telemetry else None
        critical_count = sum(
            1 for row in anomalies
            if row.get("severity") == "CRITICAL" or row.get("isAnomaly") is True
        )

        return {
            "status": "ok",
            "source": "microsoft-fabric-kql",
            "table": "telemetry_v2",
            "latestTelemetry": latest,
            "telemetry": telemetry,
            "alerts": anomalies,
            "summary": {
                "telemetryCount": len(telemetry),
                "alertCount": len(anomalies),
                "criticalCount": critical_count,
                "assetHealth": "Critical" if critical_count > 0 else "Normal",
            },
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "source": "microsoft-fabric-kql",
                "message": str(error),
            },
        )
