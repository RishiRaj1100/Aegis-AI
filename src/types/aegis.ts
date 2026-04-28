// Shared TypeScript types for AegisAI API responses

export interface Subtask {
  id?: string;
  title: string;
  name?: string;
  description?: string;
  trust_score?: number;
  confidence?: number;
  status?: 'pending' | 'active' | 'done' | 'failed';
  priority?: 'LOW' | 'MEDIUM' | 'HIGH';
  deadline_days?: number;
}

export interface DebateResult {
  optimist?: string;
  risk_analyst?: string;
  executor?: string;
  critic?: string;
  final_decision?: string;
  reasoning?: string;
  consensus_score?: number;
}

export interface ShapFactor {
  feature: string;
  value: number;
  impact: 'positive' | 'negative';
}

export interface SimilarTask {
  task_id: string;
  goal: string;
  confidence: number;
  risk_level: string;
  similarity: number;
  status: string;
  execution_plan?: string;
  resources?: string[];
  insights?: string;
}

export interface TrustDimension {
  claims?: Array<{
    claim: string;
    verified: boolean;
    evidence: string[];
  }>;
  dimensions?: {
    goal_clarity: number;
    information_quality: number;
    execution_feasibility: number;
    risk_manageability: number;
    resource_adequacy: number;
    external_uncertainty: number;
  };
  delay_risk?: number;
  confidence_score?: number;
}

export interface AegisResponse {
  task_id?: string;
  goal?: string;
  confidence?: number;
  risk_level?: 'LOW' | 'MEDIUM' | 'HIGH';
  processing_time_ms?: number;
  reasoning_provider?: string;
  plan?: {
    goal?: string;
    task_id?: string;
    subtasks?: Subtask[];
    research_insights?: string;
    dimensions?: TrustDimension;
    debate_results?: DebateResult;
    reasoning?: string;
    confidence?: number;
    risk_level?: string;
  };
  subtasks?: Subtask[];
  debate_results?: DebateResult;
  explainability?: {
    positive_factors?: string[];
    negative_factors?: string[];
    shap_values?: Record<string, number>;
    warning?: string;
  };
  trust_dimensions?: TrustDimension;
  similar_tasks?: SimilarTask[];
  reflection?: {
    past_prediction?: number;
    current_prediction?: number;
    improvement_delta?: number;
    insights?: string[];
  };
  execution_graph?: {
    task_id: string;
    goal: string;
    nodes: Array<{ id: string; label: string; type: string; status: string }>;
    edges: Array<{ source: string; target: string; label: string }>;
    mermaid: string;
  };
  model_outputs?: Record<string, unknown>;
  system_confidence?: number;
  fallback_used?: boolean;
  system_trace?: string[];
  audio_response_base64?: string;
}

export interface FollowUpResponse {
  task_id: string;
  reply: string;
  audio_base64?: string;
  language?: string;
}

export interface TaskHistory {
  task_id: string;
  goal: string;
  confidence?: number;
  risk_level?: string;
  created_at?: string;
  processing_time_ms?: number;
}
