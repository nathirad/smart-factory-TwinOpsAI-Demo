import type { LucideIcon } from "lucide-react";

interface KpiCardProps {
  title: string;
  value: string;
  detail: string;
  tone: "green" | "amber" | "red" | "azure";
  icon: LucideIcon;
}

const toneStyles = {
  green: "border-fluent-success/35 bg-fluent-success/15 text-green-300",
  amber: "border-fluent-warning/35 bg-fluent-warning/15 text-amber-200",
  red: "border-fluent-danger/35 bg-fluent-danger/15 text-red-200",
  azure: "border-azure-400/35 bg-azure-500/15 text-azure-200",
};

export default function KpiCard({ title, value, detail, tone, icon: Icon }: KpiCardProps) {
  return (
    <section className="glass-panel rounded-lg p-4 shadow-glow">
      <div className="flex items-center justify-between gap-3">
        <div className={`rounded-md border p-2 ${toneStyles[tone]}`}>
          <Icon className="h-5 w-5" />
        </div>
        <span className="text-xs font-semibold uppercase tracking-wide text-azure-200/60">Live</span>
      </div>
      <div className="mt-5">
        <p className="text-sm text-azure-100/70">{title}</p>
        <p className="mt-1 text-3xl font-semibold tracking-normal text-zinc-50">{value}</p>
        <p className="mt-2 text-sm text-azure-100/50">{detail}</p>
      </div>
    </section>
  );
}
