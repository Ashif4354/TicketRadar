import { useNavigate } from 'react-router-dom';
import { Radar, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function LandingPage() {
  const navigate = useNavigate();

  const handleGetStarted = () => {
    navigate('/app');
  };

  return (
    <main className="flex-1 flex flex-col items-center justify-center px-4 py-16 text-center max-w-4xl mx-auto z-10">
      <div className="absolute inset-0 z-0 flex items-center justify-center opacity-[0.02] pointer-events-none select-none">
        <Radar className="h-[600px] w-[600px] animate-pulse" />
      </div>

      <div className="z-10 space-y-8 relative">
        <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight leading-tight">
          Movie Ticket Tracking,<br />
          <span className="bg-gradient-to-r from-rose-400 via-pink-500 to-rose-600 bg-clip-text text-transparent">
            Automated & Instant
          </span>
        </h1>
        
        <p className="text-sm sm:text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed">
          Tired of checking BookMyShow every hour? TicketRadar automatically checks ticket availability for you and sends instant alerts to your Email or Discord the moment tickets open for your movie and cinema.
        </p>

        <div className="flex flex-col items-center justify-center gap-3 pt-4">
          <Button
            onClick={handleGetStarted}
            size="lg"
            className="h-13 px-8 text-sm font-bold bg-gradient-to-r from-rose-500 to-pink-500 hover:from-rose-600 hover:to-pink-600 text-white shadow-xl shadow-rose-500/25 gap-2 group cursor-pointer rounded-xl"
          >
            Get Started
            <Radar className="h-4.5 w-4.5 group-hover:animate-ping" />
          </Button>
          <a
            href="https://in.bookmyshow.com"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground font-semibold py-1.5 px-4 transition-colors"
          >
            Supported Booking Provider: BookMyShow
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-12 max-w-3xl mx-auto text-left">
          <div className="bg-card border border-border/80 p-5 rounded-xl space-y-2 glassmorphism hover:border-rose-500/20 transition-all duration-300">
            <div className="h-9 w-9 rounded-lg bg-rose-500/10 text-rose-400 flex items-center justify-center font-bold">1</div>
            <h3 className="font-bold text-sm text-foreground">Automatic Ticket Checking</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Provide your movie link, date, and preferred Theatres/Cinemas. TicketRadar checks for open seats every few seconds.
            </p>
          </div>

          <div className="bg-card border border-border/80 p-5 rounded-xl space-y-2 glassmorphism hover:border-rose-500/20 transition-all duration-300">
            <div className="h-9 w-9 rounded-lg bg-pink-500/10 text-pink-400 flex items-center justify-center font-bold">2</div>
            <h3 className="font-bold text-sm text-foreground">Instant Notifications</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Get notified immediately on Email or Discord the exact second tickets go on sale.
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
