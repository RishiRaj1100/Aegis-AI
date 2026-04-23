import { motion, useInView } from "framer-motion";
import { useRef, useEffect, useState } from "react";

const dimensions = [
  { name: "Feasibility", value: 88, color: "bg-aegis-emerald" },
  { name: "Clarity", value: 92, color: "bg-aegis-emerald" },
  { name: "Risk", value: 65, color: "bg-aegis-amber" },
  { name: "Resources", value: 78, color: "bg-aegis-emerald" },
  { name: "Novelty", value: 45, color: "bg-aegis-amber" },
  { name: "Ethics", value: 95, color: "bg-aegis-emerald" },
];

const AnimatedCounter = ({ target, inView }: { target: number; inView: boolean }) => {
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (!inView) return;
    let start = 0;
    const duration = 1500;
    const startTime = performance.now();
    const animate = (now: number) => {
      const progress = Math.min((now - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(Math.round(eased * target));
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [inView, target]);
  return <>{count}</>;
};

export const TrustScoreSection = () => {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section className="relative py-24 px-6">
      <div className="mx-auto max-w-6xl">
        <motion.div
          className="mb-16 text-center"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <h2 className="font-display text-3xl font-bold md:text-5xl">
            Plans you can actually <span className="text-aegis-emerald">trust.</span>
          </h2>
        </motion.div>

        <div className="grid items-center gap-16 lg:grid-cols-2" ref={ref}>
          {/* Left — explanation */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <h3 className="mb-4 text-xl font-semibold text-foreground">What the trust score measures</h3>
            <p className="mb-6 text-muted-foreground leading-relaxed">
              Every plan produced by AegisAI is scored across 10 dimensions — from
              feasibility and risk assessment to ethical alignment. The composite
              trust score gives you a single number that represents plan quality.
            </p>
            <h3 className="mb-4 text-xl font-semibold text-foreground">The revision gate</h3>
            <p className="mb-6 text-muted-foreground leading-relaxed">
              When a score falls below your configured threshold, AegisAI's
              revision gate kicks in automatically — re-planning with refined
              constraints until the score meets your standards.
            </p>
            <h3 className="mb-4 text-xl font-semibold text-foreground">Continuous calibration</h3>
            <p className="text-muted-foreground leading-relaxed">
              As you provide feedback on outcomes, the trust model calibrates
              itself. Over time, scores become increasingly accurate predictors
              of real-world plan success.
            </p>
          </motion.div>

          {/* Right — animated trust score card */}
          <motion.div
            className="flex justify-center"
            initial={{ opacity: 0, x: 30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <div className="glass-card w-full max-w-sm p-8">
              {/* Circular score */}
              <div className="mb-8 flex justify-center">
                <div className="relative flex h-44 w-44 items-center justify-center">
                  <svg className="absolute inset-0 -rotate-90" viewBox="0 0 180 180">
                    <circle
                      cx="90" cy="90" r="80"
                      fill="none"
                      stroke="hsla(0, 0%, 100%, 0.05)"
                      strokeWidth="8"
                    />
                    <motion.circle
                      cx="90" cy="90" r="80"
                      fill="none"
                      stroke="hsl(160, 84%, 39%)"
                      strokeWidth="8"
                      strokeLinecap="round"
                      strokeDasharray={502}
                      initial={{ strokeDashoffset: 502 }}
                      animate={inView ? { strokeDashoffset: 502 - (502 * 82) / 100 } : {}}
                      transition={{ duration: 1.5, ease: "easeOut" }}
                    />
                  </svg>
                  <div className="text-center">
                    <span className="font-mono text-4xl font-bold text-foreground">
                      <AnimatedCounter target={82} inView={inView} />
                    </span>
                    <span className="block text-xs text-muted-foreground mt-1">Trust Score</span>
                  </div>
                </div>
              </div>

              {/* Dimension bars */}
              <div className="space-y-3">
                {dimensions.map((dim, i) => (
                  <div key={dim.name}>
                    <div className="mb-1 flex justify-between text-xs">
                      <span className="text-muted-foreground">{dim.name}</span>
                      <span className="font-mono text-foreground">{dim.value}</span>
                    </div>
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-secondary">
                      <motion.div
                        className={`h-full rounded-full ${dim.color}`}
                        initial={{ width: 0 }}
                        animate={inView ? { width: `${dim.value}%` } : {}}
                        transition={{ duration: 0.8, delay: 0.3 + i * 0.1 }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
};
