import type { Asset } from "../types";

/** Local fallback when backend is unavailable — matches previous demo defaults (stable line). */
export function buildAssets(anomalyActive: boolean): Asset[] {
  return [
    {
      id: "motor-a",
      name: "Motor A",
      role: "Main drive motor",
      status: anomalyActive ? "critical" : "normal",
      healthScore: anomalyActive ? 63 : 96,
      vibration: anomalyActive ? 3.6 : 1.2,
      temperature: anomalyActive ? 76 : 62,
      load: anomalyActive ? 82 : 72,
      oee: anomalyActive ? 78 : 92,
      x: 26,
      y: 44,
    },
    {
      id: "motor-b",
      name: "Motor B",
      role: "Secondary drive motor",
      status: "normal",
      healthScore: 95,
      vibration: 1.3,
      temperature: 61,
      load: 68,
      oee: 91,
      x: 52,
      y: 56,
    },
    {
      id: "conveyor-c",
      name: "Conveyor C",
      role: "Line transfer conveyor",
      status: anomalyActive ? "warning" : "normal",
      healthScore: anomalyActive ? 84 : 97,
      vibration: 1.1,
      temperature: 55,
      load: anomalyActive ? 74 : 65,
      oee: anomalyActive ? 86 : 94,
      x: 74,
      y: 68,
    },
  ];
}
