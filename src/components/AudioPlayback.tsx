import { useState, useRef, useEffect } from 'react';
import { Play, Square, Pause, Volume2, Loader2, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface AudioPlaybackProps {
  base64Audio?: string;
  autoPlay?: boolean;
}

export default function AudioPlayback({ base64Audio, autoPlay = false }: AudioPlaybackProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const playPromiseRef = useRef<Promise<void> | null>(null);

  // Initialize audio when base64 changes
  useEffect(() => {
    if (!base64Audio) return;

    // Cleanup previous audio
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }

    try {
      setError(null);
      // Ensure the base64 string is properly formatted as a Data URI
      const dataUri = base64Audio.startsWith('data:') 
        ? base64Audio 
        : `data:audio/wav;base64,${base64Audio}`;
        
      const audio = new Audio(dataUri);
      
      audio.onended = () => {
        setIsPlaying(false);
        setIsPaused(false);
      };
      
      audio.onerror = (e) => {
        console.error("Audio element error:", e);
        setError("Failed to load audio");
        setIsLoading(false);
      };

      audioRef.current = audio;

      if (autoPlay) {
        handlePlay();
      }
    } catch (err) {
      console.error("Failed to initialize audio:", err);
      setError("Initialization failed");
    }

    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, [base64Audio, autoPlay]);

  const handlePlay = async () => {
    if (!audioRef.current) return;
    
    setIsLoading(true);
    setError(null);

    try {
      // Store play promise to handle interruption
      playPromiseRef.current = audioRef.current.play();
      await playPromiseRef.current;
      
      setIsPlaying(true);
      setIsPaused(false);
    } catch (err: any) {
      // Ignore AbortError as it's common during fast interaction
      if (err.name !== 'AbortError') {
        console.error("Playback error:", err);
        setError("Playback failed");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handlePause = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      setIsPaused(true);
      setIsPlaying(false);
    }
  };

  const handleStop = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setIsPlaying(false);
      setIsPaused(false);
    }
  };

  if (!base64Audio) return null;

  return (
    <motion.div 
      className="flex items-center gap-2 p-1.5 rounded-2xl bg-white border border-slate-200 shadow-sm"
      initial={{ opacity: 0, y: 5 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${error ? 'bg-rose-50' : 'bg-indigo-50'}`}>
        {error ? (
          <AlertCircle size={14} className="text-rose-500" />
        ) : (
          <Volume2 size={14} className={isPlaying ? "text-indigo-600 animate-pulse" : "text-indigo-400"} />
        )}
      </div>

      <div className="flex items-center gap-1">
        <AnimatePresence mode="wait">
          {isLoading ? (
            <motion.div key="loading" className="p-1.5" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <Loader2 size={14} className="animate-spin text-indigo-500" />
            </motion.div>
          ) : (!isPlaying || isPaused) ? (
            <motion.button
              key="play"
              onClick={handlePlay}
              className="p-1.5 rounded-lg hover:bg-slate-100 text-indigo-600 transition-colors"
              whileTap={{ scale: 0.9 }}
            >
              <Play size={14} fill="currentColor" />
            </motion.button>
          ) : (
            <motion.button
              key="pause"
              onClick={handlePause}
              className="p-1.5 rounded-lg hover:bg-slate-100 text-indigo-600 transition-colors"
              whileTap={{ scale: 0.9 }}
            >
              <Pause size={14} fill="currentColor" />
            </motion.button>
          )}
        </AnimatePresence>

        <button
          onClick={handleStop}
          disabled={!isPlaying && !isPaused}
          className="p-1.5 rounded-lg hover:bg-slate-100 disabled:opacity-20 text-slate-400 hover:text-rose-500 transition-colors"
        >
          <Square size={14} fill="currentColor" />
        </button>
      </div>

      <div className="pr-2 border-l border-slate-100 ml-1 pl-2">
        <span className="text-[9px] font-black uppercase tracking-widest text-slate-400">
          {error ? 'Err' : isPlaying ? 'Playing' : 'Audio'}
        </span>
      </div>
    </motion.div>
  );
}
