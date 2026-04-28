import { useState, useCallback, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { RotateCcw, Brain, Activity, Wifi, WifiOff, HelpCircle, MessageSquare, ChevronRight, Volume2, Send, Loader2, Info } from 'lucide-react';

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
import { useSubmitGoal, useTaskHistory, useHealth, useTaskById, useFollowUp } from '@/hooks/useAegisAPI';
import type { AegisResponse } from '@/types/aegis';
import AudioPlayback from '@/components/AudioPlayback';

const PIPELINE_STAGES = [
  'Commander', 'Trust', 'Retrieval', 'ML', 'Explainability', 'Debate', 'Execution', 'Reflection', 'Memory',
];

export default function Dashboard() {
  const [result, setResult] = useState<AegisResponse | null>(null);
  const [selectedLanguage, setSelectedLanguage] = useState('en-IN');
  const [reloadId, setReloadId] = useState<string | null>(null);
  const [activeStage, setActiveStage] = useState<number>(-1);
  const [activeTab, setActiveTab] = useState<'analysis' | 'graph' | 'debate' | 'qa' | 'reflection'>('analysis');

  const { mutate: submitGoal, isPending } = useSubmitGoal();
  const { data: history = [], isLoading: historyLoading } = useTaskHistory();
  const { data: health } = useHealth();
  const { data: reloadedTask } = useTaskById(reloadId);

  const effectiveResult = reloadId && reloadedTask ? reloadedTask : result;

  useEffect(() => {
    if (effectiveResult?.plan?.language) {
      setSelectedLanguage(effectiveResult.plan.language);
    }
  }, [effectiveResult]);

  const handleSubmit = useCallback((goal: string, language: string) => {
    setSelectedLanguage(language);
    setActiveStage(0);
    PIPELINE_STAGES.forEach((_, i) => {
      setTimeout(() => setActiveStage(i), i * 600);
    });

    submitGoal({ goal, language }, {
      onSuccess: (data) => {
        setResult(data);
        setReloadId(null);
        setActiveStage(-1);
        setActiveTab('analysis');
      },
      onError: () => setActiveStage(-1),
    });
  }, [submitGoal]);

  const isOnline = health?.status === 'ok' || health?.status === 'healthy';

  return (
    <div className="aurora-bg min-h-screen pb-20">
      <header className="sticky top-0 z-30 bg-white/80 backdrop-blur-xl border-b border-indigo-100/50">
        <div className="max-w-screen-2xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl flex items-center justify-center bg-gradient-to-br from-indigo-600 to-violet-600 shadow-lg shadow-indigo-200">
              <Brain size={22} color="white" />
            </div>
            <div>
              <h1 className="text-lg font-black tracking-tight text-slate-900" style={{ fontFamily: 'Syne' }}>AegisAI</h1>
              <div className="flex items-center gap-2">
                <div className={`w-1.5 h-1.5 rounded-full ${isOnline ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`} />
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  {isOnline ? 'Core Operational' : 'Connection Lost'}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {effectiveResult?.audio_response_base64 && (
              <AudioPlayback base64Audio={effectiveResult.audio_response_base64} autoPlay={true} />
            )}
            <div className="h-8 w-px bg-slate-100 mx-2" />
            <div className="flex flex-col items-end">
              <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Active Region</span>
              <span className="text-xs font-bold text-indigo-600">{selectedLanguage}</span>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-screen-2xl mx-auto px-6 pt-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8 mb-10">
          <div className="lg:col-span-3">
            <InputPanel onSubmit={handleSubmit} isLoading={isPending} isOnline={isOnline} />
            {isPending && (
              <motion.div className="mt-8 flex flex-wrap gap-3" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                {PIPELINE_STAGES.map((stage, i) => (
                  <div key={stage} className={`flex items-center gap-2 px-4 py-2 rounded-2xl text-[10px] font-black uppercase tracking-wider transition-all border ${
                    i <= activeStage ? 'bg-indigo-50 border-indigo-100 text-indigo-600' : 'bg-slate-50 border-slate-100 text-slate-400'
                  }`}>
                    {i < activeStage ? '✓' : i === activeStage ? '●' : '○'} {stage}
                  </div>
                ))}
              </motion.div>
            )}
          </div>
          <div className="lg:col-span-1">
            <TaskHistoryPanel tasks={history} isLoading={historyLoading} onReload={(id) => { setReloadId(id); setResult(null); }} />
          </div>
        </div>

        {effectiveResult && (
          <div className="space-y-8">
            <div className="flex items-center gap-2 p-1.5 bg-white/50 backdrop-blur-md rounded-3xl border border-white w-fit shadow-xl shadow-indigo-100/50">
              <TabNav active={activeTab === 'analysis'} onClick={() => setActiveTab('analysis')} icon={<Activity size={16}/>} label="Analysis" />
              <TabNav active={activeTab === 'graph'} onClick={() => setActiveTab('graph')} icon={<ChevronRight size={16}/>} label="Graph" />
              <TabNav active={activeTab === 'debate'} onClick={() => setActiveTab('debate')} icon={<Brain size={16}/>} label="Logic" />
              <TabNav active={activeTab === 'qa'} onClick={() => setActiveTab('qa')} icon={<HelpCircle size={16}/>} label="Verify" />
              <TabNav active={activeTab === 'reflection'} onClick={() => setActiveTab('reflection')} icon={<RotateCcw size={16}/>} label="Reflection" />
            </div>

            <AnimatePresence mode="wait">
              {activeTab === 'analysis' && (
                <motion.div key="analysis" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  <TaskSummaryCard data={effectiveResult} onAskClick={() => setActiveTab('qa')} />
                  <TrustRiskPanel data={effectiveResult} />
                  <ExplainabilityPanel data={effectiveResult} onWhyClick={() => setActiveTab('qa')} />
                  <ExecutionPlanPanel data={effectiveResult} />
                </motion.div>
              )}

              {activeTab === 'reflection' && (
                <motion.div key="reflection" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="max-w-4xl mx-auto">
                  <ReflectionPanel data={effectiveResult} />
                </motion.div>
              )}

              {activeTab === 'graph' && (
                <motion.div key="graph" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }} className="grid grid-cols-1 lg:grid-cols-3 gap-8 h-full">
                  <div className="lg:col-span-2 h-[650px] glass rounded-3xl overflow-hidden border-indigo-100/50 shadow-2xl">
                    <ExecutionGraph data={effectiveResult} />
                  </div>
                  <div className="lg:col-span-1">
                    <SimilarTasksPanel data={effectiveResult} />
                  </div>
                </motion.div>
              )}

              {activeTab === 'debate' && (
                <motion.div key="debate" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  <DebatePanel data={effectiveResult} />
                  <div className="space-y-8">
                    <TrustRiskPanel data={effectiveResult} />
                    <ExplainabilityPanel data={effectiveResult} onWhyClick={() => setActiveTab('qa')} />
                  </div>
                </motion.div>
              )}

              {activeTab === 'qa' && (
                <motion.div key="qa" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="max-w-5xl mx-auto w-full h-[700px]">
                  <CrossQuestionInline 
                    reasoning={effectiveResult.plan?.debate_results?.reasoning || effectiveResult.debate_results?.reasoning || effectiveResult.plan?.debate_results?.final_decision || effectiveResult.reasoning || "Analysis complete. Awaiting logic verification questions."}
                    taskId={effectiveResult.task_id}
                    language={selectedLanguage}
                  />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {!effectiveResult && !isPending && (
          <div className="flex flex-col items-center justify-center py-40 gap-8">
            <div className="w-32 h-32 rounded-[2.5rem] bg-white border-2 border-indigo-50 shadow-2xl flex items-center justify-center relative overflow-hidden group">
              <div className="absolute inset-0 bg-gradient-to-br from-indigo-50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
              <Brain size={64} className="text-indigo-600/20 group-hover:text-indigo-600/40 transition-colors" />
            </div>
            <div className="text-center max-w-md">
              <h2 className="text-3xl font-black text-slate-900 mb-4" style={{ fontFamily: 'Syne' }}>Neural Core Ready</h2>
              <p className="text-slate-500 leading-relaxed">Enter your mission parameters to activate the autonomous multi-agent reasoning chain and explainability engine.</p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function TabNav({ active, onClick, icon, label }: { active: boolean, onClick: () => void, icon: any, label: string }) {
  return (
    <button onClick={onClick} className={`flex items-center gap-2.5 px-6 py-2.5 rounded-2xl text-[11px] font-black uppercase tracking-wider transition-all ${
      active ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-200' : 'text-slate-500 hover:bg-slate-100 hover:text-slate-800'
    }`}>
      {icon} {label}
    </button>
  );
}

function CrossQuestionInline({ reasoning, taskId, language }: { reasoning?: string, taskId?: string, language: string }) {
  const [question, setQuestion] = useState('');
  const [chat, setChat] = useState<any[]>([]);
  const { mutate: askFollowUp, isPending } = useFollowUp();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
    }
  }, [chat, isPending]);

  const handleAsk = () => {
    if (!question.trim() || !taskId) return;
    const q = question;
    setChat(prev => [...prev, { role: 'user', content: q }]);
    setQuestion('');
    askFollowUp({ taskId, message: q, language }, {
      onSuccess: (data) => setChat(prev => [...prev, { role: 'assistant', content: data.reply, audio: data.audio_base64 }]),
      onError: (err) => setChat(prev => [...prev, { role: 'assistant', content: `Verification Failed: ${err.message}` }])
    });
  };

  return (
    <div className="glass h-full flex flex-col p-8 border-indigo-100/50 shadow-2xl rounded-[2rem]">
      <div className="flex items-center gap-3 mb-8 pb-6 border-b border-slate-100">
        <div className="w-12 h-12 rounded-2xl bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-200">
          <HelpCircle size={24} color="white" />
        </div>
        <div>
          <h3 className="text-xl font-black text-slate-900" style={{ fontFamily: 'Syne' }}>Logic Verification</h3>
          <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Cross-examine AegisAI Reasoning</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-6 pr-4 custom-scrollbar" ref={scrollRef}>
        <div className="p-5 rounded-3xl bg-indigo-50/50 border border-indigo-100/50 relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-4 opacity-10"><Info size={48} /></div>
          <p className="text-[10px] font-black uppercase text-indigo-600 mb-3 tracking-widest">Base Analysis Context</p>
          <p className="text-sm text-slate-700 leading-relaxed relative z-10">{reasoning}</p>
        </div>

        {chat.map((msg, i) => (
          <motion.div key={i} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] p-5 rounded-3xl shadow-sm ${
              msg.role === 'user' ? 'bg-indigo-600 text-white shadow-indigo-100' : 'bg-white border border-slate-100 text-slate-800'
            }`}>
              <div className="flex items-center gap-2 mb-2 opacity-50">
                {msg.role === 'user' ? <MessageSquare size={12}/> : <Brain size={12}/>}
                <span className="text-[9px] font-black uppercase tracking-widest">{msg.role === 'user' ? 'Inquiry' : 'Neural Response'}</span>
              </div>
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
              {msg.audio && <div className="mt-4"><AudioPlayback base64Audio={msg.audio} /></div>}
            </div>
          </motion.div>
        ))}

        {isPending && (
          <div className="flex justify-start">
            <div className="bg-white border border-slate-100 p-5 rounded-3xl flex items-center gap-4 shadow-sm">
              <Loader2 size={18} className="animate-spin text-indigo-600" />
              <span className="text-[11px] font-black uppercase tracking-widest text-slate-400">Processing inquiry...</span>
            </div>
          </div>
        )}
      </div>

      <div className="mt-8 pt-8 border-t border-slate-100 flex gap-4">
        <input
          className="flex-1 bg-slate-50 border-slate-100 rounded-2xl px-6 py-4 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:bg-white focus:border-indigo-500 transition-all placeholder:text-slate-400 font-medium"
          placeholder="Type your cross-question here..."
          value={question}
          onChange={e => setQuestion(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleAsk()}
        />
        <button onClick={handleAsk} disabled={isPending || !question.trim()} className="w-14 h-14 bg-indigo-600 text-white rounded-2xl shadow-xl shadow-indigo-200 hover:bg-indigo-700 hover:scale-105 active:scale-95 transition-all disabled:opacity-50 disabled:scale-100 flex items-center justify-center">
          <Send size={20} />
        </button>
      </div>
    </div>
  );
}
