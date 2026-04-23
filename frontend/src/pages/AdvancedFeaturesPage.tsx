import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { useMission } from "@/contexts/MissionContext";
import {
  RecommendationsWidget,
  SearchBar,
  APIKeyManager,
  MFASetup,
  BatchImportExport,
  WebhookManager,
} from "@/components/AdvancedFeatures";

const AdvancedFeaturesPage = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { mission } = useMission();
  const [lastSearch, setLastSearch] = useState("");
  const userId = user?.id || "";

  return (
    <div className="min-h-screen bg-background">
      <div className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-40">
        <div className="mx-auto max-w-7xl px-6 py-4 flex items-center gap-4">
          <button onClick={() => navigate("/dashboard")} className="btn-ghost !px-3 !py-2">
            <ArrowLeft size={16} />
          </button>
          <h1 className="text-2xl font-bold text-foreground">Advanced Features</h1>
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-6 py-8 space-y-6">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-3xl border border-white/10 bg-[radial-gradient(circle_at_top_left,_rgba(59,130,246,0.18),_transparent_45%),linear-gradient(180deg,rgba(12,12,16,0.9),rgba(8,8,10,0.96))] p-6 shadow-[0_0_60px_rgba(59,130,246,0.12)]"
        >
          <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Mission extensions</p>
              <h2 className="mt-1 text-2xl font-semibold text-foreground">Search, security, webhooks, and batch tools</h2>
              <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
                These utilities sit around the core mission engine. They surface recommendations, API keys, 2FA, batch import/export, and webhook automation once a user id is available.
              </p>
            </div>
            <div className="flex gap-2 text-xs text-muted-foreground">
              <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1">User scoped</span>
              <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1">Optional features</span>
            </div>
          </div>
        </motion.div>

        {mission ? (
          <div className="mission-shell mission-orbit rounded-2xl border border-white/10 bg-white/5 p-5">
            <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Latest question</p>
            <h2 className="mt-1 text-lg font-semibold text-foreground">{mission.goal}</h2>
            <p className="text-sm text-muted-foreground">Task {mission.taskId || "pending"} · {mission.status} · {mission.riskLevel}</p>
          </div>
        ) : null}

        <SearchBar userId={userId} onSearch={setLastSearch} initialQuery={mission?.goal || ""} />
        {lastSearch ? (
          <div className="text-sm text-muted-foreground">Last search: {lastSearch}</div>
        ) : null}

        <div className="grid gap-6 lg:grid-cols-2">
          <RecommendationsWidget userId={userId} />
          <APIKeyManager userId={userId} />
          <MFASetup userId={userId} />
          <WebhookManager userId={userId} />
        </div>

        <BatchImportExport userId={userId} />
      </div>
    </div>
  );
};

export default AdvancedFeaturesPage;
