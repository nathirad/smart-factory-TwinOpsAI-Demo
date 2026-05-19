from datetime import datetime, timezone
from typing import Any, Dict, List


CRITICAL_TEMP = 76
CRITICAL_VIBRATION = 3.5
CRITICAL_ENERGY_LOAD = 20


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _read_latest_from_existing_services(machine_id: str) -> Dict[str, Any]:
    """
    Production adapter point.

    ตรงนี้คือจุดเชื่อมกับ services ที่คุณทำไว้แล้ว เช่น:
    - telemetry_service
    - fabric_kql_service
    - iot_hub_service
    - mock fallback

    ถ้าคุณมี function จริงแล้ว ให้เปลี่ยน logic ใน function นี้เท่านั้น
    โดยไม่ต้องแก้ route หรือ Agent instruction
    """

    # TODO: ถ้ามี Fabric service จริง ให้ map ตรงนี้ เช่น:
    # from services.fabric_kql_service import query_latest_telemetry
    # return await query_latest_telemetry(machine_id)

    # TODO: ถ้ามี telemetry service จริง ให้ map ตรงนี้ เช่น:
    # from services.telemetry_service import get_latest_telemetry
    # return await get_latest_telemetry(machine_id)

    # MVP fallback สำหรับ demo
    return {
        "machineId": machine_id,
        "deviceId": machine_id,
        "temperature": 82,
        "vibration": 4.2,
        "energyLoad": 23,
        "status": "FAULT",
        "timestamp": _now_iso(),
        "source": "fallback-demo-telemetry",
    }


async def _read_history_from_existing_services(machine_id: str, minutes: int) -> List[Dict[str, Any]]:
    """
    Production adapter point สำหรับ telemetry history.
    ถ้ามี Fabric KQL/Eventhouse แล้ว ให้ query history ตรงนี้
    """

    latest = await _read_latest_from_existing_services(machine_id)
    return [
        {
            **latest,
            "timestamp": _now_iso(),
            "window_minutes": minutes,
        }
    ]


def _evaluate_rules(telemetry: Dict[str, Any]) -> Dict[str, Any]:
    reasons: List[str] = []

    temperature = telemetry.get("temperature")
    vibration = telemetry.get("vibration")
    energy_load = telemetry.get("energyLoad")
    status = telemetry.get("status")

    critical = False

    if temperature is not None and temperature > CRITICAL_TEMP:
        critical = True
        reasons.append(f"temperature {temperature} exceeds critical threshold {CRITICAL_TEMP}")

    if vibration is not None and vibration > CRITICAL_VIBRATION:
        critical = True
        reasons.append(f"vibration {vibration} exceeds critical threshold {CRITICAL_VIBRATION}")

    if energy_load is not None and energy_load > CRITICAL_ENERGY_LOAD:
        critical = True
        reasons.append(f"energyLoad {energy_load} exceeds critical threshold {CRITICAL_ENERGY_LOAD}")

    if critical:
        severity = "Critical"
        anomaly_flag = True
    elif status == "WARN":
        severity = "Warning"
        anomaly_flag = True
        reasons.append("status is WARN")
    else:
        severity = "Normal"
        anomaly_flag = False
        reasons.append("telemetry is within normal operating range")

    return {
        "severity": severity,
        "anomalyFlag": anomaly_flag,
        "reasons": reasons,
    }


async def get_latest_sensor_telemetry(machine_id: str) -> Dict[str, Any]:
    telemetry = await _read_latest_from_existing_services(machine_id)

    return {
        "status": "ok",
        "machineId": machine_id,
        "deviceId": telemetry.get("deviceId", machine_id),
        "timestamp": telemetry.get("timestamp"),
        "source": telemetry.get("source", "sensor-service"),
        "telemetry": {
            "temperature": telemetry.get("temperature"),
            "vibration": telemetry.get("vibration"),
            "energyLoad": telemetry.get("energyLoad"),
            "status": telemetry.get("status"),
        },
    }


async def evaluate_sensor_anomaly(machine_id: str) -> Dict[str, Any]:
    telemetry = await _read_latest_from_existing_services(machine_id)
    evaluation = _evaluate_rules(telemetry)

    return {
        "status": "ok",
        "machineId": machine_id,
        "deviceId": telemetry.get("deviceId", machine_id),
        "severity": evaluation["severity"],
        "anomalyFlag": evaluation["anomalyFlag"],
        "reasons": evaluation["reasons"],
        "timestamp": telemetry.get("timestamp"),
        "telemetry": {
            "temperature": telemetry.get("temperature"),
            "vibration": telemetry.get("vibration"),
            "energyLoad": telemetry.get("energyLoad"),
            "status": telemetry.get("status"),
        },
        "handoffSuggestion": [
            "If severity is Critical, hand off to Digital Twin Agent for downstream impact.",
            "If severity is Critical, hand off to SOP Maintenance Agent for maintenance recommendation.",
            "If a work order is needed, hand off to Safety Work Order Agent.",
        ],
        "toolEvidence": {
            "source": telemetry.get("source", "sensor-service"),
            "ruleSet": "TwinOpsAI sensor severity rules v1",
        },
    }


async def get_sensor_history(machine_id: str, minutes: int) -> Dict[str, Any]:
    history = await _read_history_from_existing_services(machine_id, minutes)

    return {
        "status": "ok",
        "machineId": machine_id,
        "windowMinutes": minutes,
        "count": len(history),
        "history": history,
    }
