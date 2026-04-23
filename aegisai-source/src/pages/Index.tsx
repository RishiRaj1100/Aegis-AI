import { useCallback, useState } from "react";
import { toast } from "sonner";
import { CommandHeader } from "@/components/aegis/CommandHeader";
import { InputPanel } from "@/components/aegis/InputPanel";
import { OutputPanel } from "@/components/aegis/OutputPanel";
import { IntelligencePanel } from "@/components/aegis/IntelligencePanel";
import { ParticleField } from "@/components/aegis/ParticleField";
import { useDecision } from "@/hooks/useDecision";
import { useRecentTasks } from "@/hooks/useRecentTasks";
import { useT } from "@/lib/i18n";
import type { Language } from "@/types/aegis";

const Index = () => {
  const [language, setLanguage] = useState<Language>("en");
  const [lastTask, setLastTask] = useState<string>("");
  const { data, loading, error, run } = useDecision();
  const { items, add, clear } = useRecentTasks();
  const t = useT(language);

  const handleSubmit = useCallback(
    async (task: string) => {
      setLastTask(task);
      try {
        const res = await run({ task, language });
        add({
          task,
          decision: res.decision,
          risk: res.risk_level,
          probability: res.success_probability,
        });
        toast.success(t("decisionDone"), { description: t("consensusReached") });
      } catch (e: any) {
        toast.error(t("errorTitle"), { description: e?.message ?? "Unknown error" });
      }
    },
    [run, language, add, t],
  );

  const handleRetry = useCallback(() => {
    if (lastTask) handleSubmit(lastTask);
  }, [lastTask, handleSubmit]);

  return (
    <div className="min-h-screen flex flex-col bg-background relative">
      <ParticleField />
      <CommandHeader language={language} />
      <main className="flex-1 px-4 lg:px-6 py-5 overflow-hidden">
        <div className="grid gap-5 h-[calc(100vh-100px)] grid-cols-1 lg:grid-cols-12">
          <div className="lg:col-span-3 min-h-[480px]">
            <InputPanel
              loading={loading}
              language={language}
              onLanguageChange={setLanguage}
              onSubmit={handleSubmit}
              recent={items}
              onClearRecent={clear}
            />
          </div>
          <div className="lg:col-span-6 min-h-[480px]">
            <OutputPanel
              data={data}
              loading={loading}
              error={error}
              language={language}
              onRetry={handleRetry}
            />
          </div>
          <div className="lg:col-span-3 min-h-[480px]">
            <IntelligencePanel data={data} language={language} />
          </div>
        </div>
      </main>
    </div>
  );
};

export default Index;
