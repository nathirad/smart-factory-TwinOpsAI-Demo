import inspect
import os
from datetime import datetime
from typing import Any

from fastapi import FastAPI, Query


def _now_string() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _status_upper(value: Any) -> str:
    return str(value or "NORMAL").upper()


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def _try_get_fabric_latest(limit: int = 1, minutes: int = 1440) -> dict[str, Any]:
    """
    Best-effort Fabric context.
    ถ้า Fabric ใช้ได้ จะใช้ telemetry_v2 ล่าสุด
    ถ้าไม่ได้ จะไม่ทำให้ /api/agents พัง
    """
    if not os.getenv("FABRIC_KQL_CLUSTER_URI"):
        return {
            "enabled": False,
            "source": "fallback",
            "latest": None,
            "error": "FABRIC_KQL_CLUSTER_URI is not configured",
        }

    try:
        from services.fabric_kql import get_latest_telemetry

        result = await _maybe_await(get_latest_telemetry(limit=limit, minutes=minutes))

        if isinstance(result, dict):
            rows = result.get("data") or result.get("rows") or []
        elif isinstance(result, list):
            rows = result
        else:
            rows = []

        latest = rows[0] if rows else None

        return {
            "enabled": True,
            "source": "microsoft-fabric-kql",
            "latest": latest,
            "error": None,
        }

    except Exception as exc:
        return {
            "enabled": True,
            "source": "fabric-error-fallback",
            "latest": None,
            "error": str(exc),
        }


def _build_local_latest_from_app_state(app_state: dict[str, Any]) -> dict[str, Any]:
    latest = app_state.get("latest_ingested_data") or {}

    return {
        "timestamp": _now_string(),
        "machineId": latest.get("machineId") or latest.get("machine_id") or "motor-A",
        "deviceId": latest.get("deviceId") or latest.get("device_id") or "simDevice01",
        "vibration": _safe_float(latest.get("vibration"), 1.2),
        "temperature": _safe_float(latest.get("temperature"), 62.0),
        "energyLoad": _safe_float(latest.get("energyLoad") or latest.get("load"), 18.0),
        "status": latest.get("status") or ("CRITICAL" if app_state.get("is_anomaly_active") else "NORMAL"),
    }


async def _build_telemetry_context(app_state: dict[str, Any]) -> dict[str, Any]:
    fabric_context = await _try_get_fabric_latest(limit=1, minutes=1440)

    latest = fabric_context.get("latest")
    if not latest:
        latest = _build_local_latest_from_app_state(app_state)

    machine_id = (
        latest.get("machineId")
        or latest.get("machine_id")
        or latest.get("assetId")
        or "motor-A"
    )

    normalized = {
        "timestamp": latest.get("timestamp") or _now_string(),
        "machineId": machine_id,
        "deviceId": latest.get("deviceId") or latest.get("device_id") or "simDevice01",
        "vibration": _safe_float(latest.get("vibration")),
        "temperature": _safe_float(latest.get("temperature")),
        "energyLoad": _safe_float(latest.get("energyLoad") or latest.get("load")),
        "status": _status_upper(latest.get("status")),
    }

    return {
        "source": fabric_context["source"],
        "fabric_error": fabric_context.get("error"),
        "latest": normalized,
    }


async def _try_get_twin_context(machine_id: str) -> dict[str, Any]:
    twin_id = str(machine_id or "motor-A")

    try:
        from services.adt_service import get_mock_twin_dependencies, get_twin_dependencies

        try:
            result = await _maybe_await(get_twin_dependencies(twin_id))
            source = result.get("source", "azure-digital-twins") if isinstance(result, dict) else "azure-digital-twins"
            return {
                "source": source,
                "twinId": twin_id,
                "data": result,
                "error": None,
            }
        except Exception as exc:
            mock_result = get_mock_twin_dependencies(twin_id)
            return {
                "source": "mock-digital-twins",
                "twinId": twin_id,
                "data": mock_result,
                "error": str(exc),
            }

    except Exception as exc:
        return {
            "source": "unavailable",
            "twinId": twin_id,
            "data": None,
            "error": str(exc),
        }


def _detect_risk(row: dict[str, Any]) -> dict[str, Any]:
    vibration = _safe_float(row.get("vibration"))
    temperature = _safe_float(row.get("temperature"))
    energy_load = _safe_float(row.get("energyLoad"))
    status = _status_upper(row.get("status"))

    reasons: list[str] = []

    if temperature > 76:
        reasons.append(f"temperature high: {temperature}")

    if vibration > 3.5:
        reasons.append(f"vibration high: {vibration}")

    if energy_load > 20:
        reasons.append(f"energyLoad high: {energy_load}")

    if status in {"WARN", "WARNING", "CRITICAL", "FAULT", "ERROR"}:
        reasons.append(f"device status is {status}")

    severity = "NORMAL"
    if reasons:
        severity = "CRITICAL" if (
            temperature > 76 or vibration > 3.5 or energy_load > 20 or status == "CRITICAL"
        ) else "WARNING"

    return {
        "severity": severity,
        "reasons": reasons,
        "temperature": temperature,
        "vibration": vibration,
        "energyLoad": energy_load,
        "status": status,
    }


