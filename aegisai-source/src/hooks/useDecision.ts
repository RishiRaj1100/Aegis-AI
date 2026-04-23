import { useCallback, useState } from "react";
import { submitTask } from "@/lib/aegisApi";
import type { DecisionResponse, TaskRequest } from "@/types/aegis";

export function useDecision() {
  const [data, setData] = useState<DecisionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async (req: TaskRequest) => {
    setLoading(true);
    setError(null);
    try {
      const res = await submitTask(req);
      setData(res);
      return res;
    } catch (e: any) {
      setError(e?.message ?? "Unknown error");
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setData(null);
    setError(null);
  }, []);

  return { data, loading, error, run, reset };
}
