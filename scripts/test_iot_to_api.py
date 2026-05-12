import json
import sys
import time
import urllib.request

API_URL = "http://localhost:8000/api/telemetry/live"

REQUIRED_FIELDS = {
    "deviceId",
    "timestamp",
    "vibration",
    "temperature",
    "energyLoad",
    "status",
}

deadline = time.time() + 60
last_response = None
last_error = None

while time.time() < deadline:
    try:
        with urllib.request.urlopen(API_URL, timeout=5) as response:
            result = json.loads(response.read().decode("utf-8"))

        last_response = result
        data = result.get("data")

        if result.get("status") == "ok" and isinstance(data, dict):
            missing = REQUIRED_FIELDS - set(data.keys())

            if not missing and data.get("deviceId") == "simDevice01":
                print("PASS: Backend API returned live IoT telemetry")
                print(json.dumps(result, indent=2))
                sys.exit(0)

    except Exception as error:
        last_error = str(error)

    time.sleep(3)

print("FAIL: Backend API did not return valid IoT telemetry within 60 seconds")

if last_error:
    print("Last error:", last_error)

if last_response:
    print("Last response:")
    print(json.dumps(last_response, indent=2))

sys.exit(1)
