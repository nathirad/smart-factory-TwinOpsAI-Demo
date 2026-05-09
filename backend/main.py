import glob
import json
import os
import random
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient
except ImportError:
    AzureKeyCredential = None
    SearchClient = None


load_dotenv()

APP_MODE = os.getenv("APP_MODE", "mock").lower()
print(f"Starting SmartFactory TwinOps API in {APP_MODE.upper()} mode")

app = FastAPI(title="SmartFactory TwinOps API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


openai_key = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=openai_key) if openai_key and OpenAI else None

search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
search_key = os.getenv("AZURE_SEARCH_KEY")
search_index = os.getenv("AZURE_SEARCH_INDEX")

search_client = None
if search_endpoint and search_key and search_index and SearchClient and AzureKeyCredential:
    try:
        search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=search_index,
            credential=AzureKeyCredential(search_key),
        )
    except Exception as exc:
        print(f"Failed to initialize Azure Search Client: {exc}")


def load_sop_knowledge_base():
    sop_content = ""
    folder_path = os.path.join(os.path.dirname(__file__), "mock-data", "SOP-Mocking")
    file_pattern = os.path.join(folder_path, "*.txt")
    files = glob.glob(file_pattern)

    if not files:
        return """
            [SOP-MA-102] Bearing Inspection
            - Criteria: vibration > 3.0 mm/s or temperature > 75 C
            - Actions: reduce load by 15% immediately and inspect bearing.
        """

    for file_path in files:
        with open(file_path, "r", encoding="utf-8") as file:
            sop_content += f"\n[{os.path.basename(file_path)}]\n{file.read()}\n"

    return sop_content


MOCK_KNOWLEDGE_BASE = load_sop_knowledge_base()


class TelemetryMetrics(BaseModel):
    vibration: float
    temperature: float
    load: float
    status: str


class IngestPayload(BaseModel):
    device_id: str
    timestamp: str
    data: TelemetryMetrics


app_state = {
    "is_anomaly_active": False,
    "anomaly_start_time": 0,
    "latest_ingested_data": None,
}


def now_string():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normal_motor_b():
    return {
        "vibration": round(random.uniform(1.1, 1.5), 2),
        "temperature": round(random.uniform(59.0, 62.0), 1),
        "load": round(random.uniform(65.0, 70.0), 1),
        "status": "Normal",
    }


def normal_conveyor_c():
    return {
        "vibration": round(random.uniform(0.9, 1.2), 2),
        "temperature": round(random.uniform(54.0, 56.0), 1),
        "load": round(random.uniform(60.0, 65.0), 1),
        "status": "Normal",
    }


def normal_motor_a():
    return {
        "vibration": round(random.uniform(1.0, 1.4), 2),
        "temperature": round(random.uniform(60.0, 63.0), 1),
        "load": round(random.uniform(68.0, 73.0), 1),
        "status": "Normal",
    }


def critical_motor_a():
    return {
        "vibration": round(random.uniform(3.0, 3.8), 2),
        "temperature": round(random.uniform(75.0, 82.0), 1),
        "load": round(random.uniform(88.0, 95.0), 1),
        "status": "Critical",
    }


@app.post("/api/ingest-telemetry")
async def ingest_telemetry(payload: IngestPayload):
    app_state["latest_ingested_data"] = payload.data.model_dump()

    if payload.data.status == "Critical":
        app_state["is_anomaly_active"] = True
        app_state["anomaly_start_time"] = payload.timestamp

    return {
        "status": "received",
        "server_received_time": now_string(),
    }


@app.get("/api/telemetry")
async def get_telemetry():
    motor_a_data = app_state["latest_ingested_data"] or normal_motor_a()

    if app_state["is_anomaly_active"]:
        motor_a_data = critical_motor_a()

    return {
        "timestamp": now_string(),
        "motor_A": motor_a_data,
        "motor_B": normal_motor_b(),
        "conveyor_C": normal_conveyor_c(),
    }


@app.post("/api/trigger-anomaly")
async def trigger_anomaly():
    app_state["is_anomaly_active"] = True
    app_state["anomaly_start_time"] = now_string()

    return {
        "Message": "Anomaly simulation triggered. Dashboard will spike.",
    }


