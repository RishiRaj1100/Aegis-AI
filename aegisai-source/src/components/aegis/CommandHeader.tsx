import { memo } from "react";
import { Shield, Activity, Sparkles } from "lucide-react";
import { useT } from "@/lib/i18n";
import type { Language } from "@/types/aegis";

interface Props {
  language: Language;
}

export const CommandHeader = memo(function CommandHeader({ language }: Props) {
  const t = useT(language);
  return (
    <header className="border-b border-border/60 bg-background/40 backdrop-blur-xl sticky top-0 z-30">
      <div className="flex items-center justify-between px-6 py-3.5">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="h-9 w-9 rounded-lg bg-gradient-primary grid place-items-center shadow-glow">
              <Shield className="h-5 w-5 text-primary-foreground" strokeWidth={2.5} />
            </div>
            <span className="absolute -top-0.5 -right-0.5 h-2.5 w-2.5 rounded-full bg-success ring-2 ring-background animate-pulse" />
          </div>
          <div className="leading-tight">
            <h1 className="font-display text-lg font-semibold tracking-tight">
              Aegis<span className="text-gradient">AI</span>
            </h1>
            <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              {t("appTagline")}
            </p>
          </div>
        </div>

        <div className="hidden md:flex items-center gap-5 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <Activity className="h-3.5 w-3.5 text-success" />
            <span className="font-mono">{t("systemNominal")}</span>
          </span>
          <span className="h-4 w-px bg-border" />
          <span className="flex items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5 text-primary" />
            <span className="font-mono">{t("agentsOnline")}</span>
          </span>
        </div>
      </div>
    </header>
  );
});