def _agent_status(started: bool) -> str:
    return "completed" if started else "not-started"


def _build_agents(started: bool, telemetry: dict[str, Any], risk: dict[str, Any], twin_context: dict[str, Any]) -> list[dict[str, Any]]:
    severity = risk["severity"]
    machine_id = telemetry["machineId"]

    if not started:
        return [
            {
                "id": "sensor",
                "order": 1,
                "name": "Sensor Agent",
                "role": "Read telemetry from IoT Hub / Fabric stream",
                "status": "not-started",
                "summary": "Waiting for anomaly trigger or agent run.",
                "elapsed": "-",
                "tone": "blue",
                "azure_service": "Azure IoT Hub + Microsoft Fabric",
            },
            {
                "id": "twin",
                "order": 2,
                "name": "Twin Agent",
                "role": "Map affected asset and downstream dependencies",
                "status": "not-started",
                "summary": "Waiting for Sensor Agent output.",
                "elapsed": "-",
                "tone": "purple",
                "azure_service": "Azure Digital Twins",
            },
            {
                "id": "maintenance",
                "order": 3,
                "name": "Maintenance Agent",
                "role": "Generate maintenance action using SOP / RAG evidence",
                "status": "not-started",
                "summary": "Waiting for Twin Agent context.",
                "elapsed": "-",
                "tone": "orange",
                "azure_service": "Azure AI Search + Azure OpenAI / Foundry",
            },
            {
                "id": "energy",
                "order": 4,
                "name": "Energy Agent",
                "role": "Assess energy and load impact",
                "status": "not-started",
                "summary": "Waiting for telemetry risk assessment.",
                "elapsed": "-",
                "tone": "green",
                "azure_service": "Microsoft Fabric KQL",
            },
            {
                "id": "safety",
                "order": 5,
                "name": "Safety Agent",
                "role": "Check safety and operational risk",
                "status": "not-started",
                "summary": "Waiting for criticality decision.",
                "elapsed": "-",
                "tone": "orange",
                "azure_service": "Azure AI / Rules Engine",
            },
            {
                "id": "business",
                "order": 6,
                "name": "Business Impact Agent",
                "role": "Estimate downtime, OEE, ROI, and work-order priority",
                "status": "not-started",
                "summary": "Waiting for final recommendation.",
                "elapsed": "-",
                "tone": "green",
                "azure_service": "Microsoft Fabric + Reports API",
            },
        ]

    return [
        {
            "id": "sensor",
            "order": 1,
            "name": "Sensor Agent",
            "role": "Read telemetry from IoT Hub / Fabric stream",
            "status": _agent_status(started),
            "summary": (
                f"Read latest telemetry for {machine_id}: "
                f"vibration={telemetry['vibration']}, "
                f"temperature={telemetry['temperature']}, "
                f"energyLoad={telemetry['energyLoad']}, "
                f"status={telemetry['status']}."
            ),
            "elapsed": "0.4s",
            "tone": "blue",
            "azure_service": "Azure IoT Hub + Microsoft Fabric",
        },
        {
            "id": "twin",
            "order": 2,
            "name": "Twin Agent",
            "role": "Map affected asset and downstream dependencies",
            "status": _agent_status(started),
            "summary": (
                f"Mapped {machine_id} in twin graph. "
                f"Dependency source={twin_context['source']}. "
                "Downstream risk checked for Motor B and Conveyor C."
            ),
            "elapsed": "0.7s",
            "tone": "purple",
            "azure_service": "Azure Digital Twins",
        },
        {
            "id": "maintenance",
            "order": 3,
            "name": "Maintenance Agent",
            "role": "Generate maintenance action using SOP / RAG evidence",
            "status": _agent_status(started),
            "summary": (
                "Recommended inspection and maintenance work order."
                if severity != "NORMAL"
                else "No urgent maintenance action required. Continue monitoring."
            ),
            "elapsed": "1.1s",
            "tone": "orange",
            "azure_service": "Azure AI Search + Azure OpenAI / Foundry",
        },
        {
            "id": "energy",
            "order": 4,
            "name": "Energy Agent",
            "role": "Assess energy and load impact",
            "status": _agent_status(started),
            "summary": (
                f"Energy load is {telemetry['energyLoad']}. "
                + ("Elevated load may increase operating cost." if telemetry["energyLoad"] > 20 else "Energy load is within acceptable range.")
            ),
            "elapsed": "0.6s",
            "tone": "green",
            "azure_service": "Microsoft Fabric KQL",
        },
        {
            "id": "safety",
            "order": 5,
            "name": "Safety Agent",
            "role": "Check safety and operational risk",
            "status": _agent_status(started),
            "summary": (
                "Safety review required before continuing full-load operation."
                if severity == "CRITICAL"
                else "No immediate safety stop required."
            ),
            "elapsed": "0.5s",
            "tone": "orange",
            "azure_service": "Azure AI / Rules Engine",
        },
        {
            "id": "business",
            "order": 6,
            "name": "Business Impact Agent",
            "role": "Estimate downtime, OEE, ROI, and work-order priority",
            "status": _agent_status(started),
            "summary": (
                "Potential OEE loss and downtime risk detected. Create high-priority work order."
                if severity == "CRITICAL"
                else "Business impact is low. Monitor trend before dispatch."
            ),
            "elapsed": "0.9s",
            "tone": "green",
            "azure_service": "Microsoft Fabric + Reports API",
        },
    ]


