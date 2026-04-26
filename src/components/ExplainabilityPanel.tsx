import { motion } from 'framer-motion';
import { FlaskConical, TrendingUp, TrendingDown, HelpCircle } from 'lucide-react';
import type { AegisResponse } from '@/types/aegis';

interface ExplainabilityPanelProps {
  data: AegisResponse;
  onWhyClick?: () => void;
}

export default function ExplainabilityPanel({ data, onWhyClick }: ExplainabilityPanelProps) {
  const explainability = data.explainability || {};
  const entries = Object.entries(explainability).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
  const maxVal = entries.length > 0 ? Math.max(...entries.map(([, v]) => Math.abs(v)), 1) : 1;

  const plan = data.plan || data;
  const reasoning = (data.plan?.debate_results?.reasoning) || plan.reasoning || '';

  return (
    <motion.div
      className="glass p-6"
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, delay: 0.1 }}
    >
      <div className="flex items-center gap-2 mb-4">
        <FlaskConical size={16} style={{ color: '#06B6D4' }} />
        <h3 className="text-sm font-bold" style={{ fontFamily: 'Syne', color: '#0F0A2E' }}>
          SHAP Explainability
        </h3>
        <button
          onClick={onWhyClick}
          className="ml-auto flex items-center gap-1 btn-ghost text-xs py-1 px-2"
        >
          <HelpCircle size={12} />
          Why?
        </button>
      </div>

      {entries.length > 0 ? (
        <div className="space-y-3">
          {entries.slice(0, 8).map(([feature, value], i) => {
            const isPositive = value >= 0;
            const pct = (Math.abs(value) / maxVal) * 100;
            const color = isPositive ? '#10B981' : '#F43F5E';
            const label = feature.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

            return (
              <motion.div key={feature}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
              >
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xs font-medium" style={{ color: '#4B5563' }}>{label}</span>
                  <div className="flex items-center gap-1">
                    {isPositive
                      ? <TrendingUp size={10} style={{ color }} />
                      : <TrendingDown size={10} style={{ color }} />}
                    <span className="text-xs font-mono font-semibold" style={{ color }}>
                      {isPositive ? '+' : ''}{value.toFixed(2)}
                    </span>
                  </div>
                </div>
                <div className="h-1.5 rounded-full" style={{ background: 'rgba(0,0,0,0.06)' }}>
                  <motion.div
                    className="h-full rounded-full"
                    style={{ background: color }}
                    initial={{ width: 0 }}
                    animate={{ width: `${pct}%` }}
                    transition={{ duration: 0.8, delay: i * 0.05 }}
                  />
                </div>
              </motion.div>
            );
          })}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-8 gap-2">
          <FlaskConical size={32} style={{ color: 'rgba(6,182,212,0.3)' }} />
          <p className="text-sm text-center" style={{ color: '#9CA3AF' }}>
            No SHAP data available.<br />Submit a goal to see feature explanations.
          </p>
        </div>
      )}

      {reasoning && (
        <div className="mt-4 p-3 rounded-xl" style={{ background: 'rgba(6,182,212,0.05)', border: '1px solid rgba(6,182,212,0.15)' }}>
          <p className="text-xs font-semibold mb-1" style={{ color: '#0E7490' }}>Reasoning</p>
          <p className="text-xs leading-relaxed" style={{ color: '#4B5563' }}>{reasoning}</p>
        </div>
      )}
    </motion.div>
  );
}
