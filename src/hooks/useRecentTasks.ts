import { useCallback, useEffect, useState } from "react";

export interface RecentTask {
  id: string;
  task: string;
  decision: string;
  risk: "low" | "medium" | "high";
  probability: number;
  ts: number;
}

const KEY = "aegis.recent.v1";
const MAX = 8;

function read(): RecentTask[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const arr = JSON.parse(raw);
    return Array.isArray(arr) ? arr : [];
  } catch {
    return [];
  }
}

export function useRecentTasks() {
  const [items, setItems] = useState<RecentTask[]>([]);

  useEffect(() => {
    setItems(read());
  }, []);

  const add = useCallback((t: Omit<RecentTask, "id" | "ts">) => {
    setItems((prev) => {
      const next = [{ ...t, id: crypto.randomUUID(), ts: Date.now() }, ...prev].slice(0, MAX);
      try {
        localStorage.setItem(KEY, JSON.stringify(next));
      } catch {}
      return next;
    });
  }, []);

  const clear = useCallback(() => {
    setItems([]);
    try {
      localStorage.removeItem(KEY);
    } catch {}
  }, []);

  return { items, add, clear };
}
