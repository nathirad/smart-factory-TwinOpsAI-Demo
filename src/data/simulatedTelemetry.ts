import type { MachineId, MachineState, TelemetryPoint } from "../types";
import { assessTelemetry, buildMachineState, clamp, round } from "../utils/anomalyDetection";

const machineIds: MachineId[] = ["Motor-A", "Conveyor-B", "Compressor-C"];

function deterministicNoise(index: number, seed: number, amplitude: number): number {
  const value = Math.sin(index * 12.9898 + seed * 78.233) * 43758.5453;
  return (value - Math.floor(value) - 0.5) * amplitude;
}

function easeInOut(progress: number): number {
  return progress <= 0 ? 0 : progress >= 1 ? 1 : progress * progress * (3 - 2 * progress);
}

function pointForMachine(machineId: MachineId, index: number, count: number, demoMode: boolean, timestamp: Date): TelemetryPoint {
  const t = index / Math.max(count - 1, 1);
  let vibration = 0;
  let temperature = 0;
  let energyKw = 0;
  let rpm = 0;
  let loadPercent = 0;
  let oee = 0;

  if (machineId === "Motor-A") {
    const anomalyStart = count - 25;
    const anomalyProgress = demoMode ? easeInOut((index - anomalyStart) / 24) : 0;
    vibration = 2.35 + Math.sin(index / 6) * 0.18 + deterministicNoise(index, 1, 0.22) + anomalyProgress * 5.95;
    temperature = 66 + Math.sin(index / 9) * 1.1 + deterministicNoise(index, 2, 0.8) + anomalyProgress * 23.5;
    energyKw = 14.1 + Math.sin(index / 7) * 0.24 + deterministicNoise(index, 3, 0.18) + anomalyProgress * 4.35;
    rpm = 1760 - anomalyProgress * 115 + deterministicNoise(index, 4, 10);
    loadPercent = 72 + Math.sin(index / 5) * 2.4 + anomalyProgress * 10 + deterministicNoise(index, 5, 1.6);
    oee = 92 - anomalyProgress * 14 + deterministicNoise(index, 6, 1.2);
  }

  if (machineId === "Conveyor-B") {
    vibration = 2.1 + Math.sin(index / 8) * 0.2 + deterministicNoise(index, 7, 0.2);
    temperature = 61 + Math.sin(index / 12) * 1.8 + deterministicNoise(index, 8, 0.8) + t * 2.4;
    energyKw = 13.1 + t * 3.1 + Math.sin(index / 5) * 0.34 + deterministicNoise(index, 9, 0.24);
    rpm = 1210 + Math.sin(index / 6) * 22 + deterministicNoise(index, 10, 10);
    loadPercent = 68 + Math.sin(index / 3) * 8.5 + deterministicNoise(index, 11, 3);
    oee = 88 - t * 3.5 + deterministicNoise(index, 12, 1.5);
  }

  if (machineId === "Compressor-C") {
    vibration = 1.55 + Math.sin(index / 10) * 0.08 + deterministicNoise(index, 13, 0.12);
    temperature = 57 + Math.sin(index / 14) * 0.7 + deterministicNoise(index, 14, 0.5);
    energyKw = 10.8 + Math.sin(index / 11) * 0.15 + deterministicNoise(index, 15, 0.16);
    rpm = 1485 + Math.sin(index / 8) * 8 + deterministicNoise(index, 16, 6);
    loadPercent = 62 + Math.sin(index / 9) * 2 + deterministicNoise(index, 17, 1.2);
    oee = 95 + Math.sin(index / 10) * 0.8 + deterministicNoise(index, 18, 0.8);
  }

  const assessed = assessTelemetry({ vibration, temperature, energyKw, loadPercent });
  const healthScore = clamp(100 - assessed.anomalyScore * 0.78, 8, 99);

  return {
    timestamp: timestamp.toISOString(),
    machineId,
    vibration: round(vibration, 1),
    temperature: round(temperature, 1),
    energyKw: round(energyKw, 1),
    rpm: Math.round(rpm),
    loadPercent: round(loadPercent, 0),
    oee: round(oee, 1),
    status: assessed.status,
    healthScore: round(healthScore, 0),
    anomalyScore: assessed.anomalyScore,
    riskLevel: assessed.riskLevel,
  };
}

export function generateTelemetry(demoMode: boolean): TelemetryPoint[] {
  const intervalSeconds = 5;
  const minutes = 5;
  const count = minutes * (60 / intervalSeconds) + 1;
  const end = new Date();
  const points: TelemetryPoint[] = [];

  machineIds.forEach((machineId) => {
    for (let index = 0; index < count; index += 1) {
      const secondsFromEnd = (count - 1 - index) * intervalSeconds;
      const timestamp = new Date(end.getTime() - secondsFromEnd * 1000);
      points.push(pointForMachine(machineId, index, count, demoMode, timestamp));
    }
  });

  return points;
}

export function getMachineSeries(points: TelemetryPoint[], machineId: MachineId): TelemetryPoint[] {
  return points.filter((point) => point.machineId === machineId);
}

export function getMachineStates(points: TelemetryPoint[]): MachineState[] {
  return machineIds.map((machineId) => buildMachineState(machineId, getMachineSeries(points, machineId)));
}

export { machineIds };
