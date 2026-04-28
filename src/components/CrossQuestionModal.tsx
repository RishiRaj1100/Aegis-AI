import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { HelpCircle, X, ChevronRight, Send, MessageSquare, Brain, Loader2 } from 'lucide-react';
import { useFollowUp } from '@/hooks/useAegisAPI';
import AudioPlayback from './AudioPlayback';

interface CrossQuestionModalProps {
  isOpen: boolean;
  onClose: () => void;
  reasoning?: string;
  taskId?: string;
  language?: string;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  audio?: string;
}

export default function CrossQuestionModal({ isOpen, onClose, reasoning, taskId, language = 'en-IN' }: CrossQuestionModalProps) {
  const [expanded, setExpanded] = useState<number | null>(null);
  const [question, setQuestion] = useState('');
  const [chat, setChat] = useState<ChatMessage[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const { mutate: askFollowUp, isPending } = useFollowUp();

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [chat, isPending]);

  const handleAsk = () => {
    if (!question.trim() || !taskId) return;

    const userMsg = question;
    setChat(prev => [...prev, { role: 'user', content: userMsg }]);
    setQuestion('');

    askFollowUp({ taskId, message: userMsg, language }, {
      onSuccess: (data) => {
        setChat(prev => [...prev, { 
          role: 'assistant', 
          content: data.reply, 
          audio: data.audio_base64 
        }]);
      },
      onError: (err) => {
        setChat(prev => [...prev, { 
          role: 'assistant', 
          content: `Error: ${err.message}` 
        }]);
      }
    });
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            className="fixed inset-0 z-40"
            style={{ background: 'rgba(15,10,46,0.6)', backdropFilter: 'blur(8px)' }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />

          <motion.div
            className="fixed z-50 top-1/2 left-1/2 w-full max-w-2xl h-[85vh]"
            style={{ transform: 'translate(-50%, -50%)' }}
            initial={{ opacity: 0, scale: 0.95, y: 30 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 30 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
          >
            <div className="glass h-full flex flex-col p-6 mx-4">
              {/* Header */}
              <div className="flex items-center gap-3 mb-6 shrink-0">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center shadow-lg"
                  style={{ background: 'linear-gradient(135deg, #7C3AED, #4F46E5)' }}>
                  <HelpCircle size={20} color="white" />
                </div>
                <div>
                  <h3 className="font-black text-lg" style={{ fontFamily: 'Syne', color: '#0F0A2E' }}>
                    Cross-Question Engine
                  </h3>
                  <p className="text-[10px] uppercase tracking-widest font-bold opacity-40">Interactive Logic Verification</p>
                </div>
                <button onClick={onClose} className="ml-auto p-2 rounded-xl hover:bg-black/5 transition-colors">
                  <X size={20} style={{ color: '#9CA3AF' }} />
                </button>
              </div>

              {/* Chat / Content Area */}
              <div ref={scrollRef} className="flex-1 overflow-y-auto pr-2 space-y-6 scrollbar-hide">
                {/* System Initial Reasoning */}
                {reasoning && (
                  <div className="p-4 rounded-2xl" style={{ background: 'rgba(124,58,237,0.05)', border: '1px solid rgba(124,58,237,0.1)' }}>
                    <div className="flex items-center gap-2 mb-2">
                      <Brain size={14} className="text-indigo-500" />
                      <p className="text-xs font-bold uppercase tracking-wider text-indigo-500">Initial Analysis Reasoning</p>
                    </div>
                    <p className="text-sm leading-relaxed text-slate-700">{reasoning}</p>
                  </div>
                )}

                {/* Dynamic Conversations */}
                <AnimatePresence>
                  {chat.map((msg, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: msg.role === 'user' ? 20 : -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div className={`max-w-[85%] p-4 rounded-2xl ${
                        msg.role === 'user' 
                          ? 'bg-indigo-600 text-white shadow-md' 
                          : 'bg-white border border-slate-100 shadow-sm'
                      }`}>
                        <div className="flex items-center gap-2 mb-1.5 opacity-60">
                          {msg.role === 'user' ? <MessageSquare size={12} /> : <Brain size={12} />}
                          <span className="text-[10px] font-bold uppercase tracking-widest">
                            {msg.role === 'user' ? 'Your Question' : 'AegisAI Response'}
                          </span>
                        </div>
                        <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                        {msg.audio && (
                          <div className="mt-3">
                            <AudioPlayback base64Audio={msg.audio} />
                          </div>
                        )}
                      </div>
                    </motion.div>
                  ))}
                </AnimatePresence>

                {isPending && (
                  <div className="flex justify-start">
                    <div className="bg-white p-4 rounded-2xl border border-slate-100 shadow-sm flex items-center gap-3">
                      <Loader2 size={16} className="animate-spin text-indigo-500" />
                      <span className="text-xs font-medium text-slate-500">Processing follow-up...</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Input Area */}
              <div className="mt-6 pt-6 border-t border-slate-100 shrink-0">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
                    placeholder="Ask a doubt or request clarification..."
                    className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                  />
                  <button
                    onClick={handleAsk}
                    disabled={isPending || !question.trim()}
                    className="w-12 h-12 rounded-xl flex items-center justify-center bg-indigo-600 text-white shadow-lg disabled:opacity-50 disabled:grayscale transition-all hover:bg-indigo-700 active:scale-95"
                  >
                    <Send size={18} />
                  </button>
                </div>
                <p className="text-[10px] text-center mt-3 text-slate-400 font-medium">
                  AegisAI will respond in your selected language and provide a voice summary.
                </p>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
