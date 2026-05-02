import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TelemetryPoint } from "../types";

interface TelemetryChartProps {
  data: TelemetryPoint[];
}

function formatTime(timestamp: string): string {
  return new Date(timestamp).toLocaleTimeString([], { minute: "2-digit", second: "2-digit" });
}

export default function TelemetryChart({ data }: TelemetryChartProps) {
  const chartData = data.map((point) => ({
    ...point,
    time: formatTime(point.timestamp),
  }));

  return (
    <section className="glass-panel rounded-lg p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-zinc-50">Live Machine Telemetry</h2>
          <p className="mt-1 text-sm text-azure-100/50">Last 5 minutes, sampled every 5 seconds</p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs">
          <span className="rounded bg-azure-400/15 px-2 py-1 text-azure-200">Vibration</span>
          <span className="rounded bg-fluent-warning/15 px-2 py-1 text-amber-200">Temperature</span>
          <span className="rounded bg-fluent-success/15 px-2 py-1 text-green-300">Energy</span>
        </div>
      </div>

      <div className="mt-4 h-80 min-h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 10, right: 12, left: -12, bottom: 0 }}>
            <CartesianGrid stroke="#123B61" strokeDasharray="3 3" />
            <XAxis dataKey="time" stroke="#8EC8FF" tick={{ fontSize: 11 }} minTickGap={22} />
            <YAxis stroke="#8EC8FF" tick={{ fontSize: 11 }} />
            <Tooltip
              contentStyle={{
                background: "#001B33",
                border: "1px solid rgba(80, 230, 255, 0.25)",
                borderRadius: 8,
                color: "#f4f4f5",
              }}
              labelStyle={{ color: "#d4d4d8" }}
            />
            <Legend wrapperStyle={{ color: "#B8DAFF", fontSize: 12 }} />
            <Line type="monotone" dataKey="vibration" name="Vibration mm/s" stroke="#50A7F5" strokeWidth={2.5} dot={false} />
            <Line type="monotone" dataKey="temperature" name="Temp C" stroke="#FFB900" strokeWidth={2.5} dot={false} />
            <Line type="monotone" dataKey="energyKw" name="Energy kW" stroke="#107C10" strokeWidth={2.5} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
