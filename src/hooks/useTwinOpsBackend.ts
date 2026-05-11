import { useCallback, useEffect, useMemo, useState } from "react";
import {
  fetchAnalyze,
  fetchAlerts,
  fetchDashboard,
  fetchDigitalTwin,
  fetchReports,
  fetchTelemetry,
  fetchWorkOrders,
  postApproveWorkOrder,
  postCreateWorkOrder,
  postDispatchWorkOrder,
  postResetAnomaly,
  postTriggerAnomaly,
} from "../api/client";
import type {
  AlertsApiResponse,
  AnalyzeApiResponse,
  DashboardApiResponse,
  DigitalTwinApiResponse,
  ReportsApiResponse,
  TelemetryApiResponse,
  WorkOrderApiResponse,
} from "../api/types";
import { buildAssets } from "../data/assetBuilders";
import type { Asset, AssetStatus } from "../types";

function apiBaseUrl(): string {
  const env = import.meta.env.VITE_API_BASE_URL;
  if (env !== undefined && env !== "") return env;
  return "";
}

function mapBackendStatus(status: string): AssetStatus {
  const s = status.toLowerCase();
  if (s.includes("critical")) return "critical";
  if (s.includes("warning") || s.includes("at risk")) return "warning";
  return "normal";
}

function healthFromMetrics(vibration: number, temperature: number, status: string): number {
  if (status === "Critical") {
    return Math.max(42, Math.round(68 - (vibration - 3) * 6 - Math.max(0, temperature - 75) * 0.35));
  }
  return Math.min(
    99,
    Math.round(94 + (1.35 - vibration) * 10 + (62 - temperature) * 0.35 + (72 - vibration * 8) * 0.05),
  );
}

export function telemetryToAssets(t: TelemetryApiResponse): Asset[] {
  const ma = t.motor_A;
  const mb = t.motor_B;
  const mc = t.conveyor_C;
  const motorACritical = ma.status === "Critical";

  return [
    {
      id: "motor-a",
      name: "Motor A",
      role: "Main drive motor",
      status: motorACritical ? "critical" : "normal",
      healthScore: healthFromMetrics(ma.vibration, ma.temperature, ma.status),
      vibration: ma.vibration,
      temperature: ma.temperature,
      load: ma.load,
      oee: motorACritical ? Math.max(70, Math.round(92 - (ma.vibration - 1.2) * 4)) : 92,
      x: 26,
      y: 44,
    },
    {
      id: "motor-b",
      name: "Motor B",
      role: "Secondary drive motor",
      status: mapBackendStatus(mb.status),
      healthScore: healthFromMetrics(mb.vibration, mb.temperature, mb.status),
      vibration: mb.vibration,
      temperature: mb.temperature,
      load: mb.load,
      oee: 91,
      x: 52,
      y: 56,
    },
    {
      id: "conveyor-c",
      name: "Conveyor C",
      role: "Line transfer conveyor",
      status: motorACritical ? "warning" : mapBackendStatus(mc.status),
      healthScore: motorACritical ? Math.min(88, healthFromMetrics(mc.vibration, mc.temperature, mc.status) - 8) : healthFromMetrics(mc.vibration, mc.temperature, mc.status),
      vibration: mc.vibration,
      temperature: mc.temperature,
      load: mc.load,
      oee: motorACritical ? 86 : 94,
      x: 74,
      y: 68,
    },
  ];
}

export function parseConfidencePercent(score: string): number {
  const n = parseInt(score.replace(/\D/g, ""), 10);
  return Number.isFinite(n) ? Math.min(100, Math.max(0, n)) : 0;
}

