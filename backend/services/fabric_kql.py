import os
from datetime import date, datetime
from typing import Any

try:
    from azure.identity import DefaultAzureCredential
    from azure.kusto.data import KustoClient, KustoConnectionStringBuilder
except ImportError:
    DefaultAzureCredential = None
    KustoClient = None
    KustoConnectionStringBuilder = None


FABRIC_KQL_CLUSTER_URI = os.getenv("FABRIC_KQL_CLUSTER_URI", "").strip().rstrip("/")
FABRIC_KQL_DATABASE = os.getenv("FABRIC_KQL_DATABASE", "twinopsai_kql_db").strip()
FABRIC_KQL_TABLE = os.getenv("FABRIC_KQL_TABLE", "telemetry_v2").strip()


def _jsonable(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _validate_table_name(table_name: str) -> str:
    safe = table_name.replace("_", "").isalnum()
    if not safe:
        raise ValueError(f"Invalid KQL table name: {table_name}")
    return table_name


def _get_kusto_client() -> KustoClient:
    if not FABRIC_KQL_CLUSTER_URI:
        raise RuntimeError("Missing FABRIC_KQL_CLUSTER_URI")

    if DefaultAzureCredential is None or KustoClient is None or KustoConnectionStringBuilder is None:
        raise RuntimeError("Azure Kusto SDK is not installed")

    credential = DefaultAzureCredential(exclude_interactive_browser_credential=False)

    kcsb = KustoConnectionStringBuilder.with_azure_token_credential(
        FABRIC_KQL_CLUSTER_URI,
        credential,
    )

    return KustoClient(kcsb)


def _rows_to_dicts(response) -> list[dict[str, Any]]:
    result_table = response.primary_results[0]
    columns = [column.column_name for column in result_table.columns]

    rows: list[dict[str, Any]] = []
    for row in result_table:
        item = {}
        for column in columns:
            item[column] = _jsonable(row[column])
        rows.append(item)

    return rows


def query_kql(kql: str) -> list[dict[str, Any]]:
    client = _get_kusto_client()
    response = client.execute(FABRIC_KQL_DATABASE, kql)
    return _rows_to_dicts(response)


def get_latest_telemetry(limit: int = 20, minutes: int = 30) -> list[dict[str, Any]]:
    table = _validate_table_name(FABRIC_KQL_TABLE)

    kql = f"""
{table}
| where ingestion_time() > ago({minutes}m)
| project timestamp, machineId, deviceId, vibration, temperature, energyLoad, status
| order by ingestion_time() desc
| take {limit}
"""

    return query_kql(kql)


def classify_anomaly(row: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []

    vibration = float(row.get("vibration") or 0)
    temperature = float(row.get("temperature") or 0)
    energy_load = float(row.get("energyLoad") or 0)
    status = str(row.get("status") or "").upper()

    if status == "WARN":
        reasons.append("status is WARN")
    if vibration > 3.5:
        reasons.append("vibration > 3.5")
    if temperature > 76:
        reasons.append("temperature > 76")
    if energy_load > 20:
        reasons.append("energyLoad > 20")

    severity = "CRITICAL" if reasons else "NORMAL"

    return {
        **row,
        "severity": severity,
        "isAnomaly": severity == "CRITICAL",
        "reasons": reasons,
    }


def get_latest_anomalies(limit: int = 20, minutes: int = 30) -> list[dict[str, Any]]:
    rows = get_latest_telemetry(limit=limit, minutes=minutes)
    return [classify_anomaly(row) for row in rows]
