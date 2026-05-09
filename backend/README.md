# Backend API README

This backend is a FastAPI prototype for the SmartFactory TwinOps AI demo. It exposes API routes for telemetry ingestion, anomaly simulation, digital twin impact, and AI/SOP-based recommendations.

The frontend does not need to know whether the backend is running in mock or production mode. It should call the same API routes in both modes. The backend chooses the data source by reading `APP_MODE` from `.env`.

## Run Backend

From the `backend` directory:

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Base URL for local frontend integration:

```text
http://localhost:8000
```

## Swagger / OpenAPI Docs

FastAPI automatically generates Swagger and OpenAPI documentation from the API routes in `main.py`.

After starting the backend, open:

```text
http://localhost:8000/docs
```

Use this page to:

- See all available backend API routes
- Inspect request and response schemas
- Test API calls directly from the browser
- Share the current API contract with the frontend team

The raw OpenAPI JSON is available at:

```text
http://localhost:8000/openapi.json
```

There is no separate committed Swagger file yet. The Swagger UI and OpenAPI schema are generated live by FastAPI when the backend server is running.

## Run Backend With Docker

From the project root:

```bash
docker compose up --build backend
```

The backend container exposes the same local base URL:

```text
http://localhost:8000
```

Docker uses:

- [Dockerfile](./Dockerfile)
- [requirements.txt](./requirements.txt)
- root [docker-compose.yml](../docker-compose.yml)
- root `.env`

The Docker setup only runs the FastAPI backend. The frontend can still run separately with `npm run dev`.

## Environment

The backend reads configuration from the project `.env` file.

```env
APP_MODE=mock
BACKEND_API_ENDPOINT=http://localhost:8000/api/ingest-telemetry
SIMULATION_INTERVAL_SECONDS=2
OPENAI_API_KEY=sk-xxxx...
AZURE_SEARCH_ENDPOINT=https://your-search-service.search.windows.net
AZURE_SEARCH_KEY=your-admin-key
AZURE_SEARCH_INDEX=sop-index
```

### `APP_MODE=mock`

Use local mocked telemetry, local SOP text files, and deterministic fallback recommendation data. This mode does not require OpenAI or Azure services.

### `APP_MODE=production`

The `/api/analyze` route attempts to use Azure AI Search for SOP retrieval and OpenAI for recommendation generation. If Azure Search or OpenAI fails, the backend falls back to mock SOP/recommendation data.

Current production support is partial. Real IoT Hub, Azure Digital Twins, Microsoft Fabric, Foundry Agent Service, and CMMS/work-order integrations are not implemented yet.

## Current API Routes

### `POST /api/ingest-telemetry`

Receives telemetry for one device and stores the latest payload in backend memory.

If `data.status` is `"Critical"`, the backend activates the anomaly scenario.

Request:

```json
{
  "device_id": "motor-A",
  "timestamp": "2026-05-09 10:24:30",
  "data": {
    "vibration": 3.4,
    "temperature": 78.2,
    "load": 91.0,
    "status": "Critical"
  }
}
```

Response:

```json
{
  "status": "received",
  "server_received_time": "2026-05-09 10:24:31"
}
```

Frontend use:

- Optional for live/mock sensor simulation.
- The existing simulator posts Motor A telemetry to this route.

### `GET /api/telemetry`

Returns latest telemetry for the three demo assets:

- Motor A
- Motor B
- Conveyor C

When anomaly is inactive, Motor A uses the latest ingested data if available, otherwise random normal values.

When anomaly is active, Motor A returns critical values.

Response:

```json
{
  "timestamp": "2026-05-09 10:24:31",
  "motor_A": {
    "vibration": 3.6,
    "temperature": 80.0,
    "load": 92.0,
    "status": "Critical"
  },
  "motor_B": {
    "vibration": 1.3,
    "temperature": 60.5,
    "load": 68.0,
    "status": "Normal"
  },
  "conveyor_C": {
    "vibration": 1.0,
    "temperature": 55.2,
    "load": 62.0,
    "status": "Normal"
  }
}
```

