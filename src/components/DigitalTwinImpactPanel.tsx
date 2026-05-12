import { useState } from "react";
import { useTwinDependencies } from "../hooks/useTwinDependencies";

type DigitalTwinImpactPanelProps = {
  baseUrl: string;
};

const twinOptions = [
  { id: "motor-A", label: "Motor A" },
  { id: "motor-B", label: "Motor B" },
  { id: "conveyor-C", label: "Conveyor C" },
];

export function DigitalTwinImpactPanel({ baseUrl }: DigitalTwinImpactPanelProps) {
  const [selectedTwinId, setSelectedTwinId] = useState("motor-A");
  const effectiveBaseUrl = baseUrl || "http://localhost:8000";
  const { data, loading, error } = useTwinDependencies(effectiveBaseUrl, selectedTwinId);

  const dependencyPath =
    data && data.graph.length > 0
      ? [data.root.id, ...data.graph.map((edge) => edge.targetId)].join(" → ")
      : data?.root.id ?? selectedTwinId;

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Azure Digital Twins
          </p>

          <h2 className="text-lg font-semibold text-slate-900">
            Impact Analysis
          </h2>

          <p className="text-sm text-slate-500">
            Shows downstream assets affected by the selected twin.
          </p>
       
	  <p className="text-xs text-slate-400">
            API: {effectiveBaseUrl}
	  </p>
	  </div>

        <select
          value={selectedTwinId}
          onChange={(event) => setSelectedTwinId(event.target.value)}
          className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700"
        >
          {twinOptions.map((option) => (
            <option key={option.id} value={option.id}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <p className="text-sm text-slate-500">
          Loading digital twin graph...
        </p>
      ) : null}

      {error ? (
        <p className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      ) : null}

      {data && !loading && !error ? (
        <div className="space-y-4">
          <div className="rounded-xl bg-slate-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Dependency Path
            </p>

            <p className="mt-1 text-base font-semibold text-slate-900">
              {dependencyPath}
            </p>
          </div>

          <div className="rounded-xl border border-slate-200 p-4">
            <p className="mb-2 text-sm font-semibold text-slate-700">
              Affected Assets
            </p>

            {data.dependencies.length === 0 ? (
              <p className="text-sm text-slate-500">
                No downstream dependencies found.
              </p>
            ) : (
              <div className="grid gap-3 md:grid-cols-2">
                {data.dependencies.map((node) => (
                  <div
                    key={node.id}
                    className="rounded-xl border border-slate-200 bg-slate-50 p-4"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold text-slate-900">
                          {node.name ?? node.id}
                        </p>

                        <p className="text-xs text-slate-500">
                          {node.id}
                        </p>

                        {node.machineType ? (
                          <p className="mt-1 text-xs text-slate-500">
                            {node.machineType}
                          </p>
                        ) : null}
                      </div>

                      <span className="rounded-full bg-emerald-100 px-2 py-1 text-xs font-semibold text-emerald-700">
                        {node.status ?? "Unknown"}
                      </span>
                    </div>

                    <div className="mt-3 grid grid-cols-3 gap-2 text-xs text-slate-600">
                      <div>
                        <p className="text-slate-400">Health</p>
                        <p className="font-semibold text-slate-800">
                          {node.healthScore ?? "-"}
                        </p>
                      </div>

                      <div>
                        <p className="text-slate-400">Temp</p>
                        <p className="font-semibold text-slate-800">
                          {node.temperature ?? "-"}
                        </p>
                      </div>

                      <div>
                        <p className="text-slate-400">Load</p>
                        <p className="font-semibold text-slate-800">
                          {node.energyLoad ?? "-"}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-xl border border-slate-200 p-4">
            <p className="mb-2 text-sm font-semibold text-slate-700">
              Graph Edges
            </p>

            {data.graph.length === 0 ? (
              <p className="text-sm text-slate-500">
                No graph edges found.
              </p>
            ) : (
              <div className="space-y-2">
                {data.graph.map((edge) => (
                  <div
                    key={edge.relationshipId}
                    className="flex flex-wrap items-center gap-2 text-sm text-slate-700"
                  >
                    <span className="font-semibold">
                      {edge.sourceId}
                    </span>

                    <span className="rounded-full bg-blue-50 px-2 py-1 text-xs font-semibold text-blue-700">
                      {edge.relationshipName}
                    </span>

                    <span className="font-semibold">
                      {edge.targetId}
                    </span>

                    <span className="text-xs text-slate-400">
                      depth {edge.depth}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : null}
    </section>
  );
}
