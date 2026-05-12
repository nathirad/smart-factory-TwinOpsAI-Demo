/** Backend GET /api/telemetry */
export interface BackendTelemetryMetrics {
  vibration: number;
  temperature: number;
  load: number;
  status: string;
}

export interface TelemetryApiResponse {
  timestamp: string;
  motor_A: BackendTelemetryMetrics;
  motor_B: BackendTelemetryMetrics;
  conveyor_C: BackendTelemetryMetrics;
}

/** Backend GET /api/digital-twin */
export interface DigitalTwinApiResponse {
  line_status: string;
  failure_risk: string;
  affected_asset: string;
  potential_impact: string;
  downstream_impact: Record<string, string>;
}

/** Backend GET /api/analyze */
export interface AnalyzeRecommendedAction {
  id: number;
  action: string;
  impact: string;
}

export interface AnalyzeRetrievedSop {
  document_id: string;
  match_score: string;
  excerpts: string[];
}

export interface AnalyzeApiResponse {
  insight: string;
  confidence_score: string;
  risk_level: string;
  recommended_actions: AnalyzeRecommendedAction[];
  retrieved_sop?: AnalyzeRetrievedSop;
}

/** Backend GET /api/agents */
export type AgentApiStatus = "completed" | "in-progress" | "pending" | "not-started";

export interface AgentApiStep {
  id: string;
  order: number;
  name: string;
  role: string;
  status: AgentApiStatus;
  summary: string;
  elapsed: string;
  tone: "blue" | "purple" | "orange" | "green";
  azure_service: string;
}

export interface AgentApiExecutionLog {
  id: string;
  agent: string;
  time: string;
  message: string;
  status: AgentApiStatus;
  azure_service: string;
}

export interface AgentsApiResponse {
  run_id: string;
  mode: string;
  anomaly_active: boolean;
  cascade_status: "standby" | "completed";
  orchestrator: {
    name: string;
    description: string;
  };
  azure_architecture: string[];
  agents: AgentApiStep[];
  execution_log: AgentApiExecutionLog[];
  recommended_next_action: string;
  generated_at: string;
}