Frontend use:

- Dashboard latest telemetry
- Asset health cards
- Telemetry charts
- Anomaly state display

### `POST /api/trigger-anomaly`

Manually starts the Motor A anomaly scenario.

Response:

```json
{
  "Message": "Anomaly simulation triggered. Dashboard will spike."
}
```

Frontend use:

- Simulate Anomaly button
- After this route succeeds, frontend can navigate to the Agents page if desired.

### `POST /api/reset-anomaly`

Resets the demo to stable monitoring state.

This clears:

- `is_anomaly_active`
- latest ingested telemetry

Response:

```json
{
  "Message": "Anomaly simulation reset to normal state."
}
```

Frontend use:

- Reset button
- Return dashboard, telemetry, recommendations, and work-order UI to stable state.

### `GET /api/digital-twin`

Returns current digital twin impact summary.

Stable response:

```json
{
  "line_status": "Stable",
  "failure_risk": "Low",
  "affected_asset": "None",
  "potential_impact": "Normal production",
  "downstream_impact": {
    "Motor_B": "Normal",
    "Conveyor_C": "Normal"
  }
}
```

Anomaly response:

```json
{
  "line_status": "Critical",
  "failure_risk": "High",
  "affected_asset": "Motor A",
  "potential_impact": "Degradation at Motor A may reduce throughput capacity of Line 1 by 18-25% if unaddressed.",
  "downstream_impact": {
    "Motor_B": "Normal",
    "Conveyor_C": "At Risk (Reduced Input)"
  }
}
```

Frontend use:

- Digital Twin page
- Dashboard digital twin preview
- Dependency impact panel
- Alert detail context

### `GET /api/analyze`

Returns AI recommendation data for the current anomaly state.

If no anomaly is active:

```json
{
  "insight": "No active anomaly",
  "confidence_score": "12%",
  "risk_level": "Low",
  "recommended_actions": []
}
```

If anomaly is active:

```json
{
  "insight": "Anomaly detected at Motor A (System Fallback)",
  "confidence_score": "88%",
  "risk_level": "High",
  "retrieved_sop": {
    "document_id": "SOP-MA-102: Bearing Inspection & Replacement",
    "match_score": "92%",
    "excerpts": [
      "Check bearings immediately."
    ]
  },
  "recommended_actions": [
    {
      "id": 1,
      "action": "Inspect within 24 hours",
      "impact": "High Impact"
    },
    {
      "id": 2,
      "action": "Reduce operating load by 15%",
      "impact": "Medium Impact"
    }
  ]
}
```

Frontend use:

- Recommendations page
- AI insight panel
- Confidence score
- SOP evidence
- Recommended action list

## Mock Data

Current mock data lives in:

```text
backend/mock-data/
```

SOP files:

```text
backend/mock-data/SOP-Mocking/SOP-MA-101.txt
backend/mock-data/SOP-Mocking/SOP-MA-102.txt
backend/mock-data/SOP-Mocking/SOP-MA-103.txt
```

### SOP Mock

The SOP mock files are local text files that simulate maintenance manuals or standard operating procedures.

In a real production setup, this knowledge would likely come from Azure AI Search, Microsoft Fabric, SharePoint, a document store, or another enterprise knowledge source. For the demo, these files let the backend generate recommendation responses without needing a real document pipeline.

Current purpose:

- Provide mock maintenance context for Motor A
- Act as fallback evidence for `GET /api/analyze`
- Let the AI recommendation flow work in `APP_MODE=mock`
- Let `APP_MODE=production` fall back safely if Azure AI Search returns no result or fails

Example usage in the backend:

