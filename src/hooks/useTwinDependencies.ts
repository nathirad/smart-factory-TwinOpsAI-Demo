import { useEffect, useState } from "react";
import { fetchTwinDependencies } from "../api/client";
import type { TwinDependenciesApiResponse } from "../api/types";

export function useTwinDependencies(baseUrl: string, twinId: string) {
  const [data, setData] = useState<TwinDependenciesApiResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!baseUrl || !twinId) return;

    let cancelled = false;

    async function loadDependencies() {
      try {
        setLoading(true);
        setError(null);

        const result = await fetchTwinDependencies(baseUrl, twinId);

        if (!cancelled) {
          setData(result);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load twin dependencies");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadDependencies();

    return () => {
      cancelled = true;
    };
  }, [baseUrl, twinId]);

  return {
    data,
    loading,
    error,
  };
}
