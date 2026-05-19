from datetime import datetime
from typing import Any

from fastapi import FastAPI


AGENT_SEQUENCE = [
    {
        "id": "sensor",
        "order": 1,
        "name": "Sensor Agent",
        "role": "Telemetry anomaly detection",
        "azure_service": "Azure IoT Hub",
        "summary": "Monitors vibration, temperature, load, and status from connected factory assets.",
        "completed_message": "Motor A vibration and temperature exceed the expected operating envelope.",
        "standby_message": "Waiting for critical telemetry from Azure IoT Hub.",
        "elapsed": "612 ms",
        "tone": "blue",
    },
    {
        "id": "twin",
        "order": 2,
        "name": "Twin Agent",
        "role": "Asset graph and dependency impact",
        "azure_service": "Azure Digital Twins",
        "summary": "Maps the affected asset to downstream dependencies and line-level impact.",
        "completed_message": "Mapped Motor A as the affected asset and Conveyor C as downstream at risk.",
        "standby_message": "Waiting for an affected asset before querying the digital twin graph.",
        "elapsed": "1.2 s",
        "tone": "blue",
    },
    {
        "id": "maintenance",
        "order": 3,
        "name": "Maintenance Agent",
        "role": "SOP and maintenance context retrieval",
        "azure_service": "Azure AI Search + Azure OpenAI",
        "summary": "Retrieves SOP context and prepares likely root cause and maintenance actions.",
        "completed_message": "Matched SOP-MA-102 and recommended bearing inspection plus load reduction.",
        "standby_message": "Waiting for confirmed asset impact before retrieving SOP context.",
        "elapsed": "1.8 s",
        "tone": "purple",
    },
    {
        "id": "energy",
        "order": 4,
        "name": "Energy Agent",
        "role": "Load and energy scenario analysis",
        "azure_service": "Microsoft Fabric Real-Time Intelligence",
        "summary": "Evaluates energy/load trade-offs for temporary mitigation.",
        "completed_message": "Estimated that a 15% load reduction lowers risk while preserving line throughput.",
        "standby_message": "Waiting for maintenance recommendation before evaluating load scenarios.",
        "elapsed": "740 ms",
        "tone": "blue",
    },
    {
        "id": "safety",
        "order": 5,
        "name": "Safety Agent",
        "role": "Approval and operational safety guardrails",
        "azure_service": "Microsoft Entra ID + Defender for IoT",
        "summary": "Checks whether the action requires supervisor approval and safety confirmation.",
        "completed_message": "Supervisor approval required before intervention; no automatic shutdown triggered.",
        "standby_message": "Waiting for recommended action before safety validation.",
        "elapsed": "520 ms",
        "tone": "orange",
    },
    {
        "id": "business",
        "order": 6,
        "name": "Business Impact Agent",
        "role": "Downtime, throughput, and cost impact estimate",
        "azure_service": "Azure Monitor + Power BI",
        "summary": "Summarizes operational impact for the supervisor and maintenance team.",
        "completed_message": "Estimated 18-25% throughput risk if Motor A is not inspected within 24 hours.",
        "standby_message": "Waiting for safety validation before calculating business impact.",
        "elapsed": "660 ms",
        "tone": "green",
    },
]


def now_string() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_time(index: int) -> str:
    base_ms = 123 + (index * 421)
    return f"{datetime.now().strftime('%H:%M:%S')}.{base_ms % 1000:03d}"


def build_agent_steps(anomaly_active: bool, cascade_started: bool) -> list[dict[str, Any]]:
    active_statuses = ["completed", "completed", "completed", "completed", "completed", "completed"]
    standby_statuses = ["pending", "pending", "pending", "pending", "pending", "pending"]
    statuses = active_statuses if anomaly_active or cascade_started else standby_statuses

    return [
        {
            "id": agent["id"],
            "order": agent["order"],
            "name": agent["name"],
            "role": agent["role"],
            "status": statuses[index],
            "summary": agent["summary"],
            "elapsed": agent["elapsed"] if statuses[index] == "completed" else "-",
            "tone": agent["tone"],
            "azure_service": agent["azure_service"],
        }
        for index, agent in enumerate(AGENT_SEQUENCE)
    ]


