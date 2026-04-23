/**
 * AegisAI - API Service Layer
 * Centralized fetch wrapper with authentication, error handling, and endpoint constants.
 */

// ════════════════════════════════════════════════════════════════════════════════
// Configuration
// ════════════════════════════════════════════════════════════════════════════════

import { ENDPOINTS } from "../../assets/js/config.js";

// ════════════════════════════════════════════════════════════════════════════════
// API Error Classes
// ════════════════════════════════════════════════════════════════════════════════

export class APIError extends Error {
  constructor(
    public status: number,
    public detail: string,
    message?: string
  ) {
    super(message || detail);
    this.name = "APIError";
  }
}

export class NetworkError extends Error {
  constructor(message: string = "Network request failed") {
    super(message);
    this.name = "NetworkError";
  }
}

// ════════════════════════════════════════════════════════════════════════════════
// Authenticated Fetch Wrapper
// ════════════════════════════════════════════════════════════════════════════════

interface FetchOptions extends RequestInit {
  skipAuth?: boolean;
  skipErrorHandling?: boolean;
}

const clearMissionCache = (): void => {
  const missionPrefix = "aegis_current_mission:";
  localStorage.removeItem("aegis_current_mission");
  for (let index = localStorage.length - 1; index >= 0; index -= 1) {
    const key = localStorage.key(index);
    if (key && key.startsWith(missionPrefix)) {
      localStorage.removeItem(key);
    }
  }
};

/**
 * Wrapper around fetch() that adds authentication, error handling, and logging.
 * Automatically includes Bearer token in Authorization header if available.
 * Handles 401 by clearing tokens and redirecting to login.
 */
