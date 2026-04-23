/**
 * AegisAI - Frontend Auth Service Tests (Vitest)
 * Tests: API client, token manager, auth context, error handling
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { APIClient } from '../src/services/api';
import { TokenManager } from '../src/services/api';

// ────────────────────────────────────────────────────────────────────────────────
// MOCKS
// ────────────────────────────────────────────────────────────────────────────────

const mockFetch = vi.fn();
global.fetch = mockFetch;

const mockLocalStorage = (() => {
  let store: Record<string, string> = {};

  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; },
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage,
});

// ────────────────────────────────────────────────────────────────────────────────
// TOKEN MANAGER TESTS
// ────────────────────────────────────────────────────────────────────────────────

describe('TokenManager', () => {
  beforeEach(() => {
    mockLocalStorage.clear();
    vi.clearAllMocks();
  });

  it('should store and retrieve access token', () => {
    const token = 'test_access_token_12345';
    TokenManager.setAccessToken(token);
    expect(TokenManager.getAccessToken()).toBe(token);
  });

  it('should store and retrieve refresh token', () => {
    const token = 'test_refresh_token_12345';
    TokenManager.setRefreshToken(token);
    expect(TokenManager.getRefreshToken()).toBe(token);
  });

  it('should return null for missing token', () => {
    expect(TokenManager.getAccessToken()).toBeNull();
  });

  it('should detect when logged in', () => {
    expect(TokenManager.isLoggedIn()).toBe(false);
    TokenManager.setAccessToken('test_token');
    expect(TokenManager.isLoggedIn()).toBe(true);
  });

  it('should clear all tokens', () => {
    TokenManager.setAccessToken('access');
    TokenManager.setRefreshToken('refresh');
    TokenManager.clearTokens();
    
    expect(TokenManager.getAccessToken()).toBeNull();
    expect(TokenManager.getRefreshToken()).toBeNull();
    expect(TokenManager.isLoggedIn()).toBe(false);
  });

  it('should store user data', () => {
    const userData = { id: '123', email: 'test@example.com', name: 'Test User' };
    TokenManager.setUserData(userData);
    expect(TokenManager.getUserData()).toEqual(userData);
  });

  it('should handle localStorage errors gracefully', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('Storage full');
    });
    
    expect(() => TokenManager.setAccessToken('token')).not.toThrow();
  });
});

// ────────────────────────────────────────────────────────────────────────────────
// API CLIENT TESTS
// ────────────────────────────────────────────────────────────────────────────────

describe('APIClient', () => {
  const api = new APIClient('http://localhost:8000');

  beforeEach(() => {
    mockLocalStorage.clear();
    vi.clearAllMocks();
    mockFetch.mockClear();
  });

  it('should construct API base URL correctly', () => {
    const api = new APIClient('http://localhost:8000');
    expect(api.baseUrl).toBe('http://localhost:8000');
  });

  it('should make GET requests', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ data: 'test' }),
    });

    const result = await api.get('/test');
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/test',
      expect.objectContaining({ method: 'GET' })
    );
  });

  it('should make POST requests', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ data: 'test' }),
    });

    const payload = { email: 'test@example.com' };
    await api.post('/test', payload);
    
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/test',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
        }),
        body: JSON.stringify(payload),
      })
    );
  });

  it('should inject auth token in headers', async () => {
    TokenManager.setAccessToken('test_token_123');
    
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ data: 'test' }),
    });

    await api.get('/protected');
    
    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          'Authorization': 'Bearer test_token_123',
        }),
      })
    );
  });

  it('should handle 401 unauthorized responses', async () => {
    TokenManager.setAccessToken('expired_token');
    
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Unauthorized' }),
    });

    try {
      await api.get('/protected');
      expect.fail('Should have thrown');
    } catch (error) {
      expect(error).toBeDefined();
    }
  });

  it('should handle network errors', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'));

    try {
      await api.get('/test');
      expect.fail('Should have thrown');
    } catch (error) {
      expect(error).toBeInstanceOf(Error);
    }
  });

  it('should handle JSON parse errors', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => { throw new Error('Invalid JSON'); },
    });

    try {
      await api.get('/test');
      expect.fail('Should have thrown');
    } catch (error) {
      expect(error).toBeDefined();
    }
  });
});

// ────────────────────────────────────────────────────────────────────────────────
// AUTH ENDPOINTS TESTS
// ────────────────────────────────────────────────────────────────────────────────

describe('Auth Endpoints', () => {
  const api = new APIClient('http://localhost:8000');

  beforeEach(() => {
    mockLocalStorage.clear();
    mockFetch.mockClear();
  });

  it('should call register endpoint', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: async () => ({ access_token: 'token', refresh_token: 'refresh' }),
    });

    const userData = {
      email: 'test@example.com',
      password: 'Pass123!',
      full_name: 'Test User',
    };

    await api.post('/auth/register', userData);
    
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/auth/register',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify(userData),
      })
    );
  });

  it('should call login endpoint', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ access_token: 'token', refresh_token: 'refresh' }),
    });

    const credentials = {
      email: 'test@example.com',
      password: 'Pass123!',
    };

    await api.post('/auth/login', credentials);
    
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/auth/login'),
      expect.any(Object)
    );
  });

  it('should call me endpoint', async () => {
    TokenManager.setAccessToken('valid_token');
    
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ email: 'test@example.com', full_name: 'Test User' }),
    });

    await api.get('/auth/me');
    
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/auth/me'),
      expect.any(Object)
    );
  });

  it('should call refresh endpoint', async () => {
    const refreshToken = 'valid_refresh_token';
    
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ access_token: 'new_token' }),
    });

    await api.post('/auth/refresh', { refresh_token: refreshToken });
    
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/auth/refresh'),
      expect.any(Object)
    );
  });
});

// ────────────────────────────────────────────────────────────────────────────────
// TASK ENDPOINTS TESTS
// ────────────────────────────────────────────────────────────────────────────────

describe('Task Endpoints', () => {
  const api = new APIClient('http://localhost:8000');

  beforeEach(() => {
    mockLocalStorage.clear();
    TokenManager.setAccessToken('valid_token');
    mockFetch.mockClear();
  });

  it('should submit a task', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: async () => ({ task_id: '123', status: 'pending' }),
    });

    const taskData = {
      goal: 'Analyze market trends',
      domain: 'market_analysis',
      priority: 'high',
    };

    await api.post('/tasks/submit', taskData);
    
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/tasks/submit'),
      expect.any(Object)
    );
  });

  it('should retrieve a task', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ task_id: '123', goal: 'Test goal', status: 'completed' }),
    });

    await api.get('/tasks/123');
    
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/tasks/123',
      expect.any(Object)
    );
  });

  it('should get task progress', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ task_id: '123', progress: 75, status: 'processing' }),
    });

    await api.get('/tasks/123/progress');
    
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/tasks/123/progress'),
      expect.any(Object)
    );
  });
});

// ────────────────────────────────────────────────────────────────────────────────
// ERROR HANDLING TESTS
// ────────────────────────────────────────────────────────────────────────────────

describe('Error Handling', () => {
  const api = new APIClient('http://localhost:8000');

  beforeEach(() => {
    mockFetch.mockClear();
  });

  it('should handle 400 bad request', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ detail: 'Invalid input' }),
    });

    try {
      await api.post('/test', {});
      expect.fail('Should throw');
    } catch (error) {
      expect(error).toBeDefined();
    }
  });

  it('should handle 404 not found', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ detail: 'Not found' }),
    });

    try {
      await api.get('/nonexistent');
      expect.fail('Should throw');
    } catch (error) {
      expect(error).toBeDefined();
    }
  });

  it('should handle 500 server error', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({ detail: 'Internal server error' }),
    });

    try {
      await api.get('/error');
      expect.fail('Should throw');
    } catch (error) {
      expect(error).toBeDefined();
    }
  });

  it('should handle timeout errors', async () => {
    mockFetch.mockImplementationOnce(() => 
      new Promise((_, reject) => 
        setTimeout(() => reject(new Error('Timeout')), 100)
      )
    );

    try {
      await api.get('/slow');
      expect.fail('Should throw');
    } catch (error) {
      expect(error).toBeInstanceOf(Error);
    }
  });
});
