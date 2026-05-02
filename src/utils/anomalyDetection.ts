import type {
  AiRecommendation,
  MachineId,
  MachineState,
  MachineStatus,
  MachineSummaryContext,
  RiskLevel,
  TelemetryPoint,
} from "../types";

export const machineBaselines: Record<
  MachineId,
  { vibration: number; temperature: number; energyKw: number; vibrationStd: number; temperatureStd: number }
> = {
  "Motor-A": { vibration: 2.4, temperature: 68, energyKw: 14.2, vibrationStd: 1.45, temperatureStd: 5.5 },
  "Conveyor-B": { vibration: 2.0, temperature: 60, energyKw: 12.8, vibrationStd: 1.0, temperatureStd: 4.2 },
  "Compressor-C": { vibration: 1.6, temperature: 57, energyKw: 10.9, vibrationStd: 0.8, temperatureStd: 3.8 },
};

export function round(value: number, digits = 1): number {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

export function zScore(value: number, baseline: number, standardDeviation: number): number {
  return round((value - baseline) / standardDeviation, 1);
}

export function assessTelemetry(point: Pick<TelemetryPoint, "vibration" | "temperature" | "energyKw" | "loadPercent">): {
  riskLevel: RiskLevel;
  status: MachineStatus;
  anomalyScore: number;
} {
  const highBearingRisk = point.vibration > 7.5 && point.temperature > 85;
  const mediumThermalOrVibrationRisk = point.vibration > 5.0 || point.temperature > 78;
  const energyOrLoadWarning = point.energyKw > 16.2 || point.loadPercent > 84;

  const anomalyScore = clamp(
    point.vibration * 6 + (point.temperature - 55) * 1.3 + (point.energyKw - 10) * 3 + Math.max(point.loadPercent - 70, 0) * 0.6,
    0,
    100
  );

  if (highBearingRisk) {
    return { riskLevel: "High", status: "critical", anomalyScore: round(anomalyScore, 0) };
  }

  if (mediumThermalOrVibrationRisk || energyOrLoadWarning) {
    return { riskLevel: "Medium", status: "warning", anomalyScore: round(anomalyScore, 0) };
  }

  return { riskLevel: "Low", status: "normal", anomalyScore: round(anomalyScore * 0.55, 0) };
}

export function calculateRollingAverage(points: TelemetryPoint[], windowSize = 12): { vibration: number; temperature: number } {
  const sample = points.slice(-windowSize);
  const totals = sample.reduce(
    (acc, point) => ({
      vibration: acc.vibration + point.vibration,
      temperature: acc.temperature + point.temperature,
    }),
    { vibration: 0, temperature: 0 }
  );

  return {
    vibration: round(totals.vibration / sample.length, 1),
    temperature: round(totals.temperature / sample.length, 1),
  };
}

export function getTrend(points: TelemetryPoint[], metric: "vibration" | "temperature" | "energyKw"): string {
  const start = points[Math.max(0, points.length - 25)]?.[metric] ?? points[0][metric];
  const current = points[points.length - 1][metric];
  const delta = current - start;

  if (delta > start * 0.42) return "rapid increase";
  if (delta > start * 0.12) return "rising";
  if (delta < -start * 0.1) return "falling";
  return "stable";
}

export function buildMachineState(machineId: MachineId, points: TelemetryPoint[]): MachineState {
  const current = points[points.length - 1];
  const roles: Record<MachineId, string> = {
    "Motor-A": "Main drive motor",
    "Conveyor-B": "Package transfer conveyor",
    "Compressor-C": "Pneumatic air supply",
  };

  return {
    machineId,
    displayName: machineId,
    role: roles[machineId],
    status: current.status,
    healthScore: current.healthScore,
    anomalyScore: current.anomalyScore,
    riskLevel: current.riskLevel,
    current,
    rollingAvg: calculateRollingAverage(points),
  };
}

export function buildSummaryContext(machineId: MachineId, points: TelemetryPoint[]): MachineSummaryContext {
  const baseline = machineBaselines[machineId];
  const current = points[points.length - 1];
  const highVibration = current.vibration > 5;
  const highTemperature = current.temperature > 78;
  const highEnergy = current.energyKw > 16.2;

  let likelyCause = "normal operating behavior";
  if (highVibration && highTemperature && highEnergy) {
    likelyCause = "bearing wear or lubrication degradation";
  } else if (highTemperature) {
    likelyCause = "possible cooling issue";
  } else if (highEnergy && !highVibration) {
    likelyCause = "possible load or process inefficiency";
  }

  return {
    machineId,
    timeWindow: "last 5 minutes",
    vibration: {
      baseline: baseline.vibration,
      current: current.vibration,
      increasePercent: round(((current.vibration - baseline.vibration) / baseline.vibration) * 100, 0),
      zScore: zScore(current.vibration, baseline.vibration, baseline.vibrationStd),
      trend: getTrend(points, "vibration"),
    },
    temperature: {
      baseline: baseline.temperature,
      current: current.temperature,
      increaseCelsius: round(current.temperature - baseline.temperature, 0),
      zScore: zScore(current.temperature, baseline.temperature, baseline.temperatureStd),
      trend: getTrend(points, "temperature"),
    },
    energy: {
      baseline: baseline.energyKw,
      current: current.energyKw,
      increasePercent: round(((current.energyKw - baseline.energyKw) / baseline.energyKw) * 100, 0),
      trend: getTrend(points, "energyKw"),
    },
    risk: current.riskLevel,
    likelyCause,
  };
}

export function buildAiRecommendation(summary: MachineSummaryContext): AiRecommendation {
  if (summary.risk === "High") {
    return {
      likelyIssue: "Bearing wear or lubrication degradation",
      evidence: `Vibration increased ${summary.vibration.increasePercent}% above baseline while temperature rose ${summary.temperature.increaseCelsius} deg C and energy consumption increased ${summary.energy.increasePercent}%.`,
      recommendedAction: "Inspect bearing and lubrication within 24 hours. Reduce load by 15% until inspection is completed.",
      urgency: "High",
      businessImpact: "Potential unplanned downtime on Packaging Line 1. Estimated OEE loss if ignored: 8-12%.",
      suggestedWorkOrder: `Create high-priority maintenance task for ${summary.machineId} bearing inspection.`,
    };
  }

  if (summary.risk === "Medium") {
    return {
      likelyIssue: summary.likelyCause,
      evidence: `Current telemetry shows ${summary.energy.trend} energy and ${summary.temperature.trend} thermal behavior against the ${summary.timeWindow} context.`,
      recommendedAction: "Schedule operator check, verify load balance, and monitor the next production cycle.",
      urgency: "Medium",
      businessImpact: "Efficiency loss may build gradually. Early action can avoid missed throughput targets.",
      suggestedWorkOrder: `Create medium-priority inspection task for ${summary.machineId}.`,
    };
  }

  return {
    likelyIssue: "No active anomaly detected",
    evidence: "Telemetry remains close to baseline with stable vibration, temperature, and energy usage.",
    recommendedAction: "Continue normal monitoring. No immediate maintenance action required.",
    urgency: "Low",
    businessImpact: "Machine is supporting healthy line performance and stable OEE.",
    suggestedWorkOrder: "No work order needed.",
  };
}
