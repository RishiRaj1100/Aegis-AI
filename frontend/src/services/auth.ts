/**
 * AegisAI auth utility helpers.
 * Provides route guarding helpers on top of TokenManager.
 */

import { TokenManager } from "@/services/api";

/**
 * Redirect user to login if auth token is missing or expired.
 * Stores current URL for post-login redirect continuity.
 */
export function requireAuth(): boolean {
  const authenticated = TokenManager.isValid();
  if (!authenticated) {
    sessionStorage.setItem("redirect_after_login", window.location.href);
    window.location.href = "/login";
    return false;
  }
  return true;
}

/**
 * Resolve and consume redirect target after successful authentication.
 */
export function redirectAfterLogin(defaultPath: string = "/dashboard"): string {
  const redirectTo = sessionStorage.getItem("redirect_after_login") || defaultPath;
  sessionStorage.removeItem("redirect_after_login");
  return redirectTo;
}
