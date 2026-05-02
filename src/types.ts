export type MachineId = "Motor-A" | "Conveyor-B" | "Compressor-C";

export type MachineStatus = "normal" | "warning" | "critical";

export type RiskLevel = "Low" | "Medium" | "High";

export interface TelemetryPoint {
  timestamp: string;
  machineId: MachineId;
  vibration: number;
  temperature: number;
  energyKw: number;
  rpm: number;
  loadPercent: number;
  oee: number;
  status: MachineStatus;
  healthScore: number;
  anomalyScore: number;
  riskLevel: RiskLevel;
}

export interface MachineState {
  machineId: MachineId;
  displayName: string;
  role: string;
  status: MachineStatus;
  healthScore: number;
  anomalyScore: number;
  riskLevel: RiskLevel;
  current: TelemetryPoint;
  rollingAvg: {
    vibration: number;
    temperature: number;
  };
}

export interface SummaryMetric {
  baseline: number;
  current: number;
  increasePercent?: number;
  increaseCelsius?: number;
  zScore?: number;
  trend: string;
}

export interface MachineSummaryContext {
  machineId: MachineId;
  timeWindow: string;
  vibration: SummaryMetric;
  temperature: SummaryMetric;
  energy: SummaryMetric;
  risk: RiskLevel;
  likelyCause: string;
}

export interface AiRecommendation {
  likelyIssue: string;
  evidence: string;
  recommendedAction: string;
  urgency: RiskLevel;
  businessImpact: string;
  suggestedWorkOrder: string;
}

export interface WorkOrder {
  id: string;
  machineId: MachineId;
  priority: "Low" | "Medium" | "High";
  recommendedAction: string;
  assignedTeam: string;
  dueTime: string;
}
