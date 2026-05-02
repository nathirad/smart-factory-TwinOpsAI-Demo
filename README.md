# SmartFactory TwinOps AI

SmartFactory TwinOps AI is a polished hackathon demo for factory operations teams. It shows how simulated machine telemetry can drive anomaly detection, digital twin health state, AI-style maintenance recommendations, and a mock work-order workflow.

Live demo: https://smart-factory-alpha.vercel.app

## What The Demo Shows

The app presents **Packaging Line 1** as a Microsoft/Azure-style industrial command center. It is designed for a short pitch where judges can quickly see the problem, the telemetry signal, the AI reasoning summary, and the maintenance action.

Core flow:

1. Simulate live factory telemetry for the last 5 minutes.
2. Detect risk with explainable threshold, rolling average, z-score style, and multivariate rules.
3. Store the latest machine state in a digital twin style view.
4. Summarize telemetry before passing it to an AI reasoning layer.
5. Generate a recommended maintenance action and mock work order.

## Demo Scenario

The line contains three machines:

- **Motor-A**: critical demo anomaly with rising vibration, temperature, and energy usage.
- **Conveyor-B**: warning condition with increasing energy usage and load fluctuation.
- **Compressor-C**: normal machine with stable vibration, temperature, and energy.

Use **Run Demo Scenario** to switch from normal line simulation to the Motor-A anomaly scenario. Use **Reset Line** to return to the normal state.

## Key Features

- Executive overview KPIs for line risk, average OEE, line health, and open work orders.
- Clickable machine cards for Motor-A, Conveyor-B, and Compressor-C.
- Recharts telemetry visualization for vibration, temperature, and energy.
- Digital twin map showing connected machines and current health state.
- AI recommendation panel built from a compact machine summary, not raw time-series rows.
- Mock work order creation with ID, machine, priority, recommended action, team, and due time.
- Demo narrative explaining how simulated data would map to PLC, IoT Gateway, OPC UA, MQTT, or IoT Hub in production.
- Concise architecture flow from sensors to maintenance work order.
- Microsoft/Azure visual tone with dark navy surfaces, Azure blue highlights, and Fluent-style status colors.

## Simulated Telemetry

Telemetry is generated in the browser with deterministic noise for stable demos. Each point includes:

- `timestamp`
- `machineId`
- `vibration`
- `temperature`
- `energyKw`
- `rpm`
- `loadPercent`
- `oee`
- `status`
- `healthScore`
- `anomalyScore`
- `riskLevel`

The app generates 5 minutes of telemetry at a 5-second interval.

## Explainable Risk Logic

The demo intentionally uses simple logic that can be explained in a pitch:

- High risk when vibration is above `7.5 mm/s` and temperature is above `85 C`.
- Medium risk when vibration is above `5.0 mm/s` or temperature is above `78 C`.
- Rolling averages summarize recent vibration and temperature.
- Z-score style values compare current readings against machine baselines.
- Multivariate rules infer likely causes such as bearing wear, cooling issues, or load inefficiency.

## Project Structure

```text
src/
  App.tsx
  components/
    AiRecommendationPanel.tsx
    ArchitectureFlow.tsx
    DigitalTwinMap.tsx
    KpiCard.tsx
    MachineCard.tsx
    TelemetryChart.tsx
    WorkOrderCard.tsx
  data/
    simulatedTelemetry.ts
  utils/
    anomalyDetection.ts
  types.ts
```

## Tech Stack

- React
- TypeScript
- Tailwind CSS
- Recharts
- Lucide React
- Vite

No backend or external API is required for this MVP.

## Run Locally

```bash
npm install
npm run dev
```

Then open:

```text
http://localhost:5173
```

## Build

```bash
npm run build
```

## Preview Production Build

```bash
npm run preview
```

## Deployment

The project is deployed on Vercel:

```text
https://smart-factory-alpha.vercel.app
```

For a new deployment:

```bash
npx vercel deploy --prod
```

## Hackathon Notes

This is a frontend-first MVP. In a production version, telemetry would come from factory systems such as PLCs, IoT gateways, OPC UA, MQTT, or Azure IoT Hub. The summarized machine context can later be sent to GPT-4o or another AI reasoning layer, while a backend API can persist telemetry, digital twin state, recommendations, and maintenance work orders.
