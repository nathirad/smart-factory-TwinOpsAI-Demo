import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

try:
    from azure.cosmos import CosmosClient, PartitionKey
except ImportError:
    CosmosClient = None
    PartitionKey = None


DEFAULT_DATABASE = "twinopsai-anomaly-db"
ANOMALY_CONTAINER = os.getenv("COSMOS_ANOMALY_CONTAINER") or os.getenv("COSMOS_CONTAINER", "anomaly-results")
WORK_ORDERS_CONTAINER = os.getenv("COSMOS_WORK_ORDERS_CONTAINER", "work-orders")
AGENT_DECISIONS_CONTAINER = os.getenv("COSMOS_AGENT_DECISIONS_CONTAINER", "agent-decisions")
ENERGY_INSIGHTS_CONTAINER = os.getenv("COSMOS_ENERGY_INSIGHTS_CONTAINER", "energy-insights")

CONTAINER_PARTITION_KEYS = {
    ANOMALY_CONTAINER: "/machineId",
    WORK_ORDERS_CONTAINER: "/machineId",
    AGENT_DECISIONS_CONTAINER: "/sessionId",
    ENERGY_INSIGHTS_CONTAINER: "/deviceId",
}


def _get_database():
    endpoint = os.getenv("COSMOS_ENDPOINT")
    key = os.getenv("COSMOS_KEY")
    database_name = os.getenv("COSMOS_DB", DEFAULT_DATABASE)

    if not endpoint or not key:
        return None

    if CosmosClient is None or PartitionKey is None:
        return None

    client = CosmosClient(endpoint, credential=key)

    return client.create_database_if_not_exists(id=database_name)


def _get_container(container_name: str | None = None, partition_key_path: str | None = None):
    selected_container = container_name or ANOMALY_CONTAINER
    database = _get_database()

    if database is None or PartitionKey is None:
        return None

    partition_path = partition_key_path or CONTAINER_PARTITION_KEYS.get(selected_container, "/id")

    container = database.create_container_if_not_exists(
        id=selected_container,
        partition_key=PartitionKey(path=partition_path),
    )

    return container


def cosmos_enabled() -> bool:
    try:
        return _get_container(ANOMALY_CONTAINER, "/machineId") is not None
    except Exception as e:
        print(f"[cosmos] disabled/error: {e}")
        return False


def cosmos_state_status() -> Dict[str, Any]:
    database_name = os.getenv("COSMOS_DB", DEFAULT_DATABASE)
    containers = [
        {"name": ANOMALY_CONTAINER, "role": "anomaly-events", "partitionKey": "/machineId"},
        {"name": WORK_ORDERS_CONTAINER, "role": "work-orders", "partitionKey": "/machineId"},
        {"name": AGENT_DECISIONS_CONTAINER, "role": "agent-decisions", "partitionKey": "/sessionId"},
        {"name": ENERGY_INSIGHTS_CONTAINER, "role": "energy-insights", "partitionKey": "/deviceId"},
    ]

    return {
        "configured": bool(os.getenv("COSMOS_ENDPOINT") and os.getenv("COSMOS_KEY")),
        "sdkAvailable": CosmosClient is not None and PartitionKey is not None,
        "database": database_name,
        "containers": containers,
    }


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
        container = _get_container(ANOMALY_CONTAINER, "/machineId")

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
        container = _get_container(ANOMALY_CONTAINER, "/machineId")

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


def upsert_work_order(work_order: Dict[str, Any]) -> Dict[str, Any]:
    item = dict(work_order)
    item.setdefault("machineId", item.get("assetId", "motor-a"))
    item["updatedAt"] = datetime.now(timezone.utc).isoformat()
    item["cosmosSaved"] = False

    try:
        container = _get_container(WORK_ORDERS_CONTAINER, "/machineId")

        if container is None:
            item["cosmosError"] = "Cosmos work-orders container is not configured"
            return item

        container.upsert_item(item)
        item["cosmosSaved"] = True
        return item
    except Exception as e:
        item["cosmosError"] = str(e)
        print(f"[cosmos] upsert work order failed: {e}")
        return item


