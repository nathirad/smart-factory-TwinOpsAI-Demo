import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

try:
    from azure.cosmos import CosmosClient
except Exception:
    CosmosClient = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _severity_from_score(score: float) -> str:
    if score >= 0.85:
        return "High"
    if score >= 0.65:
        return "Medium"
    if score >= 0.45:
        return "Low"
    return "Normal"


def detect_anomaly_from_snapshot(telemetry: Dict[str, Any]) -> Dict[str, Any]:
    motor_a = telemetry.get("motor_A", {})

    vibration = float(motor_a.get("vibration", 0) or 0)
    temperature = float(motor_a.get("temperature", 0) or 0)
    load = float(motor_a.get("load", motor_a.get("energyLoad", 0)) or 0)
    status = str(motor_a.get("status", "Normal"))

    contributing_factors: List[Dict[str, Any]] = []

    vibration_score = min(vibration / 4.0, 1.0)
    temperature_score = min(max((temperature - 60) / 25, 0), 1.0)
    load_score = min(max((load - 60) / 40, 0), 1.0)

    if vibration >= 3.2:
        contributing_factors.append({
            "metric": "vibration",
            "value": vibration,
            "reason": "Vibration is above safe operating baseline",
            "score": round(vibration_score, 3),
        })

    if temperature >= 78:
        contributing_factors.append({
            "metric": "temperature",
            "value": temperature,
            "reason": "Temperature is elevated",
            "score": round(temperature_score, 3),
        })

    if load >= 85:
        contributing_factors.append({
            "metric": "load",
            "value": load,
            "reason": "Energy/load is operating at high level",
            "score": round(load_score, 3),
        })

    score = max(vibration_score, temperature_score, load_score)
    is_anomaly = bool(contributing_factors) or status.lower() in ["critical", "warning"]
    severity = _severity_from_score(score) if is_anomaly else "Normal"

    return {
        "id": str(uuid.uuid4()),
        "machineId": "motor-A",
        "source": "backend-rule-anomaly-detector",
        "timestamp": telemetry.get("timestamp") or _now_iso(),
        "createdAt": _now_iso(),
        "isAnomaly": is_anomaly,
        "severity": severity,
        "score": round(score, 3),
        "status": status,
        "telemetry": {
            "vibration": vibration,
            "temperature": temperature,
            "load": load,
        },
        "contributingFactors": contributing_factors,
        "agentEvent": {
            "shouldTrigger": is_anomaly,
            "eventType": "agent.orchestrator.anomaly.detected" if is_anomaly else None,
            "targetPhase": "Phase 5",
        },
    }


def _get_container():
    if CosmosClient is None:
        return None

    endpoint = os.getenv("COSMOS_ENDPOINT")
    key = os.getenv("COSMOS_KEY")
    database_name = os.getenv("COSMOS_DB", "twinopsai")
    container_name = os.getenv("COSMOS_CONTAINER", "anomalyEvents")

    if not endpoint or not key:
        return None

    client = CosmosClient(endpoint, credential=key)
    database = client.get_database_client(database_name)
    return database.get_container_client(container_name)


def save_anomaly_event(event: Dict[str, Any]) -> Dict[str, Any]:
    container = _get_container()

    if container is None:
        return {
            "stored": False,
            "reason": "Cosmos DB env is missing or azure-cosmos is not installed",
        }

    container.upsert_item(event)

    return {
        "stored": True,
        "database": os.getenv("COSMOS_DB", "twinopsai"),
        "container": os.getenv("COSMOS_CONTAINER", "anomalyEvents"),
    }


def list_anomaly_events(limit: int = 20) -> List[Dict[str, Any]]:
    container = _get_container()

    if container is None:
        return []

    query = "SELECT * FROM c ORDER BY c.createdAt DESC OFFSET 0 LIMIT @limit"

    items = container.query_items(
        query=query,
        parameters=[{"name": "@limit", "value": limit}],
        enable_cross_partition_query=True,
    )

    return list(items)