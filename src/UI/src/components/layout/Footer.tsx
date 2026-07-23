import { Link } from 'react-router-dom';
import { ExternalLink } from 'lucide-react';

function GithubIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      role="img"
      viewBox="0 0 24 24"
      fill="currentColor"
      {...props}
    >
      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
    </svg>
  );
}

export function Footer() {
  return (
    <footer className="mt-auto border-t border-border/80 bg-card py-6 text-xs text-muted-foreground">
      <div className="container mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex flex-col sm:flex-row items-center justify-center md:justify-start gap-3 text-center sm:text-left">
          <p>© 2026 TicketRadar. Continuous movie showtime monitoring.</p>
          <span className="hidden sm:inline text-border">|</span>
          <div className="flex items-center gap-3">
            <Link to="/instructions" className="hover:text-foreground transition-colors underline-offset-4 hover:underline font-medium">
              Instructions
            </Link>
            <span className="text-border">•</span>
            <Link to="/tc" className="hover:text-foreground transition-colors underline-offset-4 hover:underline font-medium">
              Terms & Conditions
            </Link>
            <span className="text-border">•</span>
            <Link to="/pp" className="hover:text-foreground transition-colors underline-offset-4 hover:underline font-medium">
              Privacy Policy
            </Link>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-center md:justify-end gap-4">
          <a
            href="https://github.com/Ashif4354/TicketRadar"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-muted/40 hover:bg-muted/80 text-foreground font-medium border border-border/60 transition-colors"
          >
            <GithubIcon className="h-4 w-4" />
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
