import { motion } from "framer-motion";

const useCases = [
  {
    title: "Startup Strategy",
    goal: "Launch a SaaS product in 90 days with a team of 3",
    trust: 78,
    subtasks: 7,
    flagged: 2,
    color: "border-primary/30",
  },
  {
    title: "Research & Analysis",
    goal: "Analyze market entry opportunities for electric vehicles in India",
    trust: 91,
    subtasks: 5,
    insights: 3,
    color: "border-aegis-cyan/30",
  },
  {
    title: "Personal Planning",
    goal: "Plan a career transition from software engineering to AI research",
    trust: 85,
    subtasks: 6,
    voice: true,
    color: "border-aegis-violet/30",
  },
];

export const UseCasesSection = () => {
  return (
    <section id="features" className="relative py-24 px-6">
      <div className="mx-auto max-w-6xl">
        <motion.div
          className="mb-16 text-center"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <h2 className="font-display text-3xl font-bold md:text-5xl">
            From goal to plan <span className="text-primary">in seconds.</span>
          </h2>
        </motion.div>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {useCases.map((uc, i) => (
            <motion.div
              key={uc.title}
              className={`glass-card flex flex-col p-6 ${uc.color}`}
              initial={{ opacity: 0, scale: 0.96 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.2, duration: 0.4 }}
              whileHover={{ y: -4 }}
            >
              <span className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                {uc.title}
              </span>
              <p className="mb-6 text-sm text-foreground leading-relaxed">"{uc.goal}"</p>

              <div className="mt-auto space-y-3 border-t border-border/50 pt-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Trust Score</span>
                  <span className={`font-mono text-sm font-semibold ${
                    uc.trust >= 85 ? "text-aegis-emerald" : "text-aegis-amber"
                  }`}>
                    {uc.trust}/100
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Subtasks</span>
                  <span className="font-mono text-sm text-foreground">{uc.subtasks}</span>
                </div>
                {uc.flagged && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">Flagged for review</span>
                    <span className="font-mono text-sm text-aegis-rose">{uc.flagged}</span>
                  </div>
                )}
                {uc.insights && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">Key insights</span>
                    <span className="font-mono text-sm text-aegis-cyan">{uc.insights}</span>
                  </div>
                )}
                {uc.voice && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">Voice output</span>
                    <span className="text-xs text-aegis-emerald">Enabled</span>
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};
