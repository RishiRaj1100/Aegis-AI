import { useState } from "react";
import { motion } from "framer-motion";
import { Shield, Mail, ArrowLeft, Check, Lock, Eye, EyeOff } from "lucide-react";
import { Link } from "react-router-dom";
import { useEffect } from "react";
import { prefetchLoginPage } from "@/utils/routePrefetch";

const ForgotPassword = () => {
  const [state, setState] = useState<"email" | "sent" | "reset">("email");
  const [email, setEmail] = useState("");
  const [countdown, setCountdown] = useState(0);
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [success, setSuccess] = useState(false);

  // Check for token in URL
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("token")) setState("reset");
  }, []);

  // Countdown timer
  useEffect(() => {
    if (countdown <= 0) return;
    const t = setTimeout(() => setCountdown(countdown - 1), 1000);
    return () => clearTimeout(t);
  }, [countdown]);

  useEffect(() => {
    void prefetchLoginPage();
  }, []);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    setState("sent");
    setCountdown(60);
  };

  const handleReset = (e: React.FormEvent) => {
    e.preventDefault();
    setSuccess(true);
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-6">
      {/* Background glow */}
      <div className="pointer-events-none fixed inset-0">
        <div className="absolute left-1/2 top-1/2 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary/[0.06] blur-[120px]" />
      </div>

      <motion.div
        className="glass-card relative z-10 w-full max-w-md p-10"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        {/* Icon */}
        <div className="mb-6 flex justify-center">
          <motion.div
            className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10"
            animate={{ scale: [1, 1.05, 1] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            <Shield size={28} className="text-primary" />
          </motion.div>
        </div>

        {/* State: Email */}
        {state === "email" && (
          <div>
            <h1 className="text-center font-display text-2xl font-bold text-foreground">Reset your password</h1>
            <p className="mt-2 mb-8 text-center text-sm text-muted-foreground">
              Enter your email and we'll send a secure reset link.
            </p>
            <form onSubmit={handleSend} className="space-y-5">
              <div className="relative">
                <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="input-field !pl-10" placeholder="you@company.com" required />
              </div>
              <button type="submit" className="btn-primary w-full !py-3.5">Send Reset Link</button>
            </form>
            <Link
              to="/login"
              className="mt-6 flex items-center justify-center gap-2 text-sm text-muted-foreground hover:text-foreground"
              onMouseEnter={() => {
                void prefetchLoginPage();
              }}
              onFocus={() => {
                void prefetchLoginPage();
              }}
            >
              <ArrowLeft size={14} /> Back to Sign In
            </Link>
          </div>
        )}

        {/* State: Sent */}
        {state === "sent" && !success && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-aegis-emerald/10">
              <Check size={32} className="text-aegis-emerald" />
            </div>
            <h2 className="font-display text-2xl font-bold text-foreground">Check your inbox</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              We sent a reset link to <span className="text-foreground">{email}</span>. It expires in 15 minutes.
            </p>
            <div className="mt-8 flex flex-col gap-3">
              <a href="https://mail.google.com" target="_blank" rel="noopener" className="btn-ghost text-center">
                Open Gmail
              </a>
              <button
                onClick={() => setCountdown(60)}
                disabled={countdown > 0}
                className="btn-ghost disabled:opacity-50"
              >
                {countdown > 0 ? `Resend in ${countdown}s` : "Resend email"}
              </button>
            </div>
            <button onClick={() => setState("email")} className="mt-4 text-xs text-muted-foreground hover:text-foreground">
              Wrong email? Go back
            </button>
          </motion.div>
        )}

        {/* State: Reset */}
        {state === "reset" && !success && (
          <div>
            <h1 className="text-center font-display text-2xl font-bold text-foreground">Set new password</h1>
            <p className="mt-2 mb-8 text-center text-sm text-muted-foreground">Choose a strong password for your account.</p>
            <form onSubmit={handleReset} className="space-y-5">
              <div className="relative">
                <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <input type={showPw ? "text" : "password"} value={newPw} onChange={(e) => setNewPw(e.target.value)} className="input-field !pl-10 !pr-10" placeholder="New password" required />
                <button type="button" onClick={() => setShowPw(!showPw)} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground" aria-label="Toggle password">
                  {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              <div className="relative">
                <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <input type="password" value={confirmPw} onChange={(e) => setConfirmPw(e.target.value)} className="input-field !pl-10" placeholder="Confirm password" required />
              </div>
              <button type="submit" className="btn-primary w-full !py-3.5">Set New Password</button>
            </form>
          </div>
        )}

        {/* Success state */}
        {success && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-aegis-emerald/10">
              <Check size={32} className="text-aegis-emerald" />
            </div>
            <h2 className="font-display text-2xl font-bold text-foreground">Password updated!</h2>
            <p className="mt-2 text-sm text-muted-foreground">Redirecting to login...</p>
          </motion.div>
        )}
      </motion.div>
    </div>
  );
};

export default ForgotPassword;
