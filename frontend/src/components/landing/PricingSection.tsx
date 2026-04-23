import { motion } from "framer-motion";
import { useState } from "react";
import { Check } from "lucide-react";
import { Link } from "react-router-dom";
import { prefetchRegisterPage } from "@/utils/routePrefetch";

const plans = [
  {
    name: "Free",
    price: { monthly: 0, annual: 0 },
    features: ["10 goals/month", "All 6 agents", "7-day memory retention", "Community support"],
    cta: "Get Started Free",
    popular: false,
  },
  {
    name: "Pro",
    price: { monthly: 12, annual: 10 },
    features: ["Unlimited goals", "Semantic memory (forever)", "Ethics scanning", "Voice I/O", "Priority queue"],
    cta: "Start Pro",
    popular: true,
  },
  {
    name: "Team",
    price: { monthly: 49, annual: 39 },
    features: ["Everything in Pro", "Shared team memory", "Analytics dashboard", "API access"],
    cta: "Contact Us",
    popular: false,
  },
];

export const PricingSection = () => {
  const [annual, setAnnual] = useState(false);

  return (
    <section id="pricing" className="relative py-24 px-6">
      <div className="mx-auto max-w-5xl">
        <motion.div
          className="mb-12 text-center"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <h2 className="font-display text-3xl font-bold md:text-5xl">
            Simple, transparent <span className="text-primary">pricing.</span>
          </h2>
        </motion.div>

        {/* Toggle */}
        <div className="mb-12 flex items-center justify-center gap-3">
          <span className={`text-sm ${!annual ? "text-foreground" : "text-muted-foreground"}`}>Monthly</span>
          <button
            onClick={() => setAnnual(!annual)}
            className={`relative h-7 w-12 rounded-full transition-colors ${annual ? "bg-primary" : "bg-secondary"}`}
            aria-label="Toggle billing period"
          >
            <span
              className={`absolute top-0.5 left-0.5 h-6 w-6 rounded-full bg-foreground transition-transform ${
                annual ? "translate-x-5" : ""
              }`}
            />
          </button>
          <span className={`text-sm ${annual ? "text-foreground" : "text-muted-foreground"}`}>
            Annual
            {annual && <span className="ml-1 text-xs text-aegis-emerald">Save 20%</span>}
          </span>
        </div>

        <div className="grid gap-6 md:grid-cols-3">
          {plans.map((plan, i) => (
            <motion.div
              key={plan.name}
              className={`glass-card relative flex flex-col p-8 ${
                plan.popular ? "border-primary/40 shadow-[0_0_60px_hsla(239,84%,67%,0.12)]" : ""
              }`}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.15 }}
            >
              {plan.popular && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-primary px-3 py-1 text-xs font-medium text-primary-foreground">
                  Most Popular
                </span>
              )}
              <h3 className="text-lg font-semibold text-foreground">{plan.name}</h3>
              <div className="mt-4 mb-6">
                <span className="font-mono text-4xl font-bold text-foreground">
                  ${annual ? plan.price.annual : plan.price.monthly}
                </span>
                {plan.price.monthly > 0 && <span className="text-sm text-muted-foreground">/month</span>}
              </div>
              <ul className="mb-8 flex-1 space-y-3">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Check size={14} className="text-aegis-emerald flex-shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
              <Link
                to="/register"
                className={plan.popular ? "btn-primary text-center" : "btn-ghost text-center"}
                onMouseEnter={() => {
                  void prefetchRegisterPage();
                }}
                onFocus={() => {
                  void prefetchRegisterPage();
                }}
              >
                {plan.cta}
              </Link>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};
