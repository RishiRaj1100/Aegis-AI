// AegisAI domain types — shared across UI + API hook
export type RiskLevel = "low" | "medium" | "high";

export interface SimilarTask {
  id: string;
  title: string;
  outcome: "success" | "partial" | "failed";
  similarity: number; // 0..1
}

export interface AgentDebate {
  optimist: string;
  risk: string;
  final_decision: string;
}

export interface WorkflowNode {
  id: string;
  label: string;
  next?: string[];
}

export interface ExecutionLog {
  ts: string; // ISO timestamp
  level: "info" | "warn" | "error" | "success";
  source: string;
  message: string;
}

export interface MemoryNode {
  id: string;
  label: string;
  weight: number; // 0..1
  group: "task" | "context" | "outcome";
}

export interface DecisionResponse {
  decision: string;
  success_probability: number; // 0..1
  risk_level: RiskLevel;
  explanation: string;
  similar_tasks: SimilarTask[];
  agent_debate: AgentDebate;
  workflow: string; // mermaid source
  workflow_nodes?: WorkflowNode[];
  logs: ExecutionLog[];
  memory_nodes: MemoryNode[];
  subtasks: string[];
}

export type Language = "en" | "hi";

export interface TaskRequest {
  task: string;
  language: Language;
}