1. An anomaly is active on Motor A.
2. Frontend calls `GET /api/analyze`.
3. Backend loads SOP text from `backend/mock-data/SOP-Mocking/`.
4. Backend returns a recommendation with matched SOP evidence and recommended actions.

For frontend integration, the frontend does not need to read these files directly. It only consumes the `retrieved_sop` field returned by `GET /api/analyze`.

Telemetry simulator:

```text
backend/mock-data/sensor_simulator.py
```

The simulator generates normal and occasional critical Motor A telemetry, then posts it to `BACKEND_API_ENDPOINT`.

## Run Sensor Simulator

`sensor_simulator.py` simulates Motor A sensor telemetry and sends it to:

```text
POST /api/ingest-telemetry
```

Use it when you want the backend to receive live-looking telemetry without connecting to a real PLC, IoT Hub, OPC UA, or MQTT source.

Start the backend server first.

With Docker:

```bash
docker compose up --build backend
```

Or locally:

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Then open another terminal and run the simulator.

From the project root:

```bash
python backend/mock-data/sensor_simulator.py
```

From the `backend` folder:

```bash
python mock-data/sensor_simulator.py
```

The simulator sends a payload like this:

```json
{
  "device_id": "motor-A",
  "timestamp": "2026-05-09 10:24:30",
  "data": {
    "vibration": 3.4,
    "temperature": 78.2,
    "load": 91.0,
    "status": "Critical"
  }
}
```

Most generated telemetry is `Normal`. Occasionally the simulator sends `Critical`. When backend receives `status: "Critical"`, it automatically activates the anomaly scenario.

By default, the simulator posts to:

```env
BACKEND_API_ENDPOINT=http://localhost:8000/api/ingest-telemetry
```

By default, it sends telemetry every 2 seconds. Override this with:

```env
SIMULATION_INTERVAL_SECONDS=5
```

Stop the simulator with `Ctrl + C`.

## Backend State Model

The backend currently uses in-memory state:

```json
{
  "is_anomaly_active": false,
  "anomaly_start_time": 0,
  "latest_ingested_data": null
}
```

This means state is reset when the FastAPI process restarts. There is no database yet.

## Frontend Integration Notes

Recommended frontend flow:

1. Dashboard polls `GET /api/telemetry`.
2. Simulate Anomaly calls `POST /api/trigger-anomaly`.
3. Digital Twin page calls `GET /api/digital-twin`.
4. Recommendations page calls `GET /api/analyze`.
5. Reset calls `POST /api/reset-anomaly`.

The frontend should treat API responses as the source of truth for backend-driven demo state.

## Not Implemented Yet

The following story items do not currently have backend API routes:

- Dashboard KPI summary API
- OEE history API
- Energy usage history API
- Alert queue API
- Agent cascade execution API
- Agent execution log API
- Recommendation approval API
- Work order create/list/detail API
- Work order dispatch API
- Reports/ROI/roadmap API
- Real Azure IoT Hub telemetry ingestion
- Real Azure Digital Twins graph query
- Microsoft Fabric history/reporting integration
- Foundry Agent Service orchestration
- CMMS or maintenance system integration

## Suggested Future API Routes

These are proposed routes only. They are not implemented yet.

```text
GET  /api/dashboard
GET  /api/alerts
GET  /api/assets
GET  /api/agents
POST /api/agents/run
GET  /api/agents/logs
GET  /api/recommendations
POST /api/recommendations/{id}/approve
GET  /api/work-orders
POST /api/work-orders
GET  /api/work-orders/{id}
POST /api/work-orders/{id}/dispatch
GET  /api/reports/business-value
GET  /api/reports/azure-architecture
GET  /api/reports/roadmap
```

## Known Issues

- Backend is currently untracked in git.
- README at the project root still describes the app as frontend-only.
- Some SOP text appears with encoding artifacts and should be cleaned before production use.
- `APP_MODE=production` only affects recommendation retrieval/generation today. Other routes still use mocked or in-memory data.
