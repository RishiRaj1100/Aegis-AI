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
  id: string;
  goal: string;
  success: boolean;
  confidence?: number;
  completed_at?: string;
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
  explainability?: Record<string, number>;
  trust_dimensions?: TrustDimension;
  similar_tasks?: SimilarTask[];
  reflection?: {
    past_prediction?: number;
    current_prediction?: number;
    improvement_delta?: number;
    insights?: string[];
  };
  model_outputs?: Record<string, unknown>;
  system_confidence?: number;
  fallback_used?: boolean;
  system_trace?: string[];
}

export interface TaskHistory {
  task_id: string;
  goal: string;
  confidence?: number;
  risk_level?: string;
  created_at?: string;
  processing_time_ms?: number;
}
