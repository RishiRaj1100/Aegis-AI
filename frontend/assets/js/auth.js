/**
 * AegisAI — Auth Module
 * Token management, auth guards, session handling
 */

const Auth = (() => {
  'use strict';

  const TOKEN_KEY = 'aegis_token';
  const REFRESH_KEY = 'aegis_refresh';
  const USER_KEY = 'aegis_user';
  const API_BASE = window.AEGIS_API || 'http://localhost:8000';

  /* ── Token Management ── */
  function getToken() { return localStorage.getItem(TOKEN_KEY); }
  function getRefresh() { return localStorage.getItem(REFRESH_KEY); }
  function setTokens(access, refresh) {
    localStorage.setItem(TOKEN_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  }
  function clearTokens() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
  }

  function getUser() {
    try { return JSON.parse(localStorage.getItem(USER_KEY)); } catch { return null; }
  }
  function setUser(user) { localStorage.setItem(USER_KEY, JSON.stringify(user)); }

  /* ── API Helper ── */
  async function apiFetch(url, options = {}) {
    const token = getToken();
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(url, { ...options, headers });

    if (res.status === 401) {
      // Try refresh
      const refreshed = await refreshToken();
      if (refreshed) {
        headers['Authorization'] = `Bearer ${getToken()}`;
        return fetch(url, { ...options, headers });
      }
      clearTokens();
      window.location.href = 'login.html';
      throw new Error('Session expired');
    }
    return res;
  }

  async function refreshToken() {
    const refresh = getRefresh();
    if (!refresh) return false;
    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!res.ok) return false;
      const data = await res.json();
      setTokens(data.access_token, data.refresh_token);
      return true;
    } catch { return false; }
  }

  /* ── Auth Actions ── */
  async function login(email, password) {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Login failed');
    setTokens(data.access_token, data.refresh_token);
    if (data.user) setUser(data.user);
    return data;
  }

  async function register(name, email, password) {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Registration failed');
    setTokens(data.access_token, data.refresh_token);
    if (data.user) setUser(data.user);
    return data;
  }

  async function fetchMe() {
    const res = await apiFetch(`${API_BASE}/auth/me`);
    const data = await res.json();
    if (res.ok) setUser(data);
    return data;
  }

  function logout() {
    clearTokens();
    window.location.href = 'login.html';
  }

  /* ── Auth Guard ── */
  function requireAuth() {
    if (!getToken()) {
      window.location.href = 'login.html';
      return false;
    }
    return true;
  }

  function redirectIfAuth(target = 'dashboard.html') {
    if (getToken()) {
      window.location.href = target;
      return true;
    }
    return false;
  }

  return {
    getToken, getUser, setUser, login, register, logout,
    fetchMe, requireAuth, redirectIfAuth, apiFetch, API_BASE,
  };
})();