def _build_execution_log(started: bool, agents: list[dict[str, Any]], risk: dict[str, Any]) -> list[dict[str, Any]]:
    if not started:
        return [
            {
                "id": "log-standby",
                "agent": "Orchestrator",
                "time": _now_string(),
                "message": "Agent cascade is on standby.",
                "status": "pending",
                "azure_service": "Foundry Agent Orchestrator",
            }
        ]

    logs = []
    for agent in agents:
        logs.append({
            "id": f"log-{agent['id']}",
            "agent": agent["name"],
            "time": _now_string(),
            "message": agent["summary"],
            "status": agent["status"],
            "azure_service": agent["azure_service"],
        })

    logs.append({
        "id": "log-risk-final",
        "agent": "Orchestrator",
        "time": _now_string(),
        "message": f"Final risk decision: {risk['severity']}. Reasons: {', '.join(risk['reasons']) if risk['reasons'] else 'none'}",
        "status": "completed",
        "azure_service": "Foundry Agent Orchestrator",
    })

    return logs


def _recommended_next_action(started: bool, risk: dict[str, Any]) -> str:
    if not started:
        return "Trigger anomaly or run the agent cascade to generate an operational recommendation."

    if risk["severity"] == "CRITICAL":
        return "Create a high-priority work order, reduce load, inspect Motor A bearing, and monitor Conveyor C downstream impact."

    if risk["severity"] == "WARNING":
        return "Monitor trend, prepare maintenance inspection, and keep the line under observation."

    return "Continue monitoring. No urgent action required."


def register_agents_routes(app: FastAPI, app_state: dict[str, Any]) -> None:
    async def build_response() -> dict[str, Any]:
        telemetry_context = await _build_telemetry_context(app_state)
        telemetry = telemetry_context["latest"]
        twin_context = await _try_get_twin_context(telemetry["machineId"])
        risk = _detect_risk(telemetry)

        started = bool(app_state.get("agent_cascade_started")) or bool(app_state.get("is_anomaly_active"))
        agents = _build_agents(started, telemetry, risk, twin_context)
        execution_log = _build_execution_log(started, agents, risk)

        return {
            "run_id": f"agent-run-{app_state.get('agent_cascade_last_run') or 'standby'}",
            "mode": os.getenv("APP_MODE", "mock").lower(),
            "anomaly_active": bool(app_state.get("is_anomaly_active")),
            "cascade_status": "completed" if started else "standby",
            "orchestrator": {
                "name": "TwinOpsAI Agent Orchestrator",
                "description": "Coordinates Sensor, Twin, Maintenance, Energy, Safety, and Business Impact agents.",
            },
            "azure_architecture": [
                "Azure IoT Hub receives live telemetry.",
                "Microsoft Fabric KQL stores operational telemetry history.",
                "Azure Digital Twins maps machine dependencies.",
                "Azure AI Search retrieves SOP evidence.",
                "Azure OpenAI / Foundry generates operational recommendations.",
                "Work Orders API prepares supervisor-approved maintenance actions.",
            ],
            "telemetry_context": telemetry_context,
            "twin_context": twin_context,
            "risk": risk,
            "agents": agents,
            "execution_log": execution_log,
            "recommended_next_action": _recommended_next_action(started, risk),
            "generated_at": _now_string(),
        }

    @app.get("/api/agents")
    async def get_agents():
        return await build_response()

    @app.post("/api/agents/run")
    async def run_agents(
        simulate_anomaly: bool = Query(default=False),
    ):
        app_state["agent_cascade_started"] = True
        app_state["agent_cascade_last_run"] = _now_string()

        if simulate_anomaly:
            app_state["is_anomaly_active"] = True
            app_state["anomaly_start_time"] = app_state["agent_cascade_last_run"]

        return await build_response()

    @app.post("/api/agents/reset")
    async def reset_agents():
        app_state["agent_cascade_started"] = False
        app_state["agent_cascade_last_run"] = None

        return {
            "status": "ok",
            "message": "Agent cascade state reset.",
            "generated_at": _now_string(),
        }

    @app.get("/api/agents/health")
    async def agents_health():
        return {
            "status": "ok",
            "feature": "phase-6-agent-cascade",
            "routes": [
                "GET /api/agents",
                "POST /api/agents/run",
                "POST /api/agents/reset",
                "GET /api/agents/health",
            ],
            "generated_at": _now_string(),
        }
