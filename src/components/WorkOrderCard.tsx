import { CalendarClock, Wrench } from "lucide-react";
import type { ReactNode } from "react";
import type { WorkOrder } from "../types";

interface WorkOrderCardProps {
  workOrder: WorkOrder | null;
}

export default function WorkOrderCard({ workOrder }: WorkOrderCardProps) {
  if (!workOrder) {
    return (
      <section className="glass-panel rounded-lg p-4">
        <div className="flex items-center gap-3">
          <Wrench className="h-5 w-5 text-azure-300/60" />
          <div>
            <h2 className="text-lg font-semibold text-zinc-50">Maintenance Action Simulation</h2>
            <p className="mt-1 text-sm text-azure-100/50">Create a work order from the AI recommendation.</p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="rounded-lg border border-azure-300/35 bg-azure-500/10 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <Wrench className="h-5 w-5 text-azure-300" />
          <div>
            <h2 className="text-lg font-semibold text-zinc-50">Work Order Created</h2>
            <p className="mt-1 text-sm text-azure-100/50">{workOrder.id}</p>
          </div>
        </div>
        <span className="rounded bg-fluent-danger px-2 py-1 text-xs font-bold uppercase text-white">{workOrder.priority}</span>
      </div>

      <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
        <Field label="Machine" value={workOrder.machineId} />
        <Field label="Assigned Team" value={workOrder.assignedTeam} />
        <Field label="Due Time" value={workOrder.dueTime} icon={<CalendarClock className="h-4 w-4 text-azure-300" />} />
        <Field label="Recommended Action" value={workOrder.recommendedAction} />
      </div>
    </section>
  );
}

function Field({ label, value, icon }: { label: string; value: string; icon?: ReactNode }) {
  return (
    <div className="rounded-md bg-azure-950/70 p-3">
      <p className="flex items-center gap-2 text-xs uppercase tracking-wide text-azure-100/50">
        {icon}
        {label}
      </p>
      <p className="mt-1 font-medium text-zinc-100">{value}</p>
    </div>
  );
}