def build_execution_log(anomaly_active: bool, cascade_started: bool) -> list[dict[str, str]]:
    if not anomaly_active and not cascade_started:
        return [
            {
                "id": "standby",
                "agent": "Azure Agent Orchestrator",
                "time": log_time(0),
                "message": "Waiting for anomaly simulation before starting the multi-agent cascade.",
                "status": "pending",
                "azure_service": "Azure AI Foundry Agent Service",
            }
        ]

    logs = [
        {
            "id": agent["id"],
            "agent": agent["name"],
            "time": log_time(index),
            "message": agent["completed_message"],
            "status": "completed",
            "azure_service": agent["azure_service"],
        }
        for index, agent in enumerate(AGENT_SEQUENCE)
    ]
    logs.append(
        {
            "id": "work-order-ready",
            "agent": "Azure Agent Orchestrator",
            "time": log_time(len(AGENT_SEQUENCE)),
            "message": "Cascade completed and maintenance work-order recommendation is ready for supervisor approval.",
            "status": "completed",
            "azure_service": "Azure AI Foundry Agent Service",
        }
    )
    return logs


def build_agents_response(app_state: dict[str, Any], manual_run: bool = False) -> dict[str, Any]:
    anomaly_active = bool(app_state.get("is_anomaly_active"))
    cascade_started = bool(app_state.get("agent_cascade_started")) or manual_run

    if manual_run:
        app_state["agent_cascade_started"] = True
        app_state["agent_cascade_last_run"] = now_string()

    agents = build_agent_steps(anomaly_active, cascade_started)
    execution_log = build_execution_log(anomaly_active, cascade_started)

    return {
        "run_id": app_state.get("agent_cascade_last_run") or "standby",
        "mode": "azure-simulated",
        "anomaly_active": anomaly_active,
        "cascade_status": "completed" if anomaly_active or cascade_started else "standby",
        "orchestrator": {
            "name": "Azure AI Foundry Agent Service",
            "description": "Simulated multi-agent orchestration for the SmartFactory TwinOps demo.",
        },
        "azure_architecture": [
            "Azure IoT Hub",
            "Azure Digital Twins",
            "Microsoft Fabric Real-Time Intelligence",
            "Azure AI Search",
            "Azure OpenAI",
            "Microsoft Entra ID",
            "Defender for IoT",
            "Azure Monitor",
            "Power BI",
        ],
        "agents": agents,
        "execution_log": execution_log,
        "recommended_next_action": (
            "Approve inspection of Motor A bearings and reduce operating load by 15%."
            if anomaly_active or cascade_started
            else "Keep monitoring telemetry until anomaly scenario starts."
        ),
        "generated_at": now_string(),
    }


def register_agents_routes(app: FastAPI, app_state: dict[str, Any]) -> None:
    # Agents API feature: keeps multi-agent cascade routes isolated from core telemetry/analyze routes.
    @app.get("/api/agents")
    async def get_agents():
        return build_agents_response(app_state)

    # Agents API feature: manual run endpoint for the demo Agents page or API testing tools.
    @app.post("/api/agents/run")
    async def run_agents():
        return build_agents_response(app_state, manual_run=True)

    # Agents API feature: execution-log-only endpoint for clients that do not need the full cascade payload.
    @app.get("/api/agents/logs")
    async def get_agent_logs():
        response = build_agents_response(app_state)
        return {
            "run_id": response["run_id"],
            "cascade_status": response["cascade_status"],
            "execution_log": response["execution_log"],
            "generated_at": response["generated_at"],
        }
    @app.get("/api/agents/health")
    async def agents_health():
        return {
        "status": "ok",
        "feature": "phase-6-agent-cascade",
        "routes": [
            "GET /api/agents"
            "POST /api/agents/run",
            "GET /api/agents/logs",
            "GET /api/agents/health",
        ],
    }
