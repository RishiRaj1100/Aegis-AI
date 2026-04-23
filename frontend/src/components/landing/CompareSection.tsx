import { motion } from "framer-motion";

const features = [
  "Multi-agent pipeline execution",
  "Trust-scored plan output (0–100)",
  "Per-subtask ethics scanning",
  "Semantic memory across sessions",
  "Reflection & outcome learning",
  "Voice I/O with multilingual support",
  "Structured execution plan (DAG)",
  "Real-time planning via SSE stream",
  "Confidence calibration from feedback",
  "Revision gate (auto re-plans if trust low)",
];

type Support = "full" | "partial" | "none";

const competitors: Record<string, Support[]> = {
  AegisAI: ["full","full","full","full","full","full","full","full","full","full"],
  ChatGPT: ["none","none","none","partial","none","partial","none","none","none","none"],
  Claude:  ["none","none","partial","partial","none","none","none","none","none","none"],
  Gemini:  ["none","none","none","partial","none","partial","none","none","none","none"],
  AutoGPT: ["partial","none","none","partial","partial","none","partial","none","none","none"],
};

const CellIcon = ({ value }: { value: Support }) => {
  if (value === "full") return <span className="text-aegis-emerald font-mono">✦</span>;
  if (value === "partial") return <span className="text-aegis-amber font-mono">◑</span>;
  return <span className="text-aegis-rose font-mono">—</span>;
};

export const CompareSection = () => {
  const cols = Object.keys(competitors);

  return (
    <section id="compare" className="relative py-24 px-6">
      <div className="mx-auto max-w-6xl">
        <motion.div
          className="mb-16 text-center"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          <h2 className="font-display text-3xl font-bold md:text-5xl">
            Not a chatbot. An autonomous{" "}
            <span className="text-primary">decision system.</span>
          </h2>
        </motion.div>

        <div className="glass-card overflow-x-auto p-1">
          <table className="w-full min-w-[700px] text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="px-4 py-4 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Capability
                </th>
                {cols.map((col) => (
                  <th
                    key={col}
                    className={`px-4 py-4 text-center text-xs font-medium uppercase tracking-wider ${
                      col === "AegisAI"
                        ? "bg-aegis-emerald/5 text-aegis-emerald"
                        : "text-muted-foreground"
                    }`}
                  >
                    {col === "AegisAI" && (
                      <span className="mb-1 block text-[10px] font-semibold text-aegis-emerald">
                        MOST ADVANCED
                      </span>
                    )}
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {features.map((feature, i) => (
                <motion.tr
                  key={feature}
                  className="border-b border-border/50 transition-colors hover:bg-primary/[0.03]"
                  initial={{ opacity: 0, x: -20 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.04, duration: 0.3 }}
                >
                  <td className="px-4 py-3 text-muted-foreground">{feature}</td>
                  {cols.map((col) => (
                    <td
                      key={col}
                      className={`px-4 py-3 text-center ${
                        col === "AegisAI" ? "bg-aegis-emerald/5" : ""
                      }`}
                    >
                      <CellIcon value={competitors[col][i]} />
                    </td>
                  ))}
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>

        <motion.p
          className="mx-auto mt-8 max-w-2xl text-center text-base text-muted-foreground"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.5 }}
        >
          Trust scores quantify plan reliability across 10 dimensions. When a score
          drops below threshold, AegisAI's revision gate automatically re-plans —
          no human intervention required. This closed-loop system means your plans
          improve with every execution.
        </motion.p>
      </div>
    </section>
  );
};
