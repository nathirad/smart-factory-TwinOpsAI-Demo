import type { AgentsApiResponse, AnalyzeApiResponse, DigitalTwinApiResponse, TelemetryApiResponse } from "./types";

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
