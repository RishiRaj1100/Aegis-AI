import { useAuth } from "@/contexts/AuthContext";
import { AnalyticsDashboard } from "@/components/AnalyticsDashboard";

const AdvancedAnalyticsPage = () => {
  const { user } = useAuth();
  const userId = user?.id || "";

  return <AnalyticsDashboard userId={userId} />;
};

export default AdvancedAnalyticsPage;