def get_work_order(work_order_id: str) -> Dict[str, Any] | None:
    try:
        container = _get_container(WORK_ORDERS_CONTAINER, "/machineId")
        if container is None:
            return None

        query = "SELECT * FROM c WHERE c.id = @id"
        items = list(
            container.query_items(
                query=query,
                parameters=[{"name": "@id", "value": work_order_id}],
                enable_cross_partition_query=True,
            )
        )
        return items[0] if items else None
    except Exception as e:
        print(f"[cosmos] get work order failed: {e}")
        return None


def list_work_orders(limit: int = 50) -> List[Dict[str, Any]]:
    try:
        container = _get_container(WORK_ORDERS_CONTAINER, "/machineId")
        if container is None:
            return []

        safe_limit = max(1, min(int(limit), 100))
        query = "SELECT * FROM c ORDER BY c.updatedAt DESC"
        items = list(container.query_items(query=query, enable_cross_partition_query=True))
        return items[:safe_limit]
    except Exception as e:
        print(f"[cosmos] list work orders failed: {e}")
        return []


def save_agent_decision(session_id: str, decision: Dict[str, Any]) -> Dict[str, Any]:
    item = {
        "id": decision.get("id") or str(uuid.uuid4()),
        "sessionId": session_id,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        **decision,
        "cosmosSaved": False,
    }

    try:
        container = _get_container(AGENT_DECISIONS_CONTAINER, "/sessionId")
        if container is None:
            item["cosmosError"] = "Cosmos agent-decisions container is not configured"
            return item

        container.upsert_item(item)
        item["cosmosSaved"] = True
        return item
    except Exception as e:
        item["cosmosError"] = str(e)
        print(f"[cosmos] save agent decision failed: {e}")
        return item


def list_agent_decisions(session_id: str | None = None, limit: int = 20) -> List[Dict[str, Any]]:
    try:
        container = _get_container(AGENT_DECISIONS_CONTAINER, "/sessionId")
        if container is None:
            return []

        safe_limit = max(1, min(int(limit), 100))
        if session_id:
            query = "SELECT * FROM c WHERE c.sessionId = @sessionId ORDER BY c.createdAt DESC"
            params = [{"name": "@sessionId", "value": session_id}]
            items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
        else:
            query = "SELECT * FROM c ORDER BY c.createdAt DESC"
            items = list(container.query_items(query=query, enable_cross_partition_query=True))
        return items[:safe_limit]
    except Exception as e:
        print(f"[cosmos] list agent decisions failed: {e}")
        return []


def save_energy_insight(device_id: str, insight: Dict[str, Any]) -> Dict[str, Any]:
    item = {
        "id": insight.get("id") or str(uuid.uuid4()),
        "deviceId": device_id,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        **insight,
        "cosmosSaved": False,
    }

    try:
        container = _get_container(ENERGY_INSIGHTS_CONTAINER, "/deviceId")
        if container is None:
            item["cosmosError"] = "Cosmos energy-insights container is not configured"
            return item

        container.upsert_item(item)
        item["cosmosSaved"] = True
        return item
    except Exception as e:
        item["cosmosError"] = str(e)
        print(f"[cosmos] save energy insight failed: {e}")
        return item


def list_energy_insights(device_id: str | None = None, limit: int = 20) -> List[Dict[str, Any]]:
    try:
        container = _get_container(ENERGY_INSIGHTS_CONTAINER, "/deviceId")
        if container is None:
            return []

        safe_limit = max(1, min(int(limit), 100))
        if device_id:
            query = "SELECT * FROM c WHERE c.deviceId = @deviceId ORDER BY c.createdAt DESC"
            params = [{"name": "@deviceId", "value": device_id}]
            items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
        else:
            query = "SELECT * FROM c ORDER BY c.createdAt DESC"
            items = list(container.query_items(query=query, enable_cross_partition_query=True))
        return items[:safe_limit]
    except Exception as e:
        print(f"[cosmos] list energy insights failed: {e}")
        return []
