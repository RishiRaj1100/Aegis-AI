import React, { useState, useEffect } from 'react';
import { analyticsAPI, confidenceAPI, planAPI } from '@/services/api';
import { useMission } from '@/contexts/MissionContext';

interface KPI {
  total_tasks: number;
  completed_tasks: number;
  pending_tasks: number;
  completion_rate: number;
  average_confidence: number;
  average_trust: number;
}

const kpiSubtitle = (tasks: number, completed: number) => {
  if (tasks === 0) {
    return "No goal records yet.";
  }

  return `${completed} completed from ${tasks} stored goal${tasks === 1 ? "" : "s"}.`;
};

interface AnalyticsData {
  kpis: KPI;
  by_domain: Record<string, any>;
  by_priority: Record<string, any>;
  by_status: Record<string, any>;
}

interface Trend {
  date: string;
  value: number;
  metric: string;
}

/**
 * AnalyticsDashboard - Custom analytics with charts and KPIs
 */
export const AnalyticsDashboard: React.FC<{ userId: string }> = ({
  userId,
}) => {
  const { mission } = useMission();
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [trends, setTrends] = useState<Trend[]>([]);
  const [taskPlan, setTaskPlan] = useState<any | null>(null);
  const [taskConfidence, setTaskConfidence] = useState<any | null>(null);
  const [period, setPeriod] = useState('week');
  const [selectedMetric, setSelectedMetric] = useState('confidence');
  const [loading, setLoading] = useState(true);
  const [exportFormat, setExportFormat] = useState('json');

  useEffect(() => {
    fetchAnalytics();
  }, [userId, period, mission?.taskId]);

  useEffect(() => {
    const loadMissionAnalytics = async () => {
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
        console.error('Failed to load mission analytics:', error);
      }
    };

    void loadMissionAnalytics();
  }, [mission?.taskId]);

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      const base = await analyticsAPI.getAnalytics();

      const totalTasks = Number(base?.total_goals || 0);
      const completedTasks = Number(base?.completed_tasks || 0);
      const pendingTasks = Math.max(0, totalTasks - completedTasks);
      const completionRate = Number(base?.success_rate || 0) * 100;
      const avgConfidence = Number(base?.avg_trust_score || 0);

      const mapped: AnalyticsData = {
        kpis: {
          total_tasks: totalTasks,
          completed_tasks: completedTasks,
          pending_tasks: pendingTasks,
          completion_rate: completionRate,
          average_confidence: avgConfidence,
          average_trust: avgConfidence,
        },
        by_domain: base?.domain_distribution || {},
        by_priority: {},
        by_status: {
          completed: completedTasks,
          pending: pendingTasks,
        },
      };

      setAnalytics(mapped);

      const trendRows = Array.isArray(base?.trust_trend) ? base.trust_trend : [];
      setTrends(
        trendRows.map((t: any) => ({
          date: String(t?.date || ''),
          value: Number(t?.score || 0),
          metric: selectedMetric,
        }))
      );
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
      setAnalytics({
        kpis: {
          total_tasks: 0,
          completed_tasks: 0,
          pending_tasks: 0,
          completion_rate: 0,
          average_confidence: 0,
          average_trust: 0,
        },
        by_domain: {},
        by_priority: {},
        by_status: { completed: 0, pending: 0 },
      });
      setTrends([]);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      const content = JSON.stringify(
        {
          analytics,
          trends,
          period,
          current_mission: mission,
          generated_at: new Date().toISOString(),
        },
        null,
        2
      );
      const blob = new Blob([content], { type: 'application/json;charset=utf-8;' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `analytics-${new Date().toISOString().split('T')[0]}.json`;
      a.click();
    } catch (error) {
      console.error('Failed to export:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center bg-[radial-gradient(circle_at_top,_rgba(99,102,241,0.18),_transparent_45%),linear-gradient(180deg,rgba(10,10,18,0.96),rgba(8,8,10,1))]">
        <div className="rounded-3xl border border-white/10 bg-white/5 px-6 py-5 text-center shadow-[0_0_50px_rgba(99,102,241,0.12)]">
          <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Analytics engine</p>
          <p className="mt-2 text-xl font-semibold text-foreground">Building mission history</p>
          <p className="mt-1 text-sm text-muted-foreground">Aggregating stored goals, confidence, and mission snapshots.</p>
        </div>
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="p-6 bg-red-100 border border-red-500 rounded">
        <p className="text-red-800">Failed to load analytics</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.1),_transparent_50%),linear-gradient(180deg,rgba(8,8,12,1),rgba(12,12,16,1))] p-8">
      <div className="max-w-7xl mx-auto">
        {mission ? (
          <div className="mission-shell mission-orbit mb-6 rounded-2xl border border-white/10 bg-white/5 p-5">
            <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Latest question</p>
            <h2 className="mt-1 text-lg font-semibold text-foreground">{mission.goal}</h2>
            <p className="text-sm text-muted-foreground">Task {mission.taskId || 'pending'} · {mission.status} · {mission.riskLevel}</p>
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <div className="rounded-xl bg-black/20 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Exact confidence</p>
                <p className="mt-2 text-3xl font-semibold text-primary">{Math.round(taskConfidence?.confidence ?? taskPlan?.confidence ?? mission.confidence ?? 0)}%</p>
              </div>
              <div className="rounded-xl bg-black/20 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Exact risk</p>
                <p className="mt-2 text-xl font-semibold text-foreground">{taskConfidence?.risk_level ?? taskPlan?.risk_level ?? mission.riskLevel}</p>
              </div>
              <div className="rounded-xl bg-black/20 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Plan size</p>
                <p className="mt-2 text-xl font-semibold text-foreground">{Array.isArray(taskPlan?.subtasks) ? taskPlan.subtasks.length : mission.subtasks}</p>
              </div>
            </div>
            {taskPlan ? (
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <div className="rounded-xl bg-black/20 p-4">
                  <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Execution plan</p>
                  <p className="mt-2 text-sm text-foreground whitespace-pre-wrap">{taskPlan.execution_plan}</p>
                </div>
                <div className="rounded-xl bg-black/20 p-4">
                  <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Research insights</p>
                  <p className="mt-2 text-sm text-foreground whitespace-pre-wrap">{taskPlan.research_insights}</p>
                </div>
              </div>
            ) : null}
          </div>
        ) : null}

        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Analytics Dashboard</h1>

          <div className="flex gap-3">
            <select
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              className="px-4 py-2 border rounded"
            >
              <option value="day">Today</option>
              <option value="week">This Week</option>
              <option value="month">This Month</option>
              <option value="quarter">This Quarter</option>
              <option value="year">This Year</option>
            </select>

            <select
              value={exportFormat}
              onChange={(e) => setExportFormat(e.target.value)}
              className="px-4 py-2 border rounded"
            >
              <option value="json">Export JSON</option>
              <option value="csv">Export CSV</option>
            </select>

            <button
              onClick={handleExport}
              className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
            >
              Export
            </button>
          </div>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <KPICard
            title="Total Tasks"
            value={analytics.kpis.total_tasks}
            icon="📊"
              subtitle={kpiSubtitle(analytics.kpis.total_tasks, analytics.kpis.completed_tasks)}
          />
          <KPICard
            title="Completed"
            value={analytics.kpis.completed_tasks}
            icon="✓"
              subtitle={kpiSubtitle(analytics.kpis.total_tasks, analytics.kpis.completed_tasks)}
          />
          <KPICard
            title="Completion Rate"
            value={`${analytics.kpis.completion_rate.toFixed(1)}%`}
            icon="📈"
              subtitle={analytics.kpis.total_tasks === 0 ? "No completed records yet." : "Completed / stored goals"}
          />
          <KPICard
            title="Avg Confidence"
            value={`${analytics.kpis.average_confidence.toFixed(0)}%`}
            icon="⭐"
              subtitle={`Mean confidence across ${analytics.kpis.total_tasks} stored goals`}
          />
        </div>

        {/* Breakdown Charts */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          {/* By Status */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-bold mb-4">By Status</h2>
            <div className="space-y-3">
              {Object.entries(analytics.by_status || {}).map(
                ([status, count]) => (
                  <StatusBar key={status} status={status} count={count as number} total={analytics.kpis.total_tasks} />
                )
              )}
            </div>
          </div>

          {/* By Domain */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-bold mb-4">By Domain</h2>
            <div className="space-y-3">
              {Object.entries(analytics.by_domain || {})
                .slice(0, 5)
                .map(([domain, count]) => (
                  <DomainBar key={domain} domain={domain} count={count as number} />
                ))}
            </div>
          </div>

          {/* By Priority */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-bold mb-4">By Priority</h2>
            <div className="space-y-3">
              {Object.entries(analytics.by_priority || {}).map(
                ([priority, count]) => (
                  <PriorityBar
                    key={priority}
                    priority={priority}
                    count={count as number}
                  />
                )
              )}
            </div>
          </div>
        </div>

        {/* Trends */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-bold">Trends</h2>
            <select
              value={selectedMetric}
              onChange={(e) => setSelectedMetric(e.target.value)}
              className="px-3 py-1 border rounded text-sm"
            >
              <option value="confidence">Confidence Score</option>
              <option value="trust">Trust Score</option>
              <option value="completion">Completion Rate</option>
            </select>
          </div>

          <div className="h-64 flex items-end justify-between gap-1">
            {trends.map((trend, index) => (
              <div
                key={index}
                className="flex-1 flex flex-col items-center"
                title={`${trend.date}: ${trend.value.toFixed(1)}`}
              >
                <div
                  className="w-full bg-blue-500 rounded-t"
                  style={{
                    height: `${(trend.value / 100) * 100}%`,
                    minHeight: '2px',
                  }}
                />
                <p className="text-xs text-gray-600 mt-2">
                  {new Date(trend.date).toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                  })}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Detailed Stats */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-bold mb-4">Summary Statistics</h2>
            <div className="space-y-3">
              <StatRow
                label="Avg Confidence Score"
                value={analytics.kpis.average_confidence.toFixed(1)}
                unit="%"
              />
              <StatRow
                label="Avg Trust Score"
                value={analytics.kpis.average_trust.toFixed(1)}
                unit="%"
              />
              <StatRow
                label="Pending Tasks"
                value={analytics.kpis.pending_tasks}
                unit="tasks"
              />
              <StatRow
                label="Completion Rate"
                value={analytics.kpis.completion_rate.toFixed(1)}
                unit="%"
              />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-bold mb-4">Quick Actions</h2>
            <div className="space-y-2">
              <ActionButton
                label="View Domain Performance"
                icon="📊"
              />
              <ActionButton
                label="Download Full Report"
                icon="📥"
              />
              <ActionButton
                label="Share Analytics"
                icon="📤"
              />
              <ActionButton
                label="Schedule Report"
                icon="📅"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * KPI Card Component
 */
const KPICard: React.FC<{ title: string; value: string | number; icon: string; subtitle?: string }> = ({
  title,
  value,
  icon,
  subtitle,
}) => (
  <div className="bg-white rounded-lg shadow p-6 text-center">
    <p className="text-3xl mb-2">{icon}</p>
    <p className="text-sm text-gray-600 mb-2">{title}</p>
    <p className="text-3xl font-bold text-blue-600">{value}</p>
    {subtitle ? <p className="mt-2 text-xs text-gray-500">{subtitle}</p> : null}
  </div>
);

/**
 * Status Bar Component
 */
const StatusBar: React.FC<{ status: string; count: number; total: number }> = ({
  status,
  count,
  total,
}) => {
  const percentage = (count / total) * 100;
  const colors: Record<string, string> = {
    completed: 'bg-green-500',
    pending: 'bg-yellow-500',
    failed: 'bg-red-500',
    in_progress: 'bg-blue-500',
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <span className="text-sm font-semibold capitalize">{status}</span>
        <span className="text-sm text-gray-600">
          {count} ({percentage.toFixed(0)}%)
        </span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className={`h-2 rounded-full ${colors[status] || 'bg-gray-500'}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};

/**
 * Domain Bar Component
 */
const DomainBar: React.FC<{ domain: string; count: number }> = ({
  domain,
  count,
}) => (
  <div className="flex justify-between items-center">
    <span className="text-sm font-semibold capitalize">{domain}</span>
    <span className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-sm">
      {count}
    </span>
  </div>
);

/**
 * Priority Bar Component
 */
const PriorityBar: React.FC<{ priority: string; count: number }> = ({
  priority,
  count,
}) => {
  const priorityColors: Record<string, string> = {
    high: 'bg-red-100 text-red-800',
    medium: 'bg-yellow-100 text-yellow-800',
    low: 'bg-green-100 text-green-800',
  };

  return (
    <div className="flex justify-between items-center">
      <span className="text-sm font-semibold capitalize">{priority}</span>
      <span
        className={`px-3 py-1 rounded-full text-sm ${
          priorityColors[priority] || 'bg-gray-100'
        }`}
      >
        {count}
      </span>
    </div>
  );
};

/**
 * Stat Row Component
 */
const StatRow: React.FC<{ label: string; value: string | number; unit: string }> = ({
  label,
  value,
  unit,
}) => (
  <div className="flex justify-between items-center">
    <span className="text-sm text-gray-600">{label}</span>
    <span className="font-semibold">
      {value} <span className="text-xs text-gray-500">{unit}</span>
    </span>
  </div>
);

/**
 * Action Button Component
 */
const ActionButton: React.FC<{ label: string; icon: string }> = ({
  label,
  icon,
}) => (
  <button className="w-full flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded transition">
    <span>{icon}</span>
    <span className="text-sm text-gray-700">{label}</span>
  </button>
);
