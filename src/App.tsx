import { DigitalTwinImpactPanel } from "./components/DigitalTwinImpactPanel";
import { useMemo, useRef, useState, type ReactNode } from "react";
import type {
  AnalyzeApiResponse,
  AnalyzeRetrievedSop,
  ApiAlert,
  DashboardApiResponse,
  DigitalTwinApiResponse,
  ReportsApiResponse,
  TelemetryApiResponse,
  WorkOrderApiResponse,
} from "./api/types";
import { useTwinOpsBackend, parseConfidencePercent } from "./hooks/useTwinOpsBackend";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bell,
  BookOpen,
  Bot,
  Box,
  CalendarClock,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ClipboardCheck,
  Cpu,
  Database,
  ExternalLink,
  Factory,
  FileText,
  Gauge,
  GitBranch,
  Home,
  Info,
  Layers3,
  LineChart as LineChartIcon,
  ListChecks,
  Menu,
  Network,
  PanelLeft,
  RadioTower,
  RefreshCcw,
  Send,
  Shield,
  ShieldAlert,
  Sparkles,
  Thermometer,
  Timer,
  X,
  Wrench,
  Zap,
  type LucideIcon,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type {
  AgentStep,
  Alert,
  Asset,
  AssetStatus,
  AzureService,
  ExecutionLog,
  GeneratedWorkOrder,
  RecommendationAction,
  ReportMetric,
  RoadmapPhase,
} from "./types";

type AnomalyResult = {
  id?: string;
  machineId?: string;
  createdAt?: string;
  isAnomaly: boolean;
  severity: string;
  source?: string;
  agentTriggered?: boolean;
  cosmosSaved?: boolean;
  telemetry?: {
    vibration?: number | string;
    temperature?: number | string;
    load?: number | string;
    energyLoad?: number | string;
    status?: string;
  };
  contributingFactors?: Array<
    | string
    | {
        metric?: string;
        name?: string;
        value?: number | string;
        reason?: string;
        score?: number;
      }
  >;
};

type AnomalyFactor =
  | string
  | {
      metric?: string;
      name?: string;
      value?: number | string;
      reason?: string;
    };

function formatAnomalyFactors(factors?: AnomalyFactor[] | null): string {
  if (!factors || factors.length === 0) {
    return "none";
  }

  return factors
    .map((factor) => {
      if (typeof factor === "string") {
        return factor;
      }

      return factor.metric ?? factor.name ?? "unknown";
    })
    .join(", ");
}

type PageId = "dashboard" | "digital-twin" | "agents" | "recommendations" | "work-orders" | "reports";

const navItems: { id: PageId; label: string; icon: LucideIcon }[] = [
  { id: "dashboard", label: "Dashboard", icon: Home },
  { id: "digital-twin", label: "Digital Twin", icon: Network },
  { id: "agents", label: "Agents", icon: Bot },
  { id: "recommendations", label: "Recommendations", icon: Sparkles },
  { id: "work-orders", label: "Work Orders", icon: ClipboardCheck },
  { id: "reports", label: "Reports", icon: FileText },
];

const statusStyles: Record<AssetStatus, { label: string; dot: string; text: string; bg: string; border: string }> = {
  normal: {
    label: "Normal",
    dot: "bg-emerald-600",
    text: "text-emerald-700",
    bg: "bg-emerald-50",
    border: "border-emerald-200",
  },
  warning: {
    label: "Warning",
    dot: "bg-amber-500",
    text: "text-amber-700",
    bg: "bg-amber-50",
    border: "border-amber-200",
  },
  critical: {
    label: "Critical",
    dot: "bg-red-600",
    text: "text-red-700",
    bg: "bg-red-50",
    border: "border-red-200",
  },
  offline: {
    label: "Offline",
    dot: "bg-slate-400",
    text: "text-slate-500",
    bg: "bg-slate-100",
    border: "border-slate-200",
  },
};

const schematicSvgStyles: Record<AssetStatus, { fill: string; stroke: string; dot: string; statusText: string }> = {
  normal: { fill: "#f0fdf4", stroke: "#6ee7b7", dot: "#059669", statusText: "#047857" },
  warning: { fill: "#fffbeb", stroke: "#fcd34d", dot: "#d97706", statusText: "#b45309" },
  critical: { fill: "#fef2f2", stroke: "#f87171", dot: "#dc2626", statusText: "#b91c1c" },
  offline: { fill: "#f8fafc", stroke: "#cbd5e1", dot: "#94a3b8", statusText: "#64748b" },
};

const lineLayoutZones = [
  { kind: "buffer" as const, label: "Inbound", detail: "Buffer", x: 48, y: 132, w: 100, h: 148 },
  { kind: "buffer" as const, label: "Outbound", detail: "Buffer", x: 812, y: 132, w: 100, h: 148 },
];

const lineLayoutMachines = [
  { assetId: "motor-a", x: 198, y: 122, w: 136, h: 168 },
  { assetId: "motor-b", x: 404, y: 122, w: 136, h: 168 },
  { assetId: "conveyor-c", x: 590, y: 146, w: 188, h: 120 },
];

const energyData = [
  { time: "00:00", value: 320 },
  { time: "02:00", value: 440 },
  { time: "04:00", value: 380 },
  { time: "06:00", value: 410 },
  { time: "08:00", value: 625 },
  { time: "10:00", value: 590 },
  { time: "12:00", value: 560 },
  { time: "14:00", value: 690 },
  { time: "16:00", value: 540 },
  { time: "18:00", value: 590 },
  { time: "20:00", value: 470 },
  { time: "22:00", value: 390 },
];

const oeeData = [
  { day: "May 11", value: 79 },
  { day: "May 12", value: 82 },
  { day: "May 13", value: 85 },
  { day: "May 14", value: 86 },
  { day: "May 15", value: 88 },
  { day: "May 16", value: 87 },
  { day: "May 17", value: 87 },
];

const vibrationEvidence = [
  { day: "May 11", current: 1.1, baseline: 1.0 },
  { day: "May 12", current: 1.3, baseline: 1.1 },
  { day: "May 13", current: 1.2, baseline: 1.2 },
  { day: "May 14", current: 1.7, baseline: 1.3 },
  { day: "May 15", current: 2.2, baseline: 1.5 },
  { day: "May 16", current: 2.6, baseline: 1.7 },
  { day: "May 17", current: 3.6, baseline: 2.0 },
];

const temperatureEvidence = [
  { day: "May 11", current: 49, baseline: 48 },
  { day: "May 12", current: 52, baseline: 49 },
  { day: "May 13", current: 51, baseline: 50 },
  { day: "May 14", current: 56, baseline: 51 },
  { day: "May 15", current: 58, baseline: 52 },
  { day: "May 16", current: 62, baseline: 54 },
  { day: "May 17", current: 76, baseline: 55 },
];

const recommendationActions: RecommendationAction[] = [
  {
    id: "inspect",
    title: "Inspect within 24 hours",
    description: "Schedule inspection of Motor A bearings and related components.",
    impact: "High",
  },
  {
    id: "load",
    title: "Reduce operating load by 15%",
    description: "Temporarily reduce load to minimize stress and prevent further damage.",
    impact: "Medium",
  },
  {
    id: "work-order",
    title: "Create work order",
    description: "Generate and assign a work order to the maintenance team.",
    impact: "High",
  },
];

const azureServices: AzureService[] = [
  { id: "iot", name: "IoT Hub", status: "Connected", detail: "Telemetry ingress from PLC, OPC UA, and MQTT" },
  { id: "adt", name: "Azure Digital Twins", status: "Connected", detail: "Asset graph and dependency context" },
  { id: "fabric", name: "Microsoft Fabric", status: "Connected", detail: "Operational history and reporting lake" },
  { id: "foundry", name: "Foundry Agent Service", status: "Connected", detail: "Multi-agent orchestration and actions" },
];

const reportMetrics: ReportMetric[] = [
  { id: "downtime", label: "Downtime Reduction", value: "10-20%", detail: "ลด Unplanned Downtime", tone: "red" },
  { id: "energy", label: "Energy Reduction", value: "5-10%", detail: "ลด Energy Consumption", tone: "green" },
  { id: "oee", label: "Real-Time OEE", value: "Live", detail: "Visibility ระดับ Asset", tone: "blue" },
  { id: "triage", label: "Faster Triage", value: "AI", detail: "Response time ด้วย AI-assisted triage", tone: "orange" },
];

const roadmap: RoadmapPhase[] = [
  {
    id: "p1",
    title: "Phase 1 - Simulated dashboard",
    description: "Anomaly demo and executive visibility for one line.",
    risk: "Legacy tech isolated from pilot data.",
  },
  {
    id: "p2",
    title: "Phase 2 - Connect machines",
    description: "Azure IoT Hub connection with OPC UA or MQTT ingestion.",
    risk: "Secure gateway and telemetry validation required.",
  },
  {
    id: "p3",
    title: "Phase 3 - Train anomaly model",
    description: "Add RAG from SOPs, manuals, and historical maintenance logs.",
    risk: "AI hallucination managed with approval and source evidence.",
  },
  {
    id: "p4",
    title: "Phase 4 - Multi-line twin",
    description: "Scale dependency graph, work orders, and reporting across factories.",
    risk: "Cybersecurity via Azure Defender for IoT and Entra ID.",
  },
];

function mapApiAzureServices(services: DashboardApiResponse["azure_services"]): AzureService[] {
  return services.map((service) => ({
    id: service.id,
    name: service.name,
    status: service.status === "Connected" ? "Connected" : service.status === "Warning" ? "Warning" : "Connected",
    detail: service.detail,
  }));
}

function mapApiWorkOrder(order?: WorkOrderApiResponse | null): GeneratedWorkOrder | null {
  if (!order) return null;
  return {
    id: order.id,
    assetId: order.assetId === "motor-b" || order.assetId === "conveyor-c" ? order.assetId : "motor-a",
    assetName: order.assetName,
    priority: order.priority,
    status: order.status,
    assignee: order.assignee,
    due: order.due,
    title: order.title,
    checklist: order.checklist,
    history: [
      ...order.history,
      ...(order.dispatchStatus && order.dispatchStatus !== "Not dispatched"
        ? [{ time: "Backend", event: `Dispatch status: ${order.dispatchStatus}${order.externalSystem ? ` (${order.externalSystem})` : ""}` }]
        : []),
    ],
  };
}

