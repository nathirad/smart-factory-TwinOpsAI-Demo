import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from azure.cosmos import CosmosClient, PartitionKey
except Exception:
    CosmosClient = None
    PartitionKey = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_container():
    if CosmosClient is None or PartitionKey is None:
        return None

    endpoint = os.getenv("COSMOS_ENDPOINT")
    key = os.getenv("COSMOS_KEY")

    database_name = os.getenv("COSMOS_DB", "twinopsai-anomaly-db")
    container_name = os.getenv("COSMOS_CONTAINER", "anomaly-results")

    if not endpoint or not key:
        return None

    client = CosmosClient(endpoint, credential=key)

    database = client.create_database_if_not_exists(id=database_name)

    container = database.create_container_if_not_exists(
        id=container_name,
        partition_key=PartitionKey(path="/machineId"),
    )

    return container


def cosmos_enabled() -> bool:
    return _get_container() is not None


def save_anomaly_result(
    machine_id: str,
    telemetry: Dict[str, Any],
    is_anomaly: bool,
    severity: str,
    contributing_factors: List[Any],
    source: str = "phase-4-mvp-anomaly-detector",
    agent_triggered: bool = False,
) -> Dict[str, Any]:
    item = {
        "id": str(uuid.uuid4()),
        "machineId": machine_id,
        "timestamp": telemetry.get("timestamp") or _now_iso(),
        "createdAt": _now_iso(),
        "isAnomaly": is_anomaly,
        "severity": severity,
        "contributingFactors": contributing_factors,
        "telemetry": telemetry,
        "source": source,
        "agentTrigger": {
            "enabled": agent_triggered,
            "target": "phase-5-agent-orchestrator",
            "reason": "anomaly detected" if agent_triggered else "normal telemetry",
        },
    }

    container = _get_container()

    if container is None:
        item["stored"] = False
        item["storeReason"] = "Cosmos DB env is missing or azure-cosmos is not installed"
        return item

    container.upsert_item(item)
    item["stored"] = True
    return item


def list_anomaly_results(
    machine_id: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    container = _get_container()

    if container is None:
        return []

    if machine_id:
        query = """
        SELECT * FROM c
        WHERE c.machineId = @machineId
        ORDER BY c.createdAt DESC
        OFFSET 0 LIMIT @limit
        """
        parameters = [
            {"name": "@machineId", "value": machine_id},
            {"name": "@limit", "value": limit},
        ]
    else:
        query = """
        SELECT * FROM c
        ORDER BY c.createdAt DESC
        OFFSET 0 LIMIT @limit
        """
        parameters = [
            {"name": "@limit", "value": limit},
        ]

    items = container.query_items(
        query=query,
        parameters=parameters,
        enable_cross_partition_query=True,
    )

    return list(items)