@app.post("/api/reset-anomaly")
async def reset_anomaly():
    app_state["is_anomaly_active"] = False
    app_state["anomaly_start_time"] = 0
    app_state["latest_ingested_data"] = None

    return {
        "Message": "Anomaly simulation reset to normal state.",
    }


@app.get("/api/digital-twin")
async def get_digital_twin():
    if app_state["is_anomaly_active"]:
        return {
            "line_status": "Critical",
            "failure_risk": "High",
            "affected_asset": "Motor A",
            "potential_impact": "Degradation at Motor A may reduce throughput capacity of Line 1 by 18-25% if unaddressed.",
            "downstream_impact": {
                "Motor_B": "Normal",
                "Conveyor_C": "At Risk (Reduced Input)",
            },
        }

    return {
        "line_status": "Stable",
        "failure_risk": "Low",
        "affected_asset": "None",
        "potential_impact": "Normal production",
        "downstream_impact": {
            "Motor_B": "Normal",
            "Conveyor_C": "Normal",
        },
    }


@app.get("/api/analyze")
async def get_ai_recommendations():
    if not app_state["is_anomaly_active"]:
        return {
            "insight": "No active anomaly",
            "confidence_score": "12%",
            "risk_level": "Low",
            "recommended_actions": [],
        }

    current_data = app_state.get("latest_ingested_data") or {
        "vibration": 3.6,
        "temperature": 80.0,
        "load": 70.0,
        "status": "Critical",
    }

    retrieved_context = MOCK_KNOWLEDGE_BASE

    if APP_MODE == "production" and search_client:
        try:
            search_query = f"High vibration {current_data.get('vibration')} and temperature {current_data.get('temperature')}"
            results = search_client.search(search_text=search_query, top=2)
            search_context = ""

            for result in results:
                search_context += f"\n[Document ID: {result.get('id', 'Unknown')}]\n{result.get('content', '')}\n"

            if search_context.strip():
                retrieved_context = search_context
        except Exception as exc:
            print(f"Azure Search failed: {exc}. Falling back to local files.")

    fallback_response = {
        "insight": "Anomaly detected at Motor A (System Fallback)",
        "confidence_score": "88%",
        "risk_level": "High",
        "retrieved_sop": {
            "document_id": "SOP-MA-102: Bearing Inspection & Replacement",
            "match_score": "92%",
            "excerpts": ["Check bearings immediately."],
        },
        "recommended_actions": [
            {"id": 1, "action": "Inspect within 24 hours", "impact": "High Impact"},
            {"id": 2, "action": "Reduce operating load by 15%", "impact": "Medium Impact"},
        ],
    }

    if APP_MODE == "mock" or not openai_client:
        return fallback_response

    system_prompt = f"""
        You are 'TwinOps AI', an expert maintenance assistant for a Smart Factory.
        Analyze the incoming sensor data and provide recommendations strictly based on the provided SOP database.

        [SOP DATABASE]
        {retrieved_context}

        [INSTRUCTIONS]
        1. Compare the sensor data against the SOP thresholds.
        2. Determine the risk level (High, Medium, Low).
        3. Extract the relevant SOP document ID and exact matched excerpts.
        4. Formulate actionable recommended actions based only on the SOP.

        [OUTPUT FORMAT]
        Return only a valid JSON object matching exactly this structure:
        {{
            "insight": "Short string explaining the diagnosis",
            "confidence_score": "Percentage string e.g. 92%",
            "risk_level": "High or Medium or Low",
            "retrieved_sop": {{
                "document_id": "Matched SOP ID",
                "match_score": "Percentage string",
                "excerpts": ["string list of matching SOP rules"]
            }},
            "recommended_actions": [
                {{"id": 1, "action": "string", "impact": "High Impact or Medium Impact"}}
            ]
        }}
    """

    user_prompt = (
        f"Motor A Sensor Data: Vibration = {current_data.get('vibration')} mm/s, "
        f"Temperature = {current_data.get('temperature')} C."
    )

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
        )

        return json.loads(response.choices[0].message.content)
    except Exception as exc:
        print(f"OpenAI generation failed: {exc}. Returning fallback response.")
        return fallback_response
