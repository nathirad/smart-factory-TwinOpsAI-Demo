# Backend API README

This backend is a FastAPI prototype for the SmartFactory TwinOps AI demo. It exposes API routes for telemetry ingestion, anomaly simulation, digital twin impact, AI/SOP-based recommendations, and work-order execution.

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

## Run Backend Tests

From the project root:

```bash
pip install -r backend/requirements-dev.txt
pytest backend/tests
```

The test suite uses FastAPI `TestClient`, so it does not require starting `uvicorn` or Docker first.

Current tests cover:

- OpenAPI generation
- telemetry ingestion
- anomaly trigger/reset
- telemetry, digital twin, and AI recommendation responses
- dashboard, alerts, OEE, and energy APIs
- work order create/detail/approve/dispatch lifecycle
- production-style work order dispatch fallback
- reports APIs
- production-style external JSON fallback behavior

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
WORK_ORDER_SYSTEM_NAME=External CMMS
CMMS_DISPATCH_WEBHOOK_URL=https://your-cmms-or-logic-app-webhook.example.com/work-orders
DASHBOARD_DATA_ENDPOINT=https://your-fabric-or-api.example.com/dashboard
ALERTS_DATA_ENDPOINT=https://your-fabric-or-api.example.com/alerts
REPORTS_DATA_ENDPOINT=https://your-fabric-or-api.example.com/reports
```

### `APP_MODE=mock`

Use local mocked telemetry, local SOP text files, and deterministic fallback recommendation data. This mode does not require OpenAI or Azure services.

### `APP_MODE=production`

The `/api/analyze` route attempts to use Azure AI Search for SOP retrieval and OpenAI for recommendation generation. If Azure Search or OpenAI fails, the backend falls back to mock SOP/recommendation data.

Current production support is partial. Real IoT Hub, Azure Digital Twins, Microsoft Fabric, Foundry Agent Service, and CMMS/work-order integrations are not implemented yet.

For Work Orders, production mode is hybrid:

- Work order creation and approval are still tracked in backend memory for the demo.
- Dispatch attempts to call `CMMS_DISPATCH_WEBHOOK_URL` if configured.
- If no webhook is configured, dispatch stays safe as `Pending external dispatch` instead of pretending a real CMMS dispatch happened.
- If the webhook succeeds, backend marks the work order as `Dispatched`.

For Dashboard, Alerts, and Reports, production mode is also hybrid:

- If `DASHBOARD_DATA_ENDPOINT`, `ALERTS_DATA_ENDPOINT`, or `REPORTS_DATA_ENDPOINT` is configured, backend attempts to fetch JSON from that external service.
- If the external service is not configured or fails, backend returns production-fallback mock data with the same contract.
- This lets frontend use the same API paths in mock and production modes.

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

### `GET /api/dashboard`

Returns the dashboard summary contract for KPIs, OEE, energy usage, asset health, latest telemetry, alert queue, and Azure service status.

In `APP_MODE=mock`, data is generated from backend in-memory demo state.

In `APP_MODE=production`, backend first attempts to fetch JSON from `DASHBOARD_DATA_ENDPOINT`. If it is not configured or fails, backend returns `source: "production-fallback"`.

Response shape:

```json
{
  "mode": "mock",
  "source": "mock",
  "generated_at": "2026-05-11 10:24:31",
  "line": {
    "id": "packaging-line-1",
    "name": "Packaging Line 1",
    "status": "Stable"
  },
  "kpis": [
    {
      "id": "line-health",
      "label": "Line Health",
      "value": "95%",
      "trend": "+3%",
      "status": "Stable"
    }
  ],
  "oee": {
    "current": 87,
    "target": 90,
    "unit": "%",
    "history": [
      {
        "day": "May 17",
        "value": 87
      }
    ]
  },
  "energy": {
    "current_kw": 590,
    "baseline_kw": 590,
    "unit": "kW",
    "history": [
      {
        "time": "10:00",
        "value": 590
      }
    ]
  },
  "asset_health": [],
  "latest_telemetry": {},
  "alerts": [],
  "azure_services": []
}
```

Frontend use:

- Dashboard KPI cards
- OEE chart
- Energy chart
- Asset health cards
- Latest telemetry
- Alert preview
- Azure service status

### `GET /api/alerts`

Returns current operational alert queue.

In mock mode, alerts are derived from anomaly state. If Motor A is critical, backend returns active Motor A and downstream-impact alerts. If no anomaly is active, backend returns an informational stable-line alert.

Response shape:

```json
{
  "mode": "mock",
  "source": "mock",
  "generated_at": "2026-05-11 10:24:31",
  "alerts": [
    {
      "id": "alert-motor-a-bearing-risk",
      "title": "Bearing wear risk detected",
      "assetId": "motor-a",
      "assetName": "Motor A",
      "severity": "High",
      "timestamp": "2026-05-11 10:24:31",
      "details": "Motor A vibration and temperature moved above baseline together.",
      "status": "Active",
      "recommendedAction": "Inspect Motor A bearing and reduce load by 15%.",
      "metrics": [
        {
          "label": "Vibration",
          "value": "3.6 mm/s",
          "delta": "Elevated vs baseline"
        }
      ]
    }
  ]
}
```

Frontend use:

- Alert queue
- Notification panel
- Dashboard alert count
- Digital Twin alert detail context

### `GET /api/oee`

Returns OEE summary and history only.

Response shape:

```json
{
  "mode": "mock",
  "source": "mock",
  "generated_at": "2026-05-11 10:24:31",
  "oee": {
    "current": 87,
    "target": 90,
    "unit": "%",
    "history": []
  }
}
```

### `GET /api/energy`

Returns energy usage summary and history only.

Response shape:

```json
{
  "mode": "mock",
  "source": "mock",
  "generated_at": "2026-05-11 10:24:31",
  "energy": {
    "current_kw": 590,
    "baseline_kw": 590,
    "unit": "kW",
    "history": []
  }
}
```

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

### Agents API Feature

The Agents API is a separate backend feature implemented in:

```text
backend/features/agents_api.py
```

It simulates a Microsoft Azure multi-agent cascade for:

- Sensor Agent: Azure IoT Hub telemetry monitoring
- Twin Agent: Azure Digital Twins dependency impact
- Maintenance Agent: Azure AI Search + Azure OpenAI SOP analysis
- Energy Agent: Microsoft Fabric Real-Time Intelligence load scenario
- Safety Agent: Microsoft Entra ID + Defender for IoT guardrails
- Business Impact Agent: Azure Monitor + Power BI impact summary

Current routes:

```text
GET  /api/agents
POST /api/agents/run
GET  /api/agents/logs
```

This is still a simulated Azure agent workflow. It does not call real Azure AI Foundry Agent Service yet.

### `GET /api/agents`

Returns the current agent cascade state, Azure service mapping, agent steps, and execution log.

Frontend use:

- Agents page
- Multi-agent cascade cards
- Azure service mapping
- Execution log panel

### `POST /api/agents/run`

Manually starts the simulated agent cascade without requiring a new telemetry payload.

Frontend use:

- Manual API testing
- Future Agents page run button
- Demo control flow

### `GET /api/agents/logs`

Returns only the execution log for clients that do not need the full agent payload.

Frontend use:

- Execution log panel
- Lightweight polling
- Demo audit timeline
### `GET /api/work-orders`

Returns the current in-memory work order queue.

Response:

```json
[
  {
    "id": "WO-20260511-0001",
    "assetId": "motor-a",
    "assetName": "Motor A",
    "priority": "High",
    "status": "Awaiting approval",
    "assignee": "Maintenance Team",
    "due": "Within 24 hours",
    "title": "Bearing inspection and lubrication check",
    "checklist": [
      "Verify lockout/tagout before inspection.",
      "Inspect Motor A bearing housing and lubrication level.",
      "Check vibration trend after temporary load reduction.",
      "Record findings and attach photos to maintenance history."
    ],
    "history": [
      {
        "time": "2026-05-11 10:24:31",
        "event": "Work order generated from AI recommendation."
      }
    ],
    "recommendation_id": 1,
    "source": "mock",
    "mode": "mock",
    "externalSystem": "In-memory Work Order Queue",
    "externalId": null,
    "dispatchStatus": "Not dispatched",
    "dispatchError": null
  }
]
```

Frontend use:

- Work Orders page queue
- Maintenance queue count
- Work order status display

### `POST /api/work-orders`

Creates a work order from the current AI recommendation context.

This route requires an active anomaly. If no anomaly is active, the backend returns `409 Conflict`.

Request body is optional. If omitted, backend uses default Motor A recommendation values.

Request:

```json
{
  "recommendation_id": 1,
  "action": "Inspect within 24 hours",
  "assignee": "Maintenance Team",
  "due": "Within 24 hours"
}
```

Response:

```json
{
  "id": "WO-20260511-0001",
  "assetId": "motor-a",
  "assetName": "Motor A",
  "priority": "High",
  "status": "Awaiting approval",
  "assignee": "Maintenance Team",
  "due": "Within 24 hours",
  "title": "Bearing inspection and lubrication check",
  "checklist": [
    "Verify lockout/tagout before inspection.",
    "Inspect Motor A bearing housing and lubrication level.",
    "Check vibration trend after temporary load reduction.",
    "Record findings and attach photos to maintenance history."
  ],
  "history": [
    {
      "time": "2026-05-11 10:24:31",
      "event": "Work order generated from AI recommendation."
    },
    {
      "time": "2026-05-11 10:24:31",
      "event": "Recommended action attached: Inspect within 24 hours"
    }
  ],
  "recommendation_id": 1,
  "source": "mock",
  "mode": "mock",
  "externalSystem": "In-memory Work Order Queue",
  "externalId": null,
  "dispatchStatus": "Not dispatched",
  "dispatchError": null
}
```

Frontend use:

- Create work order button after recommendation is shown
- Generated work order panel
- Initial work order status should be `Awaiting approval`

### `GET /api/work-orders/{work_order_id}`

Returns one work order by ID.

Example:

```text
GET /api/work-orders/WO-20260511-0001
```

If the work order does not exist, backend returns `404 Not Found`.

Frontend use:

- Work order detail page
- Checklist and action history

### `POST /api/work-orders/{work_order_id}/approve`

Approves a work order before dispatch.

Example:

```text
POST /api/work-orders/WO-20260511-0001/approve
```

Optional request:

```json
{
  "approved_by": "Shift Supervisor",
  "note": "Proceed after lockout/tagout confirmation."
}
```

Response status changes to:

```json
{
  "status": "Approved"
}
```

The full response is the updated work order object.

Frontend use:

- Approve Action button
- Supervisor approval step

### `POST /api/work-orders/{work_order_id}/dispatch`

Dispatches an approved work order to the maintenance team.

This route requires status `Approved`. If the work order is still `Awaiting approval`, backend returns `409 Conflict`.

Example:

```text
POST /api/work-orders/WO-20260511-0001/dispatch
```

Optional request:

```json
{
  "dispatched_by": "Maintenance Coordinator",
  "note": "Send to rotating equipment team."
}
```

In `APP_MODE=mock`, response status changes to:

```json
{
  "status": "Dispatched",
  "dispatchStatus": "Dispatched"
}
```

In `APP_MODE=production`, dispatch behavior is hybrid:

- If `CMMS_DISPATCH_WEBHOOK_URL` is configured and the webhook succeeds, response status changes to `Dispatched`.
- If `CMMS_DISPATCH_WEBHOOK_URL` is not configured, response remains `Approved` and `dispatchStatus` becomes `Pending external dispatch`.
- If the webhook fails, response remains `Approved`, `dispatchStatus` becomes `Failed`, and `dispatchError` contains the failure reason.

The full response is always the updated work order object.

Frontend use:

- Send to Maintenance / Dispatch button
- Maintenance dispatch confirmation

### Work Order Demo Flow

Recommended frontend flow:

1. `POST /api/trigger-anomaly`
2. `GET /api/analyze`
3. `POST /api/work-orders`
4. `POST /api/work-orders/{work_order_id}/approve`
5. `POST /api/work-orders/{work_order_id}/dispatch`
6. `GET /api/work-orders`

Current work order storage is in-memory. Mock mode simulates the full lifecycle. Production mode can dispatch to a real CMMS-style webhook if `CMMS_DISPATCH_WEBHOOK_URL` is configured.

### Work Order Hybrid Behavior

The Work Orders API uses the same route contract in mock and production modes.

Mock mode:

```text
POST /api/work-orders
-> create in-memory work order
-> status = Awaiting approval