export async function apiFetch(
  url: string,
  options: FetchOptions = {}
): Promise<any> {
  const { skipAuth = false, skipErrorHandling = false, ...fetchOptions } = options;
  const isFormDataBody = typeof FormData !== "undefined" && fetchOptions.body instanceof FormData;
  const hasBody = typeof fetchOptions.body !== "undefined" && fetchOptions.body !== null;

  // Build headers
  const headers: Record<string, string> = {
    ...((fetchOptions.headers as Record<string, string>) || {}),
  };

  if (hasBody && !isFormDataBody && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  // Add auth token if not skipped
  if (!skipAuth) {
    const token = localStorage.getItem("aegis_token");
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  // Add session ID
  const sessionId = getSessionId();
  if (sessionId) {
    headers["X-Session-ID"] = sessionId;
  }

  // Make request
  let response: Response;
  try {
    response = await fetch(url, {
      ...fetchOptions,
      headers,
    });
  } catch (error) {
    throw new NetworkError(
      error instanceof Error ? error.message : "Network request failed"
    );
  }

  // Handle 401 Unauthorized — clear auth and redirect
  if (response.status === 401) {
    localStorage.removeItem("aegis_token");
    localStorage.removeItem("aegis_refresh_token");
    localStorage.removeItem("aegis_user");
    clearMissionCache();
    // Redirect to login if not already there
    if (!window.location.pathname.includes("/login")) {
      sessionStorage.setItem("redirect_after_login", window.location.href);
      window.location.href = "/login";
    }
    throw new APIError(401, "Unauthorized. Please log in again.");
  }

  // Parse response
  let data: any;
  const contentType = response.headers.get("content-type");
  if (contentType?.includes("application/json")) {
    data = await response.json();
  } else {
    data = await response.text();
  }

  // Handle errors
  if (!response.ok) {
    if (!skipErrorHandling) {
      const detail = data?.detail || data?.message || "Request failed";
      throw new APIError(response.status, detail);
    }
  }

  return data;
}

// ════════════════════════════════════════════════════════════════════════════════
// Session Management
// ════════════════════════════════════════════════════════════════════════════════

/**
 * Generate or retrieve a session ID (UUID per browser session).
 */
export function getSessionId(): string {
  let id = sessionStorage.getItem("aegis_session_id");
  if (!id) {
    id = crypto.randomUUID();
    sessionStorage.setItem("aegis_session_id", id);
  }
  return id;
}

/**
 * Clear session ID and all session storage.
 */
export function clearSession(): void {
  sessionStorage.clear();
}

// ════════════════════════════════════════════════════════════════════════════════
// Token Management
// ════════════════════════════════════════════════════════════════════════════════

export const TokenManager = {
  /**
   * Get stored access token.
   */
  getToken: (): string | null => localStorage.getItem("aegis_token"),

  /**
   * Set access token.
   */
  setToken: (token: string): void => {
    localStorage.setItem("aegis_token", token);
  },

  /**
   * Get stored refresh token.
   */
  getRefreshToken: (): string | null => localStorage.getItem("aegis_refresh_token"),

  /**
   * Set refresh token.
   */
  setRefreshToken: (token: string): void => {
    localStorage.setItem("aegis_refresh_token", token);
  },

  /**
   * Clear all tokens and user data.
   */
  clear: (): void => {
    localStorage.removeItem("aegis_token");
    localStorage.removeItem("aegis_refresh_token");
    localStorage.removeItem("aegis_user");
    clearMissionCache();
  },

  /**
   * Check if token is valid (not expired).
   * JWT format: header.payload.signature
   */
  isValid: (): boolean => {
    const token = TokenManager.getToken();
    if (!token) return false;

    try {
      const parts = token.split(".");
      if (parts.length !== 3) return false;

      const payload = JSON.parse(atob(parts[1]));
      const expiresAt = (payload.exp || 0) * 1000; // Convert to milliseconds
      return expiresAt > Date.now();
    } catch {
      return false;
    }
  },

  /**
   * Get remaining time in seconds until token expires.
   */
  getTimeToExpiry: (): number => {
    const token = TokenManager.getToken();
    if (!token) return 0;

    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      const expiresAt = (payload.exp || 0) * 1000;
      const remaining = Math.max(0, expiresAt - Date.now());
      return Math.floor(remaining / 1000);
    } catch {
      return 0;
    }
  },

  /**
   * Decode token and return payload (for debugging).
   */
  decode: (): Record<string, any> | null => {
    const token = TokenManager.getToken();
    if (!token) return null;

    try {
      return JSON.parse(atob(token.split(".")[1]));
    } catch {
      return null;
    }
  },
};

// ════════════════════════════════════════════════════════════════════════════════
// User & Auth Data
// ════════════════════════════════════════════════════════════════════════════════

export interface User {
  id: string;
  name: string;
  email: string;
  created_at: string;
}

export const UserManager = {
  /**
   * Get stored user data.
   */
  getUser: (): User | null => {
    const userStr = localStorage.getItem("aegis_user");
    if (!userStr) return null;
    try {
      return JSON.parse(userStr);
    } catch {
      return null;
    }
  },

  /**
   * Store user data.
   */
  setUser: (user: User): void => {
    localStorage.setItem("aegis_user", JSON.stringify(user));
  },

  /**
   * Clear user data.
   */
  clear: (): void => {
    localStorage.removeItem("aegis_user");
  },
};

// ════════════════════════════════════════════════════════════════════════════════
// API Methods
// ════════════════════════════════════════════════════════════════════════════════

export const authAPI = {
  /**
   * Register a new user.
   */
  register: async (name: string, email: string, password: string) => {
    return apiFetch(ENDPOINTS.REGISTER, {
      method: "POST",
      skipAuth: true,
      body: JSON.stringify({ name, email, password }),
    });
  },

  /**
   * Log in with email and password.
   */
  login: async (email: string, password: string) => {
    return apiFetch(ENDPOINTS.LOGIN, {
      method: "POST",
      skipAuth: true,
      body: JSON.stringify({ email, password }),
    });
  },

  /**
   * Refresh access token using refresh token.
   */
  refresh: async (refreshToken: string) => {
    return apiFetch(ENDPOINTS.REFRESH, {
      method: "POST",
      skipAuth: true,
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  },

  /**
   * Get current authenticated user.
   */
  me: async () => {
    return apiFetch(ENDPOINTS.ME);
  },
};

export const goalAPI = {
  /**
   * Submit a text-based goal.
   */
  submitGoal: async (
    goal: string,
    language: string = "en-IN",
    sessionId: string = "",
    documentContext?: string
  ) => {
    const payload: any = {
      goal,
      language,
    };
    if (documentContext) {
      payload.context = { document_context: documentContext };
    }
    return apiFetch(ENDPOINTS.GOAL, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  /**
   * Submit a voice-based goal.
   */
  submitVoiceGoal: async (
    audioBase64: string,
    language: string = "en-IN",
    audioFormat: string = "webm"
  ) => {
    return apiFetch(ENDPOINTS.GOAL_VOICE, {
      method: "POST",
      body: JSON.stringify({
        audio_base64: audioBase64,
        language,
        audio_format: audioFormat,
      }),
    });
  },

  /**
   * Record the outcome of a goal/task.
   */
  recordOutcome: async (
    taskId: string,
    status: "COMPLETED" | "FAILED" | "PENDING",
    notes?: string,
    actualDuration?: number
  ) => {
    return apiFetch(ENDPOINTS.GOAL_OUTCOME, {
      method: "PUT",
      body: JSON.stringify({
        task_id: taskId,
        status,
        outcome_notes: notes,
        actual_duration_minutes: actualDuration,
      }),
    });
  },

  /**
   * Send a follow-up question or message about a task.
   */
  sendFollowup: async (
    taskId: string,
    message: string,
    language: string = "en-IN"
  ) => {
    return apiFetch(ENDPOINTS.GOAL_FOLLOWUP, {
      method: "POST",
      body: JSON.stringify({
        task_id: taskId,
        message,
        language,
      }),
    });
  },
};

export const planAPI = {
  /**
   * Get the full plan for a task.
   */
  getPlan: async (taskId: string) => {
    return apiFetch(ENDPOINTS.PLAN(taskId));
  },

  /**
   * Get subtasks for a task.
   */
  getSubtasks: async (taskId: string) => {
    return apiFetch(ENDPOINTS.PLAN_SUBTASKS(taskId));
  },

  /**
   * Get plan translated to a specified language.
   */
  translatePlan: async (taskId: string, targetLanguage: string) => {
    return apiFetch(
      `${ENDPOINTS.PLAN_TRANSLATE(taskId)}?target_language=${targetLanguage}`
    );
  },
};

export const confidenceAPI = {
  /**
   * Get confidence score for a task.
   */
  getConfidence: async (taskId: string) => {
    return apiFetch(ENDPOINTS.CONFIDENCE(taskId));
  },

  /**
   * Get individual trust components for a task.
   */
  getComponents: async (taskId: string) => {
    return apiFetch(ENDPOINTS.CONFIDENCE_COMPONENTS(taskId));
  },
};

export const analyticsAPI = {
  /**
   * Get aggregated analytics data.
   */
  getAnalytics: async () => {
    return apiFetch(ENDPOINTS.ANALYTICS);
  },
};

export const intelligenceAPI = {
  getOverview: async () => apiFetch(ENDPOINTS.INTELLIGENCE_OVERVIEW),
  getGraph: async (taskId: string) => apiFetch(ENDPOINTS.INTELLIGENCE_GRAPH(taskId)),
  getSimilarTasks: async (taskId: string) => apiFetch(ENDPOINTS.INTELLIGENCE_SIMILAR(taskId)),
  findSimilarForGoal: async (goal: string, language: string = "en-IN") => apiFetch(ENDPOINTS.INTELLIGENCE_SIMILAR_GOAL, {
    method: "POST",
    body: JSON.stringify({ goal, language }),
  }),
  getProfile: async () => apiFetch(ENDPOINTS.INTELLIGENCE_PROFILE),
  predict: async (goal: string, context?: Record<string, any>) => apiFetch(ENDPOINTS.INTELLIGENCE_PREDICT, {
    method: "POST",
    body: JSON.stringify({ goal, context }),
  }),
  simulate: async (goal: string, scenario: string, context?: Record<string, any>) => apiFetch(ENDPOINTS.INTELLIGENCE_SIMULATE, {
    method: "POST",
    body: JSON.stringify({ goal, scenario, context }),
  }),
  parseWorkflow: async (workflow: string, title: string = "Workflow") => apiFetch(ENDPOINTS.INTELLIGENCE_WORKFLOW_PARSE, {
    method: "POST",
    body: JSON.stringify({ workflow, title }),
  }),
  listModels: async () => apiFetch(ENDPOINTS.INTELLIGENCE_MODELS),
  registerModel: async (payload: { name: string; version: string; description?: string; status?: string }) => apiFetch(ENDPOINTS.INTELLIGENCE_MODELS, {
    method: "POST",
    body: JSON.stringify(payload),
  }),
  rollbackModel: async (modelId: string) => apiFetch(`${ENDPOINTS.INTELLIGENCE_MODELS}/${modelId}/rollback`, {
    method: "POST",
  }),
  getDrift: async () => apiFetch(ENDPOINTS.INTELLIGENCE_DRIFT),
  getReflectionReport: async () => apiFetch(ENDPOINTS.INTELLIGENCE_REFLECTION_REPORT, {
    method: "POST",
  }),
  recordOverride: async (taskId: string, decision: "approve" | "review" | "reject", notes?: string) => apiFetch(ENDPOINTS.INTELLIGENCE_OVERRIDE, {
    method: "POST",
    body: JSON.stringify({ task_id: taskId, decision, notes }),
  }),
  getHealth: async () => apiFetch(ENDPOINTS.INTELLIGENCE_HEALTH),
};

export const systemAPI = {
  /**
   * Check system health status.
   */
  getHealth: async () => {
    return apiFetch(ENDPOINTS.HEALTH, {
      skipAuth: true,
      skipErrorHandling: true,
    });
  },
};
