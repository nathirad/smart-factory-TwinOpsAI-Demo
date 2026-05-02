# SmartFactory TwinOps AI

A polished hackathon demo showing how AI can help factory teams detect machine anomalies, predict maintenance risk, and recommend maintenance actions from simulated sensor time-series data.

Live demo: https://smart-factory-alpha.vercel.app

## Demo Scenario

The app simulates **Packaging Line 1** with three machines:

- **Motor-A**: critical anomaly scenario with rising vibration, temperature, and energy usage
- **Conveyor-B**: warning case with increasing energy and load fluctuation
- **Compressor-C**: stable normal operating state

## Features

- Executive overview dashboard with line risk, OEE, health score, and work-order status
- Live machine telemetry charts for vibration, temperature, and energy
- Digital twin health map for Packaging Line 1
- Explainable anomaly detection using thresholds, rolling averages, z-score style comparisons, and multivariate rules
- AI-style recommendation panel using summarized context instead of raw time-series rows
- Mock maintenance work order creation
- Concise production architecture flow from PLC/IoT gateway to work order

## Tech Stack

- React
- TypeScript
- Tailwind CSS
- Recharts
- Vite
- Simulated in-app telemetry, no backend required

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
