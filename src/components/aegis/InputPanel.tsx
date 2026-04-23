import { memo, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Mic, Send, Loader2, Radio, Sparkles, X, History, Trash2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { useVoiceInput } from "@/hooks/useVoiceInput";
import { useT } from "@/lib/i18n";
import type { Language } from "@/types/aegis";
import type { RecentTask } from "@/hooks/useRecentTasks";

interface Props {
  loading: boolean;
  language: Language;
  onLanguageChange: (l: Language) => void;
  onSubmit: (task: string) => void;
  recent: RecentTask[];
  onClearRecent: () => void;
}

const SUGGESTIONS_EN = [
  "Roll out the new payments system to production",
  "Migrate the analytics pipeline to event-driven",
  "Decide whether to acquire competitor X this quarter",
];
const SUGGESTIONS_HI = [
  "नई भुगतान प्रणाली को उत्पादन में रोलआउट करें",
  "विश्लेषिकी पाइपलाइन को इवेंट-संचालित में स्थानांतरित करें",
  "क्या इस तिमाही प्रतिस्पर्धी X का अधिग्रहण करें?",
];

const riskDot = {
  low: "bg-success",
  medium: "bg-warning",
  high: "bg-destructive",
} as const;

export const InputPanel = memo(function InputPanel({
  loading,
  language,
  onLanguageChange,
  onSubmit,
  recent,
  onClearRecent,
}: Props) {
  const t = useT(language);
  const [task, setTask] = useState("");
  const taRef = useRef<HTMLTextAreaElement>(null);
  const voice = useVoiceInput(language);

  useEffect(() => {
    if (voice.transcript) setTask(voice.transcript);
  }, [voice.transcript]);

  // Auto-grow textarea
  useEffect(() => {
    const el = taRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 240) + "px";
  }, [task]);

  const submit = () => {
    const value = task.trim();
    if (!value || loading) return;
    onSubmit(value);
  };

  const suggestions = language === "hi" ? SUGGESTIONS_HI : SUGGESTIONS_EN;

  return (
    <aside
      className="panel shadow-card flex flex-col h-full overflow-hidden"
      aria-label={t("missionIntake")}
    >
      <div className="px-5 py-4 border-b border-border/70 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
          <h2 className="font-display text-sm font-semibold tracking-wide uppercase text-muted-foreground">
            {t("missionIntake")}
          </h2>
        </div>
        <Badge variant="outline" className="font-mono text-[10px] border-border/70">
          01 / IN
        </Badge>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-5 space-y-5">
          <div className="space-y-2">
            <label htmlFor="task-input" className="text-xs font-medium text-muted-foreground">
              {t("describeTask")}
            </label>
            <div className="relative group">
              <Textarea
                id="task-input"
                ref={taRef}
                value={task}
                onChange={(e) => setTask(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit();
                }}
                placeholder={t("taskPlaceholder")}
                rows={5}
                className="resize-none bg-background/40 border-border/70 focus-visible:ring-primary/50 pr-12 text-sm leading-relaxed transition-all min-h-[120px]"
              />
              {task && (
                <button
                  onClick={() => setTask("")}
                  className="absolute top-2 right-2 h-6 w-6 grid place-items-center rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition opacity-0 group-hover:opacity-100 focus:opacity-100"
                  aria-label={t("clear")}
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          </div>

          {/* Voice */}
          <div className="rounded-lg border border-border/70 bg-background/30 p-4 space-y-3 transition-colors hover:border-border">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Radio className="h-3.5 w-3.5 text-primary" />
                <span className="text-xs font-medium">{t("voiceInput")}</span>
              </div>
              {voice.recording && (
                <span className="text-[10px] font-mono text-destructive flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-destructive animate-pulse" />
                  {t("listening")} · {language === "hi" ? "हिंदी" : "EN-US"}
                </span>
              )}
            </div>

            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={voice.recording ? voice.stop : voice.start}
                className={cn(
                  "relative h-12 w-12 rounded-full grid place-items-center transition-all duration-300 active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                  voice.recording
                    ? "bg-destructive text-destructive-foreground pulse-ring"
                    : "bg-gradient-primary text-primary-foreground hover:shadow-glow hover:scale-105",
                )}
                aria-label={voice.recording ? "Stop recording" : "Start recording"}
                aria-pressed={voice.recording}
              >
                <Mic className="h-5 w-5" />
              </button>

              <div className="flex-1 min-w-0">
                <AnimatePresence mode="wait">
                  {voice.transcript ? (
                    <motion.div
                      key="t"
                      initial={{ opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      className="text-xs"
                    >
                      <span className="text-muted-foreground">{t("transcript")} · </span>
                      <span className="font-mono uppercase text-[10px] text-primary">
                        {voice.detectedLanguage}
                      </span>
                      <p className="mt-1 text-foreground/90 line-clamp-2">{voice.transcript}</p>
                    </motion.div>
                  ) : (
                    <motion.p
                      key="i"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="text-xs text-muted-foreground leading-relaxed"
                    >
                      {t("voiceHint")}
                    </motion.p>
                  )}
                </AnimatePresence>
                {voice.error && (
                  <p className="mt-1 text-[11px] text-destructive font-mono flex items-center gap-1">
                    <AlertCircle className="h-3 w-3" /> {voice.error}
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Language */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-muted-foreground">{t("outputLanguage")}</label>
            <Select value={language} onValueChange={(v) => onLanguageChange(v as Language)}>
              <SelectTrigger className="bg-background/40 border-border/70 hover:border-primary/40 transition-colors">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="z-[100]">
                <SelectItem value="en">English</SelectItem>
                <SelectItem value="hi">हिंदी (Hindi)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Suggestions */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
              <Sparkles className="h-3 w-3" /> {t("quickPrompts")}
            </label>
            <div className="flex flex-wrap gap-1.5">
              {suggestions.map((s) => (
                <button
                  key={s}
                  onClick={() => setTask(s)}
                  className="text-[11px] px-2.5 py-1.5 rounded-md border border-border/70 bg-background/30 text-muted-foreground hover:text-foreground hover:border-primary/40 hover:bg-primary/5 transition text-left active:scale-[0.98]"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          {/* Recent */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                <History className="h-3 w-3" /> {t("recentTasks")}
              </label>
              {recent.length > 0 && (
                <button
                  onClick={onClearRecent}
                  className="text-muted-foreground hover:text-destructive transition p-1"
                  aria-label="Clear history"
                >
                  <Trash2 className="h-3 w-3" />
                </button>
              )}
            </div>
            {recent.length === 0 ? (
              <p className="text-[11px] text-muted-foreground italic px-1">{t("noRecent")}</p>
            ) : (
              <ul className="space-y-1.5">
                {recent.map((r) => (
                  <li key={r.id}>
                    <button
                      onClick={() => setTask(r.task)}
                      className="w-full text-left p-2.5 rounded-md border border-border/60 bg-background/20 hover:bg-background/40 hover:border-primary/30 transition group"
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <span className={cn("h-1.5 w-1.5 rounded-full", riskDot[r.risk])} />
                        <span className="text-[10px] font-mono text-muted-foreground">
                          {Math.round(r.probability * 100)}%
                        </span>
                        <span className="text-[10px] font-mono text-muted-foreground/60 ml-auto">
                          {new Date(r.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                        </span>
                      </div>
                      <p className="text-xs text-foreground/85 line-clamp-2 group-hover:text-foreground transition">
                        {r.task}
                      </p>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </ScrollArea>

      <div className="p-5 border-t border-border/70 bg-background/30">
        <Button
          onClick={submit}
          disabled={loading || !task.trim()}
          className="w-full h-11 bg-gradient-primary text-primary-foreground hover:opacity-95 hover:shadow-glow disabled:opacity-40 disabled:pointer-events-none font-medium transition-all active:scale-[0.98]"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" /> {t("synthesizing")}
            </>
          ) : (
            <>
              <Send className="h-4 w-4 mr-2" /> {t("runAegis")}
              <span className="ml-auto text-[10px] font-mono opacity-60">⌘ ↵</span>
            </>
          )}
        </Button>
      </div>
    </aside>
  );
});
