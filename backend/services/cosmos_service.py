import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

try:
    from azure.cosmos import CosmosClient, PartitionKey
except ImportError:
    CosmosClient = None
    PartitionKey = None


def _get_container():
    endpoint = os.getenv("COSMOS_ENDPOINT")
    key = os.getenv("COSMOS_KEY")
    database_name = os.getenv("COSMOS_DB", "twinopsai-anomaly-db")
    container_name = os.getenv("COSMOS_CONTAINER", "anomaly-results")

    if not endpoint or not key:
        return None

    if CosmosClient is None or PartitionKey is None:
        return None

    client = CosmosClient(endpoint, credential=key)

    database = client.create_database_if_not_exists(id=database_name)

    container = database.create_container_if_not_exists(
        id=container_name,
        partition_key=PartitionKey(path="/machineId"),
    )

    return container


def cosmos_enabled() -> bool:
    try:
        return _get_container() is not None
    except Exception as e:
        print(f"[cosmos] disabled/error: {e}")
        return False


def save_anomaly_result(
    machine_id: str,
    telemetry: Dict[str, Any],
    is_anomaly: bool,
    severity: str,
    contributing_factors: List[Any],
    source: str,
    agent_triggered: bool,
) -> Dict[str, Any]:
    item = {
        "id": str(uuid.uuid4()),
        "machineId": machine_id,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "telemetry": telemetry,
        "isAnomaly": bool(is_anomaly),
        "severity": severity,
        "contributingFactors": contributing_factors or [],
        "source": source,
        "agentTriggered": bool(agent_triggered),
        "cosmosSaved": False,
    }

    try:
        container = _get_container()

        if container is None:
            item["cosmosError"] = "Cosmos is not configured or azure-cosmos is not installed"
            return item

        item["cosmosSaved"] = True
        container.upsert_item(item)
        return item

    except Exception as e:
        item["cosmosSaved"] = False
        item["cosmosError"] = str(e)
        print(f"[cosmos] save failed: {e}")
        return item


def list_anomaly_results(machine_id: str | None = None, limit: int = 20):
    try:
        container = _get_container()

        if container is None:
            return []

        safe_limit = max(1, min(int(limit), 100))

        if machine_id:
            query = """
            SELECT * FROM c
            WHERE c.machineId = @machineId
            ORDER BY c.createdAt DESC
            """
            parameters = [
                {"name": "@machineId", "value": machine_id}
            ]

            items = list(
                container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True,
                )
            )
        else:
            query = """
            SELECT * FROM c
            ORDER BY c.createdAt DESC
            """

            items = list(
                container.query_items(
                    query=query,
                    enable_cross_partition_query=True,
                )
            )

        return items[:safe_limit]

    except Exception as e:
        print(f"[cosmos] list anomaly results failed: {e}")
        return []