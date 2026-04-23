import { motion } from "framer-motion";
import { Cpu, Search, Zap, Shield, Database, RotateCcw } from "lucide-react";

const agents = [
  { name: "Commander", desc: "Decomposes goals into structured subtasks", icon: Cpu, color: "text-primary" },
  { name: "Research", desc: "Gathers data and validates assumptions", icon: Search, color: "text-aegis-cyan" },
  { name: "Execution", desc: "Generates actionable plans per subtask", icon: Zap, color: "text-aegis-amber" },
  { name: "Trust", desc: "Scores plan feasibility across 10 dimensions", icon: Shield, color: "text-aegis-emerald" },
  { name: "Memory", desc: "Stores context for cross-session learning", icon: Database, color: "text-aegis-violet" },
  { name: "Reflection", desc: "Learns from outcomes to improve future plans", icon: RotateCcw, color: "text-aegis-rose" },
];

export const HowItWorksSection = () => {
  return (
    <section id="how-it-works" className="relative py-24 px-6">
      <div className="mx-auto max-w-6xl">
        <motion.div
          className="mb-16 text-center"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <h2 className="font-display text-3xl font-bold md:text-5xl">
            Six agents. <span className="text-primary">One coherent decision.</span>
          </h2>
        </motion.div>

        {/* Desktop: horizontal timeline */}
        <div className="hidden lg:block">
          <div className="flex items-start justify-between">
            {agents.map((agent, i) => (
              <motion.div
                key={agent.name}
                className="flex flex-1 flex-col items-center text-center"
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.15, duration: 0.4 }}
              >
                <div className="relative">
                  <div className="glass-card flex h-16 w-16 items-center justify-center rounded-2xl">
                    <agent.icon size={24} className={agent.color} />
                  </div>
                  <span className="absolute -top-2 -right-2 flex h-6 w-6 items-center justify-center rounded-full bg-primary text-[11px] font-mono font-medium text-primary-foreground">
                    {i + 1}
                  </span>
                </div>
                {/* Connector */}
                {i < 5 && (
                  <div className="absolute" style={{ display: "none" }} />
                )}
                <h3 className="mt-4 text-sm font-semibold text-foreground">{agent.name}</h3>
                <p className="mt-1 max-w-[140px] text-xs text-muted-foreground">{agent.desc}</p>
              </motion.div>
            ))}
          </div>
          {/* Connector line */}
          <div className="relative mx-auto mt-[-52px] mb-8 flex max-w-[85%] items-center px-8" style={{ zIndex: -1 }}>
            <div className="h-px w-full bg-gradient-to-r from-primary/40 via-aegis-cyan/30 to-aegis-rose/40" />
          </div>
        </div>

        {/* Mobile: vertical stack */}
        <div className="flex flex-col gap-4 lg:hidden">
          {agents.map((agent, i) => (
            <motion.div
              key={agent.name}
              className="glass-card flex items-center gap-4 p-4"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
            >
              <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl bg-primary/10">
                <agent.icon size={20} className={agent.color} />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs text-primary">{String(i + 1).padStart(2, "0")}</span>
                  <span className="text-sm font-semibold text-foreground">{agent.name}</span>
                </div>
                <p className="text-xs text-muted-foreground">{agent.desc}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};