POST /api/work-orders/{id}/approve
-> status = Approved

POST /api/work-orders/{id}/dispatch
-> status = Dispatched
-> dispatchStatus = Dispatched
```

Production mode:

```text
POST /api/work-orders
-> create backend-tracked work order draft
-> status = Awaiting approval

POST /api/work-orders/{id}/approve
-> record supervisor approval
-> status = Approved

POST /api/work-orders/{id}/dispatch
-> if CMMS_DISPATCH_WEBHOOK_URL exists, call external maintenance/CMMS endpoint
-> if external dispatch succeeds, status = Dispatched
-> if no webhook exists, status = Approved and dispatchStatus = Pending external dispatch
-> if webhook fails, status = Approved and dispatchStatus = Failed
```

This keeps the demo safe: AI can draft the work order, but approval and dispatch remain explicit API actions.

### `GET /api/reports`

Returns the full executive reports contract in one response.

In `APP_MODE=mock`, backend returns mock business value, ROI, Azure architecture, operating model, and roadmap data.

In `APP_MODE=production`, backend first attempts to fetch JSON from `REPORTS_DATA_ENDPOINT`. If it is not configured or fails, backend returns `source: "production-fallback"`.

Response sections:

```json
{
  "mode": "mock",
  "source": "mock",
  "generated_at": "2026-05-11 10:24:31",
  "business_value": {},
  "roi": {},
  "azure_architecture": {},
  "operating_model": {},
  "roadmap": {}
}
```

### `GET /api/reports/business-value`

Returns business value metrics and pain-point mapping.

Frontend use:

- Executive report metrics
- Pain-point to TwinOps response table
- Business value summary

### `GET /api/reports/roi`

Returns ROI assumptions and cost avoidance model.

Response includes:

- annual cost avoidance
- ROI percentage
- payback months
- risk exposure per hour
- value-driver assumptions

### `GET /api/reports/azure-architecture`

Returns Azure architecture story:

```text
Factory Edge
-> IoT Hub
-> Fabric Real-Time
-> Azure Digital Twins
-> Azure ML
-> Foundry Agents
-> Tools & Work Orders
```

Frontend use:

- Azure architecture report section
- Service role explanation

### `GET /api/reports/operating-model`

Returns the AI-assisted operations model and paradigm shift.

Frontend use:

- Operating model
- Traditional vs AI-driven comparison

### `GET /api/reports/roadmap`

Returns rollout roadmap phases and risk mitigation notes.

Frontend use:

- Roadmap section
- Phase cards
- Risk mitigation narrative

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
  "latest_ingested_data": null,
  "agent_cascade_started": false,
  "agent_cascade_last_run": null,
  "work_orders": {},
  "next_work_order_sequence": 1
}
```

