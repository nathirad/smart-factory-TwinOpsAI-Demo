import glob
import json
import os
import random
import asyncio
from datetime import datetime
from typing import Literal
from urllib.error import URLError
from urllib.request import Request, urlopen
from services.adt_service import get_twin_dependencies
from fastapi.responses import StreamingResponse
from services.anomaly_service import detect_anomaly_from_telemetry
from services.azure_ml_service import azure_ml_enabled, detect_with_azure_ml

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from services.cosmos_service import save_anomaly_result, list_anomaly_results, cosmos_enabled
from features.agents_api import register_agents_routes
from services.azure_ml_service import azure_ml_enabled, detect_with_azure_ml
from services.cosmos_service import cosmos_enabled, save_anomaly_result

try:
    from openai import OpenAI
except ImportError:
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
DASHBOARD_DATA_ENDPOINT = os.getenv("DASHBOARD_DATA_ENDPOINT")
ALERTS_DATA_ENDPOINT = os.getenv("ALERTS_DATA_ENDPOINT")
REPORTS_DATA_ENDPOINT = os.getenv("REPORTS_DATA_ENDPOINT")
print(f"Starting SmartFactory TwinOps API in {APP_MODE.upper()} mode")

app = FastAPI(title="SmartFactory TwinOps API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


openai_key = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=openai_key) if openai_key and OpenAI else None

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


WorkOrderStatus = Literal["Draft", "Awaiting approval", "Approved", "Dispatched"]
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

    request = Request(endpoint, headers={"Accept": "application/json"}, method="GET")

    try:
        with urlopen(request, timeout=10) as response:
            response_body = response.read().decode("utf-8")
            return json.loads(response_body) if response_body else None
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"External data fetch failed for {endpoint}: {exc}")
        return None


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
    if not work_order:
        raise HTTPException(status_code=404, detail=f"Work order {work_order_id} not found")
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
        return work_order

    payload = json.dumps(work_order).encode("utf-8")
    request = Request(
        CMMS_DISPATCH_WEBHOOK_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
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
        return work_order

    work_order["status"] = "Dispatched"
    work_order["dispatchStatus"] = "Dispatched"
    work_order["dispatchError"] = None
    work_order["externalId"] = (
        external_response.get("external_id")
        or external_response.get("work_order_id")
        or external_response.get("id")
    )
    append_work_order_history(work_order, f"Work order dispatched to {WORK_ORDER_SYSTEM_NAME}.")
    return work_order


@app.post("/api/ingest-telemetry")
async def ingest_telemetry(payload: IngestPayload):
    app_state["latest_ingested_data"] = payload.data.model_dump()

    if payload.data.status == "Critical":
        app_state["is_anomaly_active"] = True
        app_state["anomaly_start_time"] = payload.timestamp
        # Agents API feature: critical telemetry starts the simulated agent cascade alongside the anomaly scenario.
        app_state["agent_cascade_started"] = True
        app_state["agent_cascade_last_run"] = now_string()

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

    return {
        "Message": "Anomaly simulation reset to normal state.",
    }


# Agents API feature: registers isolated routes for the simulated Microsoft Azure multi-agent cascade.
register_agents_routes(app, app_state)

@app.get("/api/twins/{twin_id}/dependencies")
async def get_twin_dependencies_api(twin_id: str):
    try:
        return get_twin_dependencies(twin_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

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
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
        )

        return json.loads(response.choices[0].message.content)
    except Exception as exc:
        print(f"OpenAI generation failed: {exc}. Returning fallback response.")
        return fallback_response

# Azure IoT Hub live telemetry integration
from services.iot_hub_service import (
    start_iot_hub_listener,
    stop_iot_hub_listener,
    get_latest_telemetry,
)


@app.on_event("startup")
async def startup_iot_hub_listener():
    await start_iot_hub_listener()


@app.on_event("shutdown")
async def shutdown_iot_hub_listener():
    await stop_iot_hub_listener()


@app.get("/api/telemetry/live")
async def get_live_telemetry():
    telemetry = get_latest_telemetry()

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
            telemetry = get_latest_telemetry()

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
    app_state["work_orders"][work_order["id"]] = work_order

    return work_order


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

    return work_order


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

    return work_order
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

        return {
            "status": "ok",
            "cosmosEnabled": cosmos_enabled(),
            "detection": detection,
            "result": result,
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