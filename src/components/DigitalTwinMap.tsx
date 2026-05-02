import { Cpu, Factory, Link2 } from "lucide-react";
import type { MachineId, MachineState } from "../types";

interface DigitalTwinMapProps {
  machines: MachineState[];
  selectedMachineId: MachineId;
  onSelect: (machineId: MachineId) => void;
}

const nodeStyles = {
  normal: "border-fluent-success/50 bg-fluent-success/10 text-green-200",
  warning: "border-fluent-warning/60 bg-fluent-warning/10 text-amber-100",
  critical: "border-fluent-danger/70 bg-fluent-danger/20 text-red-100 shadow-[0_0_34px_rgba(209,52,56,0.28)]",
};

export default function DigitalTwinMap({ machines, selectedMachineId, onSelect }: DigitalTwinMapProps) {
  return (
    <section className="glass-panel rounded-lg p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-zinc-50">Digital Twin Health View</h2>
          <p className="mt-1 text-sm text-azure-100/50">Packaging Line 1 machine state and relationships</p>
        </div>
        <Factory className="h-6 w-6 text-azure-300" />
      </div>

      <div className="mt-6 flex flex-col items-stretch gap-3 lg:flex-row lg:items-center">
        {machines.map((machine, index) => (
          <div key={machine.machineId} className="flex flex-1 flex-col gap-3 lg:flex-row lg:items-center">
            <button
              type="button"
              onClick={() => onSelect(machine.machineId)}
              className={`min-h-36 rounded-lg border p-4 text-left transition hover:border-azure-300/70 ${
                nodeStyles[machine.status]
              } ${selectedMachineId === machine.machineId ? "ring-2 ring-azure-300/60" : ""}`}
            >
              <div className="flex items-center justify-between">
                <Cpu className="h-5 w-5" />
                <span className="text-xs font-bold uppercase">{machine.status}</span>
              </div>
              <h3 className="mt-4 text-xl font-semibold">{machine.displayName}</h3>
              <p className="mt-1 text-sm opacity-75">{machine.role}</p>
              <div className="mt-4 flex items-center justify-between text-sm">
                <span>Health {machine.healthScore}%</span>
                <span>Anomaly {machine.anomalyScore}</span>
              </div>
            </button>
            {index < machines.length - 1 ? (
              <div className="flex items-center justify-center text-azure-300/40 lg:w-10">
                <Link2 className="h-5 w-5 rotate-90 lg:rotate-0" />
              </div>
            ) : null}
          </div>
        ))}
      </div>
    </section>
  );
}
