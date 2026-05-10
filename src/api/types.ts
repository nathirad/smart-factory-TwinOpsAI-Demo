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
