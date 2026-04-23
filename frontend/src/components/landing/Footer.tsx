import { Github, Twitter, Linkedin } from "lucide-react";

const footerLinks = {
  Product: ["Features", "How It Works", "Pricing", "Changelog"],
  Developers: ["API Docs", "GitHub", "Status Page"],
  Company: ["About", "Blog", "Privacy Policy", "Terms"],
};

export const Footer = () => {
  return (
    <footer className="border-t border-border px-6 py-16">
      <div className="mx-auto grid max-w-6xl gap-12 md:grid-cols-4">
        <div>
          <div className="mb-3 text-lg font-semibold">
            <span className="text-foreground">Aegis</span>
            <span className="text-primary">AI</span>
          </div>
          <p className="mb-4 text-sm text-muted-foreground">
            Trust-aware autonomous decision planning.
          </p>
          <div className="flex gap-3">
            <a href="#" className="text-muted-foreground transition-colors hover:text-foreground" aria-label="GitHub"><Github size={18} /></a>
            <a href="#" className="text-muted-foreground transition-colors hover:text-foreground" aria-label="Twitter"><Twitter size={18} /></a>
            <a href="#" className="text-muted-foreground transition-colors hover:text-foreground" aria-label="LinkedIn"><Linkedin size={18} /></a>
          </div>
        </div>
        {Object.entries(footerLinks).map(([category, links]) => (
          <div key={category}>
            <h4 className="mb-3 text-sm font-semibold text-foreground">{category}</h4>
            <ul className="space-y-2">
              {links.map((link) => (
                <li key={link}>
                  <a href="#" className="text-sm text-muted-foreground transition-colors hover:text-foreground">
                    {link}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="mx-auto mt-12 max-w-6xl border-t border-border pt-6 text-center text-xs text-muted-foreground">
        <p>© 2025 AegisAI. All rights reserved. Copyright by RR.</p>
        <p className="mt-1">Developed by RR · Built with Groq + Sarvam AI.</p>
      </div>
    </footer>
  );
};
