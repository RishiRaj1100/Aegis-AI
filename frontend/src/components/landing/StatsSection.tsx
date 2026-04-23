import { motion, useInView } from "framer-motion";
import { useRef, useState, useEffect } from "react";
import { Zap, Radio, BarChart3, Globe } from "lucide-react";

const AnimatedCount = ({ target, inView }: { target: number; inView: boolean }) => {
  const [val, setVal] = useState(0);
  useEffect(() => {
    if (!inView) return;
    const dur = 1200;
    const start = performance.now();
    const tick = (now: number) => {
      const p = Math.min((now - start) / dur, 1);
      setVal(Math.round((1 - Math.pow(1 - p, 3)) * target));
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, [inView, target]);
  return <>{val}</>;
};

const stats = [
  { label: "Autonomous Agents", value: 6, icon: Zap, color: "text-primary" },
  { label: "Real-time via SSE", value: null, icon: Radio, color: "text-aegis-cyan" },
  { label: "Trust Dimensions", value: 10, icon: BarChart3, color: "text-aegis-emerald" },
  { label: "Multilingual Voice I/O", value: null, icon: Globe, color: "text-aegis-violet" },
];

export const StatsSection = () => {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true });

  return (
    <section className="py-16 px-6" ref={ref}>
      <div className="mx-auto grid max-w-5xl grid-cols-2 gap-4 md:grid-cols-4">
        {stats.map((s, i) => (
          <motion.div
            key={s.label}
            className="glass-card flex flex-col items-center p-6 text-center"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.1 }}
          >
            <s.icon size={24} className={`mb-3 ${s.color}`} />
            <span className="font-mono text-3xl font-bold text-foreground">
              {s.value ? <AnimatedCount target={s.value} inView={inView} /> : "∞"}
            </span>
            <span className="mt-1 text-xs text-muted-foreground">{s.label}</span>
          </motion.div>
        ))}
      </div>
    </section>
  );
};