export function useTwinOpsBackend(pollMs = 3000) {
  const baseUrl = apiBaseUrl();
  const [telemetry, setTelemetry] = useState<TelemetryApiResponse | null>(null);
  const [digitalTwin, setDigitalTwin] = useState<DigitalTwinApiResponse | null>(null);
  const [analyze, setAnalyze] = useState<AnalyzeApiResponse | null>(null);
  const [dashboard, setDashboard] = useState<DashboardApiResponse | null>(null);
  const [alerts, setAlerts] = useState<AlertsApiResponse | null>(null);
  const [reports, setReports] = useState<ReportsApiResponse | null>(null);
  const [workOrders, setWorkOrders] = useState<WorkOrderApiResponse[]>([]);
  const [pollError, setPollError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const [tel, twin, ann] = await Promise.all([
        fetchTelemetry(baseUrl),
        fetchDigitalTwin(baseUrl),
        fetchAnalyze(baseUrl),
      ]);
      setTelemetry(tel);
      setDigitalTwin(twin);
      setAnalyze(ann);

      const [dash, alertQueue, reportData, orders] = await Promise.all([
        fetchDashboard(baseUrl),
        fetchAlerts(baseUrl),
        fetchReports(baseUrl),
        fetchWorkOrders(baseUrl),
      ]);
      setDashboard(dash);
      setAlerts(alertQueue);
      setReports(reportData);
      setWorkOrders(orders);
      setPollError(null);
      setReady(true);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Backend unreachable";
      setPollError(msg);
    }
  }, [baseUrl]);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => void refresh(), pollMs);
    return () => window.clearInterval(id);
  }, [refresh, pollMs]);

  const anomalyActive = telemetry?.motor_A?.status === "Critical";

  const assets: Asset[] = useMemo(() => {
    if (!telemetry) return buildAssets(false);
    return telemetryToAssets(telemetry);
  }, [telemetry]);

  const triggerAnomaly = useCallback(async () => {
    setActionError(null);
    try {
      await postTriggerAnomaly(baseUrl);
      await refresh();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Trigger failed");
      throw e;
    }
  }, [baseUrl, refresh]);

  const resetAnomaly = useCallback(async () => {
    setActionError(null);
    try {
      await postResetAnomaly(baseUrl);
      setWorkOrders([]);
      await refresh();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Reset failed");
      throw e;
    }
  }, [baseUrl, refresh]);

  const createWorkOrder = useCallback(async () => {
    setActionError(null);
    try {
      const firstAction = analyze?.recommended_actions?.[0];
      const created = await postCreateWorkOrder(baseUrl, {
        recommendation_id: firstAction?.id,
        action: firstAction?.action ?? "Inspect within 24 hours",
        assignee: "Maintenance Team",
        due: "Within 24 hours",
      });
      setWorkOrders((orders) => [created, ...orders.filter((order) => order.id !== created.id)]);
      await refresh();
      return created;
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Create work order failed");
      throw e;
    }
  }, [analyze, baseUrl, refresh]);

  const approveWorkOrder = useCallback(async (workOrderId: string) => {
    setActionError(null);
    try {
      const updated = await postApproveWorkOrder(baseUrl, workOrderId, {
        approved_by: "Shift Supervisor",
        note: "Approved from TwinOps frontend.",
      });
      setWorkOrders((orders) => orders.map((order) => (order.id === updated.id ? updated : order)));
      await refresh();
      return updated;
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Approve work order failed");
      throw e;
    }
  }, [baseUrl, refresh]);

  const dispatchWorkOrder = useCallback(async (workOrderId: string) => {
    setActionError(null);
    try {
      const updated = await postDispatchWorkOrder(baseUrl, workOrderId, {
        dispatched_by: "Maintenance Coordinator",
        note: "Dispatched from TwinOps frontend.",
      });
      setWorkOrders((orders) => orders.map((order) => (order.id === updated.id ? updated : order)));
      await refresh();
      return updated;
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Dispatch work order failed");
      throw e;
    }
  }, [baseUrl, refresh]);

  return {
    baseUrl,
    ready,
    pollError,
    actionError,
    clearActionError: () => setActionError(null),
    telemetry,
    digitalTwin,
    analyze,
    dashboard,
    alerts,
    reports,
    workOrders,
    assets,
    anomalyActive,
    refresh,
    triggerAnomaly,
    resetAnomaly,
    createWorkOrder,
    approveWorkOrder,
    dispatchWorkOrder,
  };
}