function formatUsd(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(value % 1_000_000 === 0 ? 0 : 2)}M`;
  if (value >= 1_000) return `$${Math.round(value / 1_000)}K`;
  return `$${value}`;
}

function apiAlertToAlert(alert: ApiAlert): Alert {
  return {
    id: alert.id,
    title: alert.title,
    assetId: alert.assetId === "motor-b" || alert.assetId === "conveyor-c" ? alert.assetId : "motor-a",
    severity: alert.severity === "High" || alert.severity === "Medium" ? alert.severity : "Low",
    timestamp: alert.timestamp,
    details: alert.details,
    metrics: alert.metrics,
  };
}

export default function App() {
  const {
    baseUrl,
    pollError,
    actionError,
    clearActionError,
    telemetry,
    digitalTwin,
    analyze,
    agentsApi,
    dashboard,
    alerts,
    reports,
    workOrders,
    assets,
    anomalyActive,
    triggerAnomaly,
    resetAnomaly,
    runAgents,
    createWorkOrder,
    approveWorkOrder,
    dispatchWorkOrder,
    detectAnomaly,
    anomalyResults,
    latestAnomaly,
  } = useTwinOpsBackend(3000);

  const [activePage, setActivePage] = useState<PageId>("dashboard");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sidebarHidden, setSidebarHidden] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [currentWorkOrderId, setCurrentWorkOrderId] = useState<string | null>(null);
  const [currentWorkOrderStatus, setCurrentWorkOrderStatus] = useState<GeneratedWorkOrder["status"] | null>(null);
  const [workOrderActionBusy, setWorkOrderActionBusy] = useState(false);
  const demoActionSequence = useRef(0);

  
  // Agents API integration: prefer backend cascade data and keep local mock builders as a fallback.
  const agents = useMemo(() => (agentsApi ? agentsApi.agents.map(apiAgentToAgentStep) : buildAgents(anomalyActive)), [agentsApi, anomalyActive]);
  const activeAlert = useMemo(() => buildAlert(anomalyActive, telemetry, alerts?.alerts), [alerts, anomalyActive, telemetry]);
  const executionLog = useMemo(() => buildExecutionLog(anomalyActive), [anomalyActive]);
  const fallbackWorkOrder = useMemo(() => buildWorkOrder(anomalyActive ? "Awaiting approval" : "Draft"), [anomalyActive]);
  const currentApiWorkOrder = useMemo(
    () => workOrders.find((order) => order.id === currentWorkOrderId) ?? null,
    [currentWorkOrderId, workOrders],
  );
  const workOrder = useMemo(() => {
    const mapped = mapApiWorkOrder(currentApiWorkOrder);
    if (mapped) return currentWorkOrderStatus ? { ...mapped, status: currentWorkOrderStatus } : mapped;
    if (currentWorkOrderStatus) {
      return { ...fallbackWorkOrder, status: currentWorkOrderStatus };
    }
    return fallbackWorkOrder;
  }, [currentApiWorkOrder, currentWorkOrderStatus, fallbackWorkOrder]);
  const activeAlerts = dashboard?.alerts?.filter((alert) => alert.status === "Active").length ?? (anomalyActive ? 1 : 0);
  const averageHealth =
    dashboard?.asset_health?.length
      ? Math.round(dashboard.asset_health.reduce((sum, asset) => sum + asset.healthScore, 0) / dashboard.asset_health.length)
      : Math.round(assets.reduce((sum, asset) => sum + asset.healthScore, 0) / assets.length);

  const previewLineLabel =
    digitalTwin?.line_status === "Critical" ? "At Risk" : digitalTwin?.line_status === "Stable" ? "Stable" : anomalyActive ? "At Risk" : "Stable";
  const previewLineDanger = digitalTwin?.line_status === "Critical" || anomalyActive;

  async function simulateAnomaly() {
    const actionId = ++demoActionSequence.current;
    setCurrentWorkOrderId(null);
    setCurrentWorkOrderStatus("Awaiting approval");
    setActivePage("agents");

    try {
      await triggerAnomaly();
      if (actionId !== demoActionSequence.current) return;

      void detectAnomaly().catch(() => {
        /* useTwinOpsBackend sets actionError */
      });
    } catch {
      /* useTwinOpsBackend sets actionError */
    }
  }

  async function resetDemo() {
    demoActionSequence.current += 1;
      try {
        setCurrentWorkOrderId(null);
        setCurrentWorkOrderStatus(null);
        setWorkOrderActionBusy(false);
        await resetAnomaly();
      setActivePage("dashboard");
    } catch {
      /* useTwinOpsBackend sets actionError */
    }
  }

  async function runAgentCascade() {
    try {
      await runAgents();
      setActivePage("agents");
    } catch {
      /* useTwinOpsBackend sets actionError */
    }
  }

  async function approveAction() {
    if (workOrderActionBusy) return;
    setWorkOrderActionBusy(true);
    setCurrentWorkOrderStatus("Approved");
    setActivePage("work-orders");

    try {
      const existingCurrent = currentWorkOrderId ? workOrders.find((order) => order.id === currentWorkOrderId) : undefined;
      const current =
        existingCurrent && (existingCurrent.status === "Draft" || existingCurrent.status === "Awaiting approval")
          ? existingCurrent
          : await createWorkOrder();
      setCurrentWorkOrderId(current.id);
      setCurrentWorkOrderStatus("Approved");
      setActivePage("work-orders");
      const approved = await approveWorkOrder(current.id);
      setCurrentWorkOrderId(approved.id);
      setCurrentWorkOrderStatus("Approved");
    } catch {
      setCurrentWorkOrderStatus(anomalyActive ? "Awaiting approval" : null);
      /* useTwinOpsBackend sets actionError */
    } finally {
      setWorkOrderActionBusy(false);
    }
  }

  async function sendToMaintenance() {
    if (workOrderActionBusy) return;
    setWorkOrderActionBusy(true);
    setCurrentWorkOrderStatus("Dispatched");
    setActivePage("work-orders");

    try {
      const existingCurrent = currentWorkOrderId ? workOrders.find((order) => order.id === currentWorkOrderId) : undefined;
      const current =
        existingCurrent ??
        await createWorkOrder();
      setCurrentWorkOrderId(current.id);
      setCurrentWorkOrderStatus("Dispatched");
      setActivePage("work-orders");
      const approved = current.status === "Approved" ? current : await approveWorkOrder(current.id);
      setCurrentWorkOrderId(approved.id);
      const dispatched = await dispatchWorkOrder(approved.id);
      setCurrentWorkOrderId(dispatched.id);
      setCurrentWorkOrderStatus("Dispatched");
    } catch {
      setCurrentWorkOrderStatus(anomalyActive ? "Approved" : null);
      /* useTwinOpsBackend sets actionError */
    } finally {
      setWorkOrderActionBusy(false);
    }
  }

  async function openWorkOrder() {
    if (!currentWorkOrderId && anomalyActive) {
      try {
        const created = await createWorkOrder();
        setCurrentWorkOrderId(created.id);
        setCurrentWorkOrderStatus(created.status);
      } catch {
        /* useTwinOpsBackend sets actionError */
      }
    }
    navigateToPage("work-orders");
  }

  function navigateToPage(page: PageId) {
    setActivePage(page);
    setMobileSidebarOpen(false);
    setNotificationsOpen(false);
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-950">
      <TopBar
        anomalyActive={anomalyActive}
        notificationsOpen={notificationsOpen}
        sidebarHidden={sidebarHidden}
        onToggleMobileSidebar={() => {
          setMobileSidebarOpen((open) => !open);
          setNotificationsOpen(false);
        }}
        onToggleSidebarHidden={() => {
          setSidebarHidden((hidden) => !hidden);
          setMobileSidebarOpen(false);
          setNotificationsOpen(false);
        }}
        onToggleNotifications={() => {
          setNotificationsOpen((open) => !open);
          setMobileSidebarOpen(false);
        }}
        onSimulate={simulateAnomaly}
        onReset={resetDemo}
      />
      <div className="flex min-h-[calc(100vh-76px)]">
        <Sidebar
          activePage={activePage}
          collapsed={sidebarCollapsed}
          hidden={sidebarHidden}
          onNavigate={navigateToPage}
          onToggle={() => setSidebarCollapsed((collapsed) => !collapsed)}
        />
        <MobileSidebar activePage={activePage} open={mobileSidebarOpen} onClose={() => setMobileSidebarOpen(false)} onNavigate={navigateToPage} />
        <main className="flex-1 overflow-hidden pb-14">
          <div className="mx-auto w-full max-w-[1580px] px-4 py-5 sm:px-6 lg:px-7">
            {pollError ? (
              <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
                Cannot reach backend ({pollError}). Charts may show fallback values until the API at{" "}
                <code className="rounded bg-amber-100/80 px-1">{import.meta.env.VITE_API_BASE_URL || "(Vite proxy → :8000)"}</code> is available.
              </div>
            ) : null}
            {actionError ? (
              <div className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900">
                <span>{actionError}</span>
                <button type="button" onClick={clearActionError} className="font-medium text-red-700 underline">
                  Dismiss
                </button>
              </div>
            ) : null}
            {activePage === "dashboard" ? (
              <DashboardPage
                assets={assets}
                anomalyActive={anomalyActive}
                averageHealth={averageHealth}
                activeAlerts={activeAlerts}
                telemetryTimestamp={telemetry?.timestamp ?? null}
                dashboard={dashboard}
                previewLineLabel={previewLineLabel}
                previewLineDanger={previewLineDanger}
                latestAnomaly={latestAnomaly}
                anomalyResults={anomalyResults}
                onNavigate={navigateToPage}
              />
            ) : null}
            {activePage === "digital-twin" ? (
              <DigitalTwinPage
                baseUrl={baseUrl}
                assets={assets}
                alert={activeAlert}
                anomalyActive={anomalyActive}
                twin={digitalTwin}
                />
            ) : null}
            {activePage === "agents" ? <AgentsPage agents={agents} executionLog={executionLog} anomalyActive={anomalyActive} agentsApiMode={agentsApi?.mode ?? "local-fallback"} onRunCascade={runAgentCascade} /> : null}
            {activePage === "recommendations" ? (
              <RecommendationsPage
                anomalyActive={anomalyActive}
                analyze={analyze}
                telemetryTimestamp={telemetry?.timestamp ?? null}
                workOrder={workOrder}
                onApprove={approveAction}
                onSendToMaintenance={sendToMaintenance}
                onOpenWorkOrder={openWorkOrder}
                actionBusy={workOrderActionBusy}
              />
            ) : null}
            {activePage === "work-orders" ? (
              <WorkOrdersPage workOrder={workOrder} workOrders={workOrders.map(mapApiWorkOrder).filter((order): order is GeneratedWorkOrder => Boolean(order))} onApprove={approveAction} onSendToMaintenance={sendToMaintenance} actionBusy={workOrderActionBusy} />
            ) : null}
            {activePage === "reports" ? <ReportsPage reports={reports} /> : null}
          </div>
        </main>
      </div>
      <NotificationPanel
        open={notificationsOpen}
        anomalyActive={anomalyActive}
        sidebarCollapsed={sidebarCollapsed}
        sidebarHidden={sidebarHidden}
        onClose={() => setNotificationsOpen(false)}
        onNavigate={navigateToPage}
      />
      <DemoFooter sidebarCollapsed={sidebarCollapsed} sidebarHidden={sidebarHidden} backendConnected={!pollError} />
    </div>
  );
}

function TopBar({
  anomalyActive,
  notificationsOpen,
  sidebarHidden,
  onToggleMobileSidebar,
  onToggleSidebarHidden,
  onToggleNotifications,
  onSimulate,
  onReset,
}: {
  anomalyActive: boolean;
  notificationsOpen: boolean;
  sidebarHidden: boolean;
  onToggleMobileSidebar: () => void;
  onToggleSidebarHidden: () => void;
  onToggleNotifications: () => void;
  onSimulate: () => void;
  onReset: () => void;
}) {
  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="flex h-[76px] items-center justify-between gap-4 px-4 sm:px-6">
        <div className="flex min-w-0 items-center gap-3">
          <button type="button" onClick={onToggleMobileSidebar} className="icon-button lg:hidden" aria-label="Open navigation">
            <Menu className="h-5 w-5" />
          </button>
          <button
            type="button"
            onClick={onToggleSidebarHidden}
            className={`icon-button hidden lg:inline-flex ${sidebarHidden ? "bg-blue-50 text-blue-700" : ""}`}
            aria-label={sidebarHidden ? "Show sidebar" : "Hide sidebar"}
          >
            <PanelLeft className="h-5 w-5" />
          </button>
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-white shadow-sm">
            <Factory className="h-6 w-6" />
          </div>
          <div className="min-w-0">
            <h1 className="truncate text-xl font-semibold text-slate-950 sm:text-2xl">SmartFactory TwinOps AI</h1>
            <p className="hidden text-xs text-slate-500 sm:block">Industrial Digital Transformation with AI and Microsoft Azure</p>
          </div>
          <span className="hidden items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm font-medium text-blue-700 md:inline-flex">
            <span className="h-2 w-2 rounded-full bg-blue-600" />
            Demo Mode
          </span>
        </div>

        <div className="flex shrink-0 items-center gap-2 sm:gap-3">
          <button type="button" onClick={onToggleNotifications} className={`icon-button relative ${notificationsOpen ? "bg-blue-50 text-blue-700" : ""}`} aria-label="Notifications">
            <Bell className="h-5 w-5" />
            <span className="absolute right-2 top-2 h-2.5 w-2.5 rounded-full border-2 border-white bg-red-500" />
          </button>
          {anomalyActive ? (
            <button type="button" onClick={onReset} className="secondary-button hidden sm:inline-flex">
              <RefreshCcw className="h-4 w-4" />
              Reset
            </button>
          ) : null}
          <button type="button" onClick={onSimulate} className="primary-button">
            <Zap className="h-5 w-5" />
            <span className="hidden sm:inline">Simulate Anomaly</span>
          </button>
        </div>
      </div>
    </header>
  );
}

function Sidebar({
  activePage,
  collapsed,
  hidden: sidebarHidden,
  onNavigate,
  onToggle,
}: {
  activePage: PageId;
  collapsed: boolean;
  hidden: boolean;
  onNavigate: (page: PageId) => void;
  onToggle: () => void;
}) {
  return (
    <aside
      className={`shrink-0 border-r border-slate-200 bg-white transition-[width] duration-200 ${sidebarHidden ? "hidden" : "hidden lg:flex lg:flex-col"} ${collapsed ? "w-[76px]" : "w-[256px]"}`}
    >
      <nav className="flex-1 space-y-2 px-3 py-8">
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = activePage === item.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onNavigate(item.id)}
              className={`nav-item ${active ? "nav-item-active" : ""} ${collapsed ? "justify-center px-3" : ""}`}
              title={item.label}
            >
              <Icon className="h-5 w-5" />
              {collapsed ? null : item.label}
            </button>
          );
        })}
      </nav>
      <div className="border-t border-slate-200 p-4">
        <button type="button" onClick={onToggle} className={`flex items-center gap-3 text-sm font-medium text-slate-600 ${collapsed ? "justify-center" : ""}`}>
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          {collapsed ? null : "Collapse"}
        </button>
      </div>
    </aside>
  );
}

function MobileSidebar({
  activePage,
  open,
  onClose,
  onNavigate,
}: {
  activePage: PageId;
  open: boolean;
  onClose: () => void;
  onNavigate: (page: PageId) => void;
}) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-label="Navigation">
      <button type="button" className="absolute inset-0 bg-slate-900/30" onClick={onClose} aria-label="Close navigation" />
      <aside className="absolute left-0 top-0 flex h-full w-[min(300px,calc(100vw-48px))] flex-col border-r border-slate-200 bg-white shadow-2xl">
        <div className="flex h-[76px] items-center justify-between border-b border-slate-200 px-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600 text-white">
              <Factory className="h-6 w-6" />
            </div>
            <div>
              <p className="font-semibold text-slate-950">SmartFactory</p>
              <p className="text-xs text-slate-500">Navigation</p>
            </div>
          </div>
          <button type="button" onClick={onClose} className="icon-button h-9 w-9" aria-label="Close navigation">
            <X className="h-4 w-4" />
          </button>
        </div>
        <nav className="flex-1 space-y-2 overflow-y-auto px-3 py-5">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = activePage === item.id;
            return (
              <button key={item.id} type="button" onClick={() => onNavigate(item.id)} className={`nav-item ${active ? "nav-item-active" : ""}`}>
                <Icon className="h-5 w-5" />
                {item.label}
              </button>
            );
          })}
        </nav>
      </aside>
    </div>
  );
}

function PageHeader({
  title,
  subtitle,
  aside,
}: {
  title: string;
  subtitle: string;
  aside?: ReactNode;
}) {
  return (
    <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <h2 className="text-2xl font-semibold text-slate-950 sm:text-3xl">{title}</h2>
        <p className="mt-1 text-sm text-slate-600">{subtitle}</p>
      </div>
      {aside}
    </div>
  );
}

function DashboardPage({
  assets,
  anomalyActive,
  averageHealth,
  activeAlerts,
  telemetryTimestamp,
  dashboard,
  previewLineLabel,
  previewLineDanger,
  latestAnomaly,
  anomalyResults,
  onNavigate,
}: {
  assets: Asset[];
  anomalyActive: boolean;
  averageHealth: number;
  activeAlerts: number;
  telemetryTimestamp: string | null;
  dashboard: DashboardApiResponse | null;
  previewLineLabel: string;
  previewLineDanger: boolean;
  latestAnomaly: AnomalyResult | null;
  anomalyResults: AnomalyResult[];
  onNavigate: (page: PageId) => void;
}) {
  const kpiMap = new Map(dashboard?.kpis?.map((kpi) => [kpi.id, kpi]));
  const healthValue = kpiMap.get("line-health")?.value.replace(/[^\d]/g, "") || `${averageHealth}`;
  const energyValue = dashboard?.energy?.current_kw ? `${dashboard.energy.current_kw}` : kpiMap.get("energy")?.value.replace(/[^\d]/g, "") || "428";
  const oeeValue = dashboard?.oee?.current ? `${dashboard.oee.current}` : kpiMap.get("oee")?.value.replace(/[^\d]/g, "") || (anomalyActive ? "82" : "87");
  const dashboardEnergyData = dashboard?.energy?.history?.length ? dashboard.energy.history : energyData;
  const dashboardOeeData = dashboard?.oee?.history?.length ? dashboard.oee.history : oeeData;
  const serviceItems = dashboard?.azure_services?.length ? mapApiAzureServices(dashboard.azure_services) : azureServices;

  return (
    <div>
      <div className="grid items-start gap-4 xl:grid-cols-[1fr_368px]">
        <div className="space-y-4">
          <section className="grid self-start gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard title="Overall Health Score" value={healthValue} suffix="/100" detail={kpiMap.get("line-health")?.status ?? (anomalyActive ? "Needs action" : "Excellent")} tone={anomalyActive ? "red" : "green"} icon={Activity} />
            <KpiCard title="Energy Usage" value={energyValue} suffix="kW" detail={kpiMap.get("energy")?.trend ?? "Backend summary"} tone="blue" icon={Zap} />
            <KpiCard title="OEE" value={oeeValue} suffix="%" detail={kpiMap.get("oee")?.trend ?? "Backend summary"} tone="purple" icon={BarChart3} />
            <KpiCard title="Active Alerts" value={`${activeAlerts}`} detail={kpiMap.get("alerts")?.status ?? (activeAlerts ? "Motor A requires review" : "All systems normal")} tone="orange" icon={Bell} />
          </section>

        {latestAnomaly && (
          <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-slate-500">
                Azure ML Anomaly Detection
                </p>
                <h3 className="text-lg font-semibold text-slate-900">
                  {latestAnomaly.isAnomaly ? "Anomaly Detected" : "Normal Operation"}
                </h3>
              </div>

              <span className="rounded-full bg-slate-100 px-3 py-1 text-sm font-medium text-slate-700">
                  {latestAnomaly.severity}
              </span>
              </div>

    <div className="mt-3 space-y-1 text-sm text-slate-600">
      <p>Machine: {latestAnomaly.machineId ?? "motor-A"}</p>
      <p>Cosmos records: {anomalyResults.length}</p>

  <div className="mt-3 grid grid-cols-3 gap-2 rounded-xl bg-slate-50 p-3 text-xs text-slate-600">
  <div>
    <p className="font-medium text-slate-500">Temperature</p>
    <p>{latestAnomaly.telemetry?.temperature ?? "-"} °C</p>
  </div>

  <div>
    <p className="font-medium text-slate-500">Vibration</p>
    <p>{latestAnomaly.telemetry?.vibration ?? "-"}</p>
  </div>

  <div>
    <p className="font-medium text-slate-500">Energy Load</p>
    <p>{latestAnomaly.telemetry?.load ?? latestAnomaly.telemetry?.energyLoad ?? "-"}%</p>
  </div>
</div>

      {(latestAnomaly.contributingFactors ?? []).length > 0 ? (
  <div className="mt-2">
    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
      Factors:
    </p>

    <ul className="mt-1 space-y-1 text-sm text-slate-700">
      {(latestAnomaly.contributingFactors ?? []).map((factor, index) => {
        if (typeof factor === "string") {
          return <li key={index}>• {factor}</li>;
        }

        const name = factor.metric ?? factor.name ?? "unknown";
        const value = factor.value ?? "-";
        const reason = factor.reason ?? "";

        return (
          <li key={index}>
            • {name}: {value}
            {reason ? ` — ${reason}` : ""}
          </li>
        );
      })}
    </ul>
  </div>
) : (
  <p>Factors: none</p>
)}
    </div>
  </section>
)}

          <section className="grid self-start gap-4 xl:grid-cols-3">
            {assets.map((asset) => (
              <AssetHealthCard key={asset.id} asset={asset} />
            ))}
          </section>

          <section className="grid gap-4 xl:grid-cols-[1.1fr_1fr_1.1fr]">
            <ChartPanel title="Energy Usage Over Time (kWh)" subtitle="24 Hours">
              <ResponsiveContainer width="100%" height={230}>
                <AreaChart data={dashboardEnergyData} margin={{ left: -20, right: 8, top: 8, bottom: 0 }}>
                  <CartesianGrid stroke="#E5E7EB" strokeDasharray="3 3" />
                  <XAxis dataKey="time" tick={{ fontSize: 11 }} stroke="#64748B" />
                  <YAxis tick={{ fontSize: 11 }} stroke="#64748B" />
                  <Tooltip contentStyle={{ borderRadius: 8, borderColor: "#DBEAFE" }} />
                  <Area type="monotone" dataKey="value" stroke="#2563EB" fill="#DBEAFE" strokeWidth={2.5} name="Energy Usage" />
                </AreaChart>
              </ResponsiveContainer>
            </ChartPanel>

            <ChartPanel title="OEE Trend (%)" subtitle="7 Days">
              <ResponsiveContainer width="100%" height={230}>
                <BarChart data={dashboardOeeData} margin={{ left: -20, right: 8, top: 8, bottom: 0 }}>
                  <CartesianGrid stroke="#E5E7EB" strokeDasharray="3 3" />
                  <XAxis dataKey="day" tick={{ fontSize: 10 }} stroke="#64748B" />
                  <YAxis tick={{ fontSize: 11 }} stroke="#64748B" />
                  <Tooltip contentStyle={{ borderRadius: 8, borderColor: "#DBEAFE" }} />
                  <Bar dataKey="value" fill="#BFDBFE" radius={[4, 4, 0, 0]} name="OEE" />
                  <Line type="monotone" dataKey="value" stroke="#2563EB" strokeWidth={2} />
                </BarChart>
              </ResponsiveContainer>
            </ChartPanel>

            <LatestTelemetry assets={assets} latestTimestamp={telemetryTimestamp} />
          </section>
        </div>

        <div className="space-y-4">
          <DigitalTwinPreview
            assets={assets}
            lineStatusLabel={previewLineLabel}
            lineStatusDanger={previewLineDanger}
            onOpen={() => onNavigate("digital-twin")}
          />
          <AzureServicesPanel services={serviceItems} />
        </div>
      </div>
    </div>
  );
}

function downstreamDetailToStatus(detail: string): AssetStatus {
  const lower = detail.toLowerCase();
  if (lower.includes("critical")) return "critical";
  if (lower.includes("risk") || lower.includes("warning") || lower.includes("reduced")) return "warning";
  return "normal";
}

function DigitalTwinPage({
  baseUrl,
  assets,
  alert,
  anomalyActive,
  twin,
}: {
  baseUrl: string;
  assets: Asset[];
  alert: Alert;
  anomalyActive: boolean;
  twin: DigitalTwinApiResponse | null;
}) {
  const lineLabel = twin?.line_status === "Critical" ? "At Risk" : twin?.line_status === "Stable" ? "Stable" : anomalyActive ? "At Risk" : "Stable";
  const lineDanger = twin?.line_status === "Critical" || anomalyActive;
  const failureRisk = twin?.failure_risk ?? (anomalyActive ? "High" : "Low");
  const affectedAsset = twin?.affected_asset ?? (anomalyActive ? "Motor A" : "None");
  const potentialImpact =
    twin?.potential_impact ?? (anomalyActive ? "Line 1 throughput degradation" : "Normal production");
  const conveyorDetail = twin?.downstream_impact?.Conveyor_C ?? (anomalyActive ? "Warning" : "Normal");
  const motorBDetail = twin?.downstream_impact?.Motor_B ?? "Normal";
  const conveyorStatus = downstreamDetailToStatus(conveyorDetail);
  const motorBStatus = downstreamDetailToStatus(motorBDetail);

  return (
    <div>
      <PageHeader
        title="Plant Digital Twin"
        subtitle="Real-time digital representation of your production line - ภาพรวมสถานะโรงงานแบบ Real-time"
        aside={
          <div className="text-sm text-slate-600">
            Line Status:{" "}
            <span className={lineDanger ? "font-semibold text-red-700" : "font-semibold text-emerald-700"}>{lineLabel}</span>
            <span className={`ml-2 inline-block h-2.5 w-2.5 rounded-full ${lineDanger ? "bg-red-600" : "bg-emerald-600"}`} />
          </div>
        }
      />

      <section className="panel mb-4 grid gap-4 p-5 md:grid-cols-3">
        <SummaryStrip
          icon={AlertTriangle}
          label="Failure Risk"
          value={failureRisk}
          tone={failureRisk === "High" ? "red" : failureRisk === "Medium" ? "orange" : "green"}
        />
        <SummaryStrip icon={Cpu} label="Affected Asset" value={affectedAsset} tone={affectedAsset !== "None" ? "red" : "blue"} />
        <SummaryStrip icon={LineChartIcon} label="Potential Impact" value={potentialImpact.length > 56 ? `${potentialImpact.slice(0, 53)}…` : potentialImpact} tone="orange" />
      </section>

      <div className="grid gap-4 xl:grid-cols-[1fr_408px]">
        <section className="panel overflow-hidden">
          <PlantMap assets={assets} large />
          <StatusLegend />
        </section>

        <div className="space-y-4">
          <AlertDetails alert={alert} anomalyActive={anomalyActive} />
          <section className="panel p-5">
            <h3 className="section-title">Dependency Impact</h3>
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <DependencyNode label="Motor A" detail={anomalyActive ? "Critical" : "Normal"} status={anomalyActive ? "critical" : "normal"} />
              <ArrowConnector label="drives flow" />
              <DependencyNode label="Motor B" detail={motorBDetail} status={motorBStatus} />
              <ArrowConnector label="to conveyor" />
              <DependencyNode label="Conveyor C" detail={conveyorDetail} status={conveyorStatus} />
              <ArrowConnector label="feeds output" />
              <DependencyNode
                label="Line 1 Output Buffer"
                detail={anomalyActive ? "Warning" : "Normal"}
                status={anomalyActive ? "warning" : "normal"}
              />
            </div>
            <p className="mt-4 text-sm leading-6 text-slate-600">{potentialImpact}</p>
          </section>
        </div>
      </div>

            <div className="mt-4">
        <DigitalTwinImpactPanel baseUrl={baseUrl} />
      </div>
    </div>
  );
}

function AgentsPage({
  agents,
  executionLog,
  anomalyActive,
  agentsApiMode,
  onRunCascade,
}: {
  agents: AgentStep[];
  executionLog: ExecutionLog[];
  anomalyActive: boolean;
  agentsApiMode: string;
  onRunCascade: () => void;
}) {
  return (
    <div>
      <PageHeader
        title="Multi-Agent Cascade"
        subtitle="AI agents collaborate in sequence to detect, analyze, and recommend actions - Agent ทำงานเป็นลำดับเพื่อเปลี่ยนข้อมูลเป็น Action"
        aside={<OrchestrationCard agentsApiMode={agentsApiMode} onRunCascade={onRunCascade} />}
      />

      <div className="grid gap-5 xl:grid-cols-[1fr_340px]">
        <section>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
            {agents.map((agent, index) => (
              <AgentCard key={agent.id} agent={agent} isActive={agent.status === "in-progress"} showConnector={index < agents.length - 1} />
            ))}
          </div>
          <section className="panel mt-5 p-4">
            <div className="flex flex-wrap justify-center gap-5 text-sm text-slate-600">
              <LegendItem color="bg-emerald-600" label="Completed" />
              <LegendItem color="bg-violet-600" label="In Progress" ring />
              <LegendItem color="bg-white border border-slate-400" label="Pending" />
              <LegendItem color="bg-white border border-dashed border-slate-400" label="Not Started" />
            </div>
          </section>
          <CascadeSummary anomalyActive={anomalyActive} />
        </section>

        <ExecutionLogPanel logs={executionLog} />
      </div>
    </div>
  );
}

function parseAnalyzeImpact(impact: string): RecommendationAction["impact"] {
  const x = impact.toLowerCase();
  if (x.includes("high")) return "High";
  if (x.includes("medium")) return "Medium";
  return "Low";
}

function analyzeToRecommendationActions(data: AnalyzeApiResponse): RecommendationAction[] {
  return data.recommended_actions.map((a) => ({
    id: `action-${a.id}`,
    title: a.action,
    description: "Returned from backend GET /api/analyze",
    impact: parseAnalyzeImpact(a.impact),
  }));
}

function RecommendationsPage({
  anomalyActive,
  analyze,
  telemetryTimestamp,
  workOrder,
  onApprove,
  onSendToMaintenance,
  onOpenWorkOrder,
  actionBusy,
}: {
  anomalyActive: boolean;
  analyze: AnalyzeApiResponse | null;
  telemetryTimestamp: string | null;
  workOrder: GeneratedWorkOrder;
  onApprove: () => void;
  onSendToMaintenance: () => void;
  onOpenWorkOrder: () => void;
  actionBusy: boolean;
}) {
  const insightTitle = analyze?.insight ?? (anomalyActive ? "Likely bearing wear" : "No active anomaly");
  const confidencePct = analyze ? parseConfidencePercent(analyze.confidence_score) : anomalyActive ? 87 : 12;
  const riskSubtitle = analyze?.risk_level ? `${analyze.risk_level} risk` : anomalyActive ? "High confidence" : "Low risk";

  const actions =
    anomalyActive && analyze && analyze.recommended_actions.length > 0
      ? analyzeToRecommendationActions(analyze)
      : anomalyActive
        ? recommendationActions
        : [];

  return (
    <div>
      <PageHeader
        title="AI Recommendation & Action"
        subtitle="AI insights, recommended actions, and automated work order generation - คำแนะนำ AI พร้อมหลักฐานและ Human Approval"
      />

      <div className="grid gap-5 xl:grid-cols-[1fr_440px]">
        <div className="space-y-4">
          <section className={`panel p-5 ${anomalyActive ? "border-red-200 bg-red-50/55" : "border-slate-200 bg-slate-50/60"}`}>
            <div className="grid gap-4 md:grid-cols-[96px_1fr_240px] md:items-center">
              <div
                className={`flex h-20 w-20 items-center justify-center rounded-lg ${anomalyActive ? "bg-red-100 text-red-600" : "bg-slate-100 text-slate-500"}`}
              >
                <ShieldAlert className="h-12 w-12" />
              </div>
              <div>
                <p className="flex items-center gap-2 text-sm font-semibold text-blue-700">
                  <Sparkles className="h-4 w-4" />
                  AI Insight
                </p>
                <h3 className="mt-2 text-3xl font-semibold text-slate-950">{insightTitle}</h3>
                <p className="mt-2 text-sm text-slate-600">Motor A — last telemetry sample {telemetryTimestamp ?? "—"}</p>
              </div>
              <div>
                <div className="flex items-center gap-2 text-sm text-slate-600">
                  Confidence Score
                  <Info className="h-4 w-4" />
                </div>
                <p className={`mt-2 text-4xl font-semibold ${anomalyActive ? "text-red-600" : "text-slate-600"}`}>{analyze?.confidence_score ?? `${confidencePct}%`}</p>
                <div className="mt-3 h-2 rounded-lg bg-slate-200">
                  <div
                    className={`h-2 rounded-lg ${anomalyActive ? "bg-red-600" : "bg-slate-400"}`}
                    style={{ width: `${confidencePct}%` }}
                  />
                </div>
                <p className="mt-2 text-sm text-slate-600">{riskSubtitle}</p>
              </div>
            </div>
          </section>

          <section className="panel p-5">
            <h3 className="section-title">
              <Sparkles className="h-5 w-5 text-blue-600" />
              Recommended Actions
            </h3>
            <div className="mt-4 space-y-3">
              {actions.length > 0 ? (
                actions.map((action, index) => <ActionRow key={action.id} action={action} order={index + 1} />)
              ) : (
                <p className="text-sm text-slate-600">No recommended actions while the line has no active anomaly.</p>
              )}
            </div>
          </section>
        </div>

        <GeneratedWorkOrderPanel workOrder={workOrder} onOpenWorkOrder={onOpenWorkOrder} />
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-3">
        <EvidenceChart title="Evidence: Vibration Spike" metric="Motor A - Vibration (mm/s RMS)" data={vibrationEvidence} accent="#2563EB" highlight="+78%" />
        <EvidenceChart title="Evidence: Temperature Spike" metric="Motor A - Temperature (C)" data={temperatureEvidence} accent="#EF4444" highlight="+15C" />
        <SopPanel sop={analyze?.retrieved_sop} />
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1fr_1.1fr]">
        <section className="panel p-5">
          <h3 className="section-title">
            <AlertTriangle className="h-5 w-5 text-amber-500" />
            Safety & Approval Reminder
          </h3>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            Ensure lockout/tagout procedures are followed before inspection. Approval from supervisor required before dispatch.
          </p>
        </section>
        <section className="panel grid gap-3 p-5 sm:grid-cols-3">
          <button type="button" onClick={onApprove} disabled={actionBusy} className="primary-button justify-center disabled:cursor-not-allowed disabled:opacity-60">
            <Check className="h-5 w-5" />
            Approve Action
          </button>
          <button type="button" onClick={onSendToMaintenance} disabled={actionBusy} className="secondary-button justify-center disabled:cursor-not-allowed disabled:opacity-60">
            <Send className="h-5 w-5" />
            Send to Maintenance
          </button>
          <button type="button" onClick={onOpenWorkOrder} className="secondary-button justify-center">
            <ClipboardCheck className="h-5 w-5" />
            Open Work Order
          </button>
        </section>
      </div>

      <RecommendationActionResult status={workOrder.status} />
    </div>
  );
}

function WorkOrdersPage({
  workOrder,
  workOrders,
  onApprove,
  onSendToMaintenance,
  actionBusy,
}: {
  workOrder: GeneratedWorkOrder;
  workOrders: GeneratedWorkOrder[];
  onApprove: () => void;
  onSendToMaintenance: () => void;
  actionBusy: boolean;
}) {
  const queue = workOrders.length > 0 ? workOrders : [workOrder];
  const openCount = queue.filter((order) => order.status !== "Dispatched").length;

  return (
    <div>
      <PageHeader
        title="Work Orders"
        subtitle="Maintenance execution queue generated from AI recommendations - งานซ่อมบำรุงจาก AI พร้อมสถานะอนุมัติ"
        aside={<StatusPill label={workOrder.status} tone={workOrder.status === "Dispatched" ? "green" : workOrder.status === "Approved" ? "blue" : "orange"} />}
      />

      <div className="grid gap-5 xl:grid-cols-[360px_1fr]">
        <section className="panel p-4">
          <div className="flex items-center justify-between">
            <h3 className="section-title">Queue</h3>
            <span className="text-sm text-slate-500">{openCount} open</span>
          </div>
          <div className="mt-4 space-y-3">
            {queue.map((order) => (
              <button key={order.id} type="button" className={`w-full rounded-lg border p-4 text-left ${order.id === workOrder.id ? "border-blue-200 bg-blue-50" : "border-slate-200 bg-white"}`}>
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-950">{order.id}</span>
                  <StatusPill label={order.priority} tone={order.priority === "High" ? "red" : order.priority === "Medium" ? "orange" : "blue"} />
                </div>
                <p className="mt-2 text-sm font-medium text-slate-700">{order.title}</p>
                <p className="mt-1 text-sm text-slate-500">{order.assetName} - {order.due}</p>
              </button>
            ))}
          </div>
        </section>

        <section className="panel p-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <h3 className="text-2xl font-semibold text-slate-950">{workOrder.title}</h3>
              <p className="mt-1 text-sm text-slate-600">{workOrder.id}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button type="button" onClick={onApprove} disabled={actionBusy} className="secondary-button disabled:cursor-not-allowed disabled:opacity-60">
                <Check className="h-4 w-4" />
                Approve
              </button>
              <button type="button" onClick={onSendToMaintenance} disabled={actionBusy} className="primary-button disabled:cursor-not-allowed disabled:opacity-60">
                <Send className="h-4 w-4" />
                Dispatch
              </button>
            </div>
          </div>

          <div className="mt-5 grid gap-4 md:grid-cols-4">
            <InfoTile label="Asset" value={workOrder.assetName} />
            <InfoTile label="Priority" value={workOrder.priority} />
            <InfoTile label="Assignee" value={workOrder.assignee} />
            <InfoTile label="Due" value={workOrder.due} />
          </div>

          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            <div>
              <h4 className="font-semibold text-slate-950">Maintenance Checklist</h4>
              <div className="mt-3 space-y-3">
                {workOrder.checklist.map((item) => (
                  <div key={item} className="flex items-start gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
                    <ListChecks className="mt-0.5 h-4 w-4 text-blue-600" />
                    <span className="text-sm text-slate-700">{item}</span>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <h4 className="font-semibold text-slate-950">Action History</h4>
              <div className="mt-3 space-y-3">
                {workOrder.history.map((event) => (
                  <div key={`${event.time}-${event.event}`} className="flex gap-3">
                    <div className="mt-1 h-2.5 w-2.5 rounded-full bg-blue-600" />
                    <div>
                      <p className="text-sm font-medium text-slate-800">{event.event}</p>
                      <p className="text-xs text-slate-500">{event.time}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

function ReportsPage({ reports }: { reports: ReportsApiResponse | null }) {
  const metrics = reports?.business_value?.metrics ?? reportMetrics;
  const roiSummary = reports?.roi?.summary;
  const roiAssumptions = reports?.roi?.assumptions ?? [
    { driver: "Unplanned downtime", assumption: "10-20% reduction from predictive maintenance", annualImpact: 1350000 },
    { driver: "Energy waste", assumption: "5-10% reduction from load and anomaly insight", annualImpact: 310000 },
    { driver: "Manual triage delay", assumption: "Agent-assisted RCA with SOP evidence", annualImpact: 180000 },
  ];
  const painPoints = reports?.business_value?.pain_point_mapping ?? [
    { problem: "Limited risk visibility", response: "Line Health & Risk Summary", kpi: "OEE, Downtime" },
    { problem: "Too many alarms and slow root-cause analysis", response: "Likely Cause and Evidence", kpi: "MTTR, MTBF" },
    { problem: "Siloed machine data", response: "Digital Twin Dependency", kpi: "Line Throughput" },
    { problem: "Manual SOP search", response: "RAG-based recommendations", kpi: "Faster Triage" },
  ];
  const architectureFlow = reports?.azure_architecture?.flow ?? [
    { order: 1, name: "Factory Edge", role: "PLC, SCADA, OPC UA, MQTT" },
    { order: 2, name: "IoT Hub", role: "Telemetry ingress" },
    { order: 3, name: "Fabric Real-Time", role: "Operational event stream" },
    { order: 4, name: "Azure Digital Twins", role: "Asset graph" },
    { order: 5, name: "Azure ML", role: "Anomaly models" },
    { order: 6, name: "Foundry Agents", role: "Agent orchestration" },
    { order: 7, name: "Tools & Work Orders", role: "Action execution" },
  ];
  const stages = reports?.operating_model?.stages ?? [
    { name: "Raw Telemetry", detail: "Sensor, PLC, SCADA" },
    { name: "Digital Twin Context", detail: "Asset graph and dependencies" },
    { name: "AI Agent Intelligence", detail: "SOP/manual RAG" },
    { name: "Actionable Ops", detail: "Recommended action and approval" },
  ];
  const paradigm = reports?.operating_model?.paradigm_shift;
  const roadmapItems = reports?.roadmap?.phases ?? roadmap;

  return (
    <div>
      <PageHeader
        title="Executive Reports"
        subtitle="Business value, architecture, and rollout roadmap - reports are sourced from GET /api/reports"
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => (
          <ReportMetricCard key={metric.id} metric={metric} />
        ))}
      </div>

      <section className="panel mt-4 p-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h3 className="section-title">
              <BarChart3 className="h-5 w-5 text-blue-700" />
              Cost Avoidance Report
            </h3>
            <p className="mt-2 text-sm text-slate-600">ROI and payback model for the pilot line.</p>
          </div>
          <StatusPill label={reports ? "Backend Synced" : "Fallback"} tone="blue" />
        </div>
        <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <CostCard label="Annual Cost Avoidance" value={roiSummary ? formatUsd(roiSummary.annual_cost_avoidance) : "$1.84M"} detail="Avoided downtime + reduced energy waste" tone="green" />
          <CostCard label="ROI" value={roiSummary ? `${roiSummary.roi_percent}%` : "312%"} detail="Pilot year return after Azure + integration costs" tone="blue" />
          <CostCard label="Payback Period" value={roiSummary ? `${roiSummary.payback_months} mo` : "4.2 mo"} detail="Estimated months to recover pilot investment" tone="orange" />
          <CostCard label="Risk Exposure Reduced" value={roiSummary ? `${formatUsd(roiSummary.risk_exposure_per_hour)}/hr` : "$2.3M/hr"} detail="Critical downtime exposure benchmark" tone="red" />
        </div>
        <div className="mt-5 overflow-hidden rounded-lg border border-slate-200">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-100 text-slate-600">
              <tr>
                <th className="p-3">Value Driver</th>
                <th className="p-3">Assumption</th>
                <th className="p-3">Annual Impact</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {roiAssumptions.map((row) => (
                <ReportRow key={`${row.driver}-${row.assumption}`} problem={row.driver ?? "Value driver"} response={row.assumption ?? "Assumption"} kpi={typeof row.annualImpact === "number" ? `${formatUsd(row.annualImpact)} annual impact` : "TBD"} />
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1fr_1fr]">
        <section className="panel p-5">
          <h3 className="section-title">Pain Points to TwinOps Response</h3>
          <div className="mt-4 overflow-hidden rounded-lg border border-slate-200">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-100 text-slate-600">
                <tr>
                  <th className="p-3">Problem</th>
                  <th className="p-3">TwinOps AI Response</th>
                  <th className="p-3">KPI</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {painPoints.map((row) => (
                  <ReportRow key={`${row.problem}-${row.kpi}`} problem={row.problem ?? "Problem"} response={row.response ?? "TwinOps response"} kpi={row.kpi ?? "KPI"} />
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="panel p-5">
          <h3 className="section-title">AI-Assisted Operations Model</h3>
          <div className="mt-5 grid gap-3 md:grid-cols-4">
            {stages.map((stage, index) => (
              <FlowBlock key={stage.name} icon={[RadioTower, Network, Bot, ClipboardCheck][index] ?? ClipboardCheck} title={stage.name} detail={stage.detail} />
            ))}
          </div>
          <p className="mt-5 text-sm leading-6 text-slate-600">
            {reports?.operating_model?.equation ?? "Telemetry + Digital Twin Context + AI Agent Intelligence = Actionable Operations."}
          </p>
        </section>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1.2fr_1fr]">
        <section className="panel p-5">
          <h3 className="section-title">Microsoft Azure Architecture</h3>
          <div className="mt-5 grid gap-3 md:grid-cols-3 xl:grid-cols-7">
            {architectureFlow.map((step, index) => (
              <ArchitectureStep key={step.name} icon={[Factory, RadioTower, Database, Network, LineChartIcon, Bot, Wrench][index] ?? Wrench} label={step.name} index={step.order ?? index + 1} />
            ))}
          </div>
        </section>

        <section className="panel p-5">
          <h3 className="section-title">Operational Paradigm Shift</h3>
          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <ParadigmColumn title="Traditional" tone="slate" items={paradigm?.traditional ?? ["Reactive maintenance", "Manual inspection", "Siloed machine data", "Static dashboard", "Manual SOP search"]} />
            <ParadigmColumn title="AI-Driven" tone="green" items={paradigm?.ai_driven ?? ["Predictive maintenance", "Real-time monitoring", "Connected factory intelligence", "Agent-assisted operations", "RAG-based recommendations"]} />
          </div>
        </section>
      </div>

      <section className="panel mt-4 p-5">
        <h3 className="section-title">Roadmap & Risk Mitigation</h3>
        <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {roadmapItems.map((phase) => (
            <RoadmapCard key={phase.id} phase={phase} />
          ))}
        </div>
      </section>
    </div>
  );
}

function KpiCard({
  title,
  value,
  suffix,
  detail,
  tone,
  icon: Icon,
}: {
  title: string;
  value: string;
  suffix?: string;
  detail: string;
  tone: "green" | "blue" | "purple" | "orange" | "red";
  icon: LucideIcon;
}) {
  const toneClass = {
    green: "bg-emerald-50 text-emerald-700",
    blue: "bg-blue-50 text-blue-700",
    purple: "bg-violet-50 text-violet-700",
    orange: "bg-orange-50 text-orange-700",
    red: "bg-red-50 text-red-700",
  }[tone];

  return (
    <section className="panel p-4">
      <div className="flex items-start justify-between gap-3">
        <div className={`flex h-12 w-12 items-center justify-center rounded-lg ${toneClass}`}>
          <Icon className="h-6 w-6" />
        </div>
        <Info className="h-4 w-4 text-slate-400" />
      </div>
      <p className="mt-4 text-sm font-medium text-slate-700">{title}</p>
      <div className="mt-1 flex items-end gap-1">
        <span className={`text-4xl font-semibold ${tone === "red" ? "text-red-600" : tone === "green" ? "text-emerald-700" : "text-slate-950"}`}>{value}</span>
        {suffix ? <span className="pb-1 text-lg text-slate-500">{suffix}</span> : null}
      </div>
      <p className={`mt-2 text-sm ${tone === "red" ? "text-red-600" : "text-emerald-700"}`}>{detail}</p>
    </section>
  );
}

function AssetHealthCard({ asset }: { asset: Asset }) {
  const styles = statusStyles[asset.status];
  return (
    <section className="panel p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <MachineIcon status={asset.status} />
          <div>
            <h3 className="font-semibold text-slate-950">{asset.name}</h3>
            <p className="text-xs text-slate-500">{asset.role}</p>
          </div>
        </div>
        <span className={`flex items-center gap-2 text-sm font-medium ${styles.text}`}>
          <span className={`h-2 w-2 rounded-full ${styles.dot}`} />
          {styles.label}
        </span>
      </div>
      <GaugeMeter value={asset.healthScore} status={asset.status} />
      <div className="mt-4 grid grid-cols-3 divide-x divide-slate-200 border-t border-slate-200 pt-4">
        <AssetMetric icon={Activity} label="Vibration" value={`${asset.vibration} mm/s`} />
        <AssetMetric icon={Thermometer} label="Temperature" value={`${asset.temperature} C`} />
        <AssetMetric icon={Gauge} label="Load" value={`${asset.load}%`} />
      </div>
    </section>
  );
}

function MachineIcon({ status }: { status: AssetStatus }) {
  const className = status === "critical" ? "text-red-600 bg-red-50" : status === "warning" ? "text-amber-600 bg-amber-50" : "text-blue-700 bg-blue-50";
  return (
    <div className={`flex h-12 w-12 items-center justify-center rounded-lg ${className}`}>
      <Cpu className="h-7 w-7" />
    </div>
  );
}

function GaugeMeter({ value, status }: { value: number; status: AssetStatus }) {
  const color = status === "critical" ? "#DC2626" : status === "warning" ? "#F59E0B" : "#16A34A";
  return (
    <div className="mt-4">
      <div className="mx-auto h-24 w-44 overflow-hidden">
        <div
          className="h-44 w-44 rounded-full border-[10px] border-slate-200"
          style={{
            borderTopColor: color,
            borderLeftColor: color,
            transform: `rotate(${Math.max(-45, Math.min(135, value * 1.8 - 45))}deg)`,
          }}
        />
      </div>
      <div className="-mt-12 text-center">
        <span className="text-3xl font-semibold text-slate-950">{value}</span>
        <span className="text-sm text-slate-500"> /100</span>
        <p className="text-xs text-slate-600">Health Score</p>
      </div>
    </div>
  );
}

function AssetMetric({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: string }) {
  return (
    <div className="px-3 first:pl-0 last:pr-0">
      <p className="flex items-center gap-1.5 text-xs text-blue-600">
        <Icon className="h-3.5 w-3.5" />
        {label}
      </p>
      <p className="mt-2 text-lg font-medium text-slate-950">{value}</p>
      <p className="mt-1 text-xs text-emerald-700">Good</p>
    </div>
  );
}

function DigitalTwinPreview({
  assets,
  lineStatusLabel,
  lineStatusDanger,
  onOpen,
}: {
  assets: Asset[];
  lineStatusLabel: string;
  lineStatusDanger: boolean;
  onOpen: () => void;
}) {
  return (
    <section className="panel overflow-hidden p-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-slate-950">Plant Digital Twin</h3>
        <p className="text-sm text-slate-600">
          Line Status:{" "}
          <span className={lineStatusDanger ? "font-semibold text-red-700" : "font-semibold text-emerald-700"}>{lineStatusLabel}</span>
        </p>
      </div>
      <button type="button" onClick={onOpen} className="mt-3 w-full text-left">
        <PlantMap assets={assets} compact />
      </button>
      <StatusLegend compact />
    </section>
  );
}

function PlantMap({ assets, compact, large }: { assets: Asset[]; compact?: boolean; large?: boolean }) {
  const heightClass = large ? "h-[560px]" : compact ? "h-[280px]" : "h-[360px]";
  const byId = useMemo(() => Object.fromEntries(assets.map((a) => [a.id, a])), [assets]);

  return (
    <div className={`relative overflow-hidden rounded-lg border border-slate-200 bg-slate-50 shadow-inner ${heightClass}`}>
      <svg viewBox="0 0 960 420" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Line 1 schematic top view" className="h-full w-full block">
        <defs>
          <pattern id="plantFloorGrid" width="28" height="28" patternUnits="userSpaceOnUse">
            <path d="M 28 0 L 0 0 0 28" fill="none" stroke="#e2e8f0" strokeWidth="1" />
          </pattern>
          <marker id="flowArrowHead" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 z" fill="#94a3b8" />
          </marker>
        </defs>

        <rect width="960" height="420" fill="#f8fafc" />
        <rect width="960" height="420" fill="url(#plantFloorGrid)" opacity="0.55" />

        <text x="48" y="44" fill="#334155" fontSize="22" fontWeight="600">
          Line 1 — top view (schematic)
        </text>
        <text x="48" y="70" fill="#64748b" fontSize="14">
          Material flow · left → right · demo layout
        </text>

        {lineLayoutZones.map((z) => (
          <g key={`${z.label}-${z.detail}`}>
            <rect x={z.x} y={z.y} width={z.w} height={z.h} rx="14" fill="#ffffff" stroke="#e2e8f0" strokeWidth="2" />
            <text x={z.x + z.w / 2} y={z.y + 52} fill="#64748b" fontSize="13" fontWeight="600" textAnchor="middle">
              {z.label}
            </text>
            <text x={z.x + z.w / 2} y={z.y + 76} fill="#64748b" fontSize="12" textAnchor="middle">
              {z.detail}
            </text>
          </g>
        ))}

        <line x1="148" y1="206" x2="198" y2="206" stroke="#cbd5e1" strokeWidth="5" markerEnd="url(#flowArrowHead)" />
        <line x1="334" y1="206" x2="404" y2="206" stroke="#cbd5e1" strokeWidth="5" markerEnd="url(#flowArrowHead)" />
        <line x1="540" y1="206" x2="590" y2="206" stroke="#cbd5e1" strokeWidth="5" markerEnd="url(#flowArrowHead)" />
        <line x1="778" y1="206" x2="812" y2="206" stroke="#cbd5e1" strokeWidth="5" markerEnd="url(#flowArrowHead)" />

        {lineLayoutMachines.map(({ assetId, x, y, w, h }) => {
          const asset = byId[assetId];
          if (!asset) return null;
          const s = schematicSvgStyles[asset.status];
          return (
            <g key={assetId}>
              {large && asset.status === "critical" ? (
                <rect x={x - 6} y={y - 6} width={w + 12} height={h + 12} rx="18" fill="#fecaca" opacity={0.5} stroke="#f87171" strokeWidth="2" strokeDasharray="8 6" />
              ) : null}
              <rect x={x} y={y} width={w} height={h} rx="14" fill={s.fill} stroke={s.stroke} strokeWidth="2.5" />
              <circle cx={x + 22} cy={y + 30} r="7" fill={s.dot} />
              <text x={x + 38} y={y + 35} fill="#0f172a" fontSize="17" fontWeight="700">
                {asset.name}
              </text>
              <text x={x + 22} y={y + 64} fill="#64748b" fontSize="13">
                {asset.role}
              </text>
              <text x={x + 22} y={y + 88} fill={s.statusText} fontSize="13" fontWeight="600">
                {statusStyles[asset.status].label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function StatusLegend({ compact }: { compact?: boolean }) {
  return (
    <div className={`flex flex-wrap gap-4 text-sm text-slate-600 ${compact ? "mt-3" : "m-4"}`}>
      {(["normal", "warning", "critical", "offline"] as AssetStatus[]).map((status) => (
        <span key={status} className="flex items-center gap-2">
          <span className={`h-2.5 w-2.5 rounded-full ${statusStyles[status].dot}`} />
          {statusStyles[status].label}
        </span>
      ))}
    </div>
  );
}

function AzureServicesPanel({ services = azureServices }: { services?: AzureService[] }) {
  return (
    <section className="panel p-5">
      <h3 className="section-title">Azure Services</h3>
      <div className="mt-4 divide-y divide-slate-200">
        {services.map((service) => (
          <div key={service.id} className="flex items-center justify-between gap-3 py-4 first:pt-0 last:pb-0">
            <div className="flex items-center gap-3">
              <ServiceIcon id={service.id} />
              <div>
                <p className="font-medium text-slate-950">{service.name}</p>
                <p className="text-xs text-slate-500">{service.detail}</p>
              </div>
            </div>
            <span className={`flex items-center gap-2 text-sm ${service.status === "Connected" ? "text-emerald-700" : service.status === "Warning" ? "text-amber-700" : "text-blue-700"}`}>
              <CheckCircle2 className="h-4 w-4" />
              {service.status}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

function ServiceIcon({ id }: { id: string }) {
  const Icon = id === "iot" ? RadioTower : id === "adt" ? Box : id === "fabric" ? Layers3 : Bot;
  return (
    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-700">
      <Icon className="h-5 w-5" />
    </div>
  );
}

function ChartPanel({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <section className="panel p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-semibold text-slate-950">{title}</h3>
        <span className="rounded-lg border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600">{subtitle}</span>
      </div>
      {children}
    </section>
  );
}

function LatestTelemetry({ assets, latestTimestamp }: { assets: Asset[]; latestTimestamp: string | null }) {
  const timeLabel = latestTimestamp ?? "—";
  const rows = assets.flatMap((asset) => [
    { time: timeLabel, machine: asset.name, metric: "Vibration", value: `${asset.vibration} mm/s`, status: asset.status },
    { time: timeLabel, machine: asset.name, metric: "Temperature", value: `${asset.temperature} C`, status: asset.status },
    { time: timeLabel, machine: asset.name, metric: "Load", value: `${asset.load}%`, status: asset.status },
  ]);
  return (
    <section className="panel p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-semibold text-slate-950">Latest Telemetry</h3>
        <button type="button" className="text-sm font-medium text-blue-700">View All</button>
      </div>
      <div className="overflow-hidden rounded-lg border border-slate-200">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="p-2">Time</th>
              <th className="p-2">Machine</th>
              <th className="p-2">Metric</th>
              <th className="p-2">Value</th>
              <th className="p-2">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {rows.slice(0, 6).map((row) => (
              <tr key={`${row.machine}-${row.metric}`}>
                <td className="p-2">{row.time}</td>
                <td className="p-2">{row.machine}</td>
                <td className="p-2">{row.metric}</td>
                <td className="p-2 font-medium">{row.value}</td>
                <td className="p-2">
                  <span className={`block h-2 w-2 rounded-full ${statusStyles[row.status].dot}`} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-xs text-slate-500">Latest sample time from GET /api/telemetry</p>
    </section>
  );
}

function SummaryStrip({ icon: Icon, label, value, tone }: { icon: LucideIcon; label: string; value: string; tone: "red" | "green" | "blue" | "orange" }) {
  const toneClass = {
    red: "bg-red-100 text-red-700",
    green: "bg-emerald-100 text-emerald-700",
    blue: "bg-blue-100 text-blue-700",
    orange: "bg-orange-100 text-orange-700",
  }[tone];
  return (
    <div className="flex items-center gap-5 border-slate-200 md:border-r md:last:border-r-0">
      <div className={`flex h-16 w-16 items-center justify-center rounded-lg ${toneClass}`}>
        <Icon className="h-8 w-8" />
      </div>
      <div>
        <p className="text-sm text-slate-600">{label}</p>
        <p className="mt-2 text-xl font-semibold text-slate-950">{value}</p>
      </div>
    </div>
  );
}

function AlertDetails({ alert, anomalyActive }: { alert: Alert; anomalyActive: boolean }) {
  return (
    <section className="panel p-5">
      <div className="flex items-center justify-between">
        <h3 className="section-title">Alert Details</h3>
        <StatusPill label={alert.severity} tone={anomalyActive ? "red" : "green"} />
      </div>
      <div className="mt-4 divide-y divide-slate-200">
        <DetailRow icon={Timer} label="Anomaly Detected" value={alert.timestamp} />
        {alert.metrics.map((metric) => (
          <DetailRow key={metric.label} icon={metric.label.includes("Temperature") ? Thermometer : Activity} label={metric.label} value={metric.value} detail={metric.delta} danger={anomalyActive} />
        ))}
      </div>
      <div className="mt-5">
        <h4 className="font-semibold text-slate-950">Impacted Downstream Assets</h4>
        <div className="mt-3 space-y-2 text-sm">
          <div className="flex justify-between">
            <span>Conveyor C</span>
            <span className={anomalyActive ? "text-amber-700" : "text-emerald-700"}>{anomalyActive ? "Warning" : "Normal"}</span>
          </div>
          <div className="flex justify-between">
            <span>Line 1 Output Buffer</span>
            <span className={anomalyActive ? "text-amber-700" : "text-emerald-700"}>{anomalyActive ? "Warning" : "Normal"}</span>
          </div>
        </div>
      </div>
    </section>
  );
}

function DetailRow({ icon: Icon, label, value, detail, danger }: { icon: LucideIcon; label: string; value: string; detail?: string; danger?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3 py-3">
      <div className="flex items-center gap-3">
        <Icon className="h-5 w-5 text-slate-500" />
        <span className="text-sm text-slate-700">{label}</span>
      </div>
      <div className="text-right">
        <p className={`text-sm font-semibold ${danger ? "text-red-600" : "text-slate-950"}`}>{value}</p>
        {detail ? <p className="text-xs text-slate-500">{detail}</p> : null}
      </div>
    </div>
  );
}

function DependencyNode({ label, detail, status }: { label: string; detail: string; status: AssetStatus }) {
  const styles = statusStyles[status];
  return (
    <div className={`rounded-lg border px-4 py-3 text-center ${styles.bg} ${styles.border}`}>
      <p className="font-semibold text-slate-950">{label}</p>
      <p className={`text-sm ${styles.text}`}>{detail}</p>
    </div>
  );
}

function ArrowConnector({ label }: { label: string }) {
  return (
    <div className="flex min-w-24 flex-col items-center gap-1 text-center">
      <span className="text-[11px] font-medium text-slate-500">{label}</span>
      <div className="flex w-full items-center">
        <div className="h-px flex-1 bg-slate-400" />
        <ChevronRight className="h-4 w-4 text-slate-500" />
      </div>
    </div>
  );
}

function OrchestrationCard({ agentsApiMode, onRunCascade }: { agentsApiMode: string; onRunCascade: () => void }) {
  return (
    <section className="panel flex flex-wrap items-center gap-4 px-5 py-3">
      <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-violet-50 text-violet-700">
        <Bot className="h-7 w-7" />
      </div>
      <div>
        <p className="text-xs text-slate-500">Orchestrated by</p>
        <p className="font-semibold text-blue-700">Foundry Agent Service</p>
        <p className="text-xs text-slate-500">{agentsApiMode}</p>
      </div>
      <span className="ml-auto flex items-center gap-2 text-sm text-emerald-700">
        <span className="h-2 w-2 rounded-full bg-emerald-600" />
        Operational
      </span>
      <button type="button" onClick={onRunCascade} className="btn-secondary text-sm">
        <Bot className="h-4 w-4" />
        Run Cascade
      </button>
    </section>
  );
}

function AgentCard({ agent, isActive, showConnector }: { agent: AgentStep; isActive: boolean; showConnector: boolean }) {
  const Icon = agent.id === "sensor" ? Activity : agent.id === "twin" ? Box : agent.id === "maintenance" ? Wrench : agent.id === "energy" ? Zap : agent.id === "safety" ? Shield : BarChart3;
  const statusClass = agent.status === "completed" ? "text-emerald-700 bg-emerald-50 border-emerald-200" : agent.status === "in-progress" ? "text-violet-700 bg-violet-50 border-violet-200" : "text-slate-600 bg-slate-50 border-slate-200";
  return (
    <div className="relative">
      <section className={`panel flex h-full min-h-[320px] flex-col items-center p-4 text-center ${isActive ? "ring-2 ring-violet-600" : ""}`}>
        <span className="self-start rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-sm font-medium text-slate-600">{agent.order}</span>
        <div className={`mt-4 flex h-16 w-16 items-center justify-center rounded-lg ${agent.tone === "purple" ? "bg-violet-100 text-violet-700" : agent.tone === "orange" ? "bg-orange-100 text-orange-700" : agent.tone === "green" ? "bg-emerald-100 text-emerald-700" : "bg-blue-100 text-blue-700"}`}>
          <Icon className="h-8 w-8" />
        </div>
        <h3 className="mt-4 text-lg font-semibold text-slate-950">{agent.name}</h3>
        <span className={`mt-4 rounded-lg border px-3 py-1 text-sm font-medium ${statusClass}`}>{statusLabel(agent.status)}</span>
        <p className="mt-4 text-sm leading-6 text-slate-600">{agent.summary}</p>
        <div className="mt-auto pt-4 text-xs text-slate-500">
          <Timer className="mr-1 inline h-3.5 w-3.5" />
          {agent.elapsed}
        </div>
      </section>
      {showConnector ? <div className="absolute right-[-18px] top-1/2 hidden h-px w-9 bg-slate-300 xl:block" /> : null}
    </div>
  );
}

function apiAgentToAgentStep(agent: NonNullable<ReturnType<typeof useTwinOpsBackend>["agentsApi"]>["agents"][number]): AgentStep {
  return {
    id: agent.id,
    order: agent.order,
    name: agent.name,
    role: agent.role,
    status: agent.status,
    summary: agent.summary,
    elapsed: agent.elapsed,
    tone: agent.tone,
  };
}

function apiLogToExecutionLog(log: NonNullable<ReturnType<typeof useTwinOpsBackend>["agentsApi"]>["execution_log"][number]): ExecutionLog {
  return {
    id: log.id,
    agent: log.agent,
    time: log.time,
    message: log.message,
    status: log.status,
  };
}

function ExecutionLogPanel({ logs }: { logs: ExecutionLog[] }) {
  return (
    <section className="panel p-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-slate-950">Live Execution Log</h3>
        <span className="flex items-center gap-2 text-sm font-medium text-emerald-700">
          <span className="h-2 w-2 rounded-full bg-emerald-600" />
          Live
        </span>
      </div>
      <div className="mt-5 space-y-5">
        {logs.map((log) => (
          <div key={log.id} className="grid grid-cols-[24px_1fr_20px] gap-3">
            <Box className={`h-5 w-5 ${log.status === "completed" ? "text-blue-600" : log.status === "in-progress" ? "text-violet-700" : "text-slate-400"}`} />
            <div>
              <p className="text-sm text-slate-500">{log.time}</p>
              <p className={`font-semibold ${log.status === "in-progress" ? "text-violet-700" : log.status === "completed" ? "text-blue-700" : "text-slate-600"}`}>{log.agent}</p>
              <p className="mt-2 text-sm leading-6 text-slate-600">{log.message}</p>
            </div>
            {log.status === "completed" ? <CheckCircle2 className="h-5 w-5 text-emerald-600" /> : <span className="mt-1 h-4 w-4 rounded-full border-2 border-slate-400" />}
          </div>
        ))}
      </div>
    </section>
  );
}

function CascadeSummary({ anomalyActive }: { anomalyActive: boolean }) {
  return (
    <section className="panel mt-5 p-5">
      <h3 className="font-semibold text-slate-950">Cascade Summary</h3>
      <div className="mt-4 grid gap-4 md:grid-cols-4">
        <InfoTile label="Cascade ID" value="CAS-2025-05-17-102430" />
        <InfoTile label="Started At" value="May 17, 2025 10:24:30 AM" />
        <InfoTile label="Elapsed Time" value={anomalyActive ? "00:00:03" : "00:00:00"} />
        <InfoTile label="Status" value={anomalyActive ? "In Progress" : "Standby"} />
      </div>
    </section>
  );
}

function LegendItem({ color, label, ring }: { color: string; label: string; ring?: boolean }) {
  return (
    <span className="flex items-center gap-2">
      <span className={`h-3 w-3 rounded-full ${color} ${ring ? "ring-2 ring-violet-200" : ""}`} />
      {label}
    </span>
  );
}

function ActionRow({ action, order }: { action: RecommendationAction; order: number }) {
  const impactTone = action.impact === "High" ? "bg-blue-50 text-blue-700" : "bg-amber-50 text-amber-700";
  return (
    <div className="grid grid-cols-[40px_52px_1fr_auto] items-center gap-3 rounded-lg border border-slate-200 bg-white p-3">
      <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-600 text-sm font-semibold text-white">{order}</span>
      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-700">
        {order === 1 ? <Timer className="h-5 w-5" /> : order === 2 ? <Activity className="h-5 w-5" /> : <ClipboardCheck className="h-5 w-5" />}
      </div>
      <div>
        <p className="font-semibold text-slate-950">{action.title}</p>
        <p className="text-sm text-slate-600">{action.description}</p>
      </div>
      <span className={`rounded-lg px-3 py-1 text-sm font-medium ${impactTone}`}>{action.impact} Impact</span>
    </div>
  );
}

function GeneratedWorkOrderPanel({ workOrder, onOpenWorkOrder }: { workOrder: GeneratedWorkOrder; onOpenWorkOrder: () => void }) {
  return (
    <section className="panel p-5">
      <h3 className="section-title">
        <ClipboardCheck className="h-5 w-5 text-blue-700" />
        Generated Work Order
      </h3>
      <div className="mt-5 space-y-5 text-sm">
        <KeyValue label="Work Order ID" value={workOrder.id} />
        <KeyValue label="Asset" value={workOrder.assetName} />
        <KeyValue label="Priority" value={workOrder.priority} badge="red" />
        <KeyValue label="Suggested Assignee" value={workOrder.assignee} />
        <KeyValue label="Due" value={workOrder.due} />
        <KeyValue label="Status" value={workOrder.status} badge={workOrder.status === "Dispatched" ? "green" : "orange"} />
      </div>
      <button type="button" onClick={onOpenWorkOrder} className="secondary-button mt-10 w-full justify-center">
        Open Work Order
        <ExternalLink className="h-4 w-4" />
      </button>
    </section>
  );
}

function RecommendationActionResult({ status }: { status: GeneratedWorkOrder["status"] }) {
  if (status === "Awaiting approval") {
    return (
      <section className="panel mt-4 border-amber-200 bg-amber-50 p-5">
        <h3 className="section-title text-amber-800">
          <Timer className="h-5 w-5" />
          Awaiting Human Approval
        </h3>
        <p className="mt-2 text-sm text-amber-800">
          Recommendation is ready. Supervisor approval is required before dispatch - รอผู้ควบคุมอนุมัติก่อนส่งงานซ่อมบำรุง.
        </p>
      </section>
    );
  }

  if (status === "Approved") {
    return (
      <section className="panel mt-4 border-blue-200 bg-blue-50 p-5">
        <h3 className="section-title text-blue-800">
          <CheckCircle2 className="h-5 w-5" />
          Action Approved
        </h3>
        <p className="mt-2 text-sm text-blue-800">
          The maintenance action has been approved. Work order is still waiting to be sent to the maintenance team.
        </p>
      </section>
    );
  }

  return (
    <section className="panel mt-4 border-emerald-200 bg-emerald-50 p-5">
      <h3 className="section-title text-emerald-800">
        <Send className="h-5 w-5" />
        Sent to Maintenance
      </h3>
      <p className="mt-2 text-sm text-emerald-800">
        Work order has been dispatched to the maintenance queue with safety reminder and SOP evidence attached.
      </p>
    </section>
  );
}

function EvidenceChart({
  title,
  metric,
  data,
  accent,
  highlight,
}: {
  title: string;
  metric: string;
  data: { day: string; current: number; baseline: number }[];
  accent: string;
  highlight: string;
}) {
  return (
    <section className="panel p-4">
      <h3 className="font-semibold text-slate-950">{title}</h3>
      <p className="mt-3 text-sm text-slate-600">{metric}</p>
      <div className="mt-3 grid grid-cols-[1fr_112px] gap-3">
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={data} margin={{ left: -24, right: 8, top: 8, bottom: 0 }}>
            <CartesianGrid stroke="#E5E7EB" strokeDasharray="3 3" />
            <XAxis dataKey="day" tick={{ fontSize: 10 }} stroke="#64748B" />
            <YAxis tick={{ fontSize: 10 }} stroke="#64748B" />
            <Tooltip contentStyle={{ borderRadius: 8, borderColor: "#DBEAFE" }} />
            <Line type="monotone" dataKey="current" stroke={accent} strokeWidth={2.5} dot={false} name="Current" />
            <Line type="monotone" dataKey="baseline" stroke="#CBD5E1" strokeDasharray="5 5" strokeWidth={2} dot={false} name="Baseline" />
          </LineChart>
        </ResponsiveContainer>
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p className="text-2xl font-semibold" style={{ color: accent }}>
            {highlight}
          </p>
          <p className="text-xs text-slate-500">vs baseline</p>
          <div className="mt-4 text-xs text-slate-600">
            <p>Peak</p>
            <p className="font-semibold text-slate-950">3.6 mm/s</p>
            <p className="mt-3">Time</p>
            <p className="font-semibold text-slate-950">May 17, 10:24 AM</p>
          </div>
        </div>
      </div>
      <p className="mt-2 flex items-center gap-2 text-sm text-emerald-700">
        <span className="h-2 w-2 rounded-full bg-emerald-600" />
        Anomaly detected
      </p>
    </section>
  );
}

function SopPanel({ sop }: { sop?: AnalyzeRetrievedSop }) {
  const docTitle = sop?.document_id ?? "SOP-MA-102: Bearing Inspection & Replacement";
  const matchLabel = sop?.match_score ?? "92% match";
  const excerpts =
    sop?.excerpts?.length ? sop.excerpts : [
        "Increased vibration RMS above baseline indicates potential bearing wear.",
        "Temperature rise above baseline may indicate increased friction.",
        "Act promptly to inspect bearings and prevent unplanned downtime.",
      ];

  return (
    <section className="panel p-4">
      <h3 className="section-title">
        <BookOpen className="h-5 w-5 text-blue-700" />
        Retrieved SOP / Manual Context
      </h3>
      <div className="mt-4 rounded-lg border border-blue-200 bg-blue-50 p-3">
        <p className="text-sm font-semibold text-blue-700">{docTitle}</p>
        <p className="text-xs text-slate-600">{sop ? "From GET /api/analyze · retrieved_sop" : "Section 4.2 - Symptoms and Diagnostics (demo fallback)"}</p>
        <span className="mt-2 inline-block rounded-lg bg-emerald-100 px-2 py-1 text-xs font-semibold text-emerald-700">{matchLabel}</span>
      </div>
      <div className="mt-4 text-sm leading-6 text-slate-600">
        <p className="font-semibold text-slate-950">Relevant Excerpts</p>
        <ul className="mt-2 list-disc space-y-1 pl-5">
          {excerpts.map((line, i) => (
            <li key={i}>{line}</li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function KeyValue({ label, value, badge }: { label: string; value: string; badge?: "red" | "orange" | "green" }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-slate-600">{label}</span>
      {badge ? <StatusPill label={value} tone={badge} /> : <span className="font-medium text-slate-950">{value}</span>}
    </div>
  );
}

function InfoTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-2 font-semibold text-slate-950">{value}</p>
    </div>
  );
}

function ReportMetricCard({ metric }: { metric: ReportMetric }) {
  const toneClass = {
    blue: "bg-blue-50 text-blue-700",
    green: "bg-emerald-50 text-emerald-700",
    orange: "bg-orange-50 text-orange-700",
    red: "bg-red-50 text-red-700",
  }[metric.tone];
  return (
    <section className="panel p-5">
      <div className={`inline-flex rounded-lg px-3 py-2 text-sm font-semibold ${toneClass}`}>{metric.label}</div>
      <p className="mt-4 text-4xl font-semibold text-slate-950">{metric.value}</p>
      <p className="mt-2 text-sm text-slate-600">{metric.detail}</p>
    </section>
  );
}

function CostCard({
  label,
  value,
  detail,
  tone,
}: {
  label: string;
  value: string;
  detail: string;
  tone: "blue" | "green" | "orange" | "red";
}) {
  const toneClass = {
    blue: "bg-blue-50 text-blue-700",
    green: "bg-emerald-50 text-emerald-700",
    orange: "bg-amber-50 text-amber-700",
    red: "bg-red-50 text-red-700",
  }[tone];

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <span className={`inline-flex rounded-lg px-3 py-1 text-xs font-semibold ${toneClass}`}>{label}</span>
      <p className="mt-4 text-3xl font-semibold text-slate-950">{value}</p>
      <p className="mt-2 text-sm leading-6 text-slate-600">{detail}</p>
    </div>
  );
}

function ReportRow({ problem, response, kpi }: { problem: string; response: string; kpi: string }) {
  return (
    <tr>
      <td className="p-3 text-slate-700">{problem}</td>
      <td className="p-3 font-medium text-blue-700">{response}</td>
      <td className="p-3 text-slate-700">{kpi}</td>
    </tr>
  );
}

function FlowBlock({ icon: Icon, title, detail }: { icon: LucideIcon; title: string; detail: string }) {
  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-center">
      <Icon className="mx-auto h-7 w-7 text-blue-700" />
      <p className="mt-3 font-semibold text-slate-950">{title}</p>
      <p className="mt-2 text-xs text-slate-600">{detail}</p>
    </div>
  );
}

function ArchitectureStep({ icon: Icon, label, index }: { icon: LucideIcon; label: string; index: number }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-center">
      <span className="text-xs font-semibold text-slate-500">{index}</span>
      <Icon className="mx-auto mt-2 h-6 w-6 text-blue-700" />
      <p className="mt-2 text-sm font-medium text-slate-950">{label}</p>
    </div>
  );
}

function ParadigmColumn({ title, tone, items }: { title: string; tone: "slate" | "green"; items: string[] }) {
  return (
    <div>
      <h4 className={`rounded-lg px-3 py-2 text-center font-semibold text-white ${tone === "green" ? "bg-emerald-600" : "bg-slate-500"}`}>{title}</h4>
      <div className="mt-3 space-y-2">
        {items.map((item) => (
          <div key={item} className={`rounded-lg px-3 py-2 text-center text-sm font-medium ${tone === "green" ? "bg-cyan-50 text-cyan-800" : "bg-slate-100 text-slate-600"}`}>
            {item}
          </div>
        ))}
      </div>
    </div>
  );
}

function RoadmapCard({ phase }: { phase: RoadmapPhase }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <Shield className="h-7 w-7 text-blue-700" />
      <h4 className="mt-3 font-semibold text-slate-950">{phase.title}</h4>
      <p className="mt-2 text-sm leading-6 text-slate-600">{phase.description}</p>
      <p className="mt-3 text-xs font-medium text-slate-500">{phase.risk}</p>
    </div>
  );
}

function StatusPill({ label, tone }: { label: string; tone: "red" | "orange" | "green" | "blue" }) {
  const toneClass = {
    red: "bg-red-50 text-red-700",
    orange: "bg-amber-50 text-amber-700",
    green: "bg-emerald-50 text-emerald-700",
    blue: "bg-blue-50 text-blue-700",
  }[tone];
  return <span className={`rounded-lg px-3 py-1 text-sm font-semibold ${toneClass}`}>{label}</span>;
}

function InfoBand({ text }: { text: string }) {
  return (
    <div className="mt-4 flex items-center gap-3 rounded-lg border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-slate-600">
      <Info className="h-5 w-5 text-blue-700" />
      {text}
    </div>
  );
}

function NotificationPanel({
  open,
  anomalyActive,
  sidebarCollapsed,
  sidebarHidden,
  onClose,
  onNavigate,
}: {
  open: boolean;
  anomalyActive: boolean;
  sidebarCollapsed: boolean;
  sidebarHidden: boolean;
  onClose: () => void;
  onNavigate: (page: PageId) => void;
}) {
  if (!open) return null;

  const notifications = [
    {
      id: "n1",
      title: anomalyActive ? "Motor A anomaly detected" : "Line running normally",
      detail: anomalyActive ? "Vibration and temperature exceeded baseline. Agent cascade started." : "No active anomaly. Monitoring continues.",
      time: "10:24 AM",
      tone: anomalyActive ? "red" : "green",
      page: anomalyActive ? "agents" : "dashboard",
    },
    {
      id: "n2",
      title: "Foundry Agent Service operational",
      detail: "Sensor, Twin, Maintenance, Energy, Safety, and Business Impact agents are available.",
      time: "10:23 AM",
      tone: "blue",
      page: "agents",
    },
    {
      id: "n3",
      title: "Cost Avoidance report refreshed",
      detail: "ROI and payback period are ready for executive review.",
      time: "10:18 AM",
      tone: "orange",
      page: "reports",
    },
  ] as const;

  return (
    <div className="fixed inset-0 z-50" role="dialog" aria-label="Notifications">
      <button
        type="button"
        className={`absolute bottom-0 right-0 top-[76px] bg-slate-900/10 ${sidebarHidden ? "lg:left-0" : sidebarCollapsed ? "lg:left-[76px]" : "lg:left-[256px]"} left-0`}
        onClick={onClose}
        aria-label="Close notifications"
      />
      <aside className="absolute right-4 top-20 w-[min(420px,calc(100vw-32px))] rounded-lg border border-slate-200 bg-white p-4 shadow-2xl">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-slate-950">Notifications</h3>
            <p className="text-sm text-slate-500">Mock operational alerts - การแจ้งเตือนจำลอง</p>
            <p className="mt-1 text-xs text-slate-400">Click outside or press X to close.</p>
          </div>
          <button type="button" onClick={onClose} className="icon-button h-9 w-9" aria-label="Close notifications">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="mt-4 space-y-3">
          {notifications.map((item) => {
            const toneClass =
              item.tone === "red"
                ? "bg-red-50 text-red-700 border-red-200"
                : item.tone === "green"
                  ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                  : item.tone === "orange"
                    ? "bg-amber-50 text-amber-700 border-amber-200"
                    : "bg-blue-50 text-blue-700 border-blue-200";
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => {
                  onNavigate(item.page);
                  onClose();
                }}
                className="w-full rounded-lg border border-slate-200 bg-white p-4 text-left transition hover:border-blue-200 hover:bg-blue-50"
              >
                <div className="flex items-start gap-3">
                  <span className={`mt-1 rounded-lg border p-2 ${toneClass}`}>
                    <Bell className="h-4 w-4" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-semibold text-slate-950">{item.title}</p>
                      <span className="text-xs text-slate-500">{item.time}</span>
                    </div>
                    <p className="mt-1 text-sm leading-6 text-slate-600">{item.detail}</p>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </aside>
    </div>
  );
}

function DemoFooter({
  sidebarCollapsed,
  sidebarHidden,
  backendConnected,
}: {
  sidebarCollapsed: boolean;
  sidebarHidden: boolean;
  backendConnected: boolean;
}) {
  return (
    <footer
      className={`fixed bottom-0 left-0 right-0 z-30 border-t border-slate-200 bg-white/95 px-4 py-3 text-sm text-slate-600 backdrop-blur ${sidebarHidden ? "lg:pl-4" : sidebarCollapsed ? "lg:pl-[92px]" : "lg:pl-[272px]"}`}
    >
      <div className="mx-auto flex max-w-[1580px] items-center gap-3">
        <Info className="h-5 w-5 text-blue-700" />
        <span>
          {backendConnected
            ? "Telemetry, digital twin, and analyze views poll the local TwinOps FastAPI backend (demo)."
            : "Backend unreachable — charts may show offline fallback values until the API is running."}
        </span>
      </div>
    </footer>
  );
}

function buildAlert(anomalyActive: boolean, telemetry: TelemetryApiResponse | null, apiAlerts?: ApiAlert[]): Alert {
  if (apiAlerts && apiAlerts.length > 0) return apiAlertToAlert(apiAlerts[0]);

  const ma = telemetry?.motor_A;
  const ts = telemetry?.timestamp ?? "—";
  return {
    id: "alert-live",
    title: anomalyActive ? "Bearing wear risk detected" : "No active anomaly",
    assetId: "motor-a",
    severity: anomalyActive ? "High" : "Low",
    timestamp: ts,
    details: anomalyActive ? "Motor A vibration and temperature moved above baseline together." : "Line is operating within baseline.",
    metrics: anomalyActive && ma
      ? [
          { label: "Vibration", value: `${ma.vibration} mm/s`, delta: "Elevated vs baseline" },
          { label: "Temperature", value: `${ma.temperature} C`, delta: "Elevated vs baseline" },
          { label: "Load", value: `${ma.load}%`, delta: "Operating load" },
        ]
      : anomalyActive
        ? [
            { label: "Vibration Spike", value: "3.6 mm/s", delta: "Above baseline" },
            { label: "Temperature Spike", value: "76 C", delta: "Above baseline" },
            { label: "Predicted Issue Probability", value: "82%", delta: "High likelihood of failure" },
          ]
        : [
            { label: "Vibration", value: ma ? `${ma.vibration} mm/s` : "1.2 mm/s", delta: "Within baseline" },
            { label: "Temperature", value: ma ? `${ma.temperature} C` : "62 C", delta: "Within baseline" },
            { label: "Predicted Issue Probability", value: "8%", delta: "Low likelihood" },
          ],
  };
}

function buildAgents(anomalyActive: boolean): AgentStep[] {
  const activeStatuses: AgentStep["status"][] = anomalyActive
    ? ["completed", "completed", "in-progress", "pending", "pending", "pending"]
    : ["pending", "pending", "pending", "pending", "pending", "pending"];
  const data = [
    ["sensor", "Sensor", "Spike detected in vibration and temperature", "10:24:30 AM / 612 ms", "blue"],
    ["twin", "Twin", "Affected asset and downstream dependency mapped", "10:24:31 AM / 1.2 s", "blue"],
    ["maintenance", "Maintenance", "Likely root cause analyzed from SOP/manual context", "10:24:33 AM / 1.8 s", "purple"],
    ["energy", "Energy", "Load reduction scenario evaluated", "-", "blue"],
    ["safety", "Safety", "Human approval required before intervention", "-", "orange"],
    ["business", "Business Impact", "Downtime and energy impact estimated", "-", "green"],
  ] as const;

  return data.map(([id, name, summary, elapsed, tone], index) => ({
    id,
    order: index + 1,
    name,
    role: name,
    status: activeStatuses[index],
    summary,
    elapsed,
    tone,
  }));
}

function buildExecutionLog(anomalyActive: boolean): ExecutionLog[] {
  if (!anomalyActive) {
    return [
      { id: "standby", agent: "System", time: "10:24:30.000", message: "Waiting for anomaly simulation.", status: "pending" },
    ];
  }
  return [
    { id: "sensor", agent: "Sensor Agent", time: "10:24:30.123", message: "Spike detected in vibration and temperature on Motor A.", status: "completed" },
    { id: "twin", agent: "Twin Agent", time: "10:24:31.342", message: "Mapped affected asset: Motor A and dependencies: Conveyor C, Gearbox G1.", status: "completed" },
    { id: "maintenance", agent: "Maintenance Agent", time: "10:24:33.128", message: "Analyzing maintenance history, SOPs, and manuals for likely root cause...", status: "in-progress" },
    { id: "waiting-maintenance", agent: "Waiting for Maintenance Agent", time: "10:24:33.129", message: "Waiting for Maintenance Agent to complete...", status: "pending" },
    { id: "energy", agent: "Waiting for Energy Agent", time: "10:24:33.129", message: "Waiting for Energy Agent to complete...", status: "pending" },
    { id: "business", agent: "Business Impact Agent", time: "10:24:33.129", message: "Waiting for Safety Agent to complete...", status: "pending" },
  ];
}

function buildWorkOrder(status: GeneratedWorkOrder["status"]): GeneratedWorkOrder {
  return {
    id: "WO-2025-0517-0001",
    assetId: "motor-a",
    assetName: "Motor A",
    priority: "High",
    status,
    assignee: "Maintenance Team",
    due: "Within 24 hours",
    title: "Bearing inspection and lubrication check",
    checklist: [
      "Verify lockout/tagout before inspection.",
      "Inspect Motor A bearing housing and lubrication level.",
      "Check vibration trend after temporary load reduction.",
      "Record findings and attach photos to maintenance history.",
    ],
    history: [
      { time: "May 17, 2025 10:24 AM", event: "AI recommendation generated from anomaly cascade." },
      { time: "May 17, 2025 10:25 AM", event: `Work order status set to ${status}.` },
    ],
  };
}

function statusLabel(status: AgentStep["status"]): string {
  if (status === "in-progress") return "In Progress";
  if (status === "not-started") return "Not Started";
  return status.charAt(0).toUpperCase() + status.slice(1);
}
