import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Send, Zap, LogOut, BarChart3, Mic, MicOff, Orbit } from "lucide-react";
import { useAuth, withAuth } from "@/contexts/AuthContext";
import { useMission } from "@/contexts/MissionContext";
import { goalAPI, APIError } from "@/services/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/use-toast";

// ════════════════════════════════════════════════════════════════════════════════
// Components
// ════════════════════════════════════════════════════════════════════════════════

const PipelineProgress = ({ agents, activeAgent }: any) => {
  return (
    <div className="space-y-5 overflow-hidden rounded-2xl border border-white/10 bg-[radial-gradient(circle_at_top,_rgba(99,102,241,0.14),_transparent_55%),linear-gradient(180deg,rgba(10,10,18,0.92),rgba(8,8,12,0.96))] p-5 shadow-[0_0_70px_rgba(99,102,241,0.12)]">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h3 className="text-sm font-semibold text-foreground">Pipeline Theater</h3>
          <p className="text-xs text-muted-foreground">The agents are working through your mission in sequence.</p>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-white/10 bg-black/20 px-3 py-1 text-[11px] uppercase tracking-[0.24em] text-muted-foreground">
          <span className="h-2 w-2 rounded-full bg-primary shadow-[0_0_12px_rgba(99,102,241,0.8)]" />
          Live
        </div>
      </div>

      <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-black/30 p-4">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_rgba(59,130,246,0.16),_transparent_60%)]" />
        <motion.div
          aria-hidden="true"
          className="absolute left-1/2 top-1/2 h-40 w-40 -translate-x-1/2 -translate-y-1/2 rounded-full border border-cyan-400/20"
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 24, ease: "linear" }}
        >
          <div className="absolute -left-1 top-1/2 h-2 w-2 -translate-y-1/2 rounded-full bg-cyan-300 shadow-[0_0_18px_rgba(103,232,249,0.95)]" />
          <div className="absolute right-0 top-1/2 h-2 w-2 -translate-y-1/2 rounded-full bg-fuchsia-300 shadow-[0_0_18px_rgba(232,121,249,0.95)]" />
        </motion.div>

        <div className="relative z-10 flex items-center gap-3 overflow-x-auto pb-2">
          {agents.map((agent: string, i: number) => {
            const state = i < activeAgent ? "done" : i === activeAgent ? "active" : "idle";
            return (
              <div key={agent} className="flex items-center gap-3 flex-shrink-0">
                <motion.div
                  animate={state === "active" ? { y: [0, -4, 0], scale: [1, 1.04, 1] } : { y: 0, scale: 1 }}
                  transition={{ repeat: state === "active" ? Infinity : 0, duration: 1.6, ease: "easeInOut" }}
                  className={`relative flex h-12 items-center gap-2 rounded-full border px-4 text-sm whitespace-nowrap backdrop-blur-sm transition-all ${
                    state === "done"
                      ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-300 shadow-[0_0_18px_rgba(16,185,129,0.12)]"
                      : state === "active"
                      ? "border-primary/40 bg-primary/15 text-primary shadow-[0_0_28px_rgba(99,102,241,0.22)]"
                      : "border-white/10 bg-white/5 text-muted-foreground"
                  }`}
                >
                  <span className="font-mono text-[11px]">{String(i + 1).padStart(2, "0")}</span>
                  <span>{agent}</span>
                  {state === "active" ? <span className="absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full bg-cyan-300 shadow-[0_0_16px_rgba(103,232,249,0.95)]" /> : null}
                </motion.div>
                {i < agents.length - 1 ? (
                  <motion.div
                    className={`h-px w-6 flex-shrink-0 rounded-full ${i < activeAgent ? "bg-emerald-400/60" : "bg-white/10"}`}
                    animate={i < activeAgent ? { opacity: [0.5, 1, 0.5], scaleX: [1, 1.15, 1] } : { opacity: 1, scaleX: 1 }}
                    transition={{ repeat: i < activeAgent ? Infinity : 0, duration: 1.8, ease: "easeInOut" }}
                  />
                ) : null}
              </div>
            );
          })}
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-3">
          {[
            { label: "Commander", value: activeAgent >= 0 ? "Decomposing" : "Queued" },
            { label: "Execution", value: activeAgent >= 2 ? "Structuring" : "Waiting" },
            { label: "Trust", value: activeAgent >= 3 ? "Scoring" : "Standing by" },
          ].map((stat) => (
            <div key={stat.label} className="rounded-xl border border-white/10 bg-white/5 p-3">
              <p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">{stat.label}</p>
              <p className="mt-1 text-sm font-medium text-foreground">{stat.value}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

const ResultsPanel = ({ data, onPlayReply, onStopReply, replyMode, canPlayReply, isReplyPlaying }: any) => {
  if (!data) return null;

  const plan = data.plan || data;
  const confidence = Number(plan?.confidence ?? data.confidence ?? 0);
  const riskLevel = String(plan?.risk_level ?? data.risk_level ?? "MEDIUM");
  const subtasks = Array.isArray(plan?.subtasks) ? plan.subtasks : [];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <div className="grid gap-4 md:grid-cols-3">
        {/* Trust Score */}
        <div className="glass-card p-6 rounded-lg">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-muted-foreground">Confidence</h3>
            <span className="text-2xl font-bold text-primary">{Math.round(confidence)}%</span>
          </div>
          <div className="w-full bg-secondary rounded-full h-2">
            <div
              className="bg-primary h-2 rounded-full transition-all duration-700"
              style={{ width: `${confidence}%` }}
            />
          </div>
          <p className="text-xs text-muted-foreground mt-3">Risk: {riskLevel}</p>
        </div>

        {/* Subtasks */}
        <div className="glass-card p-6 rounded-lg">
          <p className="text-sm font-semibold text-muted-foreground mb-2">Subtasks</p>
          <p className="text-2xl font-bold text-aegis-cyan">{subtasks.length}</p>
          <p className="text-xs text-muted-foreground mt-3">Ready to execute</p>
        </div>

        {/* Execution Time */}
        <div className="glass-card p-6 rounded-lg">
          <p className="text-sm font-semibold text-muted-foreground mb-2">Est. Duration</p>
          <p className="text-2xl font-bold text-aegis-violet">
            {data.plan?.subtasks
              ?.reduce((sum: number, t: any) => sum + (t.estimated_duration_minutes || 0), 0)
              .toFixed(0) || 0} min
          </p>
          <p className="text-xs text-muted-foreground mt-3">Based on subtasks</p>
        </div>
      </div>

      {/* Plan Detail */}
      <div className="glass-card p-6 rounded-lg space-y-4">
        <div>
          <h3 className="font-semibold text-foreground mb-2">Goal</h3>
          <p className="text-sm text-muted-foreground">{data.plan?.goal}</p>
        </div>

        <div>
          <h3 className="font-semibold text-foreground mb-2">Execution Plan</h3>
          <p className="text-sm text-muted-foreground whitespace-pre-wrap">{data.plan?.execution_plan}</p>
        </div>

        {data.plan?.spoken_summary && (
          <div>
            <div className="flex items-center justify-between gap-3 mb-2">
              <h3 className="font-semibold text-foreground">Spoken Summary</h3>
              <div className="flex items-center gap-2">
                {canPlayReply ? (
                  <button type="button" onClick={onPlayReply} className="rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs font-medium text-primary hover:bg-primary/15">
                    Play answer ({replyMode})
                  </button>
                ) : null}
                {isReplyPlaying ? (
                  <button type="button" onClick={onStopReply} className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-medium text-muted-foreground hover:text-foreground">
                    Stop audio
                  </button>
                ) : null}
              </div>
            </div>
            <p className="text-sm text-muted-foreground whitespace-pre-wrap">{data.plan.spoken_summary}</p>
            <p className="mt-2 text-xs text-muted-foreground">This reply can be replayed manually if autoplay is blocked by the browser.</p>
          </div>
        )}

        {data.plan?.research_insights && (
          <div>
            <h3 className="font-semibold text-foreground mb-2">Research Insights</h3>
            <p className="text-sm text-muted-foreground whitespace-pre-wrap">{data.plan.research_insights}</p>
          </div>
        )}

        {data.plan?.subtasks && data.plan.subtasks.length > 0 && (
          <div>
            <h3 className="font-semibold text-foreground mb-3">Subtasks</h3>
            <div className="space-y-2">
              {subtasks.slice(0, 5).map((task: any, i: number) => (
                <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-secondary/50">
                  <span className="text-xs font-mono text-primary mt-0.5">{String(i + 1).padStart(2, "0")}</span>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-foreground">{task.title}</p>
                    <p className="text-xs text-muted-foreground">{task.description}</p>
                  </div>
                </div>
              ))}
              {subtasks.length > 5 && (
                <p className="text-xs text-muted-foreground text-center py-2">
                  +{subtasks.length - 5} more subtasks
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
};

// ════════════════════════════════════════════════════════════════════════════════
// Main Component
// ════════════════════════════════════════════════════════════════════════════════

const Dashboard = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { toast } = useToast();
  const { mission, setMission } = useMission();

  const [goal, setGoal] = useState("");
  const [language, setLanguage] = useState("en-IN");
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [activeAgent, setActiveAgent] = useState(0);
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState<any>(null);
  const [voiceReply, setVoiceReply] = useState<{ audioBase64?: string; spokenSummary?: string; mode: string } | null>(null);
  const [isReplyPlaying, setIsReplyPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const agents = ["Commander", "Research", "Execution", "Trust", "Memory", "Reflection"];

  useEffect(() => {
    if (!isLoading) {
      return;
    }

    const timer = window.setInterval(() => {
      setActiveAgent((current) => Math.min(current + 1, agents.length - 1));
    }, 650);

    return () => window.clearInterval(timer);
  }, [isLoading, agents.length]);

  useEffect(() => {
    const audioBase64 = results?.audio_response_base64;
    const spokenSummary = results?.plan?.spoken_summary;

    setVoiceReply({
      audioBase64,
      spokenSummary,
      mode: audioBase64 ? "Sarvam audio" : spokenSummary ? "browser speech" : "text only",
    });

    if (!audioBase64 && !spokenSummary) {
      setIsReplyPlaying(false);
      return;
    }

    if (audioBase64) {
      try {
        const audio = new Audio(`data:audio/mpeg;base64,${audioBase64}`);
        audioRef.current = audio;
        setIsReplyPlaying(true);
        audio.onended = () => setIsReplyPlaying(false);
        audio.onpause = () => setIsReplyPlaying(false);
        void audio.play().catch(() => setIsReplyPlaying(false));
        return () => {
          audio.pause();
          audioRef.current = null;
          setIsReplyPlaying(false);
        };
      } catch (error) {
        console.error("Failed to play Sarvam audio response:", error);
        setIsReplyPlaying(false);
      }
    }

    if (spokenSummary && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(spokenSummary);
      utterance.lang = language;
      setIsReplyPlaying(true);
      utterance.onend = () => setIsReplyPlaying(false);
      utterance.onerror = () => setIsReplyPlaying(false);
      window.speechSynthesis.speak(utterance);
      return () => {
        window.speechSynthesis.cancel();
        setIsReplyPlaying(false);
      };
    }
  }, [results, language]);

  const playVoiceReply = () => {
    const audioBase64 = voiceReply?.audioBase64;
    const spokenSummary = voiceReply?.spokenSummary;

    if (audioBase64) {
      try {
        if (audioRef.current) {
          audioRef.current.pause();
          audioRef.current.currentTime = 0;
        }
        const audio = new Audio(`data:audio/mpeg;base64,${audioBase64}`);
        audioRef.current = audio;
        setIsReplyPlaying(true);
        audio.onended = () => setIsReplyPlaying(false);
        audio.onpause = () => setIsReplyPlaying(false);
        void audio.play().catch(() => setIsReplyPlaying(false));
        return;
      } catch (error) {
        console.error("Manual Sarvam audio playback failed:", error);
        setIsReplyPlaying(false);
      }
    }

    if (spokenSummary && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(spokenSummary);
      utterance.lang = language;
      setIsReplyPlaying(true);
      utterance.onend = () => setIsReplyPlaying(false);
      utterance.onerror = () => setIsReplyPlaying(false);
      window.speechSynthesis.speak(utterance);
    }
  };

  const stopVoiceReply = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      audioRef.current = null;
    }
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    setIsReplyPlaying(false);
  };

  // Handle goal submission
  const handleSubmitGoal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!goal.trim()) {
      toast({
        title: "Error",
        description: "Please enter a goal",
        variant: "destructive",
      });
      return;
    }

    setIsLoading(true);
    setResults(null);
    setActiveAgent(0);

    try {
      const response = await goalAPI.submitGoal(goal, language);
      setResults(response);
      setMission({
        goal,
        taskId: response.task_id || response.plan?.task_id || "",
        language,
        status: response.status || "IN_PROGRESS",
        confidence: Number(response.plan?.confidence ?? response.confidence ?? 0),
        riskLevel: String(response.plan?.risk_level ?? response.risk_level ?? "MEDIUM"),
        subtasks: Array.isArray(response.plan?.subtasks) ? response.plan.subtasks.length : Array.isArray(response.subtasks) ? response.subtasks.length : 0,
        updatedAt: new Date().toISOString(),
        source: "dashboard",
      });
      toast({
        title: "Success",
        description: "Goal processed successfully",
      });
      setGoal("");
    } catch (error) {
      const message = error instanceof APIError ? error.detail : "Failed to process goal";
      toast({
        title: "Error",
        description: message,
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Handle voice input
  const handleStartRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks: any[] = [];

      recorder.ondataavailable = (e) => chunks.push(e.data);
      recorder.onstop = async () => {
        const blob = new Blob(chunks, { type: "audio/webm" });
        const reader = new FileReader();
        reader.onload = async () => {
          const base64 = (reader.result as string).split(",")[1];
          setIsLoading(true);
          try {
            const response = await goalAPI.submitVoiceGoal(base64, language, "webm");
            setResults(response);
            setMission({
              goal: response.plan?.goal || "Voice goal",
              taskId: response.task_id || response.plan?.task_id || "",
              language,
              status: response.status || "IN_PROGRESS",
              confidence: Number(response.plan?.confidence ?? response.confidence ?? 0),
              riskLevel: String(response.plan?.risk_level ?? response.risk_level ?? "MEDIUM"),
              subtasks: Array.isArray(response.plan?.subtasks) ? response.plan.subtasks.length : Array.isArray(response.subtasks) ? response.subtasks.length : 0,
              updatedAt: new Date().toISOString(),
              source: "voice",
            });
            toast({
              title: "Success",
              description: "Voice goal processed successfully",
            });
          } catch (error) {
            const message = error instanceof APIError ? error.detail : "Failed to process voice";
            toast({
              title: "Error",
              description: message,
              variant: "destructive",
            });
          } finally {
            setIsLoading(false);
          }
        };
        reader.readAsDataURL(blob);
        stream.getTracks().forEach((t) => t.stop());
      };

      recorder.start();
      setMediaRecorder(recorder);
      setIsRecording(true);
    } catch (error) {
      toast({
        title: "Error",
        description: "Could not access microphone",
        variant: "destructive",
      });
    }
  };

  const handleStopRecording = () => {
    if (mediaRecorder) {
      mediaRecorder.stop();
      setIsRecording(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b border-border bg-card/50 backdrop-blur-sm">
        <div className="mx-auto max-w-7xl px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">
              <span className="text-foreground">Aegis</span>
              <span className="text-primary">AI</span>
            </h1>
            <p className="text-sm text-muted-foreground">Welcome, {user?.name}</p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate("/analytics")}
              className="btn-ghost !px-4 !py-2 flex items-center gap-2"
            >
              <BarChart3 size={16} />
              Analytics
            </button>
            <button
              onClick={() => navigate("/advanced-features")}
              className="btn-ghost !px-4 !py-2 flex items-center gap-2"
            >
              <Zap size={16} />
              Advanced
            </button>
            <button
              onClick={() => navigate("/monitoring")}
              className="btn-ghost !px-4 !py-2 flex items-center gap-2"
            >
              <BarChart3 size={16} />
              Monitoring
            </button>
            <button
              onClick={() => navigate("/intelligence")}
              className="btn-ghost !px-4 !py-2 flex items-center gap-2"
            >
              <Orbit size={16} />
              Intelligence
            </button>
            <button
              onClick={() => {
                logout();
              }}
              className="btn-ghost !px-4 !py-2 flex items-center gap-2 text-aegis-rose hover:text-aegis-rose"
            >
              <LogOut size={16} />
              Sign Out
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="mx-auto max-w-7xl px-6 py-8">
        {mission ? (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6 mission-shell mission-orbit rounded-2xl border border-white/10 bg-white/5 p-4"
          >
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Current mission</p>
                <h2 className="mt-1 text-lg font-semibold text-foreground">{mission.goal}</h2>
                <p className="text-sm text-muted-foreground">Task {mission.taskId || "pending"} · {mission.status} · {mission.riskLevel}</p>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-muted-foreground">{mission.language}</span>
                <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-muted-foreground">{mission.subtasks} subtasks</span>
                <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-muted-foreground">{Math.round(mission.confidence)}% confidence</span>
              </div>
            </div>
          </motion.div>
        ) : null}

        <div className="grid gap-8 lg:grid-cols-3">
          {/* Sidebar */}
          <div className="lg:col-span-1 space-y-6">
            {/* Goal Input */}
            <motion.form
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              onSubmit={handleSubmitGoal}
              className="glass-card p-6 rounded-lg space-y-4"
            >
              <h2 className="text-lg font-semibold text-foreground">New Goal</h2>
              <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Ask once, all tabs sync</p>

              <textarea
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                placeholder="Describe your goal or challenge..."
                className="input-field min-h-24"
              />

              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-2">Language</label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="input-field"
                >
                  <option value="en-IN">English</option>
                  <option value="hi-IN">Hindi</option>
                  <option value="bn-IN">Bengali</option>
                  <option value="ta-IN">Tamil</option>
                </select>
              </div>

              <div className="flex gap-2">
                <button
                  type="submit"
                  disabled={isLoading}
                  className="btn-primary flex-1 flex items-center justify-center gap-2"
                >
                  <Send size={16} />
                  {isLoading ? "Processing..." : "Submit"}
                </button>

                {!isRecording ? (
                  <button
                    type="button"
                    onClick={handleStartRecording}
                    className="btn-ghost !px-4"
                  >
                    <Mic size={16} />
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={handleStopRecording}
                    className="btn-danger !px-4"
                  >
                    <MicOff size={16} />
                  </button>
                )}
              </div>
            </motion.form>

            {/* Pipeline Preview */}
            {isLoading && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="glass-card p-6 rounded-lg"
              >
                <PipelineProgress agents={agents} activeAgent={activeAgent} />
              </motion.div>
            )}
          </div>

          {/* Main Content */}
          <div className="lg:col-span-2">
            {!results ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-center py-16"
              >
                <Zap size={48} className="mx-auto mb-4 text-muted-foreground" />
                <p className="text-muted-foreground">Submit a goal to get started</p>
              </motion.div>
            ) : (
              <ResultsPanel
                data={results}
                onPlayReply={playVoiceReply}
                onStopReply={stopVoiceReply}
                replyMode={voiceReply?.mode || "text only"}
                canPlayReply={Boolean(voiceReply?.audioBase64 || voiceReply?.spokenSummary)}
                isReplyPlaying={isReplyPlaying}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default withAuth(Dashboard);
