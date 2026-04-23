import { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { ChevronDown, Play } from "lucide-react";
import { Link } from "react-router-dom";
import { prefetchRegisterPage } from "@/utils/routePrefetch";

const words = ["Plans.", "Researches.", "Decides."];

export const HeroSection = () => {
  return (
    <section className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-6 pt-16">
      {/* Mesh gradient blobs */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-1/4 top-1/3 h-[500px] w-[500px] rounded-full bg-primary/10 blur-[120px]" />
        <div className="absolute right-1/4 top-1/2 h-[400px] w-[400px] rounded-full bg-aegis-cyan/8 blur-[120px]" />
      </div>

      <div className="relative z-10 flex flex-col items-center text-center">
        {/* Pill badge */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mb-8 flex items-center gap-2 rounded-full border border-primary/30 bg-primary/5 px-4 py-1.5 text-sm text-primary"
        >
          <span className="inline-block h-2 w-2 animate-pulse-glow rounded-full bg-aegis-emerald" />
          Multi-Agent AI System · v2.0
        </motion.div>

        {/* Headline */}
        <motion.h1
          className="font-display text-5xl font-bold leading-tight tracking-tight md:text-7xl lg:text-8xl"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          <span className="block">AI That <span className="text-primary">Plans.</span></span>
          <motion.span
            className="block"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6, duration: 0.4 }}
          >
            <span className="text-aegis-cyan">Researches.</span>
          </motion.span>
          <motion.span
            className="block"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.0, duration: 0.4 }}
          >
            <span className="text-aegis-violet">Decides.</span>
          </motion.span>
        </motion.h1>

        {/* Subheadline */}
        <motion.p
          className="mt-6 max-w-xl text-lg text-muted-foreground md:text-xl"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.4, duration: 0.6 }}
        >
          AegisAI decomposes your goals into researched, trust-scored execution
          plans through a 6-agent autonomous pipeline — then learns from every outcome.
        </motion.p>

        {/* CTA buttons */}
        <motion.div
          className="mt-10 flex flex-col items-center gap-4 sm:flex-row"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.8, duration: 0.5 }}
        >
          <Link
            to="/register"
            className="btn-primary !px-8 !py-4 text-base"
            onMouseEnter={() => {
              void prefetchRegisterPage();
            }}
            onFocus={() => {
              void prefetchRegisterPage();
            }}
          >
            Start Planning Free
          </Link>
          <button className="btn-ghost flex items-center gap-2 !px-8 !py-4 text-base">
            <Play size={16} />
            See How It Works
          </button>
        </motion.div>

        {/* Floating pipeline mockup */}
        <motion.div
          className="mt-16 w-full max-w-3xl"
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 2.2, duration: 0.8 }}
        >
          <div className="animate-float glass-card p-6">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-sm font-medium text-foreground">Pipeline Progress</span>
              <span className="font-mono text-xs text-aegis-emerald">Active</span>
            </div>
            <div className="flex items-center gap-2 overflow-x-auto pb-2">
              {["Commander", "Research", "Execution", "Trust", "Memory", "Reflection"].map(
                (agent, i) => (
                  <div key={agent} className="flex items-center gap-2">
                    <div
                      className={`flex h-10 items-center gap-2 rounded-lg border px-4 text-sm whitespace-nowrap ${
                        i < 3
                          ? "border-aegis-emerald/30 bg-aegis-emerald/10 text-aegis-emerald"
                          : i === 3
                          ? "border-primary/30 bg-primary/10 text-primary animate-pulse-glow"
                          : "border-border bg-secondary text-muted-foreground"
                      }`}
                    >
                      <span className="font-mono text-xs">{String(i + 1).padStart(2, "0")}</span>
                      {agent}
                    </div>
                    {i < 5 && (
                      <div className={`h-px w-4 flex-shrink-0 ${i < 3 ? "bg-aegis-emerald/40" : "bg-border"}`} />
                    )}
                  </div>
                )
              )}
            </div>
          </div>
        </motion.div>

        {/* Scroll hint */}
        <motion.div
          className="mt-16 text-muted-foreground"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 2.8 }}
        >
          <ChevronDown size={24} className="animate-bounce-subtle" />
        </motion.div>
      </div>
    </section>
  );
};
