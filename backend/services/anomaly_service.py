import os
from typing import Any, Dict, List

import requests


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def build_anomaly_batch_from_telemetry(telemetry: Dict[str, Any]) -> List[Dict[str, Any]]:
    motor_a = telemetry.get("motor_A", {})

    return [
        {
            "timestamp": telemetry.get("timestamp"),
            "machineId": "motor-A",
            "vibration": _to_float(motor_a.get("vibration")),
            "temperature": _to_float(motor_a.get("temperature")),
            "load": _to_float(motor_a.get("load")),
            "energyLoad": _to_float(motor_a.get("energyLoad", motor_a.get("load"))),
            "status": motor_a.get("status", "Normal"),
        }
    ]


def infer_contributing_factors_from_batch(batch: List[Dict[str, Any]]) -> List[str]:
    latest = batch[-1] if batch else {}

    vibration = _to_float(latest.get("vibration"))
    temperature = _to_float(latest.get("temperature"))
    load = _to_float(latest.get("energyLoad", latest.get("load")))
    status = str(latest.get("status", "")).lower()

    factors: List[str] = []

    if vibration >= 3.0:
        factors.append("vibration")

    if temperature >= 78:
        factors.append("temperature")

    if load >= 85:
        factors.append("energyLoad")

    if status in ["critical", "warning"] and not factors:
        factors.append("machineStatus")

    return factors


def detect_anomaly_local_fallback(batch: List[Dict[str, Any]]) -> Dict[str, Any]:
    latest = batch[-1] if batch else {}

    vibration = _to_float(latest.get("vibration"))
    temperature = _to_float(latest.get("temperature"))
    load = _to_float(latest.get("energyLoad", latest.get("load")))

    factors = infer_contributing_factors_from_batch(batch)
    is_anomaly = len(factors) > 0

    if vibration >= 3.5 or temperature >= 82 or load >= 90:
        severity = "High"
        score = 0.95
    elif is_anomaly:
        severity = "Medium"
        score = 0.7
    else:
        severity = "Low"
        score = 0.1

    return {
        "isAnomaly": is_anomaly,
        "severity": severity,
        "contributingFactors": factors,
        "score": score,
        "source": "local-fallback-detector",
    }


def detect_anomaly_from_telemetry(telemetry: Dict[str, Any]) -> Dict[str, Any]:
    batch = build_anomaly_batch_from_telemetry(telemetry)

    endpoint = os.getenv("AZURE_ML_ANOMALY_ENDPOINT") or os.getenv("AZURE_ML_SCORING_URI")
    key = os.getenv("AZURE_ML_ANOMALY_KEY") or os.getenv("AZURE_ML_ENDPOINT_KEY")
    deployment_name = os.getenv("AZURE_ML_DEPLOYMENT_NAME")

    if not endpoint or not key:
        return detect_anomaly_local_fallback(batch)

    try:
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

        if deployment_name:
            headers["azureml-model-deployment"] = deployment_name

        response = requests.post(
            endpoint,
            headers=headers,
            json={
                "series": batch,
                "data": batch,
                "telemetry": telemetry,
            },
            timeout=30,
        )

        response.raise_for_status()
        raw = response.json()

        if isinstance(raw, list) and raw:
            raw = raw[0]

        if isinstance(raw, dict) and isinstance(raw.get("result"), dict):
            raw = raw["result"]

        if not isinstance(raw, dict):
            raw = {}

        ml_factors = (
            raw.get("contributingFactors")
            or raw.get("contributing_factors")
            or raw.get("factors")
            or []
        )

        rule_factors = infer_contributing_factors_from_batch(batch)
        factors = ml_factors if len(ml_factors) > 0 else rule_factors

        is_anomaly = (
            bool(raw.get("isAnomaly", False))
            or bool(raw.get("is_anomaly", False))
            or len(factors) > 0
        )

        latest = batch[-1] if batch else {}
        vibration = _to_float(latest.get("vibration"))
        temperature = _to_float(latest.get("temperature"))
        load = _to_float(latest.get("energyLoad", latest.get("load")))

        severity = raw.get("severity")

        if not severity or severity in ["Normal", "Low"]:
            if is_anomaly:
                if vibration >= 3.5 or temperature >= 82 or load >= 90:
                    severity = "High"
                else:
                    severity = "Medium"
            else:
                severity = "Low"

        score = raw.get("score")
        if score is None:
            score = 0.95 if is_anomaly else 0.1

        return {
            "isAnomaly": is_anomaly,
            "severity": severity,
            "contributingFactors": factors,
            "score": score,
            "source": "azure-ml-managed-endpoint",
        }

    except Exception as e:
        fallback = detect_anomaly_local_fallback(batch)
        fallback["source"] = "local-fallback-after-azure-ml-error"
        fallback["azureMlError"] = str(e)
        return fallback
