import { motion } from 'framer-motion';
import { ClockIcon, ChevronRight, Trash2 } from 'lucide-react';
import type { TaskHistory } from '@/types/aegis';

interface TaskHistoryPanelProps {
  tasks: TaskHistory[];
  isLoading: boolean;
  onReload: (taskId: string) => void;
}

export default function TaskHistoryPanel({ tasks, isLoading, onReload }: TaskHistoryPanelProps) {
  return (
    <motion.div
      className="glass p-5"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.45 }}
    >
      <div className="flex items-center gap-2 mb-4">
        <ClockIcon size={16} style={{ color: '#4F46E5' }} />
        <h3 className="text-sm font-bold" style={{ fontFamily: 'Syne', color: '#0F0A2E' }}>
          Task History
        </h3>
        <span className="badge badge-info ml-auto">{tasks.length} tasks</span>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton h-12 rounded-xl" />
          ))}
        </div>
      ) : tasks.length === 0 ? (
        <div className="py-8 flex flex-col items-center gap-2">
          <ClockIcon size={28} style={{ color: 'rgba(79,70,229,0.2)' }} />
          <p className="text-xs text-center" style={{ color: '#9CA3AF' }}>
            No history yet. Submit your first goal!
          </p>
        </div>
      ) : (
        <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
          {tasks.map((task, i) => {
            const riskBadge =
              task.risk_level === 'HIGH' ? 'badge-danger' :
              task.risk_level === 'LOW' ? 'badge-success' : 'badge-warning';

            return (
              <motion.button
                key={task.task_id}
                onClick={() => onReload(task.task_id)}
                className="w-full text-left glass-sm p-3 flex items-center gap-3 hover:scale-[1.01] transition-transform"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.04 }}
                whileHover={{ x: 2 }}
              >
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-semibold truncate" style={{ color: '#0F0A2E' }}>
                    {task.goal}
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    {task.risk_level && (
                      <span className={`badge ${riskBadge}`}>{task.risk_level}</span>
                    )}
                    {task.confidence !== undefined && (
                      <span className="text-xs font-mono" style={{ color: '#9CA3AF' }}>
                        {task.confidence}% conf
                      </span>
                    )}
                    {task.created_at && (
                      <span className="text-xs" style={{ color: '#D1D5DB' }}>
                        {new Date(task.created_at).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                </div>
                <ChevronRight size={14} style={{ color: '#D1D5DB', flexShrink: 0 }} />
              </motion.button>
            );
          })}
        </div>
      )}
    </motion.div>
  );
}
