import json
import os
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def azure_ml_enabled() -> bool:
    return bool(
        os.getenv("AZURE_ML_SCORING_URI")
        and os.getenv("AZURE_ML_ENDPOINT_KEY")
    )


def _normalize_ml_response(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            payload = {}

    if isinstance(payload, list) and payload:
        payload = payload[0]

    if not isinstance(payload, dict):
        payload = {}

    contributing_factors = (
        payload.get("contributingFactors")
        or payload.get("contributing_factors")
        or payload.get("factors")
        or []
    )

    return {
        "isAnomaly": bool(payload.get("isAnomaly") or payload.get("is_anomaly", False)),
        "severity": payload.get("severity", "Low"),
        "contributingFactors": contributing_factors,
        "score": payload.get("score", payload.get("anomalyScore", 0.0)),
        "source": payload.get("source", "azure-ml-managed-online-endpoint"),
    }


def detect_with_azure_ml(telemetry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    scoring_uri = os.getenv("AZURE_ML_SCORING_URI")
    endpoint_key = os.getenv("AZURE_ML_ENDPOINT_KEY")
    deployment_name = os.getenv("AZURE_ML_DEPLOYMENT_NAME")

    if not scoring_uri or not endpoint_key:
        return None

    body = json.dumps({
        "telemetry": telemetry
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {endpoint_key}",
    }

    if deployment_name:
        headers["azureml-model-deployment"] = deployment_name

    request = Request(
        scoring_uri,
        data=body,
        headers=headers,
        method="POST",
    )

    try:
        with urlopen(request, timeout=15) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8")
        raise RuntimeError(f"Azure ML endpoint error {exc.code}: {error_body}") from exc
    except URLError as exc:
        raise RuntimeError(f"Azure ML endpoint unreachable: {exc.reason}") from exc

    payload = json.loads(raw) if raw else {}
    return _normalize_ml_response(payload)