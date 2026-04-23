import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { User, Mail, Lock, Eye, EyeOff, Check } from "lucide-react";
import { Link } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/components/ui/use-toast";
import { APIError } from "@/services/api";
import { prefetchAppRoutesOnce, prefetchLoginPage } from "@/utils/routePrefetch";

const Register = () => {
  const { register, isLoading } = useAuth();
  const { toast } = useToast();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [agreed, setAgreed] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    prefetchAppRoutesOnce();
  }, []);

  const strength = (() => {
    let s = 0;
    if (password.length >= 8) s++;
    if (/[A-Z]/.test(password)) s++;
    if (/\d/.test(password)) s++;
    if (/[^A-Za-z0-9]/.test(password)) s++;
    return s;
  })();

  const strengthLabel = ["", "Weak", "Fair", "Good", "Strong"][strength] || "";
  const strengthColors = ["bg-secondary", "bg-aegis-rose", "bg-aegis-amber", "bg-primary", "bg-aegis-emerald"];

  const pwMatch = confirmPw.length > 0 && password === confirmPw;
  const pwMismatch = confirmPw.length > 0 && password !== confirmPw;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (password !== confirmPw) {
      setError("Passwords don't match");
      return;
    }

    if (!agreed) {
      setError("You must agree to the terms");
      return;
    }

    try {
      await register(name, email, password);
    } catch (err) {
      const message = err instanceof APIError ? err.detail : "Registration failed";
      setError(message);
      toast({
        title: "Registration Failed",
        description: message,
        variant: "destructive",
      });
    }
  };

  const checks = [
    { label: "8+ characters", met: password.length >= 8 },
    { label: "One uppercase", met: /[A-Z]/.test(password) },
    { label: "One number", met: /\d/.test(password) },
    { label: "One symbol", met: /[^A-Za-z0-9]/.test(password) },
  ];

  return (
    <div className="flex min-h-screen">
      {/* Left — brand panel */}
      <div className="hidden flex-1 items-center justify-center bg-card lg:flex">
        <div className="relative w-full max-w-sm px-8">
          <div className="absolute -inset-20 bg-gradient-to-br from-primary/8 to-aegis-cyan/5 blur-3xl rounded-full" />
          <div className="relative">
            <div className="mb-8">
              <span className="text-lg font-semibold text-foreground">Aegis</span>
              <span className="text-lg font-semibold text-primary">AI</span>
            </div>
            <div className="glass-card p-6">
              <p className="text-sm text-foreground italic leading-relaxed">
                "The trust score alone changed how we present plans to clients."
              </p>
              <div className="mt-4 flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/20 text-xs font-medium text-primary">
                  SK
                </div>
                <div>
                  <p className="text-xs font-medium text-foreground">Sarah Kim</p>
                  <p className="text-xs text-muted-foreground">Strategy Lead, Nexus Co</p>
                </div>
              </div>
            </div>
            <p className="mt-8 text-sm text-muted-foreground">
              Join <span className="text-foreground font-medium">4,200+</span> planners using AegisAI
            </p>
            <div className="mt-3 flex -space-x-2">
              {["bg-primary", "bg-aegis-cyan", "bg-aegis-violet", "bg-aegis-emerald", "bg-aegis-amber"].map((c, i) => (
                <div key={i} className={`flex h-8 w-8 items-center justify-center rounded-full border-2 border-card text-[10px] font-medium text-foreground ${c}`}>
                  {["JD", "AK", "ML", "RW", "TS"][i]}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Right — form */}
      <div className="flex flex-1 items-center justify-center px-6 py-12">
        <motion.div
          className="w-full max-w-md"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
        >
          <Link to="/" className="mb-12 inline-block text-lg font-semibold lg:hidden">
            <span className="text-foreground">Aegis</span>
            <span className="text-primary">AI</span>
          </Link>

          <h1 className="font-display text-3xl font-bold text-foreground">Create your account</h1>
          <p className="mt-2 mb-8 text-sm text-muted-foreground">Start your first mission in 30 seconds</p>

          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-6 rounded-lg border border-aegis-rose/30 bg-aegis-rose/10 p-3 text-sm text-aegis-rose"
            >
              {error}
            </motion.div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-muted-foreground">Full Name</label>
              <div className="relative">
                <User size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <input type="text" value={name} onChange={(e) => setName(e.target.value)} className="input-field !pl-10" placeholder="Jane Doe" required minLength={2} />
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-muted-foreground">Email</label>
              <div className="relative">
                <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="input-field !pl-10" placeholder="you@company.com" required />
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-muted-foreground">Password</label>
              <div className="relative">
                <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <input type={showPw ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)} className="input-field !pl-10 !pr-10" placeholder="••••••••" required />
                <button type="button" onClick={() => setShowPw(!showPw)} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground" aria-label="Toggle password">
                  {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {/* Strength meter */}
              {password.length > 0 && (
                <div className="mt-2">
                  <div className="flex gap-1">
                    {[1, 2, 3, 4].map((i) => (
                      <div key={i} className={`h-1 flex-1 rounded-full transition-colors ${strength >= i ? strengthColors[strength] : "bg-secondary"}`} />
                    ))}
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">{strengthLabel}</p>
                  <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
                    {checks.map((c) => (
                      <span key={c.label} className={`flex items-center gap-1 text-xs transition-colors ${c.met ? "text-aegis-emerald" : "text-muted-foreground"}`}>
                        <Check size={10} /> {c.label}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-muted-foreground">Confirm Password</label>
              <div className="relative">
                <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="password"
                  value={confirmPw}
                  onChange={(e) => setConfirmPw(e.target.value)}
                  className={`input-field !pl-10 ${pwMatch ? "!border-aegis-emerald/50" : ""} ${pwMismatch ? "!border-aegis-rose/50" : ""}`}
                  placeholder="••••••••"
                  required
                />
              </div>
              {pwMismatch && <p className="mt-1 text-xs text-aegis-rose">Passwords don't match</p>}
            </div>

            <div className="my-6 flex items-center gap-3">
              <div className="h-px flex-1 bg-border" />
              <span className="text-xs text-muted-foreground">OR</span>
              <div className="h-px flex-1 bg-border" />
            </div>

            <label className="flex items-start gap-3 cursor-pointer">
              <input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} className="mt-0.5 h-4 w-4 rounded border-border accent-primary" />
              <span className="text-xs text-muted-foreground">
                I agree to the <a href="#" className="text-primary hover:underline">Terms of Service</a> and{" "}
                <a href="#" className="text-primary hover:underline">Privacy Policy</a>
              </span>
            </label>

            <button type="submit" className="btn-primary w-full !py-3.5" disabled={isLoading || !agreed}>
              {isLoading ? "Creating account..." : "Create Account"}
            </button>
          </form>

          <p className="mt-8 text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link
              to="/login"
              className="text-primary hover:underline"
              onMouseEnter={() => {
                void prefetchLoginPage();
              }}
              onFocus={() => {
                void prefetchLoginPage();
              }}
            >
              Sign in
            </Link>
          </p>
        </motion.div>
      </div>
    </div>
  );
};

export default Register;
