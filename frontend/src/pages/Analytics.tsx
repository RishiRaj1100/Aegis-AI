import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, LogOut } from "lucide-react";
import { useAuth, withAuth } from "@/contexts/AuthContext";
import { useMission } from "@/contexts/MissionContext";
import { analyticsAPI, confidenceAPI, planAPI, APIError } from "@/services/api";
import { useToast } from "@/components/ui/use-toast";

interface AnalyticsData {
  total_goals: number;
  avg_trust_score: number;
  success_rate: number;
  completed_tasks: number;
  trust_trend: Array<{ date: string; score: number }>;
  domain_distribution: Record<string, number>;
  risk_distribution: Record<string, number>;
  ethics_flags_by_type: Record<string, number>;
  ethics_flags_this_week: number;
}

const Analytics = () => {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const { toast } = useToast();
  const { mission } = useMission();

  const [data, setData] = useState<AnalyticsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [taskPlan, setTaskPlan] = useState<any | null>(null);
  const [taskConfidence, setTaskConfidence] = useState<any | null>(null);

  useEffect(() => {
    const loadAnalytics = async () => {
      try {
        const result = await analyticsAPI.getAnalytics();
        setData(result);
      } catch (error) {
        const message = error instanceof APIError ? error.detail : "Failed to load analytics";
        toast({
          title: "Error",
          description: message,
          variant: "destructive",
        });
      } finally {
        setIsLoading(false);
      }
    };

    loadAnalytics();
  }, [toast]);

  useEffect(() => {
    const loadMissionSnapshot = async () => {
      if (!mission?.taskId) {
        setTaskPlan(null);
        setTaskConfidence(null);
        return;
      }

      try {
        const [planResult, confidenceResult] = await Promise.all([
          planAPI.getPlan(mission.taskId),
          confidenceAPI.getConfidence(mission.taskId),
        ]);
        setTaskPlan(planResult);
        setTaskConfidence(confidenceResult);
      } catch (error) {
        console.error("Failed to load mission snapshot:", error);
      }
    };

    void loadMissionSnapshot();
  }, [mission?.taskId]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border border-primary border-t-transparent mx-auto mb-4" />
          <p className="text-muted-foreground">Loading analytics...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-40">
        <div className="mx-auto max-w-7xl px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate("/dashboard")}
              className="btn-ghost !px-3 !py-2"
            >
              <ArrowLeft size={16} />
            </button>
            <h1 className="text-2xl font-bold text-foreground">Analytics</h1>
            <button onClick={() => navigate("/intelligence")} className="btn-ghost !px-3 !py-2 ml-2">
              Intelligence Lab
            </button>
            <button onClick={() => navigate("/advanced-features")} className="btn-ghost !px-3 !py-2">
              Advanced Features
            </button>
            <button onClick={() => navigate("/advanced-analytics")} className="btn-ghost !px-3 !py-2">
              Advanced Analytics
            </button>
            <button onClick={() => navigate("/monitoring")} className="btn-ghost !px-3 !py-2">
              Monitoring
            </button>
          </div>

          <button
            onClick={() => {
              logout();
            }}
            className="btn-ghost !px-4 !py-2 flex items-center gap-2 text-aegis-rose hover:text-aegis-rose"
          >
            <LogOut size={16} />
            Sign Out
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="mx-auto max-w-7xl px-6 py-8 space-y-8">
        {mission ? (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="mission-shell mission-orbit rounded-2xl border border-white/10 bg-white/5 p-5"
          >
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Latest question</p>
                <h2 className="mt-1 text-xl font-semibold text-foreground">{mission.goal}</h2>
                <p className="text-sm text-muted-foreground">Task {mission.taskId || "pending"} · {mission.status} · {mission.riskLevel}</p>
              </div>
              <div className="flex flex-wrap gap-2 text-sm">
                <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-muted-foreground">{Math.round(mission.confidence)}% confidence</span>
                <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-muted-foreground">{mission.subtasks} subtasks</span>
                <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-muted-foreground">{mission.language}</span>
              </div>
            </div>

            {taskPlan ? (
              <div className="mt-4 grid gap-3 md:grid-cols-3">
                <div className="rounded-xl bg-black/20 p-4">
                  <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Execution plan</p>
                  <p className="mt-2 text-sm text-foreground line-clamp-3">{taskPlan.execution_plan || taskPlan.plan?.execution_plan || "No execution plan available yet."}</p>
                </div>
                <div className="rounded-xl bg-black/20 p-4">
                  <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Research</p>
                  <p className="mt-2 text-sm text-foreground line-clamp-3">{taskPlan.research_insights || taskPlan.plan?.research_insights || "No research summary available yet."}</p>
                </div>
                <div className="rounded-xl bg-black/20 p-4">
                  <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Confidence</p>
                  <p className="mt-2 text-2xl font-semibold text-primary">{Math.round(taskConfidence?.confidence ?? taskPlan.confidence ?? mission.confidence)}%</p>
                  <p className="text-xs text-muted-foreground">{taskConfidence?.risk_level ?? taskPlan.risk_level ?? mission.riskLevel}</p>
                </div>
              </div>
            ) : null}
          </motion.div>
        ) : null}

        {/* KPI Cards */}
        <div className="grid gap-4 md:grid-cols-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0 }}
            className="glass-card p-6 rounded-lg"
          >
            <p className="text-sm font-semibold text-muted-foreground mb-2">Total Goals</p>
            <p className="text-3xl font-bold text-primary">{data?.total_goals || 0}</p>
            <p className="mt-2 text-xs text-muted-foreground">Stored goal records for this account.</p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="glass-card p-6 rounded-lg"
          >
            <p className="text-sm font-semibold text-muted-foreground mb-2">Avg Confidence</p>
            <p className="text-3xl font-bold text-aegis-cyan">{(data?.avg_trust_score || 0).toFixed(1)}%</p>
            <p className="mt-2 text-xs text-muted-foreground">Mean confidence across saved goals.</p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="glass-card p-6 rounded-lg"
          >
            <p className="text-sm font-semibold text-muted-foreground mb-2">Success Rate</p>
            <p className="text-3xl font-bold text-aegis-emerald">{((data?.success_rate || 0) * 100).toFixed(1)}%</p>
            <p className="mt-2 text-xs text-muted-foreground">Completed tasks divided by total stored goals.</p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="glass-card p-6 rounded-lg"
          >
            <p className="text-sm font-semibold text-muted-foreground mb-2">Completed</p>
            <p className="text-3xl font-bold text-aegis-violet">{data?.completed_tasks || 0}</p>
            <p className="mt-2 text-xs text-muted-foreground">Tasks marked COMPLETED in history.</p>
          </motion.div>
        </div>

        {/* Risk Distribution */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="glass-card p-6 rounded-lg"
        >
          <h2 className="text-lg font-semibold text-foreground mb-4">Risk Distribution</h2>
          <p className="text-xs text-muted-foreground mb-4">Risk buckets are derived from each task's stored confidence.</p>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="flex items-center gap-4 p-4 rounded-lg bg-secondary/50">
              <div className="text-3xl font-bold text-aegis-emerald">{data?.risk_distribution.LOW || 0}</div>
              <div>
                <p className="font-semibold text-foreground">Low Risk</p>
                <p className="text-xs text-muted-foreground">Confidence ≥ 70%</p>
              </div>
            </div>

            <div className="flex items-center gap-4 p-4 rounded-lg bg-secondary/50">
              <div className="text-3xl font-bold text-aegis-amber">{data?.risk_distribution.MEDIUM || 0}</div>
              <div>
                <p className="font-semibold text-foreground">Medium Risk</p>
                <p className="text-xs text-muted-foreground">Confidence 40–70%</p>
              </div>
            </div>

            <div className="flex items-center gap-4 p-4 rounded-lg bg-secondary/50">
              <div className="text-3xl font-bold text-aegis-rose">{data?.risk_distribution.HIGH || 0}</div>
              <div>
                <p className="font-semibold text-foreground">High Risk</p>
                <p className="text-xs text-muted-foreground">Confidence &lt; 40%</p>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Domain Distribution */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="glass-card p-6 rounded-lg"
        >
          <h2 className="text-lg font-semibold text-foreground mb-4">Domains</h2>
          <p className="text-xs text-muted-foreground mb-4">Domains come from the saved task metadata. Empty means the task was never tagged.</p>
          <div className="space-y-3">
            {Object.entries(data?.domain_distribution || {}).map(([domain, count]) => (
              <div key={domain} className="flex items-center justify-between p-3 rounded-lg bg-secondary/50">
                <p className="font-medium text-foreground capitalize">{domain}</p>
                <p className="text-sm font-semibold text-primary">{count} goals</p>
              </div>
            ))}
            {Object.keys(data?.domain_distribution || {}).length === 0 && (
              <p className="text-sm text-muted-foreground text-center py-4">No data yet</p>
            )}
          </div>
        </motion.div>

        {/* Ethics Flags */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="glass-card p-6 rounded-lg"
        >
          <h2 className="text-lg font-semibold text-foreground mb-4">Ethics & Compliance</h2>
          <p className="text-xs text-muted-foreground mb-4">Visible only when the stored task history contains ethics annotations.</p>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-3">
              <h3 className="font-semibold text-foreground text-sm">Flags by Type</h3>
              {["privacy", "bias", "legal", "other"].map((type) => (
                <div key={type} className="flex items-center justify-between p-3 rounded-lg bg-secondary/50">
                  <p className="capitalize text-foreground text-sm">{type}</p>
                  <p className="font-semibold text-aegis-rose">
                    {data?.ethics_flags_by_type[type as keyof typeof data.ethics_flags_by_type] || 0}
                  </p>
                </div>
              ))}
            </div>

            <div className="flex items-center justify-center p-6 rounded-lg bg-secondary/50">
              <div className="text-center">
                <p className="text-4xl font-bold text-primary">{data?.ethics_flags_this_week || 0}</p>
                <p className="text-sm text-muted-foreground mt-2">Flags This Week</p>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Trust Trend */}
        {data?.trust_trend && data.trust_trend.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.7 }}
            className="glass-card p-6 rounded-lg"
          >
            <h2 className="text-lg font-semibold text-foreground mb-4">Confidence Trend</h2>
            <div className="space-y-3">
              {data.trust_trend.slice(-10).map((point, i) => (
                <div key={i} className="flex items-center gap-4">
                  <span className="text-xs font-mono text-muted-foreground min-w-20">{point.date}</span>
                  <div className="flex-1 bg-secondary rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-primary h-2 rounded-full transition-all"
                      style={{ width: `${point.score}%` }}
                    />
                  </div>
                  <span className="text-sm font-semibold text-primary min-w-12">{point.score}%</span>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
};

export default withAuth(Analytics);