This means state is reset when the FastAPI process restarts. `POST /api/reset-anomaly` also clears work orders and resets the work-order sequence. There is no database yet.

## Frontend Integration Notes

Recommended frontend flow:

1. Dashboard polls `GET /api/telemetry`.
2. Simulate Anomaly calls `POST /api/trigger-anomaly`.
3. Dashboard can call `GET /api/dashboard`, `GET /api/alerts`, `GET /api/oee`, or `GET /api/energy`.
4. Digital Twin page calls `GET /api/digital-twin`.
5. Recommendations page calls `GET /api/analyze`.
6. Recommendations page creates a work order with `POST /api/work-orders`.
7. Supervisor approval calls `POST /api/work-orders/{work_order_id}/approve`.
8. Dispatch calls `POST /api/work-orders/{work_order_id}/dispatch`.
9. Reports page calls `GET /api/reports` or individual report routes.
10. Reset calls `POST /api/reset-anomaly`.
11. Agents page can call `GET /api/agents` or `GET /api/agents/logs`.

The frontend should treat API responses as the source of truth for backend-driven demo state.

## Not Implemented Yet

The following story items do not currently have backend API routes:

- Dashboard KPI summary API
- OEE history API
- Energy usage history API
- Alert queue API
- Recommendation approval API
- Work order create/list/detail API
- Work order dispatch API
- Reports/ROI/roadmap API
- Agent cascade execution API
- Agent execution log API
- Real Azure IoT Hub telemetry ingestion
- Real Azure Digital Twins graph query
- Microsoft Fabric history/reporting integration
- Real Azure AI Foundry Agent Service orchestration
- CMMS or maintenance system integration

## Suggested Future API Routes

These are proposed routes only. Agents API routes are already implemented separately above.

```text
GET  /api/assets
GET  /api/recommendations
POST /api/recommendations/{id}/approve
```

## Known Issues

- Backend is currently untracked in git.
- README at the project root still describes the app as frontend-only.
- Some SOP text appears with encoding artifacts and should be cleaned before production use.
- `APP_MODE=production` is hybrid. Recommendations can use Azure AI Search/OpenAI, Work Orders can call a CMMS webhook, and Dashboard/Alerts/Reports can call external JSON endpoints. If those services are not configured, backend returns production-fallback mock data.
- Work Orders API storage is still in memory. Production dispatch only calls a real external maintenance system when `CMMS_DISPATCH_WEBHOOK_URL` is configured.
- Dashboard, Alerts, and Reports production mode currently depends on external JSON endpoints if configured. There is no direct Fabric or Azure Digital Twins SDK integration yet.
