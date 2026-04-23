let didPrefetchAppRoutes = false;
let didPrefetchLandingAuth = false;

export const prefetchLoginPage = () => import("@/pages/Login.tsx");
export const prefetchRegisterPage = () => import("@/pages/Register.tsx");
export const prefetchForgotPasswordPage = () => import("@/pages/ForgotPassword.tsx");
export const prefetchDashboardPage = () => import("@/pages/Dashboard.tsx");
export const prefetchAnalyticsPage = () => import("@/pages/Analytics.tsx");

const runWhenIdle = (task: () => void) => {
  const idleApi = (globalThis as Window & { requestIdleCallback?: (cb: () => void, options?: { timeout: number }) => void }).requestIdleCallback;
  if (typeof idleApi === "function") {
    idleApi(task, { timeout: 1000 });
    return;
  }
  setTimeout(task, 150);
};

export const prefetchAppRoutesOnce = () => {
  if (didPrefetchAppRoutes) {
    return;
  }
  didPrefetchAppRoutes = true;

  runWhenIdle(() => {
    void prefetchDashboardPage();
    void prefetchAnalyticsPage();
  });
};

export const prefetchLandingAuthRoutesOnce = () => {
  if (didPrefetchLandingAuth) {
    return;
  }
  didPrefetchLandingAuth = true;

  runWhenIdle(() => {
    void prefetchLoginPage();
    void prefetchRegisterPage();
  });
};

export const prefetchRouteForPath = async (path: string) => {
  const cleanPath = path.split("?")[0].split("#")[0];

  if (cleanPath === "/dashboard" || cleanPath === "/ui/dashboard") {
    await prefetchDashboardPage();
    return;
  }

  if (cleanPath === "/analytics" || cleanPath === "/ui/analytics") {
    await prefetchAnalyticsPage();
    return;
  }

  if (cleanPath === "/login" || cleanPath === "/ui/login") {
    await prefetchLoginPage();
    return;
  }

  if (cleanPath === "/register" || cleanPath === "/ui/register") {
    await prefetchRegisterPage();
    return;
  }

  if (cleanPath === "/forgot-password" || cleanPath === "/ui/forgot-password") {
    await prefetchForgotPasswordPage();
  }
};
