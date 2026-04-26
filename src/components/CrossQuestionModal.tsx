import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { HelpCircle, X, ChevronRight } from 'lucide-react';

interface CrossQuestionModalProps {
  isOpen: boolean;
  onClose: () => void;
  reasoning?: string;
}

const DEEPER_EXPLANATIONS = [
  {
    q: 'Why this confidence score?',
    a: 'The XGBoost model assigns confidence based on historical similarity, resource availability, deadline pressure, and dependency complexity. The SHAP values above show each factor\'s contribution.',
  },
  {
    q: 'What if I change the deadline?',
    a: 'Reducing deadline_days by 30% typically increases delay risk by ~15-25% and reduces confidence by ~10%. The model is most sensitive to this feature.',
  },
  {
    q: 'Alternative approach?',
    a: 'An agile decomposition with weekly checkpoints would lower risk. Consider breaking the task into independent parallel subtasks to reduce the critical path.',
  },
];

export default function CrossQuestionModal({ isOpen, onClose, reasoning }: CrossQuestionModalProps) {
  const [expanded, setExpanded] = useState<number | null>(null);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 z-40"
            style={{ background: 'rgba(15,10,46,0.4)', backdropFilter: 'blur(4px)' }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />

          {/* Modal */}
          <motion.div
            className="fixed z-50 top-1/2 left-1/2 w-full max-w-lg"
            style={{ transform: 'translate(-50%, -50%)' }}
            initial={{ opacity: 0, scale: 0.92, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.92, y: 20 }}
            transition={{ type: 'spring', stiffness: 300, damping: 25 }}
          >
            <div className="glass p-6 mx-4">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center"
                  style={{ background: 'linear-gradient(135deg, #7C3AED, #4F46E5)' }}>
                  <HelpCircle size={16} color="white" />
                </div>
                <h3 className="font-bold" style={{ fontFamily: 'Syne', color: '#0F0A2E' }}>
                  Deep Reasoning Explorer
                </h3>
                <button onClick={onClose} className="ml-auto p-1.5 rounded-lg hover:bg-black/5 transition-colors">
                  <X size={16} style={{ color: '#9CA3AF' }} />
                </button>
              </div>

              {reasoning && (
                <div className="mb-4 p-3 rounded-xl" style={{ background: 'rgba(6,182,212,0.06)', border: '1px solid rgba(6,182,212,0.2)' }}>
                  <p className="text-xs font-semibold mb-1" style={{ color: '#0E7490' }}>System Reasoning</p>
                  <p className="text-sm leading-relaxed" style={{ color: '#374151' }}>{reasoning}</p>
                </div>
              )}

              <p className="text-xs font-semibold mb-3" style={{ color: '#7C3AED' }}>
                Click to explore deeper explanations:
              </p>

              <div className="space-y-2">
                {DEEPER_EXPLANATIONS.map((item, i) => (
                  <div key={i} className="glass-sm overflow-hidden">
                    <button
                      onClick={() => setExpanded(expanded === i ? null : i)}
                      className="w-full flex items-center gap-2 p-3 text-left"
                    >
                      <ChevronRight
                        size={13}
                        style={{
                          color: '#7C3AED',
                          transition: 'transform 0.2s',
                          transform: expanded === i ? 'rotate(90deg)' : 'none',
                        }}
                      />
                      <span className="text-sm font-medium" style={{ color: '#0F0A2E' }}>{item.q}</span>
                    </button>
                    <AnimatePresence>
                      {expanded === i && (
                        <motion.div
                          initial={{ height: 0 }}
                          animate={{ height: 'auto' }}
                          exit={{ height: 0 }}
                          className="overflow-hidden"
                        >
                          <p className="text-xs px-4 pb-3 leading-relaxed" style={{ color: '#4B5563' }}>{item.a}</p>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
