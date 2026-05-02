import { Bot, Database, Factory, GitBranch, LineChart, RadioTower, Wrench } from "lucide-react";

const steps = [
  { label: "Sensor / PLC / IoT Gateway", icon: RadioTower, tone: "text-fluent-cyan" },
  { label: "Time-Series Storage", icon: Database, tone: "text-azure-300" },
  { label: "Anomaly Detection", icon: LineChart, tone: "text-fluent-warning" },
  { label: "Digital Twin State", icon: Factory, tone: "text-azure-200" },
  { label: "GPT-4o AI Recommendation", icon: Bot, tone: "text-azure-400" },
  { label: "Maintenance Work Order", icon: Wrench, tone: "text-fluent-cyan" },
];

export default function ArchitectureFlow() {
  return (
    <section className="glass-panel rounded-lg p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-zinc-50">Production Architecture Path</h2>
          <p className="mt-1 text-sm text-azure-100/50">Hackathon MVP today, backend-ready tomorrow</p>
        </div>
        <GitBranch className="h-5 w-5 text-azure-300/60" />
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-3 xl:grid-cols-6">
        {steps.map((step, index) => (
          <div key={step.label} className="relative rounded-lg border border-azure-400/15 bg-azure-950/60 p-3">
            <step.icon className={`h-5 w-5 ${step.tone}`} />
            <p className="mt-3 min-h-10 text-sm font-medium leading-5 text-zinc-200">{step.label}</p>
            {index < steps.length - 1 ? (
              <span className="absolute -right-2 top-1/2 hidden h-5 w-5 -translate-y-1/2 items-center justify-center rounded-full border border-azure-400/20 bg-azure-950 text-xs text-azure-200/60 xl:flex">
                &gt;
              </span>
            ) : null}
          </div>
        ))}
      </div>
    </section>
  );
}
