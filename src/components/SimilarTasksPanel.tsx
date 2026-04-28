import { motion } from 'framer-motion';
import { History, CheckCircle, XCircle, ChevronRight } from 'lucide-react';
import type { AegisResponse, SimilarTask } from '@/types/aegis';

interface SimilarTasksPanelProps {
  data: AegisResponse;
}

export default function SimilarTasksPanel({ data }: SimilarTasksPanelProps) {
  const tasks: SimilarTask[] = data.similar_tasks || [];

  return (
    <motion.div
      className="glass p-6"
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, delay: 0.15 }}
    >
      <div className="flex items-center gap-2 mb-4">
        <History size={16} style={{ color: '#F59E0B' }} />
        <h3 className="text-sm font-bold" style={{ fontFamily: 'Syne', color: '#0F0A2E' }}>
          Similar Tasks
        </h3>
        <span className="badge badge-warning ml-auto">{tasks.length} found</span>
      </div>

      <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
        {tasks.length > 0 ? (
          tasks.map((task, i) => (
            <motion.div
              key={task.id}
              className="glass-sm p-3 flex items-center gap-3 cursor-pointer hover:scale-[1.01] transition-transform"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06 }}
              whileHover={{ x: 2 }}
            >
              {task.status === 'COMPLETED'
                ? <CheckCircle size={14} style={{ color: '#10B981', flexShrink: 0 }} />
                : <XCircle size={14} style={{ color: '#F43F5E', flexShrink: 0 }} />}

              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium truncate" style={{ color: '#0F0A2E' }}>{task.goal}</p>
                {task.confidence !== undefined && (
                  <p className="text-xs mt-0.5" style={{ color: '#9CA3AF', fontFamily: 'JetBrains Mono' }}>
                    Similarity: {Math.round((task.similarity || 0) * 100)}%
                  </p>
                )}
              </div>

              <div className="flex items-center gap-2 flex-shrink-0">
                <span className={`badge ${task.status === 'COMPLETED' ? 'badge-success' : 'badge-danger'}`}>
                  {task.status}
                </span>
                <ChevronRight size={12} style={{ color: '#D1D5DB' }} />
              </div>
            </motion.div>
          ))
        ) : (
          <div className="flex flex-col items-center justify-center py-10 gap-2 opacity-50">
            <History size={32} style={{ color: '#9CA3AF' }} />
            <p className="text-xs text-center" style={{ color: '#9CA3AF' }}>
              No similar historical tasks found.<br />The system will learn from your current goal.
            </p>
          </div>
        )}
      </div>
    </motion.div>
  );
}
