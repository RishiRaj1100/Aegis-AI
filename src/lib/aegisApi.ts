import type { DecisionResponse, Language, TaskRequest } from "@/types/aegis";

const API_BASE = (import.meta as any).env?.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

const languageMap: Record<Language, string> = {
  en: "en-IN",
  hi: "hi-IN",
};

function toMermaidFromGraph(graph: any): string {
  if (!graph?.nodes?.length) {
    return "flowchart TD\n  A[\"Task\"] --> B[\"Decision\"] --> C[\"Reflection\"]";
  }
  const lines = ["flowchart TD"];
  for (const node of graph.nodes) {
    // Sanitize ID: only alphanumeric and underscores
    const id = String(node.id).replace(/[^a-zA-Z0-9_]/g, "_");
    // Sanitize Label: replace double quotes with single, remove newlines
    const label = String(node.label ?? node.id)
      .replace(/"/g, "'")
      .replace(/\n/g, " ")
      .replace(/\r/g, "")
      .trim();
    lines.push(`  ${id}["${label}"]`);
  }
  for (const edge of graph.edges ?? []) {
    const source = String(edge.source).replace(/[^a-zA-Z0-9_]/g, "_");
    const target = String(edge.target).replace(/[^a-zA-Z0-9_]/g, "_");
    lines.push(`  ${source} --> ${target}`);
  }
  return lines.join("\n");
}

function normalizeLogLevel(value: string): "info" | "warn" | "error" | "success" {
  if (value === "warn") return "warn";
  if (value === "error") return "error";
  if (value === "success") return "success";
  return "info";
}

function mapAnalyzeResponse(raw: any): DecisionResponse {
  const graph = raw.execution_graph ?? {};
  const risk = String(raw.risk_level ?? "MEDIUM").toUpperCase() as "LOW" | "MEDIUM" | "HIGH";
  return {
    task_id: String(raw.task_id ?? crypto.randomUUID()),
    decision: String(raw.debate?.final_decision ?? "Decision synthesis completed."),
    success_probability: Number(raw.success_probability ?? 0.5),
    delay_risk: Number(raw.delay_risk ?? 0.5),
    risk_level: risk,
    explanation: String(raw.reasoning ?? ""),
    similar_tasks: (raw.similar_tasks ?? []).map((item: any) => ({
      task: String(item.task ?? ""),
      outcome: String(item.outcome ?? "unknown"),
      similarity: Number(item.similarity ?? 0),
    })),
    agent_debate: {
      optimist: String(raw.debate?.optimist ?? ""),
      risk: String(raw.debate?.risk ?? ""),
      executor: String(raw.debate?.executor ?? ""),
      final_decision: String(raw.debate?.final_decision ?? ""),
      confidence: Number(raw.debate?.confidence ?? 0.5),
    },
    workflow: toMermaidFromGraph(graph),
    logs: (raw.traces ?? []).map((trace: any) => ({
      ts: String(trace.timestamp ?? new Date().toISOString()),
      level: normalizeLogLevel("info"),
      source: String(trace.agent ?? "pipeline"),
      message: `Latency ${Math.round(Number(trace.latency_ms ?? 0))}ms`,
    })),
    memory_nodes: (graph.nodes ?? []).map((node: any) => ({
      id: String(node.id),
      label: String(node.label ?? node.id),
      weight: 0.7,
      group: node.type === "reflection" ? "outcome" : node.type === "decision" ? "context" : "task",
    })),
    subtasks: (raw.execution_plan ?? []).map((step: any) => String(step)),
    recommendations: (raw.recommendations ?? []).map((r: any) => String(r)),
    trust_analysis: raw.trust_analysis ?? {},
  };
}

export async function submitTask(req: TaskRequest): Promise<DecisionResponse> {
  const res = await fetch(`${API_BASE}/analyze_task`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    body: JSON.stringify({
      task: req.task,
      language: languageMap[req.language],
      context: {},
    }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Task failed: ${res.status} ${detail}`);
  }
  const raw = await res.json();
  return mapAnalyzeResponse(raw);
}

export async function submitVoice(blob: Blob, language: Language): Promise<{ transcript: string; detected_language: Language }> {
  if (!API_BASE) throw new Error("VITE_API_BASE_URL is not configured");
  const fd = new FormData();
  fd.append("audio", blob, "voice.webm");
  fd.append("language", language);
  const res = await fetch(`${API_BASE}/voice-input`, { method: "POST", body: fd, cache: "no-store" });
  if (!res.ok) throw new Error(`Voice failed: ${res.status}`);
  return res.json();
}

export async function sendFeedback(payload: { decision: string; rating: "up" | "down"; note?: string }): Promise<void> {
  await fetch(`${API_BASE}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    body: JSON.stringify({
      task_id: payload.note || "ui-feedback",
      predicted_success: payload.rating === "up" ? 1.0 : 0.0,
      actual_outcome: payload.rating === "up" ? "success" : "failed",
      notes: payload.decision,
    }),
  });
}
