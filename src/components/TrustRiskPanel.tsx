import { motion } from 'framer-motion';
import { ShieldCheck, CheckCircle2, XCircle, AlertOctagon } from 'lucide-react';
import type { AegisResponse } from '@/types/aegis';

interface TrustRiskPanelProps {
  data: AegisResponse;
}

export default function TrustRiskPanel({ data }: TrustRiskPanelProps) {
  const trustData = data.trust_dimensions || (data.plan?.dimensions as typeof data.trust_dimensions);
  const claims = Array.isArray(trustData?.claims) ? trustData.claims : [];
  const dims = trustData?.dimensions;

  const verifiedCount = claims.filter((c) => c.verified).length;
  const total = claims.length;
  let trustScore = total > 0 ? (verifiedCount / total) * 100 : (data.confidence || 70);
  if (isNaN(trustScore)) trustScore = 0;

  const dimensionLabels: Record<string, string> = {
    goal_clarity: 'Goal Clarity',
    information_quality: 'Info Quality',
    execution_feasibility: 'Feasibility',
    risk_manageability: 'Manageability',
    resource_adequacy: 'Resources',
    external_uncertainty: 'Stability',
  };

  return (
    <motion.div
      className="glass p-6"
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, delay: 0.4 }}
    >
      <div className="flex items-center gap-2 mb-4">
        <ShieldCheck size={16} style={{ color: '#10B981' }} />
        <h3 className="text-sm font-bold" style={{ fontFamily: 'Syne', color: '#0F0A2E' }}>
          Trust & Risk
        </h3>
        {total > 0 && (
          <span className={`badge ml-auto ${verifiedCount === total ? 'badge-success' : 'badge-warning'}`}>
            {verifiedCount}/{total} verified
          </span>
        )}
      </div>

      {/* Trust score bar */}
      <div className="mb-6">
        <div className="flex justify-between text-xs mb-1.5" style={{ color: '#9CA3AF' }}>
          <span>Claim Verification Score</span>
          <span style={{ fontFamily: 'JetBrains Mono', color: '#10B981' }}>
            {Math.round(trustScore)}%
          </span>
        </div>
        <div className="h-2 rounded-full" style={{ background: 'rgba(16,185,129,0.1)' }}>
          <motion.div
            className="h-full rounded-full"
            style={{ background: 'linear-gradient(90deg, #10B981, #06B6D4)' }}
            initial={{ width: 0 }}
            animate={{ width: `${trustScore}%` }}
            transition={{ duration: 1, delay: 0.2 }}
          />
        </div>
      </div>

      {/* 6D Trust Model */}
      {dims && (
        <div className="mb-6 space-y-3">
          <h4 className="text-[10px] font-bold uppercase tracking-wider mb-2" style={{ color: '#9CA3AF' }}>
            6D Trust Dimensions
          </h4>
          <div className="grid grid-cols-2 gap-x-4 gap-y-3">
            {Object.entries(dims).map(([key, val], i) => (
              <div key={key} className="space-y-1">
                <div className="flex justify-between text-[10px]">
                  <span style={{ color: '#6B7280' }}>{dimensionLabels[key] || key}</span>
                  <span style={{ color: '#0F0A2E', fontWeight: 600 }}>{Math.round((val as number) * 100)}%</span>
                </div>
                <div className="h-1 rounded-full" style={{ background: 'rgba(0,0,0,0.05)' }}>
                  <motion.div
                    className="h-full rounded-full"
                    style={{ background: (val as number) > 0.7 ? '#10B981' : (val as number) > 0.4 ? '#F59E0B' : '#F43F5E' }}
                    initial={{ width: 0 }}
                    animate={{ width: `${(val as number) * 100}%` }}
                    transition={{ duration: 0.8, delay: 0.5 + i * 0.1 }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Claims */}
      <div className="space-y-3">
        <h4 className="text-[10px] font-bold uppercase tracking-wider mb-2" style={{ color: '#9CA3AF' }}>
          Extracted Claims
        </h4>
        {claims.length > 0 ? (
          claims.map((claim, i) => (
            <motion.div
              key={i}
              className="glass-sm p-3"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08 }}
            >
              <div className="flex items-start gap-2">
                {claim.verified
                  ? <CheckCircle2 size={14} style={{ color: '#10B981', flexShrink: 0, marginTop: 1 }} />
                  : <XCircle size={14} style={{ color: '#F43F5E', flexShrink: 0, marginTop: 1 }} />}
                <div>
                  <p className="text-xs font-semibold" style={{ color: '#0F0A2E' }}>{claim.claim}</p>
                  {claim.evidence?.map((ev: string, j: number) => (
                    <p key={j} className="text-[10px] mt-0.5 flex items-center gap-1" style={{ color: '#6B7280' }}>
                      <AlertOctagon size={9} style={{ color: '#9CA3AF' }} /> {ev}
                    </p>
                  ))}
                </div>
              </div>
            </motion.div>
          ))
        ) : (
          <div className="flex flex-col items-center justify-center py-6 gap-2 opacity-50">
            <ShieldCheck size={32} style={{ color: '#9CA3AF' }} />
            <p className="text-[10px] text-center" style={{ color: '#9CA3AF' }}>
              Waiting for analysis...
            </p>
          </div>
        )}
      </div>
    </motion.div>
  );
}
