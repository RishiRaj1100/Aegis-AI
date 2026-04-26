import { motion } from 'framer-motion';
import { RotateCcw, TrendingUp, Lightbulb } from 'lucide-react';
import type { AegisResponse } from '@/types/aegis';

interface ReflectionPanelProps {
  data: AegisResponse;
}

export default function ReflectionPanel({ data }: ReflectionPanelProps) {
  const reflection = data.reflection;
  const current = reflection?.current_prediction ?? Math.round((data.confidence ?? 0));
  const past = reflection?.past_prediction ?? Math.max(0, current - (reflection?.improvement_delta ?? 8));
  const delta = reflection?.improvement_delta ?? (current - past);
  const insights: string[] = reflection?.insights ?? [
    'Model confidence improved from previous similar tasks.',
    'Deadline pressure reduced after resource realignment.',
    'Trust score stabilised with additional evidence.',
  ];

  return (
    <motion.div
      className="glass p-6"
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, delay: 0.35 }}
    >
      <div className="flex items-center gap-2 mb-4">
        <RotateCcw size={16} style={{ color: '#7C3AED' }} />
        <h3 className="text-sm font-bold" style={{ fontFamily: 'Syne', color: '#0F0A2E' }}>
          Reflection
        </h3>
        {delta > 0 && (
          <span className="badge badge-success ml-auto">+{Math.round(delta)}% improved</span>
        )}
      </div>

      {/* Past vs Current */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="glass-sm p-3 text-center">
          <p className="text-xs mb-1" style={{ color: '#9CA3AF' }}>Past Prediction</p>
          <p className="text-2xl font-bold" style={{ fontFamily: 'Syne', color: '#6B7280' }}>{past}%</p>
        </div>
        <div className="glass-sm p-3 text-center" style={{ borderColor: 'rgba(124,58,237,0.3)' }}>
          <p className="text-xs mb-1" style={{ color: '#7C3AED' }}>Current Prediction</p>
          <p className="text-2xl font-bold" style={{ fontFamily: 'Syne', color: '#7C3AED' }}>{current}%</p>
        </div>
      </div>

      {/* Delta bar */}
      <div className="mb-4">
        <div className="flex justify-between text-xs mb-1" style={{ color: '#9CA3AF' }}>
          <span>Improvement Delta</span>
          <span className="flex items-center gap-1" style={{ color: delta >= 0 ? '#10B981' : '#F43F5E' }}>
            <TrendingUp size={10} />
            {delta >= 0 ? '+' : ''}{Math.round(delta)}%
          </span>
        </div>
        <div className="h-2 rounded-full" style={{ background: 'rgba(124,58,237,0.1)' }}>
          <motion.div
            className="h-full rounded-full"
            style={{ background: delta >= 0 ? 'linear-gradient(90deg,#10B981,#06B6D4)' : '#F43F5E' }}
            initial={{ width: 0 }}
            animate={{ width: `${Math.min(100, Math.abs(delta))}%` }}
            transition={{ duration: 1, delay: 0.2 }}
          />
        </div>
      </div>

      {/* Insights */}
      <div className="space-y-2">
        {insights.slice(0, 3).map((insight, i) => (
          <motion.div
            key={i}
            className="flex items-start gap-2 p-2 rounded-lg"
            style={{ background: 'rgba(124,58,237,0.04)' }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.1 + i * 0.1 }}
          >
            <Lightbulb size={12} className="mt-0.5 flex-shrink-0" style={{ color: '#F59E0B' }} />
            <p className="text-xs leading-relaxed" style={{ color: '#4B5563' }}>{insight}</p>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
