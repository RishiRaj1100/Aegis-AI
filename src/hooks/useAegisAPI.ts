import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { AegisResponse, TaskHistory } from '@/types/aegis';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

// ── Submit a new goal ────────────────────────────────────────────────────────
export function useSubmitGoal() {
  const qc = useQueryClient();
  return useMutation<AegisResponse, Error, { goal: string; language: string }>({
    mutationFn: async ({ goal, language }) => {
      const res = await fetch(`${API_BASE}/goal`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          goal,
          language,
          modality: 'text',
          context: {},
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(err.detail || 'Failed to process goal');
      }
      return res.json();
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['taskHistory'] });
    },
  });
}

// ── Task history ─────────────────────────────────────────────────────────────
export function useTaskHistory() {
  return useQuery<TaskHistory[]>({
    queryKey: ['taskHistory'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/tasks/history?limit=20`);
      if (!res.ok) return [];
      const data = await res.json();
      return data.tasks || data || [];
    },
    staleTime: 30_000,
    retry: false,
  });
}

// ── Health check ─────────────────────────────────────────────────────────────
export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/health`);
      return res.json();
    },
    refetchInterval: 30_000,
    retry: false,
  });
}

// ── Reload a specific task by ID ──────────────────────────────────────────────
export function useTaskById(taskId: string | null) {
  return useQuery<AegisResponse>({
    queryKey: ['task', taskId],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/tasks/${taskId}`);
      if (!res.ok) throw new Error('Task not found');
      return res.json();
    },
    enabled: !!taskId,
    retry: false,
  });
}
