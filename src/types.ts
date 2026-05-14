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

export type AssetId = "motor-a" | "motor-b" | "conveyor-c";

export type AssetStatus = "normal" | "warning" | "critical" | "offline";

export interface Asset {
  id: AssetId;
  name: string;
  role: string;
  status: AssetStatus;
  healthScore: number;
  vibration: number;
  temperature: number;
  load: number;
  oee: number;
  x: number;
  y: number;
}

export interface Alert {
  id: string;
  title: string;
  assetId: AssetId;
  severity: "Low" | "Medium" | "High";
  timestamp: string;
  details: string;
  metrics: {
    label: string;
    value: string;
    delta: string;
  }[];
}

export type AgentStatus = "completed" | "in-progress" | "pending" | "not-started";

export interface AgentStep {
  id: string;
  order: number;
  name: string;
  role: string;
  status: AgentStatus;
  summary: string;
  elapsed: string;
  tone: "blue" | "purple" | "orange" | "green";
}

export interface ExecutionLog {
  id: string;
  agent: string;
  time: string;
  message: string;
  status: AgentStatus;
}

export interface RecommendationAction {
  id: string;
  title: string;
  description: string;
  impact: "High" | "Medium" | "Low";
}

export interface GeneratedWorkOrder {
  id: string;
  assetId: AssetId;
  assetName: string;
  priority: "High" | "Medium" | "Low";
  status: "Draft" | "Awaiting approval" | "Approved" | "Dispatched";
  assignee: string;
  due: string;
  title: string;
  checklist: string[];
  history: {
    time: string;
    event: string;
  }[];
}

export interface AzureService {
  id: string;
  name: string;
  status: "Connected" | "Warning" | "Offline";
  detail: string;
}

export interface ReportMetric {
  id: string;
  label: string;
  value: string;
  detail: string;
  tone: "blue" | "green" | "orange" | "red";
}

export interface RoadmapPhase {
  id: string;
  title: string;
  description: string;
  risk: string;
}

export type AnomalyFactor =
  | string
  | {
      metric?: string;
      name?: string;
      value?: number | string;
      reason?: string;
    };

export interface AnomalyTelemetrySnapshot {
  vibration?: number;
  temperature?: number;
  load?: number;
  energyLoad?: number;
  status?: string;
}

export interface AnomalyResultApiResponse {
  id: string;
  machineId?: string;
  createdAt?: string;
  telemetry?: AnomalyTelemetrySnapshot;
  isAnomaly?: boolean;
  severity?: "Low" | "Medium" | "High" | string;
  contributingFactors?: AnomalyFactor[];
  source?: string;
  agentTriggered?: boolean;
  cosmosSaved?: boolean;
}

export interface AnomalyResultsApiResponse {
  status: string;
  source?: string;
  cosmosEnabled?: boolean;
  count: number;
  results: AnomalyResultApiResponse[];
}