import os
from typing import Any

try:
    from azure.identity import DefaultAzureCredential
    from azure.digitaltwins.core import DigitalTwinsClient
except ImportError:
    DefaultAzureCredential = None
    DigitalTwinsClient = None


TWIN_ID_MAP = {
    "motor-a": "motor-A",
    "motor-b": "motor-B",
    "conveyor-c": "conveyor-C",
    "factory": "factory-001",
    "line": "line-001",
}

MOCK_TWINS = {
    "motor-A": {
        "id": "motor-A",
        "model": "dtmi:smartfactory:Machine;1",
        "name": "Motor A",
        "machineType": "Motor",
        "location": "Packaging Line 1",
        "status": "Critical",
        "healthScore": 62,
        "vibration": 3.4,
        "temperature": 78.2,
        "energyLoad": 91.0,
    },
    "motor-B": {
        "id": "motor-B",
        "model": "dtmi:smartfactory:Machine;1",
        "name": "Motor B",
        "machineType": "Motor",
        "location": "Packaging Line 1",
        "status": "Normal",
        "healthScore": 95,
        "vibration": 1.2,
        "temperature": 61.0,
        "energyLoad": 68.0,
    },
    "conveyor-C": {
        "id": "conveyor-C",
        "model": "dtmi:smartfactory:Machine;1",
        "name": "Conveyor C",
        "machineType": "Conveyor",
        "location": "Packaging Line 1",
        "status": "At Risk",
        "healthScore": 84,
        "vibration": 1.0,
        "temperature": 55.0,
        "energyLoad": 63.0,
    },
}

_client: Any | None = None


def normalize_twin_id(twin_id: str) -> str:
    return TWIN_ID_MAP.get(twin_id, twin_id)


def get_client() -> Any:
    global _client

    if _client is not None:
        return _client

    if DefaultAzureCredential is None or DigitalTwinsClient is None:
        raise RuntimeError("Azure Digital Twins SDK is not installed")

    adt_url = os.getenv("ADT_URL") or os.getenv("ADT_ENDPOINT")

    if not adt_url:
        raise RuntimeError("Missing ADT_URL environment variable")

    credential = DefaultAzureCredential()
    _client = DigitalTwinsClient(adt_url, credential)
    return _client


def clean_twin(twin: dict[str, Any]) -> dict[str, Any]:
    metadata = twin.get("$metadata", {})

    return {
        "id": twin.get("$dtId"),
        "model": metadata.get("$model"),
        "name": twin.get("name"),
        "machineType": twin.get("machineType"),
        "location": twin.get("location"),
        "status": twin.get("status"),
        "healthScore": twin.get("healthScore"),
        "vibration": twin.get("vibration"),
        "temperature": twin.get("temperature"),
        "energyLoad": twin.get("energyLoad"),
    }


def get_twin_dependencies(twin_id: str) -> dict[str, Any]:
    client = get_client()
    root_id = normalize_twin_id(twin_id)

    root_twin = client.get_digital_twin(root_id)

    visited = {root_id}
    frontier = [root_id]
    graph_edges = []
    dependencies = []

    for depth in range(3):
        next_frontier = []

        for source_id in frontier:
            relationships = list(client.list_relationships(source_id))

            for rel in relationships:
                rel_name = rel.get("$relationshipName")
                target_id = rel.get("$targetId")

                if not target_id:
                    continue

                target_twin = client.get_digital_twin(target_id)
                clean_target = clean_twin(target_twin)

                edge = {
                    "sourceId": source_id,
                    "relationshipId": rel.get("$relationshipId"),
                    "relationshipName": rel_name,
                    "targetId": target_id,
                    "depth": depth + 1,
                }

                graph_edges.append(edge)
                dependencies.append(clean_target)

                if target_id not in visited:
                    visited.add(target_id)
                    next_frontier.append(target_id)

        frontier = next_frontier

        if not frontier:
            break

    return {
        "source": "azure-digital-twins",
        "twinId": root_id,
        "root": clean_twin(root_twin),
        "dependencies": dependencies,
        "graph": graph_edges,
    }


def get_mock_twin_dependencies(twin_id: str) -> dict[str, Any]:
    root_id = normalize_twin_id(twin_id)
    dependencies = [MOCK_TWINS["motor-B"], MOCK_TWINS["conveyor-C"]] if root_id == "motor-A" else []
    graph = [
        {
            "sourceId": root_id,
            "relationshipId": f"{root_id}-feeds-motor-B",
            "relationshipName": "feedsTo",
            "targetId": "motor-B",
            "depth": 1,
        },
        {
            "sourceId": root_id,
            "relationshipId": f"{root_id}-feeds-conveyor-C",
            "relationshipName": "feedsTo",
            "targetId": "conveyor-C",
            "depth": 1,
        },
    ] if root_id == "motor-A" else []

    return {
        "source": "mock-digital-twins",
        "twinId": root_id,
        "root": MOCK_TWINS.get(root_id, {"id": root_id, "name": root_id, "status": "Unknown"}),
        "dependencies": dependencies,
        "graph": graph,
    }
