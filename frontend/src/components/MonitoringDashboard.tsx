import React, { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { apiFetch } from '@/services/api';
import { useMission } from '@/contexts/MissionContext';

interface HealthStatus {
  status: 'healthy' | 'degraded' | 'critical' | 'unknown';
  service: string;
  response_time_ms: number;
  message: string;
}

interface SystemMetrics {
  requests_per_second: number;
  average_response_time_ms: number;
  error_rate: number;
  uptime_percentage: number;
}

interface Alert {
  id: string;
  title: string;
  message: string;
  severity: 'info' | 'warning' | 'critical';
  timestamp: string;
}

interface DashboardData {
  health: {
    mongodb: HealthStatus;
    redis: HealthStatus;
    api: HealthStatus;
  };
  metrics: SystemMetrics;
  alerts: Alert[];
  active_connections: number;
  cache_hit_rate: number;
  uptime_percentage: number;
}

const defaultHealth = (service: string): HealthStatus => ({
  status: 'unknown',
  service,
  response_time_ms: 0,
  message: 'Loading...',
});

const coerceStatus = (value: any): HealthStatus['status'] => {
  const raw = String(value || '').toLowerCase();
  if (raw.includes('healthy') || raw.includes('success')) return 'healthy';
  if (raw.includes('degrad')) return 'degraded';
  if (raw.includes('critical') || raw.includes('error') || raw.includes('fail')) return 'critical';
  return 'unknown';
};

/**
 * MonitoringDashboard - Real-time health and mission telemetry dashboard
 */
export const MonitoringDashboard: React.FC = () => {
  const { mission } = useMission();
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(5000);
  const [selectedService, setSelectedService] = useState<'mongodb' | 'redis' | 'api'>('mongodb');

  const healthRows = useMemo(
    () => [
      { key: 'mongodb' as const, label: 'MongoDB' },
      { key: 'redis' as const, label: 'Redis' },
      { key: 'api' as const, label: 'API' },
    ],
    []
  );

  useEffect(() => {
    fetchDashboardData();
    const interval = window.setInterval(fetchDashboardData, refreshInterval);
    return () => window.clearInterval(interval);
  }, [refreshInterval, mission?.taskId]);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);

      const [databaseHealth, redisHealth, apiHealth, alertsResponse, performanceResponse, uptimeResponse] = await Promise.all([
        apiFetch('/api/monitoring/health/database'),
        apiFetch('/api/monitoring/health/redis'),
        apiFetch('/api/monitoring/health/api'),
        apiFetch('/api/monitoring/alerts?limit=5'),
        apiFetch('/api/monitoring/performance/stats?hours=24'),
        apiFetch('/api/monitoring/uptime?days=7'),
      ]);

      const performance = performanceResponse?.stats || performanceResponse || {};
      const alerts = Array.isArray(alertsResponse?.alerts) ? alertsResponse.alerts : [];

      setDashboardData({
        health: {
          mongodb: {
            status: coerceStatus(databaseHealth?.health_status || databaseHealth?.status),
            service: databaseHealth?.service || 'mongodb',
            response_time_ms: Number(databaseHealth?.response_time_ms || 0),
            message: databaseHealth?.message || 'Database health loaded',
          },
          redis: {
            status: coerceStatus(redisHealth?.health_status || redisHealth?.status),
            service: redisHealth?.service || 'redis',
            response_time_ms: Number(redisHealth?.response_time_ms || 0),
            message: redisHealth?.message || 'Redis health loaded',
          },
          api: {
            status: coerceStatus(apiHealth?.health_status || apiHealth?.status),
            service: apiHealth?.service || 'api',
            response_time_ms: Number(apiHealth?.response_time_ms || 0),
            message: apiHealth?.message || 'API health loaded',
          },
        },
        metrics: {
          requests_per_second: Number(performance.requests_per_second || performance.rps || 0),
          average_response_time_ms: Number(performance.average_response_time_ms || performance.avg_response_time_ms || 0),
          error_rate: Number(performance.error_rate || 0),
          uptime_percentage: Number(uptimeResponse?.uptime_percentage || performance.uptime_percentage || 0),
        },
        alerts: alerts.map((alert: any, index: number) => ({
          id: String(alert?.id || `${index}`),
          title: String(alert?.title || alert?.type || 'Alert'),
          message: String(alert?.message || alert?.details || 'No additional details available.'),
          severity: (alert?.severity || 'info') as Alert['severity'],
          timestamp: String(alert?.timestamp || alert?.created_at || new Date().toISOString()),
        })),
        active_connections: Number(performance.active_connections || performance.connections || 0),
        cache_hit_rate: Number(performance.cache_hit_rate || performance.cacheHitRate || 0),
        uptime_percentage: Number(uptimeResponse?.uptime_percentage || performance.uptime_percentage || 0),
      });
    } catch (error) {
      console.error('Failed to fetch monitoring data:', error);
      setDashboardData({
        health: {
          mongodb: defaultHealth('mongodb'),
          redis: defaultHealth('redis'),
          api: defaultHealth('api'),
        },
        metrics: {
          requests_per_second: 0,
          average_response_time_ms: 0,
          error_rate: 0,
          uptime_percentage: 0,
        },
        alerts: [],
        active_connections: 0,
        cache_hit_rate: 0,
        uptime_percentage: 0,
      });
    } finally {
      setLoading(false);
    }
  };

  if (loading && !dashboardData) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center bg-[radial-gradient(circle_at_top,_rgba(16,185,129,0.14),_transparent_45%),linear-gradient(180deg,rgba(8,8,10,1),rgba(12,12,16,1))]">
        <div className="rounded-3xl border border-white/10 bg-white/5 px-6 py-5 text-center shadow-[0_0_50px_rgba(16,185,129,0.08)]">
          <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Monitoring</p>
          <p className="mt-2 text-xl font-semibold text-foreground">Checking live system pulse</p>
          <p className="mt-1 text-sm text-muted-foreground">MongoDB, Redis, API health, alerts, and throughput are being collected.</p>
        </div>
      </div>
    );
  }

  if (!dashboardData) {
    return (
      <div className="p-6 bg-red-100 border border-red-500 rounded">
        <p className="text-red-800">Failed to load monitoring dashboard</p>
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return '#10b981';
      case 'degraded':
        return '#f59e0b';
      case 'critical':
        return '#ef4444';
      default:
        return '#6b7280';
    }
  };

  const getStatusBgClass = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'bg-emerald-500/10 border-emerald-500/30';
      case 'degraded':
        return 'bg-amber-500/10 border-amber-500/30';
      case 'critical':
        return 'bg-rose-500/10 border-rose-500/30';
      default:
        return 'bg-white/5 border-white/10';
    }
  };

  return (
    <div className="min-h-screen bg-background p-6 md:p-8">
      <div className="mx-auto max-w-7xl space-y-8">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">System monitoring</p>
            <h1 className="mt-1 text-3xl font-bold text-foreground">Live operational pulse</h1>
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground">This dashboard now reflects live health, uptime, alerts, and the latest mission context instead of static demo data.</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={fetchDashboardData}
              className="btn-primary flex items-center gap-2"
            >
              Refresh
            </button>
            <select
              value={refreshInterval}
              onChange={(e) => setRefreshInterval(parseInt(e.target.value))}
              className="input-field w-auto"
            >
              <option value={1000}>1s refresh</option>
              <option value={5000}>5s refresh</option>
              <option value={10000}>10s refresh</option>
              <option value={30000}>30s refresh</option>
            </select>
          </div>
        </div>

        {mission ? (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="mission-shell mission-orbit rounded-2xl border border-white/10 bg-white/5 p-5"
          >
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Current mission</p>
                <h2 className="mt-1 text-xl font-semibold text-foreground">{mission.goal}</h2>
                <p className="text-sm text-muted-foreground">Task {mission.taskId || 'pending'} · {mission.status} · {mission.riskLevel}</p>
              </div>
              <div className="flex flex-wrap gap-2 text-sm">
                <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-muted-foreground">{Math.round(mission.confidence)}% confidence</span>
                <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-muted-foreground">{mission.subtasks} subtasks</span>
                <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-muted-foreground">{mission.language}</span>
              </div>
            </div>
          </motion.div>
        ) : null}

        <div className="grid gap-4 md:grid-cols-3">
          {healthRows.map((row) => {
            const health = dashboardData.health[row.key];
            return (
              <motion.div
                key={row.key}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                className={`rounded-2xl border p-5 ${getStatusBgClass(health.status)}`}
              >
                <div className="flex items-center gap-3">
                  <span className="h-3 w-3 rounded-full" style={{ backgroundColor: getStatusColor(health.status) }} />
                  <div>
                    <p className="text-sm text-muted-foreground">{row.label}</p>
                    <h3 className="text-lg font-semibold text-foreground">{health.status.toUpperCase()}</h3>
                  </div>
                </div>
                <p className="mt-4 text-sm text-muted-foreground">{health.message}</p>
                <p className="mt-2 text-xs text-muted-foreground">Response: {health.response_time_ms.toFixed(2)}ms</p>
              </motion.div>
            );
          })}
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <div className="glass-card p-6 rounded-2xl">
            <h2 className="text-lg font-bold mb-4">Performance Metrics</h2>
            <div className="space-y-4">
              <MetricCard label="Requests/Second" value={dashboardData.metrics.requests_per_second.toFixed(2)} unit="req/s" trend="up" />
              <MetricCard label="Avg Response Time" value={dashboardData.metrics.average_response_time_ms.toFixed(0)} unit="ms" trend="down" />
              <MetricCard label="Error Rate" value={dashboardData.metrics.error_rate.toFixed(2)} unit="%" trend="down" />
              <MetricCard label="Cache Hit Rate" value={dashboardData.cache_hit_rate.toFixed(2)} unit="%" trend="up" />
            </div>
          </div>

          <div className="glass-card p-6 rounded-2xl">
            <h2 className="text-lg font-bold mb-4">Mission Health</h2>
            <div className="space-y-4">
              <MetricCard label="Uptime" value={dashboardData.uptime_percentage.toFixed(1)} unit="%" trend="up" />
              <MetricCard label="Active Connections" value={dashboardData.active_connections.toString()} unit="users" />
              <ProgressBar label="Uptime SLA" value={dashboardData.uptime_percentage} target={99.9} />
            </div>
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <div className="glass-card p-6 rounded-2xl">
            <h2 className="text-lg font-bold mb-4">Service Details</h2>
            <div className="flex flex-wrap gap-2 mb-4">
              {healthRows.map((service) => (
                <button
                  key={service.key}
                  onClick={() => setSelectedService(service.key)}
                  className={`px-4 py-2 rounded-full border text-sm transition-colors ${
                    selectedService === service.key
                      ? 'border-primary/40 bg-primary/10 text-primary'
                      : 'border-white/10 bg-white/5 text-muted-foreground'
                  }`}
                >
                  {service.label}
                </button>
              ))}
            </div>

            <div className="space-y-3 text-sm">
              <DetailItem label="Status" value={dashboardData.health[selectedService].status} />
              <DetailItem label="Response Time" value={`${dashboardData.health[selectedService].response_time_ms.toFixed(2)}ms`} />
              <DetailItem label="Message" value={dashboardData.health[selectedService].message} />
            </div>
          </div>

          <div className="glass-card p-6 rounded-2xl">
            <h2 className="text-lg font-bold mb-4">Recent Alerts</h2>
            {dashboardData.alerts.length === 0 ? (
              <p className="text-muted-foreground">No active alerts</p>
            ) : (
              <div className="space-y-2">
                {dashboardData.alerts.map((alert) => (
                  <AlertItem key={alert.id} alert={alert} />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

const MetricCard: React.FC<{
  label: string;
  value: string;
  unit: string;
  trend?: 'up' | 'down';
}> = ({ label, value, unit, trend }) => (
  <div className="flex items-start justify-between rounded-xl border border-white/10 bg-black/20 p-4">
    <div>
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-bold text-foreground">{value}</p>
      <p className="text-xs text-muted-foreground">{unit}</p>
    </div>
    {trend ? (
      <div className={`text-xl ${trend === 'up' ? 'text-emerald-400' : 'text-cyan-400'}`}>
        {trend === 'up' ? '↑' : '↓'}
      </div>
    ) : null}
  </div>
);

const ProgressBar: React.FC<{
  label: string;
  value: number;
  target: number;
}> = ({ label, value, target }) => {
  const percentage = Math.min((value / target) * 100, 100);
  return (
    <div>
      <div className="mb-1 flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="text-xs font-semibold text-foreground">{value.toFixed(2)}%</p>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-white/10">
        <div className="h-2 rounded-full bg-gradient-to-r from-emerald-400 to-cyan-400" style={{ width: `${percentage}%` }} />
      </div>
      <p className="mt-1 text-xs text-muted-foreground">Target: {target}%</p>
    </div>
  );
};

const DetailItem: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div className="flex items-center justify-between rounded-lg border border-white/10 bg-black/20 px-4 py-3">
    <span className="text-muted-foreground">{label}</span>
    <span className="font-semibold text-foreground">{value}</span>
  </div>
);

const AlertItem: React.FC<{ alert: Alert }> = ({ alert }) => {
  const severityColors = {
    info: 'border-cyan-400/30 bg-cyan-400/10 text-cyan-100',
    warning: 'border-amber-400/30 bg-amber-400/10 text-amber-100',
    critical: 'border-rose-400/30 bg-rose-400/10 text-rose-100',
  };

  return (
    <div className={`rounded-xl border p-4 ${severityColors[alert.severity]}`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="font-semibold text-sm">{alert.title}</p>
          <p className="text-sm mt-1 opacity-90">{alert.message}</p>
        </div>
        <span className="text-xs opacity-70">{new Date(alert.timestamp).toLocaleTimeString()}</span>
      </div>
    </div>
  );
};
