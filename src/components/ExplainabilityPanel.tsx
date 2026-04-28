import { motion } from 'framer-motion';
import { FlaskConical, TrendingUp, TrendingDown, HelpCircle, ShieldCheck, AlertCircle } from 'lucide-react';
import type { AegisResponse } from '@/types/aegis';

interface ExplainabilityPanelProps {
  data: AegisResponse;
  onWhyClick?: () => void;
}

export default function ExplainabilityPanel({ data, onWhyClick }: ExplainabilityPanelProps) {
  const explain = data.explainability || {};
  const shapValues = (explain.shap_values || {}) as Record<string, number>;
  const positiveFactors = explain.positive_factors || [];
  const negativeFactors = explain.negative_factors || [];
  
  const entries = Object.entries(shapValues)
    .map(([k, v]) => [k, typeof v === 'number' ? v : parseFloat(v as string)])
    .filter(([, v]) => !isNaN(v as number))
    .sort((a, b) => Math.abs(b[1] as number) - Math.abs(a[1] as number));
    
  const maxVal = entries.length > 0 ? Math.max(...entries.map(([, v]) => Math.abs(v as number)), 1) : 1;

  return (
    <motion.div
      className="glass p-6 h-full flex flex-col"
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, delay: 0.1 }}
    >
      <div className="flex items-center gap-2 mb-6">
        <div className="w-8 h-8 rounded-xl bg-cyan-50 flex items-center justify-center">
          <FlaskConical size={18} className="text-cyan-600" />
        </div>
        <h3 className="text-sm font-black uppercase tracking-wider text-slate-800" style={{ fontFamily: 'Syne' }}>
          SHAP Explainability Core
        </h3>
        {explain.warning && (
          <div className="ml-auto group relative">
            <AlertCircle size={14} className="text-amber-500 cursor-help" />
            <div className="absolute bottom-full right-0 mb-2 w-48 p-2 bg-slate-900 text-white text-[10px] rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
              {explain.warning}
            </div>
          </div>
        )}
      </div>

      <div className="space-y-6 flex-1 overflow-y-auto pr-2 custom-scrollbar">
        {/* Numerical Drivers */}
        {entries.length > 0 && (
          <div className="space-y-3">
            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-4">Neural Feature Weights</p>
            {entries.slice(0, 6).map(([feature, value], i) => {
              const val = value as number;
              const isPositive = val >= 0;
              const pct = (Math.abs(val) / maxVal) * 100;
              const color = isPositive ? '#10B981' : '#F43F5E';
              const label = feature.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

              return (
                <div key={feature}>
                  <div className="flex justify-between items-center mb-1.5">
                    <span className="text-[11px] font-bold text-slate-600">{label}</span>
                    <span className="text-[10px] font-mono font-black" style={{ color }}>
                      {isPositive ? '+' : ''}{val.toFixed(2)}
                    </span>
                  </div>
                  <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">
                    <motion.div
                      className="h-full rounded-full"
                      style={{ background: color }}
                      initial={{ width: 0 }}
                      animate={{ width: `${pct}%` }}
                      transition={{ duration: 1, delay: i * 0.1 }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Textual Drivers */}
        <div className="grid grid-cols-1 gap-4 pt-2">
          {positiveFactors.length > 0 && (
            <div className="p-4 rounded-2xl bg-emerald-50/50 border border-emerald-100/50">
              <div className="flex items-center gap-2 mb-3">
                <ShieldCheck size={14} className="text-emerald-600" />
                <span className="text-[10px] font-black uppercase tracking-widest text-emerald-700">Success Catalysts</span>
              </div>
              <ul className="space-y-2">
                {positiveFactors.map((f, i) => (
                  <li key={i} className="text-[11px] leading-relaxed text-emerald-900 flex gap-2">
                    <span className="opacity-40">•</span> {f}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {negativeFactors.length > 0 && (
            <div className="p-4 rounded-2xl bg-rose-50/50 border border-rose-100/50">
              <div className="flex items-center gap-2 mb-3">
                <TrendingDown size={14} className="text-rose-600" />
                <span className="text-[10px] font-black uppercase tracking-widest text-rose-700">Risk Drivers</span>
              </div>
              <ul className="space-y-2">
                {negativeFactors.map((f, i) => (
                  <li key={i} className="text-[11px] leading-relaxed text-rose-900 flex gap-2">
                    <span className="opacity-40">•</span> {f}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      <button
        onClick={onWhyClick}
        className="mt-6 w-full py-3 rounded-2xl bg-slate-900 text-white text-[11px] font-black uppercase tracking-widest hover:bg-indigo-600 transition-all flex items-center justify-center gap-2"
      >
        <HelpCircle size={14} />
        Verification Request
      </button>
    </motion.div>
  );
}
