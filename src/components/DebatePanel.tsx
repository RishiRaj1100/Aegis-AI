import { motion, AnimatePresence } from 'framer-motion';
import { Users, ChevronDown } from 'lucide-react';
import { useState } from 'react';
import type { AegisResponse, DebateResult } from '@/types/aegis';

interface DebatePanelProps {
  data: AegisResponse;
}

const AGENTS: Array<{
  key: keyof DebateResult;
  label: string;
  color: string;
  bg: string;
  border: string;
  emoji: string;
  default: string;
}> = [
  {
    key: 'optimist',
    label: 'Optimist',
    color: '#10B981',
    bg: 'rgba(16,185,129,0.06)',
    border: 'rgba(16,185,129,0.25)',
    emoji: '🟢',
    default: 'The potential impact clearly justifies starting this mission immediately with full commitment.',
  },
  {
    key: 'risk_analyst',
    label: 'Risk Analyst',
    color: '#F43F5E',
    bg: 'rgba(244,63,94,0.06)',
    border: 'rgba(244,63,94,0.25)',
    emoji: '🔴',
    default: 'Potential blockers in environmental stability require mitigation before commencing operations.',
  },
  {
    key: 'executor',
    label: 'Executor',
    color: '#F59E0B',
    bg: 'rgba(245,158,11,0.06)',
    border: 'rgba(245,158,11,0.25)',
    emoji: '🟡',
    default: 'Clear milestones and resource allocation must be defined before initiating any subtask.',
  },
];

export default function DebatePanel({ data }: DebatePanelProps) {
  const [expanded, setExpanded] = useState(false);
  const plan = data.plan || data;
  const debate: DebateResult = plan.debate_results || data.debate_results || {};

  return (
    <motion.div
      className="glass p-6"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.2 }}
    >
      <div className="flex items-center gap-2 mb-4">
        <Users size={16} style={{ color: '#7C3AED' }} />
        <h3 className="text-sm font-bold" style={{ fontFamily: 'Syne', color: '#0F0A2E' }}>
          Multi-Agent Debate
        </h3>
        {debate.consensus_score !== undefined && (
          <span className="badge badge-violet ml-auto">
            Consensus: {Math.round(debate.consensus_score)}%
          </span>
        )}
      </div>

      {/* Agent bubbles */}
      <div className="space-y-3">
        {AGENTS.map((agent, i) => {
          const text = debate[agent.key] as string | undefined;
          return (
            <motion.div
              key={agent.key}
              className="agent-bubble"
              style={{ background: agent.bg, borderColor: agent.border }}
              initial={{ opacity: 0, x: -16 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1 + i * 0.1 }}
            >
              <div className="flex items-center gap-2 mb-2">
                <span>{agent.emoji}</span>
                <span className="text-xs font-bold" style={{ color: agent.color, fontFamily: 'Syne' }}>
                  {agent.label}
                </span>
              </div>
              <p className="text-xs leading-relaxed" style={{ color: '#374151' }}>
                {text || agent.default}
              </p>
            </motion.div>
          );
        })}
      </div>

      {/* Final decision */}
      <div className="mt-4">
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center justify-between p-3 rounded-xl transition-all"
          style={{ background: 'rgba(124,58,237,0.06)', border: '1px solid rgba(124,58,237,0.2)' }}
        >
          <span className="text-xs font-bold" style={{ color: '#7C3AED', fontFamily: 'Syne' }}>
            ⚡ Final Decision
          </span>
          <ChevronDown
            size={14}
            style={{
              color: '#7C3AED',
              transform: expanded ? 'rotate(180deg)' : 'rotate(0)',
              transition: 'transform 0.2s',
            }}
          />
        </button>

        <AnimatePresence>
          {expanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="overflow-hidden"
            >
              <div className="p-3 mt-2 rounded-xl" style={{ background: 'rgba(124,58,237,0.04)' }}>
                <p className="text-sm leading-relaxed" style={{ color: '#0F0A2E' }}>
                  {debate.final_decision || 'Proceed with mission under controlled, staged rollout conditions with risk monitoring at each milestone.'}
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
