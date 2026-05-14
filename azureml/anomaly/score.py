import json


def init():
    pass


def run(raw_data):
    data = json.loads(raw_data)

    telemetry = data.get("telemetry", {})
    motor_a = telemetry.get("motor_A", telemetry)

    vibration = float(motor_a.get("vibration", 0))
    temperature = float(motor_a.get("temperature", 0))
    load = float(motor_a.get("load", motor_a.get("energyLoad", 0)))

    contributing_factors = []

    if vibration >= 3.0:
        contributing_factors.append({
            "metric": "vibration",
            "value": vibration,
            "reason": "Vibration is above baseline threshold"
        })

    if temperature >= 78:
        contributing_factors.append({
            "metric": "temperature",
            "value": temperature,
            "reason": "Temperature is above safe operating range"
        })

    if load >= 85:
        contributing_factors.append({
            "metric": "energyLoad",
            "value": load,
            "reason": "Energy load is elevated"
        })

    is_anomaly = len(contributing_factors) > 0

    if vibration >= 3.5 or temperature >= 82 or load >= 90:
        severity = "High"
    elif is_anomaly:
        severity = "Medium"
    else:
        severity = "Low"

    return {
        "isAnomaly": is_anomaly,
        "severity": severity,
        "contributingFactors": contributing_factors,
        "model": "azure-ml-mvp-threshold-anomaly-model",
        "source": "azure-ml-managed-online-endpoint"
    }
