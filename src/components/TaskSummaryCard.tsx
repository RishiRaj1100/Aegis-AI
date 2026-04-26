import { motion } from 'framer-motion';
import { TrendingUp, Clock, AlertTriangle, CheckCircle, Cpu } from 'lucide-react';
import type { AegisResponse } from '@/types/aegis';

interface TaskSummaryCardProps {
  data: AegisResponse;
}

function RingGauge({ value, color, size = 80 }: { value: number; color: string; size?: number }) {
  const r = size / 2 - 8;
  const circ = 2 * Math.PI * r;
  const offset = circ * (1 - value / 100);

  return (
    <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
      <circle className="ring-track" cx={size / 2} cy={size / 2} r={r} />
      <motion.circle
        className="ring-fill"
        cx={size / 2} cy={size / 2} r={r}
        stroke={color}
        strokeDasharray={circ}
        initial={{ strokeDashoffset: circ }}
        animate={{ strokeDashoffset: offset }}
        transition={{ duration: 1.2, ease: [0.4, 0, 0.2, 1] }}
      />
    </svg>
  );
}

export default function TaskSummaryCard({ data }: TaskSummaryCardProps) {
  const plan = data.plan || data;
  const confidence = Math.round(data.confidence ?? plan.confidence ?? 0);
  const riskLevel = data.risk_level || plan.risk_level || 'MEDIUM';
  const processingTime = data.processing_time_ms
    ? `${(data.processing_time_ms / 1000).toFixed(1)}s`
    : '—';
  const provider = data.reasoning_provider || 'Groq';
  const taskId = (data.task_id || plan.task_id || '').toString().substring(0, 8);

  const delayRisk = Math.round(
    (data.trust_dimensions as { delay_risk?: number })?.delay_risk ??
    (plan.dimensions as { delay_risk?: number })?.delay_risk ??
    (100 - confidence) * 0.4
  );

  const riskColor =
    riskLevel === 'HIGH' ? '#F43F5E' :
    riskLevel === 'LOW'  ? '#10B981' : '#F59E0B';
  const riskBadge =
    riskLevel === 'HIGH' ? 'badge-danger' :
    riskLevel === 'LOW'  ? 'badge-success' : 'badge-warning';

  return (
    <motion.div
      className="glass p-6"
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4 }}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <CheckCircle size={16} style={{ color: '#7C3AED' }} />
        <h3 className="text-sm font-bold" style={{ fontFamily: 'Syne', color: '#0F0A2E' }}>
          Task Summary
        </h3>
        <span className={`badge badge-violet ml-auto`}>
          ID: {taskId || '—'}
        </span>
      </div>

      {/* Goal text */}
      <p className="text-sm mb-5 leading-relaxed" style={{ color: '#4B5563' }}>
        {plan.goal || 'Mission analysis complete'}
      </p>

      {/* Metrics grid */}
      <div className="grid grid-cols-3 gap-3">
        {/* Success probability ring */}
        <div className="glass-sm p-3 flex flex-col items-center gap-2">
          <div className="relative">
            <RingGauge value={confidence} color="#7C3AED" size={72} />
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-lg font-bold" style={{ fontFamily: 'Syne', color: '#7C3AED' }}>
                {confidence}
              </span>
            </div>
          </div>
          <div className="text-center">
            <p className="text-xs font-semibold" style={{ color: '#0F0A2E' }}>Success</p>
            <p className="text-xs" style={{ color: '#9CA3AF' }}>Probability</p>
          </div>
        </div>

        {/* Delay risk ring */}
        <div className="glass-sm p-3 flex flex-col items-center gap-2">
          <div className="relative">
            <RingGauge value={delayRisk} color="#F59E0B" size={72} />
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-lg font-bold" style={{ fontFamily: 'Syne', color: '#F59E0B' }}>
                {delayRisk}
              </span>
            </div>
          </div>
          <div className="text-center">
            <p className="text-xs font-semibold" style={{ color: '#0F0A2E' }}>Delay</p>
            <p className="text-xs" style={{ color: '#9CA3AF' }}>Risk %</p>
          </div>
        </div>

        {/* Metadata */}
        <div className="glass-sm p-3 flex flex-col gap-2 justify-center">
          <div className="flex items-center gap-2">
            <AlertTriangle size={12} style={{ color: riskColor }} />
            <span className={`badge ${riskBadge}`}>{riskLevel}</span>
          </div>
          <div className="flex items-center gap-2">
            <Clock size={12} style={{ color: '#9CA3AF' }} />
            <span className="text-xs font-mono" style={{ color: '#6B7280' }}>{processingTime}</span>
          </div>
          <div className="flex items-center gap-2">
            <Cpu size={12} style={{ color: '#9CA3AF' }} />
            <span className="text-xs" style={{ color: '#6B7280' }}>{provider}</span>
          </div>
          {data.fallback_used && (
            <span className="badge badge-warning text-xs">Fallback</span>
          )}
        </div>
      </div>

      {/* Key Strategic Insights */}
      {plan.research_insights && (
        <div className="mt-5 p-4 rounded-xl" style={{ background: 'rgba(124,58,237,0.04)', border: '1px solid rgba(124,58,237,0.08)' }}>
          <h4 className="text-xs font-bold uppercase tracking-wider mb-2" style={{ color: '#7C3AED' }}>
            Key Strategic Insights
          </h4>
          <ul className="space-y-1.5">
            {plan.research_insights.split('\n').filter(l => l.trim().length > 5).slice(0, 4).map((point, i) => (
              <li key={i} className="text-xs flex gap-2" style={{ color: '#4B5563' }}>
                <span style={{ color: '#7C3AED' }}>•</span>
                {point.replace(/^[*-]\s*/, '').trim()}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Confidence bar */}
      <div className="mt-5">
        <div className="flex justify-between text-xs mb-1" style={{ color: '#9CA3AF' }}>
          <span>Overall Confidence</span>
          <span style={{ fontFamily: 'JetBrains Mono', color: '#7C3AED' }}>{confidence}%</span>
        </div>
        <div className="h-1.5 rounded-full" style={{ background: 'rgba(124,58,237,0.1)' }}>
          <motion.div
            className="h-full rounded-full"
            style={{ background: 'linear-gradient(90deg, #7C3AED, #06B6D4)' }}
            initial={{ width: 0 }}
            animate={{ width: `${confidence}%` }}
            transition={{ duration: 1.2, ease: [0.4, 0, 0.2, 1] }}
          />
        </div>
      </div>

      {/* Trace info */}
      {data.system_trace && data.system_trace.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {data.system_trace.slice(0, 4).map((step, i) => (
            <span key={i} className="badge badge-violet text-xs">{step}</span>
          ))}
        </div>
      )}

      {/* Provider badge */}
      <div className="mt-3 flex items-center gap-2">
        <TrendingUp size={12} style={{ color: '#10B981' }} />
        <span className="text-xs" style={{ color: '#6B7280' }}>
          Processed by <strong style={{ color: '#7C3AED' }}>{provider}</strong>
          {data.fallback_used ? ' (fallback active)' : ''}
        </span>
      </div>
    </motion.div>
  );
}
