/**
 * AegisAI - Auth Context
 * Provides authentication state and methods throughout the React app.
 */

import React, { createContext, useContext, useEffect, useState } from "react";
import { authAPI, TokenManager, UserManager, User, APIError } from "@/services/api";
import { redirectAfterLogin } from "@/services/auth";
import { prefetchLoginPage, prefetchRouteForPath } from "@/utils/routePrefetch";

interface AuthContextType {
  // State
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  error: string | null;

  // Methods
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  clearError: () => void;
  checkAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: React.ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Initialize auth state from storage
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const storedUser = UserManager.getUser();
        const hasValidToken = TokenManager.isValid();

        if (storedUser && hasValidToken) {
          setUser(storedUser);
        } else {
          // Try to refresh token if refresh token exists
          const refreshToken = TokenManager.getRefreshToken();
          if (refreshToken) {
            try {
              const response = await authAPI.refresh(refreshToken);
              TokenManager.setToken(response.access_token);
              // Fetch updated user info
              const userInfo = await authAPI.me();
              UserManager.setUser(userInfo);
              setUser(userInfo);
            } catch {
              // Refresh failed, clear auth
              TokenManager.clear();
              UserManager.clear();
              setUser(null);
            }
          }
        }
      } catch (err) {
        console.error("Auth initialization failed:", err);
        TokenManager.clear();
        UserManager.clear();
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    initializeAuth();
  }, []);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await authAPI.login(email, password);
      TokenManager.setToken(response.access_token);
      TokenManager.setRefreshToken(response.refresh_token);
      UserManager.setUser(response.user);
      setUser(response.user);

      // Redirect to dashboard or intended page
      const redirectTo = redirectAfterLogin("/dashboard");
      await prefetchRouteForPath(redirectTo);
      window.location.href = redirectTo;
    } catch (err) {
      const errorMsg = err instanceof APIError ? err.detail : "Login failed";
      setError(errorMsg);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (name: string, email: string, password: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await authAPI.register(name, email, password);
      TokenManager.setToken(response.access_token);
      TokenManager.setRefreshToken(response.refresh_token);
      UserManager.setUser(response.user);
      setUser(response.user);

      // Redirect to dashboard
      await prefetchRouteForPath("/dashboard");
      window.location.href = "/dashboard";
    } catch (err) {
      const errorMsg = err instanceof APIError ? err.detail : "Registration failed";
      setError(errorMsg);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    TokenManager.clear();
    UserManager.clear();
    setUser(null);
    setError(null);
    void prefetchLoginPage();
    window.location.href = "/login";
  };

  const clearError = () => setError(null);

  const checkAuth = async () => {
    try {
      const userInfo = await authAPI.me();
      UserManager.setUser(userInfo);
      setUser(userInfo);
    } catch (err) {
      TokenManager.clear();
      UserManager.clear();
      setUser(null);
      throw err;
    }
  };

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: !!user && TokenManager.isValid(),
    error,
    login,
    register,
    logout,
    clearError,
    checkAuth,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

/**
 * Hook to use auth context.
 * Must be used within an AuthProvider.
 */
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
};

/**
 * HOC to require authentication on a page.
 * Redirects to login if not authenticated.
 */
export const withAuth = <P extends object>(
  Component: React.ComponentType<P>
): React.FC<P> => {
  return (props: P) => {
    const { isAuthenticated, isLoading } = useAuth();
    const [redirected, setRedirected] = useState(false);

    useEffect(() => {
      if (!isLoading && !isAuthenticated && !redirected) {
        sessionStorage.setItem("redirect_after_login", window.location.href);
        window.location.href = "/login";
        setRedirected(true);
      }
    }, [isLoading, isAuthenticated, redirected]);

    if (isLoading) {
      return (
        <div className="flex h-screen items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border border-primary border-t-transparent mx-auto mb-4" />
            <p className="text-muted-foreground">Loading...</p>
          </div>
        </div>
      );
    }

    if (!isAuthenticated) {
      return null;
    }

    return <Component {...props} />;
  };
};
