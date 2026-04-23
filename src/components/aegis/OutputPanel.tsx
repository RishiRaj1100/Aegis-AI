import { memo, useState } from "react";
import { motion } from "framer-motion";
import {
  Brain,
  Gauge,
  ShieldAlert,
  FileText,
  Layers,
  Users,
  ThumbsUp,
  ThumbsDown,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ListChecks,
  Sparkles,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { sendFeedback } from "@/lib/aegisApi";
import type { DecisionResponse, RiskLevel, Language } from "@/types/aegis";
import { toast } from "sonner";
import { useT } from "@/lib/i18n";

interface Props {
  data: DecisionResponse | null;
  loading: boolean;
  error: string | null;
  language: Language;
  onRetry?: () => void;
}

function SectionTitle({ icon: Icon, label, step }: { icon: any; label: string; step: string }) {
  return (
    <div className="flex items-center justify-between">
      <CardTitle className="flex items-center gap-2 text-sm font-display tracking-wide uppercase text-muted-foreground">
        <Icon className="h-4 w-4 text-primary" />
        {label}
      </CardTitle>
      <span className="text-[10px] font-mono text-muted-foreground/70">{step}</span>
    </div>
  );
}

function EmptyState({ language }: { language: Language }) {
  const t = useT(language);
  return (
    <div className="h-full grid place-items-center p-10">
      <div className="text-center max-w-md space-y-5">
        <div className="relative mx-auto h-24 w-24">
          <div className="absolute inset-0 rounded-full bg-gradient-primary opacity-20 blur-2xl animate-glow-pulse" />
          <div className="relative h-full w-full rounded-2xl border border-border/70 bg-card/60 backdrop-blur grid place-items-center">
            <Brain className="h-10 w-10 text-primary" />
          </div>
        </div>
        <h3 className="font-display text-2xl tracking-tight">{t("awaitingMission")}</h3>
        <p className="text-sm text-muted-foreground leading-relaxed">{t("awaitingDesc")}</p>
        <div className="grid grid-cols-3 gap-2 pt-2">
          {[
            { l: t("decisionSummary"), n: "01" },
            { l: t("riskLevel"), n: "02" },
            { l: t("multiAgentDebate"), n: "03" },
          ].map((s) => (
            <div
              key={s.n}
              className="rounded-lg border border-border/60 bg-card/40 px-3 py-2 text-[10px] font-mono uppercase tracking-wider text-muted-foreground truncate"
            >
              {s.n} · {s.l}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ErrorState({ error, onRetry, language }: { error: string; onRetry?: () => void; language: Language }) {
  const t = useT(language);
  return (
    <div className="h-full grid place-items-center p-10">
      <div className="text-center max-w-md space-y-4">
        <div className="mx-auto h-16 w-16 rounded-2xl border border-destructive/30 bg-destructive/10 grid place-items-center">
          <XCircle className="h-7 w-7 text-destructive" />
        </div>
        <h3 className="font-display text-xl">{t("errorTitle")}</h3>
        <p className="text-sm text-muted-foreground font-mono break-all">{error}</p>
        {onRetry && (
          <Button onClick={onRetry} variant="outline" className="border-border/70">
            Retry
          </Button>
        )}
      </div>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="p-6 space-y-4 animate-fade-in">
      {[0, 1, 2, 3, 4].map((i) => (
        <div
          key={i}
          className="rounded-xl border border-border/60 bg-card/50 p-5 overflow-hidden relative"
          style={{ animationDelay: `${i * 80}ms` }}
        >
          <div
            className="absolute inset-0 bg-gradient-to-r from-transparent via-primary/5 to-transparent"
            style={{
              backgroundSize: "1000px 100%",
              animation: "shimmer 1.6s infinite linear",
            }}
          />
          <div className="h-3 w-1/3 bg-muted rounded mb-3" />
          <div className="h-2 w-full bg-muted/60 rounded mb-2" />
          <div className="h-2 w-5/6 bg-muted/60 rounded" />
          {i === 1 && <div className="mt-4 h-2 w-full bg-muted/40 rounded-full" />}
        </div>
      ))}
    </div>
  );
}

export const OutputPanel = memo(function OutputPanel({ data, loading, error, language, onRetry }: Props) {
  const t = useT(language);
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null);

  if (error && !loading) {
    return (
      <section className="panel shadow-card h-full overflow-hidden">
        <ErrorState error={error} onRetry={onRetry} language={language} />
      </section>
    );
  }
  if (loading && !data) {
    return (
      <section className="panel shadow-card h-full overflow-hidden">
        <LoadingState />
      </section>
    );
  }
  if (!data) {
    return (
      <section className="panel shadow-card h-full overflow-hidden">
        <EmptyState language={language} />
      </section>
    );
  }

  const riskMeta: Record<RiskLevel, { label: string; cls: string; ring: string; icon: any }> = {
    low: {
      label: t("lowRisk"),
      cls: "bg-success/10 text-success border-success/30",
      ring: "from-success/40 to-success/0",
      icon: CheckCircle2,
    },
    medium: {
      label: t("mediumRisk"),
      cls: "bg-warning/10 text-warning border-warning/30",
      ring: "from-warning/40 to-warning/0",
      icon: AlertTriangle,
    },
    high: {
      label: t("highRisk"),
      cls: "bg-destructive/10 text-destructive border-destructive/30",
      ring: "from-destructive/40 to-destructive/0",
      icon: AlertTriangle,
    },
  };

  const outcomeBadge = {
    success: "bg-success/10 text-success border-success/30",
    partial: "bg-warning/10 text-warning border-warning/30",
    failed: "bg-destructive/10 text-destructive border-destructive/30",
  };
  const outcomeLabel = {
    success: t("outcomeSuccess"),
    partial: t("outcomePartial"),
    failed: t("outcomeFailed"),
  };

  const risk = riskMeta[data.risk_level];
  const RiskIcon = risk.icon;
  const probabilityPct = Math.round(data.success_probability * 100);

  // Simple positive/negative factor extraction from explanation sentences
  const sentences = data.explanation.split(/(?<=[.!?।])\s+/).filter(Boolean);

  const handleFeedback = async (rating: "up" | "down") => {
    setFeedback(rating);
    try {
      await sendFeedback({ decision: data.decision, rating });
      toast.success(t("feedbackSaved"));
    } catch {
      toast.error(t("feedbackFailed"));
    }
  };

  return (
    <section className="panel shadow-card h-full overflow-hidden flex flex-col">
      <div className="px-6 py-4 border-b border-border/70 flex items-center justify-between bg-gradient-to-r from-primary/5 via-transparent to-accent/5">
        <div className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
          <h2 className="font-display text-sm font-semibold tracking-wide uppercase text-muted-foreground">
            {t("decisionSynthesis")}
          </h2>
        </div>
        <Badge variant="outline" className="font-mono text-[10px] border-border/70">
          02 / OUT
        </Badge>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-6 space-y-5">
          {/* Decision Summary */}
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
            <Card className="border-border/70 bg-card/60 backdrop-blur overflow-hidden relative group">
              <div className={cn("absolute inset-0 bg-gradient-to-br opacity-30 pointer-events-none", risk.ring)} />
              <CardHeader className="pb-3 relative">
                <SectionTitle icon={Brain} label={t("decisionSummary")} step="01" />
              </CardHeader>
              <CardContent className="space-y-4 relative">
                <p className="text-lg leading-relaxed font-display tracking-tight">{data.decision}</p>
                <div className="flex flex-wrap gap-2 items-center pt-1">
                  <Badge className={cn("border font-mono text-[10px]", risk.cls)}>
                    <RiskIcon className="h-3 w-3 mr-1" />
                    {risk.label}
                  </Badge>
                  <Badge variant="outline" className="font-mono text-[10px] border-border/70 text-muted-foreground">
                    {t("successProbability").toUpperCase()} {probabilityPct}%
                  </Badge>
                  <div className="ml-auto flex items-center gap-1">
                    <Button
                      size="sm"
                      variant="ghost"
                      className={cn("h-8 px-2 transition-colors", feedback === "up" && "text-success bg-success/10")}
                      onClick={() => handleFeedback("up")}
                      aria-label={t("helpful")}
                    >
                      <ThumbsUp className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className={cn("h-8 px-2 transition-colors", feedback === "down" && "text-destructive bg-destructive/10")}
                      onClick={() => handleFeedback("down")}
                      aria-label={t("notHelpful")}
                    >
                      <ThumbsDown className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Probability + Risk side by side */}
          <div className="grid md:grid-cols-2 gap-5">
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
              <Card className="border-border/70 bg-card/60 backdrop-blur h-full">
                <CardHeader className="pb-3">
                  <SectionTitle icon={Gauge} label={t("successProbability")} step="02" />
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-baseline gap-2">
                    <motion.span
                      key={probabilityPct}
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      className="text-4xl font-display font-semibold text-gradient"
                    >
                      {probabilityPct}%
                    </motion.span>
                    <span className="text-xs text-muted-foreground font-mono">
                      ± {Math.max(3, Math.round((1 - data.success_probability) * 12))}%
                    </span>
                  </div>
                  <Progress value={probabilityPct} className="h-2" />
                  <p className="text-[11px] text-muted-foreground font-mono">{t("calibrated")}</p>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
              <Card className="border-border/70 bg-card/60 backdrop-blur h-full">
                <CardHeader className="pb-3">
                  <SectionTitle icon={ShieldAlert} label={t("riskLevel")} step="03" />
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-4">
                    <div
                      className={cn(
                        "h-16 w-16 rounded-xl grid place-items-center border relative",
                        risk.cls,
                      )}
                    >
                      <RiskIcon className="h-7 w-7" />
                      {data.risk_level === "high" && (
                        <span className="absolute -top-1 -right-1 h-3 w-3 rounded-full bg-destructive animate-ping" />
                      )}
                    </div>
                    <div className="space-y-1">
                      <p className="font-display text-xl">{risk.label}</p>
                      <p className="text-xs text-muted-foreground leading-relaxed max-w-[200px]">
                        {t("riskComposite")}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          </div>

          {/* Explanation as bullet reasoning */}
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
            <Card className="border-border/70 bg-card/60 backdrop-blur">
              <CardHeader className="pb-3">
                <SectionTitle icon={FileText} label={t("explanation")} step="04" />
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {sentences.map((s, i) => {
                    const isNegative = /risk|fail|delay|concern|jokhim|विफल|जोखिम|देरी/i.test(s);
                    return (
                      <li
                        key={i}
                        className="flex items-start gap-2.5 text-sm leading-relaxed"
                      >
                        <span
                          className={cn(
                            "mt-1.5 h-1.5 w-1.5 rounded-full shrink-0",
                            isNegative ? "bg-warning" : "bg-success",
                          )}
                        />
                        <span className="text-foreground/85">{s}</span>
                      </li>
                    );
                  })}
                </ul>
              </CardContent>
            </Card>
          </motion.div>

          {/* Subtasks */}
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
            <Card className="border-border/70 bg-card/60 backdrop-blur">
              <CardHeader className="pb-3">
                <SectionTitle icon={ListChecks} label={t("generatedSubtasks")} step="05" />
              </CardHeader>
              <CardContent>
                <ScrollArea className="max-h-72 pr-3">
                  <ol className="space-y-2">
                    {data.subtasks.map((s, i) => (
                      <li
                        key={i}
                        className="flex items-start gap-3 p-2.5 rounded-md border border-border/50 bg-background/30 text-sm hover:bg-background/50 hover:border-border transition"
                      >
                        <span className="font-mono text-[10px] mt-0.5 px-1.5 py-0.5 rounded bg-primary/10 text-primary border border-primary/20 shrink-0">
                          {String(i + 1).padStart(2, "0")}
                        </span>
                        <span className="leading-relaxed">{s}</span>
                      </li>
                    ))}
                  </ol>
                </ScrollArea>
              </CardContent>
            </Card>
          </motion.div>

          {/* Similar Tasks */}
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
            <Card className="border-border/70 bg-card/60 backdrop-blur">
              <CardHeader className="pb-3">
                <SectionTitle icon={Layers} label={t("similarMissions")} step="06" />
              </CardHeader>
              <CardContent>
                <ScrollArea className="max-h-56 pr-3">
                  <div className="space-y-2">
                    {data.similar_tasks.map((tk) => (
                      <div
                        key={tk.id}
                        className="flex items-center gap-3 p-3 rounded-md border border-border/60 bg-background/30 hover:bg-background/50 transition group"
                      >
                        <span className="font-mono text-[10px] text-muted-foreground w-16">{tk.id}</span>
                        <span className="text-sm flex-1 truncate group-hover:text-primary transition-colors">
                          {tk.title}
                        </span>
                        <Badge
                          variant="outline"
                          className={cn("font-mono text-[10px]", outcomeBadge[tk.outcome])}
                        >
                          {outcomeLabel[tk.outcome]}
                        </Badge>
                        <span className="font-mono text-[10px] text-muted-foreground w-12 text-right">
                          {Math.round(tk.similarity * 100)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </motion.div>

          {/* Agent Debate as tabs */}
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
            <Card className="border-border/70 bg-card/60 backdrop-blur">
              <CardHeader className="pb-3">
                <SectionTitle icon={Users} label={t("multiAgentDebate")} step="07" />
              </CardHeader>
              <CardContent>
                <Tabs defaultValue="final" className="w-full">
                  <TabsList className="grid grid-cols-3 bg-background/40 border border-border/60">
                    <TabsTrigger value="optimist" className="text-xs data-[state=active]:bg-success/10 data-[state=active]:text-success">
                      {t("optimistAgent")}
                    </TabsTrigger>
                    <TabsTrigger value="risk" className="text-xs data-[state=active]:bg-destructive/10 data-[state=active]:text-destructive">
                      {t("riskAgent")}
                    </TabsTrigger>
                    <TabsTrigger value="final" className="text-xs data-[state=active]:bg-primary/10 data-[state=active]:text-primary">
                      <Sparkles className="h-3 w-3 mr-1" /> Final
                    </TabsTrigger>
                  </TabsList>

                  <TabsContent value="optimist" className="mt-3">
                    <div className="rounded-lg border border-success/30 bg-success/5 p-4">
                      <p className="text-sm leading-relaxed text-foreground/90">{data.agent_debate.optimist}</p>
                    </div>
                  </TabsContent>
                  <TabsContent value="risk" className="mt-3">
                    <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4">
                      <p className="text-sm leading-relaxed text-foreground/90">{data.agent_debate.risk}</p>
                    </div>
                  </TabsContent>
                  <TabsContent value="final" className="mt-3">
                    <div className="rounded-lg border border-primary/30 bg-gradient-to-br from-primary/10 to-accent/5 p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <Brain className="h-3.5 w-3.5 text-primary" />
                        <span className="font-display text-xs uppercase tracking-wider text-primary">
                          {t("finalDecision")}
                        </span>
                      </div>
                      <p className="text-sm leading-relaxed">{data.agent_debate.final_decision}</p>
                    </div>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </ScrollArea>
    </section>
  );
});
