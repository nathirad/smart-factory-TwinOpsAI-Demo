import { useMemo, useState } from "react";
import { Activity, AlertTriangle, BarChart3, Factory, Play, RotateCcw, ShieldCheck, Wrench } from "lucide-react";
import AiRecommendationPanel from "./components/AiRecommendationPanel";
import ArchitectureFlow from "./components/ArchitectureFlow";
import DigitalTwinMap from "./components/DigitalTwinMap";
import KpiCard from "./components/KpiCard";
import MachineCard from "./components/MachineCard";
import TelemetryChart from "./components/TelemetryChart";
import WorkOrderCard from "./components/WorkOrderCard";
import { generateTelemetry, getMachineSeries, getMachineStates } from "./data/simulatedTelemetry";
import type { MachineId, WorkOrder } from "./types";
import { buildAiRecommendation, buildSummaryContext, round } from "./utils/anomalyDetection";

export default function App() {
  const [demoMode, setDemoMode] = useState(false);
  const [selectedMachineId, setSelectedMachineId] = useState<MachineId>("Motor-A");
  const [workOrder, setWorkOrder] = useState<WorkOrder | null>(null);

  const telemetry = useMemo(() => generateTelemetry(demoMode), [demoMode]);
  const machines = useMemo(() => getMachineStates(telemetry), [telemetry]);
  const selectedSeries = useMemo(() => getMachineSeries(telemetry, selectedMachineId), [telemetry, selectedMachineId]);
  const summary = useMemo(() => buildSummaryContext(selectedMachineId, selectedSeries), [selectedMachineId, selectedSeries]);
  const recommendation = useMemo(() => buildAiRecommendation(summary), [summary]);

  const latestPoints = machines.map((machine) => machine.current);
  const criticalCount = machines.filter((machine) => machine.status === "critical").length;
  const warningCount = machines.filter((machine) => machine.status === "warning").length;
  const averageOee = round(latestPoints.reduce((sum, point) => sum + point.oee, 0) / latestPoints.length, 1);
  const lineHealth = round(machines.reduce((sum, machine) => sum + machine.healthScore, 0) / machines.length, 0);
  const lineRisk = criticalCount > 0 ? "High" : warningCount > 0 ? "Medium" : "Low";
  const selectedMachine = machines.find((machine) => machine.machineId === selectedMachineId)!;

  function runDemoScenario() {
    setDemoMode(true);
    setSelectedMachineId("Motor-A");
    setWorkOrder(null);
  }

  function resetScenario() {
    setDemoMode(false);
    setWorkOrder(null);
  }

  function createWorkOrder() {
    const dueTime = summary.risk === "High" ? "Within 24 hours" : summary.risk === "Medium" ? "Next shift" : "No due time";
    setWorkOrder({
      id: `WO-${new Date().getFullYear()}-${selectedMachineId.replace("-", "")}-042`,
      machineId: selectedMachineId,
      priority: recommendation.urgency,
      recommendedAction: recommendation.recommendedAction,
      assignedTeam: summary.risk === "High" ? "Maintenance Team Alpha" : "Reliability Engineering",
      dueTime,
    });
  }

  return (
    <main className="dashboard-grid min-h-screen px-4 py-5 text-zinc-100 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-[1600px]">
        <header className="flex flex-col gap-5 border-b border-azure-400/20 pb-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-3xl">
            <div className="flex items-center gap-3 text-sm font-semibold uppercase tracking-wide text-azure-200">
              <Factory className="h-5 w-5" />
              Packaging Line 1
            </div>
            <h1 className="mt-3 text-4xl font-semibold tracking-normal text-white sm:text-5xl">SmartFactory TwinOps AI</h1>
            <p className="mt-3 max-w-2xl text-base leading-7 text-azure-100/70">
              AI-assisted factory operations for anomaly detection, predictive maintenance risk, digital twin state, and maintenance action simulation.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={runDemoScenario}
              className="flex items-center gap-2 rounded-md bg-azure-500 px-4 py-3 text-sm font-bold text-white shadow-glow transition hover:bg-azure-400"
            >
              <Play className="h-4 w-4" />
              Run Demo Scenario
            </button>
            <button
              type="button"
              onClick={resetScenario}
              className="flex items-center gap-2 rounded-md border border-azure-300/25 bg-azure-950/70 px-4 py-3 text-sm font-semibold text-azure-100 transition hover:border-azure-300/60 hover:text-white"
            >
              <RotateCcw className="h-4 w-4" />
              Reset Line
            </button>
          </div>
        </header>

        <section className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <KpiCard
            title="Line Risk"
            value={lineRisk}
            detail={`${criticalCount} critical, ${warningCount} warning machines`}
            tone={lineRisk === "High" ? "red" : lineRisk === "Medium" ? "amber" : "green"}
            icon={AlertTriangle}
          />
          <KpiCard title="Average OEE" value={`${averageOee}%`} detail="Current machine average" tone="azure" icon={BarChart3} />
          <KpiCard title="Line Health" value={`${lineHealth}%`} detail="Digital twin health index" tone={lineHealth < 55 ? "red" : lineHealth < 75 ? "amber" : "green"} icon={ShieldCheck} />
          <KpiCard title="Open Work Orders" value={workOrder ? "1" : "0"} detail="Generated from AI recommendation" tone={workOrder ? "amber" : "green"} icon={Wrench} />
        </section>

        <section className="mt-5 grid gap-5 xl:grid-cols-[1.7fr_0.9fr]">
          <div className="space-y-5">
            <section className="glass-panel rounded-lg p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-zinc-50">Executive Overview Dashboard</h2>
                  <p className="mt-1 text-sm text-azure-100/50">Machine risk, health score, and latest operating state</p>
                </div>
                <span className="rounded-md border border-azure-400/20 bg-azure-950/75 px-3 py-2 text-sm text-azure-100/70">
                  Mode: {demoMode ? "Anomaly scenario active" : "Normal line simulation"}
                </span>
              </div>
              <div className="mt-4 grid gap-3 lg:grid-cols-3">
                {machines.map((machine) => (
                  <MachineCard
                    key={machine.machineId}
                    machine={machine}
                    selected={machine.machineId === selectedMachineId}
                    onSelect={setSelectedMachineId}
                  />
                ))}
              </div>
            </section>

            <TelemetryChart data={selectedSeries} />

            <DigitalTwinMap machines={machines} selectedMachineId={selectedMachineId} onSelect={setSelectedMachineId} />
          </div>

          <div className="space-y-5">
            <AiRecommendationPanel summary={summary} recommendation={recommendation} onCreateWorkOrder={createWorkOrder} />
            <WorkOrderCard workOrder={workOrder} />
          </div>
        </section>

        <section className="mt-5 grid gap-5 xl:grid-cols-[0.9fr_1.4fr]">
          <section className="glass-panel rounded-lg p-4">
            <div className="flex items-center gap-3">
              <Activity className="h-5 w-5 text-fluent-warning" />
              <h2 className="text-lg font-semibold text-zinc-50">Demo Narrative</h2>
            </div>
            <div className="mt-4 space-y-3 text-sm leading-6 text-azure-100/65">
              <p>1. Sensor data is simulated for this hackathon demo, using realistic industrial telemetry patterns.</p>
              <p>2. In production, data would arrive from PLC, IoT Gateway, OPC UA, MQTT, or IoT Hub streams.</p>
              <p>3. The AI layer receives a compact machine summary, not hundreds of raw time-series rows.</p>
              <p>4. The digital twin stores the latest machine state and line relationships for Packaging Line 1.</p>
              <p>5. The value is earlier warning, less unplanned downtime, and faster maintenance decisions.</p>
            </div>
          </section>

          <div className="space-y-5">
            <ArchitectureFlow />
            <section className="glass-panel rounded-lg p-4">
              <h2 className="text-lg font-semibold text-zinc-50">Selected Machine Snapshot</h2>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <Snapshot label="Machine" value={selectedMachine.displayName} />
                <Snapshot label="Rolling vibration avg" value={`${selectedMachine.rollingAvg.vibration} mm/s`} />
                <Snapshot label="Rolling temp avg" value={`${selectedMachine.rollingAvg.temperature} C`} />
                <Snapshot label="Likely cause" value={summary.likelyCause} />
              </div>
            </section>
          </div>
        </section>
      </div>
    </main>
  );
}

function Snapshot({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-azure-400/15 bg-azure-950/65 p-3">
      <p className="text-xs uppercase tracking-wide text-azure-100/50">{label}</p>
      <p className="mt-2 text-sm font-semibold text-zinc-100">{value}</p>
    </div>
  );
}
