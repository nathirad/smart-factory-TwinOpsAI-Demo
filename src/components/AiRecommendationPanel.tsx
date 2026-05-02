import { BrainCircuit, ClipboardCheck, Gauge, Lightbulb, ShieldAlert, type LucideIcon } from "lucide-react";
import type { AiRecommendation, MachineSummaryContext } from "../types";

interface AiRecommendationPanelProps {
  summary: MachineSummaryContext;
  recommendation: AiRecommendation;
  onCreateWorkOrder: () => void;
}

const urgencyStyles = {
  Low: "bg-fluent-success/15 text-green-300 border-fluent-success/35",
  Medium: "bg-fluent-warning/15 text-amber-200 border-fluent-warning/35",
  High: "bg-fluent-danger/15 text-red-200 border-fluent-danger/40",
};

export default function AiRecommendationPanel({ summary, recommendation, onCreateWorkOrder }: AiRecommendationPanelProps) {
  return (
    <aside className="glass-panel rounded-lg p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-zinc-50">AI Recommendation</h2>
          <p className="mt-1 text-sm text-azure-100/50">Summarized context, not raw sensor rows</p>
        </div>
        <BrainCircuit className="h-6 w-6 text-azure-300" />
      </div>

      <div className="mt-5 rounded-lg border border-azure-400/15 bg-azure-950/60 p-3">
        <div className="flex items-center justify-between gap-3">
          <span className="text-sm font-semibold text-azure-100">{summary.machineId}</span>
          <span className={`rounded border px-2 py-1 text-xs font-bold uppercase ${urgencyStyles[summary.risk]}`}>{summary.risk}</span>
        </div>
        <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
          <Metric label="Vib z" value={`${summary.vibration.zScore}`} />
          <Metric label="Temp delta" value={`${summary.temperature.increaseCelsius} C`} />
          <Metric label="Energy" value={`${summary.energy.increasePercent}%`} />
        </div>
      </div>

      <div className="mt-5 space-y-4">
        <PanelItem icon={ShieldAlert} title="Likely Issue" text={recommendation.likelyIssue} />
        <PanelItem icon={Gauge} title="Evidence" text={recommendation.evidence} />
        <PanelItem icon={Lightbulb} title="Recommended Action" text={recommendation.recommendedAction} />
        <PanelItem icon={ClipboardCheck} title="Business Impact" text={recommendation.businessImpact} />
      </div>

      <button
        type="button"
        onClick={onCreateWorkOrder}
        className="mt-5 flex w-full items-center justify-center gap-2 rounded-md bg-azure-500 px-4 py-3 text-sm font-bold text-white transition hover:bg-azure-400"
      >
        <ClipboardCheck className="h-4 w-4" />
        Create Work Order
      </button>
    </aside>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-azure-900/70 px-2 py-2">
      <p className="text-azure-100/50">{label}</p>
      <p className="mt-1 font-semibold text-zinc-100">{value}</p>
    </div>
  );
}

function PanelItem({ icon: Icon, title, text }: { icon: LucideIcon; title: string; text: string }) {
  return (
    <div className="flex gap-3">
      <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-azure-900/70 text-azure-300">
        <Icon className="h-4 w-4" />
      </div>
      <div>
        <h3 className="text-sm font-semibold text-zinc-200">{title}</h3>
        <p className="mt-1 text-sm leading-6 text-azure-100/55">{text}</p>
      </div>
    </div>
  );
}
