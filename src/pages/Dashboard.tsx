import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Brain, Activity, Wifi, WifiOff } from 'lucide-react';

import InputPanel from '@/components/InputPanel';
import TaskSummaryCard from '@/components/TaskSummaryCard';
import ExplainabilityPanel from '@/components/ExplainabilityPanel';
import SimilarTasksPanel from '@/components/SimilarTasksPanel';
import DebatePanel from '@/components/DebatePanel';
import ExecutionPlanPanel from '@/components/ExecutionPlanPanel';
import ExecutionGraph from '@/components/ExecutionGraph';
import ReflectionPanel from '@/components/ReflectionPanel';
import TrustRiskPanel from '@/components/TrustRiskPanel';
import TaskHistoryPanel from '@/components/TaskHistoryPanel';
import CrossQuestionModal from '@/components/CrossQuestionModal';

import { useSubmitGoal, useTaskHistory, useHealth, useTaskById } from '@/hooks/useAegisAPI';
import type { AegisResponse } from '@/types/aegis';

// Pipeline stage labels
const PIPELINE_STAGES = [
  'Commander', 'Trust', 'Retrieval', 'ML', 'Explainability', 'Debate', 'Execution', 'Reflection', 'Memory',
];

export default function Dashboard() {
  const [result, setResult] = useState<AegisResponse | null>(null);
  const [reloadId, setReloadId] = useState<string | null>(null);
  const [whyOpen, setWhyOpen] = useState(false);
  const [activeStage, setActiveStage] = useState<number>(-1);

  const { mutate: submitGoal, isPending } = useSubmitGoal();
  const { data: history = [], isLoading: historyLoading } = useTaskHistory();
  const { data: health } = useHealth();
  const { data: reloadedTask } = useTaskById(reloadId);

  // When a task is reloaded from history
  const effectiveResult = reloadId && reloadedTask ? reloadedTask : result;

  const handleSubmit = useCallback((goal: string, language: string) => {
    // Animate pipeline stages
    setActiveStage(0);
    const stages = PIPELINE_STAGES;
    stages.forEach((_, i) => {
      setTimeout(() => setActiveStage(i), i * 600);
    });

    submitGoal({ goal, language }, {
      onSuccess: (data) => {
        setResult(data);
        setReloadId(null);
        setActiveStage(-1);
      },
      onError: () => setActiveStage(-1),
    });
  }, [submitGoal]);

  const isOnline = health?.status === 'ok' || health?.status === 'healthy';

  return (
    <div className="aurora-bg min-h-screen" style={{ position: 'relative' }}>
      {/* Header */}
      <header className="sticky top-0 z-30" style={{ background: 'rgba(240,242,255,0.8)', backdropFilter: 'blur(20px)', borderBottom: '1px solid rgba(124,58,237,0.1)' }}>
        <div className="max-w-screen-xl mx-auto px-6 py-3 flex items-center gap-4">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, #7C3AED, #4F46E5)' }}>
              <Brain size={18} color="white" />
            </div>
            <div>
              <h1 className="text-sm font-black" style={{ fontFamily: 'Syne', color: '#0F0A2E', letterSpacing: '-0.3px' }}>
                AegisAI
              </h1>
              <p className="text-xs" style={{ color: '#9CA3AF', lineHeight: 1.2 }}>Autonomous Decision Intelligence</p>
            </div>
          </div>

          {/* Pipeline progress */}
          {isPending && (
            <motion.div
              className="hidden md:flex items-center gap-1.5 ml-6"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              {PIPELINE_STAGES.map((stage, i) => (
                <div key={stage} className="flex items-center gap-1.5">
                  <motion.div
                    className="px-2 py-0.5 rounded-full text-xs font-medium transition-all"
                    style={{
                      background: i <= activeStage
                        ? 'rgba(124,58,237,0.15)'
                        : 'rgba(0,0,0,0.04)',
                      color: i <= activeStage ? '#7C3AED' : '#D1D5DB',
                      border: i === activeStage ? '1px solid rgba(124,58,237,0.4)' : '1px solid transparent',
                    }}
                    animate={i === activeStage ? { scale: [1, 1.05, 1] } : {}}
                    transition={{ repeat: Infinity, duration: 0.8 }}
                  >
                    {stage}
                  </motion.div>
                  {i < PIPELINE_STAGES.length - 1 && (
                    <div className="w-3 h-px" style={{ background: i < activeStage ? '#7C3AED' : '#E5E7EB' }} />
                  )}
                </div>
              ))}
            </motion.div>
          )}

          {/* Status indicator */}
          <div className="ml-auto flex items-center gap-2">
            {isOnline !== undefined && (
              <div className="flex items-center gap-1.5">
                {isOnline
                  ? <Wifi size={13} style={{ color: '#10B981' }} />
                  : <WifiOff size={13} style={{ color: '#F43F5E' }} />}
                <span className="text-xs font-medium" style={{ color: isOnline ? '#10B981' : '#F43F5E' }}>
                  {isOnline ? 'Connected' : 'Offline'}
                </span>
              </div>
            )}
            {isPending && (
              <div className="flex items-center gap-2">
                <motion.div
                  className="w-1.5 h-1.5 rounded-full"
                  style={{ background: '#7C3AED' }}
                  animate={{ scale: [1, 1.5, 1], opacity: [1, 0.5, 1] }}
                  transition={{ duration: 1, repeat: Infinity }}
                />
                <span className="text-xs font-medium" style={{ color: '#7C3AED' }}>Analysing...</span>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main layout */}
      <div className="max-w-screen-xl mx-auto px-6 py-6">
        {/* Top row: Input + History */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-5">
          <div className="lg:col-span-2">
            <InputPanel onSubmit={handleSubmit} isLoading={isPending} />
          </div>
          <div>
            <TaskHistoryPanel
              tasks={history}
              isLoading={historyLoading}
              onReload={(id) => { setReloadId(id); setResult(null); }}
            />
          </div>
        </div>

        {/* Loading skeleton */}
        {isPending && !effectiveResult && (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="glass p-6 space-y-3">
                <div className="skeleton h-4 w-32 rounded-lg" />
                <div className="skeleton h-20 rounded-xl" />
                <div className="skeleton h-4 w-48 rounded-lg" />
              </div>
            ))}
          </div>
        )}

        {/* Results grid */}
        <AnimatePresence mode="wait">
          {effectiveResult && (
            <motion.div
              key={effectiveResult.task_id || 'result'}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.4 }}
            >
              {/* Row 1: Summary + Explainability + Similar Tasks */}
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5 mb-5">
                <TaskSummaryCard data={effectiveResult} />
                <ExplainabilityPanel data={effectiveResult} onWhyClick={() => setWhyOpen(true)} />
                <SimilarTasksPanel data={effectiveResult} />
              </div>

              {/* Row 2: Debate + Execution Plan + Trust & Risk */}
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5 mb-5">
                <DebatePanel data={effectiveResult} />
                <ExecutionPlanPanel data={effectiveResult} />
                <TrustRiskPanel data={effectiveResult} />
              </div>

              {/* Row 3: Execution Graph + Reflection */}
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
                <ExecutionGraph data={effectiveResult} />
                <ReflectionPanel data={effectiveResult} />
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Empty state */}
        {!effectiveResult && !isPending && (
          <motion.div
            className="flex flex-col items-center justify-center py-20 gap-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
          >
            <motion.div
              className="w-20 h-20 rounded-2xl flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, rgba(124,58,237,0.12), rgba(79,70,229,0.08))' }}
              animate={{ y: [0, -8, 0] }}
              transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
            >
              <Brain size={36} style={{ color: '#7C3AED', opacity: 0.6 }} />
            </motion.div>
            <div className="text-center">
              <h2 className="text-xl font-bold mb-2" style={{ fontFamily: 'Syne', color: '#0F0A2E' }}>
                Ready to Analyse
              </h2>
              <p className="text-sm max-w-md text-center" style={{ color: '#6B7280' }}>
                Enter a goal or decision you need AegisAI to evaluate. The system will run it through 8 pipeline stages — Commander → Trust → Retrieval → ML → Explainability → Debate → Execution → Reflection.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Activity size={14} style={{ color: '#10B981' }} />
              <span className="text-sm" style={{ color: '#10B981', fontFamily: 'JetBrains Mono' }}>
                All systems operational
              </span>
            </div>
          </motion.div>
        )}
      </div>

      {/* Cross-question modal */}
      <CrossQuestionModal
        isOpen={whyOpen}
        onClose={() => setWhyOpen(false)}
        reasoning={effectiveResult?.plan?.debate_results?.reasoning || effectiveResult?.plan?.reasoning}
      />
    </div>
  );
}
