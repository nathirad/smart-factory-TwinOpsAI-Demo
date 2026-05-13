import type {
  AlertsApiResponse,
  AnalyzeApiResponse,
  AgentsApiResponse,
  DashboardApiResponse,
  DigitalTwinApiResponse,
  ReportsApiResponse,
  TelemetryApiResponse,
  WorkOrderApiResponse,
  WorkOrderApprovalRequest,
  WorkOrderCreateRequest,
  WorkOrderDispatchRequest,
} from "./types";

function joinUrl(base: string, path: string): string {
  const b = base.endsWith("/") ? base.slice(0, -1) : base;
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${b}${p}`;
}

async function readJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export async function fetchTelemetry(baseUrl: string): Promise<TelemetryApiResponse> {
  const res = await fetch(joinUrl(baseUrl, "/api/telemetry"));
  return readJson<TelemetryApiResponse>(res);
}

export async function fetchDigitalTwin(baseUrl: string): Promise<DigitalTwinApiResponse> {
  const res = await fetch(joinUrl(baseUrl, "/api/digital-twin"));
  return readJson<DigitalTwinApiResponse>(res);
}

export async function fetchAnalyze(baseUrl: string): Promise<AnalyzeApiResponse> {
  const res = await fetch(joinUrl(baseUrl, "/api/analyze"));
  return readJson<AnalyzeApiResponse>(res);
}

export async function fetchAgents(baseUrl: string): Promise<AgentsApiResponse> {
  const res = await fetch(joinUrl(baseUrl, "/api/agents"));
  return readJson<AgentsApiResponse>(res);
}

export async function postRunAgents(baseUrl: string): Promise<AgentsApiResponse> {
  const res = await fetch(joinUrl(baseUrl, "/api/agents/run"), { method: "POST" });
  return readJson<AgentsApiResponse>(res);
}
export async function fetchDashboard(baseUrl: string): Promise<DashboardApiResponse> {
  const res = await fetch(joinUrl(baseUrl, "/api/dashboard"));
  return readJson<DashboardApiResponse>(res);
}

export async function fetchAlerts(baseUrl: string): Promise<AlertsApiResponse> {
  const res = await fetch(joinUrl(baseUrl, "/api/alerts"));
  return readJson<AlertsApiResponse>(res);
}

export async function fetchReports(baseUrl: string): Promise<ReportsApiResponse> {
  const res = await fetch(joinUrl(baseUrl, "/api/reports"));
  return readJson<ReportsApiResponse>(res);
}

export async function fetchWorkOrders(baseUrl: string): Promise<WorkOrderApiResponse[]> {
  const res = await fetch(joinUrl(baseUrl, "/api/work-orders"));
  return readJson<WorkOrderApiResponse[]>(res);
}

export async function postTriggerAnomaly(baseUrl: string): Promise<void> {
  const res = await fetch(joinUrl(baseUrl, "/api/trigger-anomaly"), { method: "POST" });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `${res.status} ${res.statusText}`);
  }
}

export async function postResetAnomaly(baseUrl: string): Promise<void> {
  const res = await fetch(joinUrl(baseUrl, "/api/reset-anomaly"), { method: "POST" });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `${res.status} ${res.statusText}`);
  }
}

export async function postCreateWorkOrder(baseUrl: string, payload?: WorkOrderCreateRequest): Promise<WorkOrderApiResponse> {
  const res = await fetch(joinUrl(baseUrl, "/api/work-orders"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload ?? {}),
  });
  return readJson<WorkOrderApiResponse>(res);
}

export async function postApproveWorkOrder(baseUrl: string, workOrderId: string, payload?: WorkOrderApprovalRequest): Promise<WorkOrderApiResponse> {
  const res = await fetch(joinUrl(baseUrl, `/api/work-orders/${workOrderId}/approve`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload ?? {}),
  });
  return readJson<WorkOrderApiResponse>(res);
}

export async function postDispatchWorkOrder(baseUrl: string, workOrderId: string, payload?: WorkOrderDispatchRequest): Promise<WorkOrderApiResponse> {
  const res = await fetch(joinUrl(baseUrl, `/api/work-orders/${workOrderId}/dispatch`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload ?? {}),
  });
  return readJson<WorkOrderApiResponse>(res);
}

export type LiveTelemetry = {
  deviceId: string;
  timestamp: string;
  vibration: number;
  temperature: number;
  energyLoad: number;
  status: string;
};

export type TelemetryStreamPayload = {
  source: string;
  status: "ok" | "waiting" | "error";
  message?: string;
  data: LiveTelemetry | null;
};

export function subscribeTelemetryStream(
  baseUrl: string,
  onTelemetry: (data: LiveTelemetry) => void,
  onStatus?: (payload: TelemetryStreamPayload) => void,
  onError?: (error: Event) => void
): () => void {
  const eventSource = new EventSource(
    joinUrl(baseUrl, "/api/telemetry/stream")
  );

  eventSource.onmessage = (event) => {
    const payload: TelemetryStreamPayload = JSON.parse(event.data);

    onStatus?.(payload);

    if (payload.status === "ok" && payload.data) {
      onTelemetry(payload.data);
    }
  };

  eventSource.onerror = (error) => {
    console.error("SSE telemetry stream error:", error);
    onError?.(error);
  };

  return () => {
    eventSource.close();
  };
}