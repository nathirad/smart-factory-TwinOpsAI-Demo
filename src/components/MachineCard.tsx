import { Activity, Gauge, Thermometer, Zap, type LucideIcon } from "lucide-react";
import type { MachineId, MachineState } from "../types";

interface MachineCardProps {
  machine: MachineState;
  selected: boolean;
  onSelect: (machineId: MachineId) => void;
}

const statusStyles = {
  normal: "bg-fluent-success text-white",
  warning: "bg-fluent-warning text-zinc-950",
  critical: "bg-fluent-danger text-white",
};

const borderStyles = {
  normal: "border-fluent-success/35",
  warning: "border-fluent-warning/45",
  critical: "border-fluent-danger/55",
};

export default function MachineCard({ machine, selected, onSelect }: MachineCardProps) {
  return (
    <button
      type="button"
      onClick={() => onSelect(machine.machineId)}
      className={`w-full rounded-lg border p-4 text-left transition hover:-translate-y-0.5 hover:border-azure-300/70 ${
        selected ? "bg-azure-950/80 ring-2 ring-azure-300/55" : "bg-azure-950/45"
      } ${borderStyles[machine.status]}`}
      aria-pressed={selected}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className={`h-2.5 w-2.5 rounded-full ${statusStyles[machine.status]} ${machine.status === "critical" ? "status-pulse" : ""}`} />
            <h3 className="text-base font-semibold text-zinc-50">{machine.displayName}</h3>
          </div>
          <p className="mt-1 text-xs text-azure-100/50">{machine.role}</p>
        </div>
        <span className={`rounded px-2 py-1 text-xs font-bold uppercase ${statusStyles[machine.status]}`}>
          {machine.riskLevel}
        </span>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3 text-sm">
        <Metric icon={Activity} label="Vibration" value={`${machine.current.vibration} mm/s`} />
        <Metric icon={Thermometer} label="Temp" value={`${machine.current.temperature} C`} />
        <Metric icon={Zap} label="Energy" value={`${machine.current.energyKw} kW`} />
        <Metric icon={Gauge} label="Health" value={`${machine.healthScore}%`} />
      </div>

      <div className="mt-4 h-2 rounded-full bg-azure-900/80">
        <div
          className={`h-2 rounded-full ${
            machine.riskLevel === "High" ? "bg-fluent-danger" : machine.riskLevel === "Medium" ? "bg-fluent-warning" : "bg-fluent-success"
          }`}
          style={{ width: `${machine.healthScore}%` }}
        />
      </div>
    </button>
  );
}

function Metric({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2 rounded-md bg-azure-950/70 px-2 py-2">
      <Icon className="h-4 w-4 text-azure-300/70" />
      <div className="min-w-0">
        <p className="truncate text-[11px] uppercase tracking-wide text-azure-100/50">{label}</p>
        <p className="truncate font-medium text-zinc-200">{value}</p>
      </div>
    </div>
  );
}
