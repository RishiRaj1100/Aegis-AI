import { useState } from 'react';
import { motion } from 'framer-motion';
import { Send, Mic, MicOff, Globe, Zap } from 'lucide-react';
import { useVoice } from '@/hooks/useVoice';

interface InputPanelProps {
  onSubmit: (goal: string, language: string) => void;
  isLoading: boolean;
  isOnline?: boolean;
}

const LANGUAGES = [
  { code: 'en-IN', label: 'English' },
  { code: 'hi-IN', label: 'हिन्दी' },
  { code: 'ta-IN', label: 'தமிழ்' },
  { code: 'te-IN', label: 'తెలుగు' },
];

export default function InputPanel({ onSubmit, isLoading, isOnline }: InputPanelProps) {
  const [goal, setGoal] = useState('');
  const [language, setLanguage] = useState('en-IN');

  const { isListening, startListening, stopListening, interimTranscript } = useVoice((text) => {
    setGoal((prev) => prev ? `${prev} ${text}` : text);
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!goal.trim() || isLoading) return;
    onSubmit(goal.trim(), language);
  };

  return (
    <motion.div
      className="glass p-6 relative overflow-hidden"
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      {/* Background decoration */}
      <div className="absolute top-0 right-0 w-48 h-48 rounded-full opacity-30"
        style={{ background: 'radial-gradient(circle, rgba(124,58,237,0.15) 0%, transparent 70%)', transform: 'translate(30%, -30%)' }} />

      {/* Header */}
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center"
          style={{ background: 'linear-gradient(135deg, #7C3AED, #4F46E5)' }}>
          <Zap size={18} color="white" />
        </div>
        <div>
          <h2 className="text-base font-bold" style={{ fontFamily: 'Syne', color: '#0F0A2E' }}>
            Mission Input
          </h2>
          <p className="text-xs" style={{ color: '#9CA3AF' }}>Describe what you want AegisAI to analyse</p>
        </div>
        {/* System status dot */}
        <div className="ml-auto flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isOnline ? 'bg-emerald-400' : 'bg-rose-400'} pulse-ring`} />
          <span className="text-xs font-medium" style={{ color: isOnline ? '#059669' : '#E11D48' }}>
            {isOnline ? 'ONLINE' : 'OFFLINE'}
          </span>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Main textarea */}
        <div className="relative">
          <textarea
            id="goal-input"
            value={isListening ? (goal + (interimTranscript ? ' ' + interimTranscript : '')) : goal}
            onChange={(e) => setGoal(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleSubmit(e); }}
            placeholder="e.g. Build a customer churn prediction model and deploy it with an explainable dashboard..."
            rows={3}
            className="w-full resize-none rounded-xl p-4 text-sm outline-none transition-all"
            style={{
              background: 'rgba(255,255,255,0.7)',
              border: '1.5px solid rgba(124,58,237,0.2)',
              color: '#0F0A2E',
              fontFamily: 'Inter',
              lineHeight: '1.7',
            }}
            onFocus={(e) => { e.target.style.borderColor = 'rgba(124,58,237,0.5)'; e.target.style.boxShadow = '0 0 0 3px rgba(124,58,237,0.08)'; }}
            onBlur={(e) => { e.target.style.borderColor = 'rgba(124,58,237,0.2)'; e.target.style.boxShadow = 'none'; }}
          />
          <div className="absolute bottom-3 right-3 text-xs" style={{ color: '#D1D5DB', fontFamily: 'JetBrains Mono' }}>
            {goal.length}/1000
          </div>
        </div>

        {/* Controls row */}
        <div className="flex items-center gap-3 flex-wrap">
          {/* Language selector */}
          <div className="flex items-center gap-2 glass-sm px-3 py-2">
            <Globe size={14} style={{ color: '#7C3AED' }} />
            <select
              id="language-select"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="text-xs outline-none bg-transparent font-medium"
              style={{ color: '#0F0A2E', fontFamily: 'Inter' }}
            >
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>{l.label}</option>
              ))}
            </select>
          </div>

          {/* Mic button */}
          <motion.button
            type="button"
            onClick={isListening ? stopListening : () => startListening(language)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all ${
              isListening
                ? 'bg-rose-50 border border-rose-300 text-rose-600'
                : 'glass-sm text-violet-600'
            }`}
            whileTap={{ scale: 0.95 }}
          >
            {isListening ? <MicOff size={14} /> : <Mic size={14} />}
            {isListening ? 'Listening...' : 'Voice'}
            {isListening && (
              <span className="flex gap-0.5">
                {[0, 1, 2].map((i) => (
                  <motion.span key={i} className="w-0.5 rounded-full bg-rose-400"
                    animate={{ height: ['4px', '12px', '4px'] }}
                    transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.1 }} />
                ))}
              </span>
            )}
          </motion.button>

          {/* Submit button */}
          <motion.button
            type="submit"
            disabled={!goal.trim() || isLoading}
            className="btn-primary ml-auto flex items-center gap-2"
            whileTap={{ scale: 0.97 }}
            id="submit-goal-btn"
          >
            {isLoading ? (
              <>
                <motion.div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full"
                  animate={{ rotate: 360 }} transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }} />
                Analysing...
              </>
            ) : (
              <>
                <Send size={15} />
                Analyse Mission
              </>
            )}
          </motion.button>
        </div>

        {/* Keyboard hint */}
        <p className="text-xs" style={{ color: '#D1D5DB', fontFamily: 'JetBrains Mono' }}>
          Ctrl + Enter to submit
        </p>
      </form>
    </motion.div>
  );
}
