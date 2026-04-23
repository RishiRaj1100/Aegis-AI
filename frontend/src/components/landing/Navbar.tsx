import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Menu, X } from "lucide-react";
import { Link } from "react-router-dom";
import { prefetchLoginPage, prefetchRegisterPage } from "@/utils/routePrefetch";

const navLinks = ["Features", "How It Works", "Compare", "Pricing"];

export const Navbar = () => {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 60);
    window.addEventListener("scroll", handler, { passive: true });
    return () => window.removeEventListener("scroll", handler);
  }, []);

  const scrollTo = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
    setMobileOpen(false);
  };

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? "border-b border-border bg-background/80 backdrop-blur-xl"
          : "bg-transparent"
      }`}
    >
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-0.5 text-lg font-semibold tracking-tight">
          <span className="text-foreground">Aegis</span>
          <span className="text-primary">AI</span>
        </Link>

        {/* Center links — desktop */}
        <div className="hidden items-center gap-8 md:flex">
          {navLinks.map((link) => (
            <button
              key={link}
              onClick={() => scrollTo(link.toLowerCase().replace(/\s+/g, "-"))}
              className="text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              {link}
            </button>
          ))}
        </div>

        {/* Right actions */}
        <div className="hidden items-center gap-3 md:flex">
          <Link
            to="/login"
            className="btn-ghost !py-2 !px-5 text-sm"
            onMouseEnter={() => {
              void prefetchLoginPage();
            }}
            onFocus={() => {
              void prefetchLoginPage();
            }}
          >
            Sign In
          </Link>
          <Link
            to="/register"
            className="btn-primary !py-2 !px-5 text-sm"
            onMouseEnter={() => {
              void prefetchRegisterPage();
            }}
            onFocus={() => {
              void prefetchRegisterPage();
            }}
          >
            Get Started
          </Link>
        </div>

        {/* Mobile hamburger */}
        <button
          className="text-muted-foreground md:hidden"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label="Toggle menu"
        >
          {mobileOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {/* Mobile drawer */}
      {mobileOpen && (
        <motion.div
          initial={{ opacity: 0, x: "100%" }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: "100%" }}
          transition={{ duration: 0.3 }}
          className="fixed inset-0 top-16 z-40 flex flex-col gap-2 border-t border-border bg-background p-6 md:hidden"
        >
          {navLinks.map((link) => (
            <button
              key={link}
              onClick={() => scrollTo(link.toLowerCase().replace(/\s+/g, "-"))}
              className="py-3 text-left text-lg text-muted-foreground transition-colors hover:text-foreground"
            >
              {link}
            </button>
          ))}
          <div className="mt-4 flex flex-col gap-3">
            <Link
              to="/login"
              className="btn-ghost text-center"
              onTouchStart={() => {
                void prefetchLoginPage();
              }}
            >
              Sign In
            </Link>
            <Link
              to="/register"
              className="btn-primary text-center"
              onTouchStart={() => {
                void prefetchRegisterPage();
              }}
            >
              Get Started
            </Link>
          </div>
        </motion.div>
      )}
    </nav>
  );
};
