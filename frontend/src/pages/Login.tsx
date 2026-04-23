import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Mail, Lock, Eye, EyeOff } from "lucide-react";
import { Link } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/components/ui/use-toast";
import { APIError } from "@/services/api";
import {
  prefetchAppRoutesOnce,
  prefetchForgotPasswordPage,
  prefetchRegisterPage,
} from "@/utils/routePrefetch";

const Login = () => {
  const { login, isLoading } = useAuth();
  const { toast } = useToast();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    prefetchAppRoutesOnce();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!email || !password) {
      setError("Please fill in all fields");
      return;
    }

    try {
      await login(email, password);
    } catch (err) {
      const message = err instanceof APIError ? err.detail : "Login failed";
      setError(message);
      toast({
        title: "Login Failed",
        description: message,
        variant: "destructive",
      });
    }
  };

  return (
    <div className="flex min-h-screen">
      {/* Left — form */}
      <div className="flex flex-1 items-center justify-center px-6 py-12">
        <motion.div
          className="w-full max-w-md"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
        >
          <Link to="/" className="mb-12 inline-block text-lg font-semibold">
            <span className="text-foreground">Aegis</span>
            <span className="text-primary">AI</span>
          </Link>

          <h1 className="font-display text-3xl font-bold text-foreground">Welcome back</h1>
          <p className="mt-2 mb-8 text-sm text-muted-foreground">Continue where you left off</p>

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
              <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-muted-foreground">Email</label>
              <div className="relative">
                <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input-field !pl-10"
                  placeholder="you@company.com"
                  required
                />
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-muted-foreground">Password</label>
              <div className="relative">
                <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <input
                  type={showPw ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-field !pl-10 !pr-10"
                  placeholder="••••••••"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  aria-label="Toggle password visibility"
                >
                  {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              <div className="mt-1.5 text-right">
                <Link
                  to="/forgot-password"
                  className="text-xs text-primary hover:underline"
                  onMouseEnter={() => {
                    void prefetchForgotPasswordPage();
                  }}
                  onFocus={() => {
                    void prefetchForgotPasswordPage();
                  }}
                >
                  Forgot password?
                </Link>
              </div>
            </div>

            <button type="submit" className="btn-primary w-full !py-3.5" disabled={isLoading}>
              {isLoading ? "Signing in..." : "Sign In"}
            </button>
          </form>

          <div className="my-6 flex items-center gap-3">
            <div className="h-px flex-1 bg-border" />
            <span className="text-xs text-muted-foreground">OR</span>
            <div className="h-px flex-1 bg-border" />
          </div>

          <p className="text-center text-sm text-muted-foreground">
            Don't have an account?{" "}
            <Link
              to="/register"
              className="text-primary hover:underline font-semibold"
              onMouseEnter={() => {
                void prefetchRegisterPage();
              }}
              onFocus={() => {
                void prefetchRegisterPage();
              }}
            >
              Sign up
            </Link>
          </p>
        </motion.div>
      </div>

      {/* Right — asset */}
      <div className="hidden flex-1 items-center justify-center bg-gradient-to-br from-primary/10 to-aegis-cyan/10 lg:flex">
        <div className="relative max-w-sm">
          <div className="absolute -inset-20 bg-gradient-to-br from-primary/20 to-aegis-cyan/20 blur-3xl" />
          <div className="relative">
            <div className="text-center">
              <p className="text-lg font-semibold text-foreground mb-2">Ready to plan with confidence?</p>
              <p className="text-sm text-muted-foreground max-w-xs">
                AegisAI helps you decompose goals, assess risk, and execute with trust.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
