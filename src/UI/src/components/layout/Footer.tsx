import React from 'react';
import { Link } from 'react-router-dom';
import { Github, ExternalLink } from 'lucide-react';

export function Footer() {
  return (
    <footer className="mt-auto border-t border-border/80 bg-card py-6 text-xs text-muted-foreground">
      <div className="container mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex flex-col sm:flex-row items-center gap-3 text-center sm:text-left">
          <p>© 2026 TicketRadar. Continuous BookMyShow showtime monitoring.</p>
          <span className="hidden sm:inline text-border">|</span>
          <div className="flex items-center gap-3">
            <Link to="/tc" className="hover:text-foreground transition-colors underline-offset-4 hover:underline font-medium">
              Terms & Conditions
            </Link>
            <span className="text-border">•</span>
            <Link to="/pp" className="hover:text-foreground transition-colors underline-offset-4 hover:underline font-medium">
              Privacy Policy
            </Link>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-4">
          <a
            href="https://github.com/Ashif4354/TicketRadar"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-muted/40 hover:bg-muted/80 text-foreground font-medium border border-border/60 transition-colors"
          >
            <Github className="h-4 w-4" />
            <span>Ashif4354/TicketRadar</span>
            <ExternalLink className="h-3 w-3 opacity-60 ml-0.5" />
          </a>

          <div className="flex items-center gap-2 bg-muted/30 border border-border/50 px-3 py-1.5 rounded-lg font-medium text-foreground">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-muted-foreground">Status:</span>
            <span>Ready & Active</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
