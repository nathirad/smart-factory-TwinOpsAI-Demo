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
export interface ApiMetricPoint {
  [key: string]: string | number;
}

export interface DashboardKpi {
  id: string;
  label: string;
  value: string;
  trend: string;
  status: string;
}

export interface DashboardAssetHealth {
  id: string;
  name: string;
  role: string;
  status: string;
  healthScore: number;
  vibration: number;
  temperature: number;
  load: number;
  oee: number;
}

export interface ApiAlert {
  id: string;
  title: string;
  assetId: string;
  assetName: string;
  severity: "Low" | "Medium" | "High" | string;
  timestamp: string;
  details: string;
  status: string;
  recommendedAction: string;
  metrics: {
    label: string;
    value: string;
    delta: string;
  }[];
}

export interface DashboardApiResponse {
  mode: string;
  source: string;
  generated_at: string;
  line: {
    id: string;
    name: string;
    status: string;
  };
  kpis: DashboardKpi[];
  oee: {
    current: number;
    target: number;
    unit: string;
    history: ApiMetricPoint[];
  };
  energy: {
    current_kw: number;
    baseline_kw: number;
    unit: string;
    history: ApiMetricPoint[];
  };
  asset_health: DashboardAssetHealth[];
  latest_telemetry: TelemetryApiResponse;
  alerts: ApiAlert[];
  azure_services: {
    id: string;
    name: string;
    status: string;
    detail: string;
  }[];
}

export interface AlertsApiResponse {
  mode: string;
  source: string;
  generated_at: string;
  alerts: ApiAlert[];
}

export interface WorkOrderHistoryItem {
  time: string;
  event: string;
}

export interface WorkOrderApiResponse {
  id: string;
  assetId: string;
  assetName: string;
  priority: "High" | "Medium" | "Low";
  status: "Draft" | "Awaiting approval" | "Approved" | "Dispatched";
  assignee: string;
  due: string;
  title: string;
  checklist: string[];
  history: WorkOrderHistoryItem[];
  recommendation_id?: number | null;
  source?: string;
  mode?: string;
  externalSystem?: string | null;
  externalId?: string | null;
  dispatchStatus?: "Not dispatched" | "Pending external dispatch" | "Dispatched" | "Failed" | string;
  dispatchError?: string | null;
}

export interface WorkOrderCreateRequest {
  recommendation_id?: number;
  action?: string;
  assignee?: string;
  due?: string;
}

export interface WorkOrderApprovalRequest {
  approved_by?: string;
  note?: string;
}

export interface WorkOrderDispatchRequest {
  dispatched_by?: string;
  note?: string;
}

export interface ReportMetricApi {
  id: string;
  label: string;
  value: string;
  detail: string;
  tone: "blue" | "green" | "orange" | "red";
}

export interface ReportRowApi {
  problem?: string;
  response?: string;
  kpi?: string;
  driver?: string;
  assumption?: string;
  annualImpact?: number;
}

export interface ReportsApiResponse {
  mode: string;
  source: string;
  generated_at: string;
  business_value: {
    metrics: ReportMetricApi[];
    pain_point_mapping: ReportRowApi[];
  };
  roi: {
    currency: string;
    summary: {
      annual_cost_avoidance: number;
      roi_percent: number;
      payback_months: number;
      risk_exposure_per_hour: number;
    };
    assumptions: ReportRowApi[];
    notes: string[];
  };
  azure_architecture: {
    flow: {
      order: number;
      name: string;
      role: string;
    }[];
    service_roles: {
      id: string;
      name: string;
      status: string;
      detail: string;
    }[];
  };
  operating_model: {
    equation: string;
    stages: {
      name: string;
      detail: string;
    }[];
    paradigm_shift: {
      traditional: string[];
      ai_driven: string[];
    };
  };
  roadmap: {
    phases: {
      id: string;
      title: string;
      description: string;
      risk: string;
    }[];
  };
}

/** Backend GET /api/twins/{twinId}/dependencies */
export interface TwinDependencyNode {
  id: string;
  model?: string;
  name?: string;
  machineType?: string;
  location?: string | null;
  status?: string;
  healthScore?: number;
  vibration?: number;
  temperature?: number;
  energyLoad?: number;
}

export interface TwinDependencyEdge {
  sourceId: string;
  relationshipId: string;
  relationshipName: string;
  targetId: string;
  depth: number;
}

export interface TwinDependenciesApiResponse {
  source: string;
  twinId: string;
  root: TwinDependencyNode;
  dependencies: TwinDependencyNode[];
  graph: TwinDependencyEdge[];
}

export interface AnomalyResult {
  id?: string;
  machineId?: string;
  timestamp?: string;
  createdAt?: string;
  isAnomaly: boolean;
  severity: "Normal" | "Low" | "Medium" | "High" | "Critical" | string;
  contributingFactors: Array<
    | string
    | {
        metric?: string;
        name?: string;
        value?: number;
        reason?: string;
        score?: number;
      }
  >;
  telemetry?: Record<string, unknown>;
  source?: string;
  agentTriggered?: boolean;
  stored?: boolean;
  savedToCosmos?: boolean;
  agentTrigger?: {
    enabled?: boolean;
    target?: string;
    reason?: string;
  };
}

export interface AnomalyDetectApiResponse {
  status: string;
  cosmosEnabled: boolean;
  result: AnomalyResult;
  agentTrigger?: {
    enabled: boolean;
    target: string;
    reason: string;
  };
}

export interface AnomalyResultsApiResponse {
  status: string;
  cosmosEnabled?: boolean;
  count?: number;
  results?: AnomalyResult[];
  items?: AnomalyResult[];
  data?: AnomalyResult[];
}