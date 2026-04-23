/**
 * AegisAI frontend runtime API configuration.
 * All API route paths should be defined here to avoid hardcoded URLs elsewhere.
 */

const DEFAULT_API_BASE = "http://localhost:8000";

function resolveApiBase() {
  const configuredBase =
    (typeof import.meta !== "undefined" && import.meta.env && import.meta.env.VITE_API_BASE_URL) ||
    DEFAULT_API_BASE;

  if (typeof window !== "undefined") {
    try {
      const currentOrigin = new URL(window.location.origin);
      const parsedBase = new URL(configuredBase, window.location.origin);
      const localHosts = new Set(["localhost", "127.0.0.1", "[::1]"]);

      if (currentOrigin.port === parsedBase.port && localHosts.has(currentOrigin.hostname) && localHosts.has(parsedBase.hostname)) {
        return window.location.origin;
      }
    } catch {
      return configuredBase;
    }
  }

  return configuredBase;
}

export const API_BASE = resolveApiBase();

export const ENDPOINTS = {
  // Auth
  REGISTER: `${API_BASE}/auth/register`,
  LOGIN: `${API_BASE}/auth/login`,
  REFRESH: `${API_BASE}/auth/refresh`,
  ME: `${API_BASE}/auth/me`,

  // Pipeline
  PROCESS: `${API_BASE}/goal`,
  PROCESS_STREAM: `${API_BASE}/api/process-stream`,
  GOAL: `${API_BASE}/goal`,
  GOAL_VOICE: `${API_BASE}/goal/voice`,
  GOAL_OUTCOME: `${API_BASE}/goal/outcome`,
  GOAL_FOLLOWUP: `${API_BASE}/goal/followup`,

  // Plans
  PLAN: (taskId) => `${API_BASE}/plan/${taskId}`,
  PLAN_SUBTASKS: (taskId) => `${API_BASE}/plan/${taskId}/subtasks`,
  PLAN_TRANSLATE: (taskId) => `${API_BASE}/plan/${taskId}/translate`,

  // Confidence
  CONFIDENCE: (taskId) => `${API_BASE}/confidence/${taskId}`,
  CONFIDENCE_COMPONENTS: (taskId) => `${API_BASE}/confidence/${taskId}/components`,

  // Intelligence
  INTELLIGENCE_TASKS: `${API_BASE}/intelligence/tasks`,
  INTELLIGENCE_OVERVIEW: `${API_BASE}/intelligence/overview`,
  INTELLIGENCE_GRAPH: (taskId) => `${API_BASE}/intelligence/graph/${taskId}`,
  INTELLIGENCE_SIMILAR: (taskId) => `${API_BASE}/intelligence/similar/${taskId}`,
  INTELLIGENCE_SIMILAR_GOAL: `${API_BASE}/intelligence/similar`,
  INTELLIGENCE_PROFILE: `${API_BASE}/intelligence/profile`,
  INTELLIGENCE_PREDICT: `${API_BASE}/intelligence/predict`,
  INTELLIGENCE_SIMULATE: `${API_BASE}/intelligence/simulate`,
  INTELLIGENCE_WORKFLOW_PARSE: `${API_BASE}/intelligence/workflow/parse`,
  INTELLIGENCE_MODELS: `${API_BASE}/intelligence/models`,
  INTELLIGENCE_DRIFT: `${API_BASE}/intelligence/drift`,
  INTELLIGENCE_REFLECTION_REPORT: `${API_BASE}/intelligence/reflection/report`,
  INTELLIGENCE_OVERRIDE: `${API_BASE}/intelligence/override`,
  INTELLIGENCE_HEALTH: `${API_BASE}/intelligence/health`,

  // System
  ANALYTICS: `${API_BASE}/analytics`,
  HEALTH: `${API_BASE}/health`,
};
