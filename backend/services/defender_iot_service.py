import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient, LogsQueryStatus


SEVERITY_SCORE = {
    "Informational": 10,
    "Info": 10,
    "Low": 25,
    "Minor": 35,
    "Medium": 55,
    "Warning": 55,
    "Major": 75,
    "High": 85,
    "Critical": 95,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _score_to_risk(score: int) -> str:
    if score >= 80:
        return "HIGH"
    if score >= 50:
        return "MEDIUM"
    return "LOW"


def _get_alert_score(alerts: list[dict[str, Any]]) -> int:
    if not alerts:
        return 0

    scores = []
    for alert in alerts:
        severity = str(alert.get("severity", "Low"))
        scores.append(SEVERITY_SCORE.get(severity, 25))

    return max(scores)


def _build_safety_signal(security_risk: str, alerts: list[dict[str, Any]]) -> dict[str, Any]:
    if security_risk == "HIGH":
        return {
            "security_blocker": True,
            "approval_required": True,
            "dispatch_allowed": False,
            "reason": "High OT security risk detected. Supervisor approval is required before critical dispatch.",
            "evidence": [
                f"{alert.get('severity', 'Unknown')}: {alert.get('title', 'Unknown alert')}"
                for alert in alerts
            ],
        }

    if security_risk == "MEDIUM":
        return {
            "security_blocker": False,
            "approval_required": True,
            "dispatch_allowed": False,
            "reason": "Medium OT security risk detected. Review is recommended before dispatch.",
            "evidence": [
                f"{alert.get('severity', 'Unknown')}: {alert.get('title', 'Unknown alert')}"
                for alert in alerts
            ],
        }

    return {
        "security_blocker": False,
        "approval_required": False,
        "dispatch_allowed": True,
        "reason": "No high OT security risk detected.",
        "evidence": [],
    }


def _build_response(
    source: str,
    asset_id: str,
    alerts: list[dict[str, Any]],
    mode: str,
) -> dict[str, Any]:
    risk_score = _get_alert_score(alerts)
    security_risk = _score_to_risk(risk_score)
    safety_signal = _build_safety_signal(security_risk, alerts)

    return {
        "status": "ok",
        "mode": mode,
        "source": source,
        "asset_id": asset_id,
        "security_risk": security_risk,
        "risk_score": risk_score,
        "alerts": alerts,
        "safety_signal": safety_signal,
        "generated_at": _now_iso(),
    }


def get_mock_defender_alerts(asset_id: str = "motor-A") -> dict[str, Any]:
    alerts = [
        {
            "id": "DFIOT-MOCK-001",
            "severity": "High",
            "title": "Suspicious OT communication pattern",
            "description": (
                "Unexpected communication from an engineering workstation "
                "to the motor controller during an anomaly window."
            ),
            "engine": "Anomaly",
            "asset_id": asset_id,
            "source": "Microsoft Defender for IoT",
            "status": "simulated",
            "recommended_action": (
                "Verify maintenance activity and require supervisor approval "
                "before remote or critical dispatch."
            ),
            "created_at": _now_iso(),
        }
    ]

    return _build_response(
        source="mock-defender-iot",
        asset_id=asset_id,
        alerts=alerts,
        mode="mock",
    )


async def get_sensor_defender_alerts(
    asset_id: str = "motor-A",
    hours: int = 24,
) -> dict[str, Any]:
    sensor_url = os.getenv("DEFENDER_SENSOR_URL", "").rstrip("/")
    token = os.getenv("DEFENDER_SENSOR_TOKEN", "")
    verify_ssl = os.getenv("DEFENDER_SENSOR_VERIFY_SSL", "false").lower() == "true"

    if not sensor_url or not token:
        raise RuntimeError(
            "DEFENDER_SENSOR_URL or DEFENDER_SENSOR_TOKEN is missing. "
            "Set DEFENDER_MODE=mock if you do not have a real sensor yet."
        )

    from_time_ms = int(
        (datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp() * 1000
    )

    url = f"{sensor_url}/api/v1/alerts"
    params = {
        "state": "unhandled",
        "fromTime": from_time_ms,
    }

    headers = {
        "Authorization": token,
    }

    async with httpx.AsyncClient(verify=verify_ssl, timeout=20) as client:
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        raw_alerts = response.json()

    normalized_alerts = []

    for raw in raw_alerts:
        title = raw.get("title", "Defender for IoT alert")
        message = raw.get("message", "")
        severity = raw.get("severity", "Low")
        engine = raw.get("engine", "Unknown")

        alert_text = f"{title} {message} {raw}".lower()

        # Simple asset filter for demo. In production, map Defender device IDs/IPs to ADT asset IDs.
        if asset_id.lower() not in alert_text and asset_id.lower() != "motor-a":
            continue

        timestamp_ms = raw.get("time")
        created_at = _now_iso()

        if timestamp_ms:
            created_at = datetime.fromtimestamp(
                int(timestamp_ms) / 1000,
                tz=timezone.utc,
            ).isoformat()

        normalized_alerts.append(
            {
                "id": f"DFIOT-{raw.get('id', 'unknown')}",
                "severity": severity,
                "title": title,
                "description": message,
                "engine": engine,
                "asset_id": asset_id,
                "source": "Microsoft Defender for IoT OT sensor",
                "status": "real_sensor",
                "created_at": created_at,
                "raw": raw,
            }
        )

    return _build_response(
        source="defender-iot-sensor",
        asset_id=asset_id,
        alerts=normalized_alerts,
        mode="sensor",
    )


def get_sentinel_defender_alerts(
    asset_id: str = "motor-A",
    hours: int = 24,
) -> dict[str, Any]:
    workspace_id = os.getenv("LOG_ANALYTICS_WORKSPACE_ID", "")

    if not workspace_id:
        raise RuntimeError(
            "LOG_ANALYTICS_WORKSPACE_ID is missing. "
            "Set DEFENDER_MODE=mock if Sentinel is not connected yet."
        )

    safe_asset = asset_id.replace("'", "''")

    query = f"""
    SecurityAlert
    | where TimeGenerated > ago({hours}h)
    | where ProviderName == "IoTSecurity"
        or ProductName has "Defender for IoT"
        or ProviderName has "Microsoft Defender for IoT"
    | where tostring(CompromisedEntity) contains "{safe_asset}"
        or tostring(Entities) contains "{safe_asset}"
        or AlertName contains "{safe_asset}"
        or Description contains "{safe_asset}"
        or "{safe_asset}" == "motor-A"
    | project
        TimeGenerated,
        AlertName,
        AlertSeverity,
        Description,
        ProviderName,
        ProductName,
        CompromisedEntity,
        Entities
    | order by TimeGenerated desc
    | take 20
    """

    credential = DefaultAzureCredential()
    client = LogsQueryClient(credential)

    result = client.query_workspace(
        workspace_id=workspace_id,
        query=query,
        timespan=timedelta(hours=hours),
    )

    alerts: list[dict[str, Any]] = []

    if result.status == LogsQueryStatus.SUCCESS:
        table = result.tables[0]
        columns = [col.name for col in table.columns]

        for row in table.rows:
            item = dict(zip(columns, row))

            alerts.append(
                {
                    "id": f"SENTINEL-{len(alerts) + 1}",
                    "severity": item.get("AlertSeverity", "Low"),
                    "title": item.get("AlertName", "Defender for IoT alert"),
                    "description": item.get("Description", ""),
                    "asset_id": asset_id,
                    "source": "Microsoft Sentinel / Defender for IoT",
                    "status": "sentinel",
                    "provider": item.get("ProviderName", ""),
                    "product": item.get("ProductName", ""),
                    "created_at": str(item.get("TimeGenerated", _now_iso())),
                    "raw": item,
                }
            )

    return _build_response(
        source="microsoft-sentinel",
        asset_id=asset_id,
        alerts=alerts,
        mode="sentinel",
    )


async def get_defender_security_risk(
    asset_id: str = "motor-A",
    hours: int = 24,
) -> dict[str, Any]:
    mode = os.getenv("DEFENDER_MODE", "mock").lower()

    if mode == "sensor":
        return await get_sensor_defender_alerts(asset_id=asset_id, hours=hours)

    if mode == "sentinel":
        return get_sentinel_defender_alerts(asset_id=asset_id, hours=hours)

    return get_mock_defender_alerts(asset_id=asset_id)


def get_security_status() -> dict[str, Any]:
    mode = os.getenv("DEFENDER_MODE", "mock").lower()

    return {
        "status": "ok",
        "defender_mode": mode,
        "defender_for_iot": "enabled_in_code" if mode != "mock" else "simulated",
        "sentinel": "configured" if os.getenv("LOG_ANALYTICS_WORKSPACE_ID") else "not_configured",
        "sensor_url_configured": bool(os.getenv("DEFENDER_SENSOR_URL")),
        "sensor_token_configured": bool(os.getenv("DEFENDER_SENSOR_TOKEN")),
        "key_vault_configured": bool(os.getenv("KEY_VAULT_URL")),
        "generated_at": _now_iso(),
    }