import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ListChecks, ChevronDown, ChevronUp, CircleDot } from 'lucide-react';
import type { AegisResponse, Subtask } from '@/types/aegis';

interface ExecutionPlanPanelProps {
  data: AegisResponse;
}

const PRIORITY_COLORS: Record<string, string> = {
  HIGH: '#F43F5E',
  MEDIUM: '#F59E0B',
  LOW: '#10B981',
};

export default function ExecutionPlanPanel({ data }: ExecutionPlanPanelProps) {
  const [showAll, setShowAll] = useState(false);

  const plan = data.plan || data;
  const subtasks: Subtask[] = plan.subtasks || data.subtasks || [];
  const visible = showAll ? subtasks : subtasks.slice(0, 5);
  const hasMore = subtasks.length > 5;

  return (
    <motion.div
      className="glass p-6"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.25 }}
    >
      <div className="flex items-center gap-2 mb-4">
        <ListChecks size={16} style={{ color: '#10B981' }} />
        <h3 className="text-sm font-bold" style={{ fontFamily: 'Syne', color: '#0F0A2E' }}>
          Execution Plan
        </h3>
        <span className="badge badge-success ml-auto">{subtasks.length} subtasks</span>
      </div>

      {subtasks.length === 0 ? (
        <div className="py-8 flex flex-col items-center gap-2">
          <ListChecks size={32} style={{ color: 'rgba(16,185,129,0.3)' }} />
          <p className="text-sm text-center" style={{ color: '#9CA3AF' }}>
            No subtasks generated yet.
          </p>
        </div>
      ) : (
        <>
          <div className="space-y-2">
            <AnimatePresence initial={false}>
              {visible.map((task, i) => {
                const score = task.trust_score ?? task.confidence ?? 0;
                const priorityColor = PRIORITY_COLORS[task.priority || 'MEDIUM'] || '#F59E0B';

                return (
                  <motion.div
                    key={task.id || i}
                    className="glass-sm p-3 flex items-start gap-3"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    transition={{ delay: i * 0.05 }}
                    layout
                  >
                    <div className="flex-shrink-0 flex items-center gap-2 mt-0.5">
                      <CircleDot size={12} style={{ color: priorityColor }} />
                      <span className="text-xs font-mono font-bold" style={{ color: '#D1D5DB', minWidth: '24px' }}>
                        {String(i + 1).padStart(2, '0')}
                      </span>
                    </div>

                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold" style={{ color: '#0F0A2E' }}>
                        {task.title || task.name || `Subtask ${i + 1}`}
                      </p>
                      {task.description && (
                        <p className="text-xs mt-0.5 leading-relaxed" style={{ color: '#6B7280' }}>
                          {task.description}
                        </p>
                      )}
                      {task.deadline_days !== undefined && (
                        <p className="text-xs mt-1" style={{ color: '#9CA3AF', fontFamily: 'JetBrains Mono' }}>
                          ⏱ {task.deadline_days}d deadline
                        </p>
                      )}
                    </div>

                    {score > 0 && (
                      <div className="flex-shrink-0 text-right">
                        <span className={`badge ${score >= 75 ? 'badge-success' : score >= 50 ? 'badge-warning' : 'badge-danger'}`}>
                          {Math.round(score)}%
                        </span>
                      </div>
                    )}
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>

          {/* Show more / Show less button — fixed clickable area */}
          {hasMore && (
            <motion.button
              id="show-more-subtasks-btn"
              onClick={() => setShowAll((v) => !v)}
              className="mt-3 w-full flex items-center justify-center gap-2 py-2 rounded-xl text-xs font-semibold transition-all"
              style={{
                background: 'rgba(16,185,129,0.06)',
                border: '1px solid rgba(16,185,129,0.2)',
                color: '#059669',
                cursor: 'pointer',
              }}
              whileTap={{ scale: 0.98 }}
              whileHover={{ background: 'rgba(16,185,129,0.1)' }}
            >
              {showAll ? (
                <><ChevronUp size={13} /> Show Less</>
              ) : (
                <><ChevronDown size={13} /> Show {subtasks.length - 5} More</>
              )}
            </motion.button>
          )}
        </>
      )}
    </motion.div>
  );
}
