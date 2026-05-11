import os
from dotenv import load_dotenv
import random
import time
from datetime import datetime
import requests

load_dotenv()

BACKEND_API_ENDPOINT = os.getenv("BACKEND_API_ENDPOINT", "http://localhost:8000/api/ingest-telemetry")
SIMULATION_INTERVAL_SECONDS = float(os.getenv("SIMULATION_INTERVAL_SECONDS", "2"))

def generate_telemetry_data():
    
    is_anomaly = random.random() > 0.85
    
    if is_anomaly:
        vibration = round(random.uniform(3.0, 3.8), 2)
        temperature = round(random.uniform(75.0, 82.0), 1)
        load = round(random.uniform(88.0, 95.0), 1)
        status = "Critical"
    else:
        vibration = round(random.uniform(1.0, 1.4), 2)
        temperature = round(random.uniform(60.0, 63.0), 1)
        load = round(random.uniform(68.0, 73.0), 1)
        status = "Normal"
        
    payload = {
        "device_id": "motor-A",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data": {
            "vibration": vibration,
            "temperature": temperature,
            "load": load,
            "status": status
        }
    }
    
    return payload, is_anomaly

def start_simulation():
    print("Starting sensor data simulation...")
    print(f"Targeting Backend API Endpoint: {BACKEND_API_ENDPOINT} \n")
    
    try:
        while True:
            telemetry_data, is_anomaly = generate_telemetry_data()
            
            try:
                response = requests.post(BACKEND_API_ENDPOINT, json=telemetry_data)
                response.raise_for_status()
                time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if is_anomaly:
                    print(f"[{time_str}] Anomaly Detected! Sent data: {telemetry_data}")
                else:
                    print(f"[{time_str}] Sent data: {telemetry_data}")
            except requests.exceptions.RequestException as exc:
                print(f"Failed to send telemetry to {BACKEND_API_ENDPOINT}: {exc}")

            time.sleep(SIMULATION_INTERVAL_SECONDS)
                
    except KeyboardInterrupt:
        print("Simulation stopped by user.")
        
if __name__ == "__main__":
    start_simulation()
