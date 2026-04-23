import { lazy, Suspense, useEffect, useRef } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes, useLocation, useNavigationType } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import DevRoutePerfOverlay from "@/components/dev/RoutePerfOverlay";
import { AuthProvider, withAuth } from "@/contexts/AuthContext";
import { MissionProvider } from "@/contexts/MissionContext";
import { reportDevRouteCommit } from "@/utils/routeTiming";

const Index = lazy(() => import("./pages/Index.tsx"));
const Login = lazy(() => import("./pages/Login.tsx"));
const Register = lazy(() => import("./pages/Register.tsx"));
const ForgotPassword = lazy(() => import("./pages/ForgotPassword.tsx"));
const Dashboard = lazy(() => import("./pages/Dashboard.tsx"));
const Analytics = lazy(() => import("./pages/Analytics.tsx"));
const Intelligence = lazy(() => import("./pages/Intelligence.tsx"));
const AdvancedFeaturesPage = lazy(() => import("./pages/AdvancedFeaturesPage.tsx"));
const AdvancedAnalyticsPage = lazy(() => import("./pages/AdvancedAnalyticsPage.tsx"));
const MonitoringPage = lazy(() => import("./pages/MonitoringPage.tsx"));
const NotFound = lazy(() => import("./pages/NotFound.tsx"));

const queryClient = new QueryClient();
const ProtectedDashboard = withAuth(Dashboard);
const ProtectedAnalytics = withAuth(Analytics);
const ProtectedAdvancedFeatures = withAuth(AdvancedFeaturesPage);
const ProtectedAdvancedAnalytics = withAuth(AdvancedAnalyticsPage);
const ProtectedMonitoring = withAuth(MonitoringPage);

const DevRouteTimingProbe = () => {
  const location = useLocation();
  const navigationType = useNavigationType();
  const currentPath = `${location.pathname}${location.search}${location.hash}`;
  const previousPathRef = useRef(currentPath);

  useEffect(() => {
    if (!import.meta.env.DEV) {
      previousPathRef.current = currentPath;
      return;
    }

    const previousPath = previousPathRef.current;
    previousPathRef.current = currentPath;

    const cancelReport = reportDevRouteCommit(currentPath, navigationType, previousPath);
    return cancelReport;
  }, [currentPath, navigationType]);

  return null;
};

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
        <AuthProvider>
          <MissionProvider>
            <Toaster />
            <Sonner />
            <DevRoutePerfOverlay />
            <BrowserRouter>
              <DevRouteTimingProbe />
              <Suspense fallback={<div className="min-h-screen flex items-center justify-center text-muted-foreground">Loading...</div>}>
                <Routes>
              <Route path="/" element={<Index />} />
              <Route path="/ui" element={<Index />} />
              <Route path="/login" element={<Login />} />
              <Route path="/ui/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/ui/register" element={<Register />} />
              <Route path="/forgot-password" element={<ForgotPassword />} />
              <Route path="/ui/forgot-password" element={<ForgotPassword />} />
              <Route path="/dashboard" element={<ProtectedDashboard />} />
              <Route path="/ui/dashboard" element={<ProtectedDashboard />} />
              <Route path="/analytics" element={<ProtectedAnalytics />} />
              <Route path="/ui/analytics" element={<ProtectedAnalytics />} />
              <Route path="/advanced-features" element={<ProtectedAdvancedFeatures />} />
              <Route path="/ui/advanced-features" element={<ProtectedAdvancedFeatures />} />
              <Route path="/advanced-analytics" element={<ProtectedAdvancedAnalytics />} />
              <Route path="/ui/advanced-analytics" element={<ProtectedAdvancedAnalytics />} />
              <Route path="/monitoring" element={<ProtectedMonitoring />} />
              <Route path="/ui/monitoring" element={<ProtectedMonitoring />} />
              <Route path="/intelligence" element={<Intelligence />} />
              <Route path="/ui/intelligence" element={<Intelligence />} />
              <Route path="*" element={<NotFound />} />
                </Routes>
              </Suspense>
            </BrowserRouter>
          </MissionProvider>
        </AuthProvider>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
