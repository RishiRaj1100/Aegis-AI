import { memo } from "react";
import { GitBranch, Network, Terminal } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MemoryGraph3D } from "./MemoryGraph3D";
import { MermaidDiagram } from "./MermaidDiagram";
import type { DecisionResponse, Language } from "@/types/aegis";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n";

interface Props {
  data: DecisionResponse | null;
  language: Language;
}

const levelStyle = {
  info: "text-primary",
  warn: "text-warning",
  error: "text-destructive",
  success: "text-success",
} as const;

function PanelHeader({ icon: Icon, title, step }: { icon: any; title: string; step: string }) {
  return (
    <div className="flex items-center justify-between px-4 py-2.5 border-b border-border/70 bg-background/30">
      <div className="flex items-center gap-2">
        <Icon className="h-3.5 w-3.5 text-primary" />
        <span className="text-xs font-display uppercase tracking-wider text-muted-foreground">
          {title}
        </span>
      </div>
      <span className="text-[10px] font-mono text-muted-foreground/70">{step}</span>
    </div>
  );
}

export const IntelligencePanel = memo(function IntelligencePanel({ data, language }: Props) {
  const t = useT(language);
  const nodes = data?.memory_nodes ?? [];
  const flow = data?.workflow ?? "flowchart TD\n  A[\"Mission Pending\"]";
  const logs = data?.logs ?? [];

  return (
    <aside className="panel shadow-card h-full overflow-hidden flex flex-col" aria-label={t("intelligenceView")}>
      <div className="px-5 py-4 border-b border-border/70 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
          <h2 className="font-display text-sm font-semibold tracking-wide uppercase text-muted-foreground">
            {t("intelligenceView")}
          </h2>
        </div>
        <Badge variant="outline" className="font-mono text-[10px] border-border/70">
          03 / IQ
        </Badge>
      </div>

      <div className="flex-1 overflow-hidden flex flex-col">
        {/* 3D Memory graph */}
        <div className="border-b border-border/70 shrink-0">
          <PanelHeader icon={Network} title={t("memoryGraph")} step="A · 3D" />
          <div className="p-3">
            <MemoryGraph3D nodes={nodes} />
          </div>
        </div>

        {/* Workflow */}
        <div className="border-b border-border/70 shrink-0">
          <PanelHeader icon={GitBranch} title={t("workflow")} step="B" />
            <div className="p-4 min-h-[200px] flex items-center justify-center">
              <MermaidDiagram chart={flow} id="workflow-graph" />
            </div>
        </div>

        {/* Logs */}
        <div className="flex-1 min-h-0 flex flex-col">
          <PanelHeader icon={Terminal} title={t("executionLogs")} step="C" />
          <ScrollArea className="flex-1">
            <div className="p-3 font-mono text-[11px] space-y-1">
              {logs.length === 0 ? (
                <p className="text-muted-foreground px-2 py-4 text-center">{t("noLogs")}</p>
              ) : (
                logs.map((l, i) => (
                  <div
                    key={i}
                    className="flex gap-2 px-2 py-1.5 rounded hover:bg-background/40 transition border border-transparent hover:border-border/40 animate-fade-in"
                    style={{ animationDelay: `${i * 40}ms` }}
                  >
                    <span className="text-muted-foreground/70 shrink-0">
                      {new Date(l.ts).toLocaleTimeString([], { hour12: false })}
                    </span>
                    <span className={cn("shrink-0 uppercase", levelStyle[l.level])}>
                      {l.level.padEnd(5)}
                    </span>
                    <span className="text-muted-foreground shrink-0">{l.source}</span>
                    <span className="text-foreground/85 break-all">{l.message}</span>
                  </div>
                ))
              )}
            </div>
          </ScrollArea>
        </div>
      </div>
    </aside>
  );
});
