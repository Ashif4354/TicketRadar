import { useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  ArrowLeft, 
  BookOpen, 
  ExternalLink, 
  Globe, 
  Ticket, 
  Calendar, 
  Building2, 
  Bell, 
  Clock, 
  Sparkles,
  AlertCircle,
  ChevronRight,
  MousePointerClick
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface ProviderMeta {
  id: string;
  name: string;
  shortName: string;
  status: 'Active' | 'Coming Soon';
  description: string;
  website: string;
}

const PROVIDERS: ProviderMeta[] = [
  {
    id: 'bookmyshow',
    name: 'BookMyShow (BMS)',
    shortName: 'BookMyShow',
    status: 'Active',
    description: 'India\'s largest online movie ticket booking platform.',
    website: 'https://in.bookmyshow.com'
  },
  {
    id: 'district',
    name: 'District (by Zomato)',
    shortName: 'District',
    status: 'Coming Soon',
    description: 'Popular movie and event ticketing platform.',
    website: 'https://district.in'
  },
  {
    id: 'pvr',
    name: 'PVR INOX Official',
    shortName: 'PVR INOX',
    status: 'Coming Soon',
    description: 'Direct booking system for PVR & INOX multiplex chains.',
    website: 'https://www.pvrcinemas.com'
  }
];

export function InstructionsPage() {
  const { hash } = useLocation();

  useEffect(() => {
    if (hash) {
      const targetId = hash.replace('#', '');
      const element = document.getElementById(targetId);
      if (element) {
        // Small delay to ensure render complete
        setTimeout(() => {
          element.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
      }
    } else {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }, [hash]);

  const scrollToSection = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
      window.history.pushState(null, '', `#${id}`);
    }
  };

  return (
    <main className="flex-1 container mx-auto max-w-4xl px-4 py-8 sm:px-6">
      {/* Navigation Top Bar */}
      <div className="mb-6 flex items-center justify-between">
        <Link 
          to="/app" 
          className="inline-flex items-center gap-2 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors bg-muted/30 hover:bg-muted/60 px-3.5 py-2 rounded-xl border border-border/50 shadow-sm"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Dashboard
        </Link>

        <Badge className="bg-rose-500/10 text-rose-400 border border-rose-500/20 text-xs font-semibold px-3 py-1 rounded-full flex items-center gap-1.5">
          <BookOpen className="h-3.5 w-3.5" />
          User Guide & Setup Instructions
        </Badge>
      </div>

      <Card className="border border-border/80 shadow-2xl glassmorphism glow-primary p-6 sm:p-10 rounded-2xl space-y-8">
        
        {/* Header Header Banner */}
        <CardHeader className="p-0 border-b border-border/60 pb-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1.5">
              <div className="flex items-center gap-2">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-rose-500 to-pink-500 text-white shadow-md shadow-rose-500/20">
                  <BookOpen className="h-5 w-5" />
                </div>
                <div>
                  <CardTitle className="text-2xl sm:text-3xl font-extrabold tracking-tight">
                    Booking Platform Instructions
                  </CardTitle>
                  <CardDescription className="text-xs text-muted-foreground mt-0.5">
                    Step-by-step guides on how to configure ticket alerts for each booking provider
                  </CardDescription>
                </div>
              </div>
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-0 space-y-10">

          {/* Table of Contents / Index Section */}
          <section className="bg-muted/20 border border-border/60 rounded-2xl p-5 sm:p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-border/40 pb-3">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-rose-400" />
                <h2 className="text-sm font-bold uppercase tracking-wider text-foreground">
                  Index / Quick Navigation
                </h2>
              </div>
              <span className="text-[11px] text-muted-foreground font-medium">
                {PROVIDERS.length} Providers Listed
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {PROVIDERS.map((provider) => (
                <button
                  key={provider.id}
                  onClick={() => scrollToSection(provider.id)}
                  className={`flex flex-col justify-between text-left p-3.5 rounded-xl border transition-all cursor-pointer group ${
                    provider.status === 'Active'
                      ? 'bg-card/80 border-border hover:border-rose-500/50 hover:shadow-lg hover:shadow-rose-500/5'
                      : 'bg-muted/10 border-border/40 opacity-70 hover:opacity-100'
                  }`}
                >
                  <div className="flex items-center justify-between w-full mb-2">
                    <span className="font-bold text-xs text-foreground group-hover:text-rose-400 transition-colors flex items-center gap-1.5">
                      {provider.shortName}
                      <ChevronRight className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </span>
                    {provider.status === 'Active' ? (
                      <Badge className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-bold px-2 py-0.5">
                        Active
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="text-[10px] text-muted-foreground border-border/60 px-2 py-0.5">
                        Soon
                      </Badge>
                    )}
                  </div>
                  <p className="text-[11px] text-muted-foreground line-clamp-2 leading-relaxed">
                    {provider.description}
                  </p>
                </button>
              ))}
            </div>
          </section>

          {/* SECTION 1: BOOKMYSHOW (BMS) INSTRUCTIONS */}
          <section 
            id="bookmyshow" 
            className="scroll-mt-24 sm:scroll-mt-28 space-y-6 pt-2 border-t border-border/40"
          >
            {/* Section Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-gradient-to-r from-rose-500/10 via-rose-500/5 to-transparent border border-rose-500/20 p-4 sm:p-5 rounded-2xl">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-xl bg-rose-500 text-white flex items-center justify-center font-bold text-base shadow-md shadow-rose-500/20 shrink-0">
                  BMS
                </div>
                <div>
                  <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
                    BMS (BookMyShow) Instructions
                  </h2>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    How to capture the correct URL and theatre names from BookMyShow
                  </p>
                </div>
              </div>

              <a
                href="https://in.bookmyshow.com"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-rose-400 hover:text-rose-300 bg-rose-500/10 hover:bg-rose-500/20 px-3.5 py-2 rounded-xl border border-rose-500/30 transition-all self-start sm:self-auto shrink-0"
              >
                <span>Visit BookMyShow</span>
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </div>

            {/* Step-by-Step Instructions */}
            <div className="space-y-4">
              
              {/* Step 1 */}
              <div className="bg-card border border-border/70 rounded-xl p-4 sm:p-5 flex gap-4 transition-all hover:border-border">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-rose-500/10 text-rose-400 font-bold text-sm border border-rose-500/20">
                  1
                </div>
                <div className="space-y-1.5 flex-1">
                  <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                    <Globe className="h-4 w-4 text-rose-400" />
                    Open BookMyShow & Pick Movie
                  </h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    First, visit the official BookMyShow website (<a href="https://in.bookmyshow.com" target="_blank" rel="noopener noreferrer" className="text-rose-400 hover:underline">in.bookmyshow.com</a>). Search for and click on the movie you want to watch, then click on the <strong className="text-foreground font-semibold">"Book Now"</strong> button.
                  </p>
                </div>
              </div>

              {/* Step 2 */}
              <div className="bg-card border border-border/70 rounded-xl p-4 sm:p-5 flex gap-4 transition-all hover:border-border">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-rose-500/10 text-rose-400 font-bold text-sm border border-rose-500/20">
                  2
                </div>
                <div className="space-y-1.5 flex-1">
                  <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                    <Building2 className="h-4 w-4 text-rose-400" />
                    Proceed to Theatres Listing Page
                  </h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Proceed to the theatres/cinemas listing page where available showtimes and theatre lists are displayed.
                  </p>
                </div>
              </div>

              {/* Step 3 */}
              <div className="bg-card border border-border/70 rounded-xl p-4 sm:p-5 flex gap-4 transition-all hover:border-border">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-rose-500/10 text-rose-400 font-bold text-sm border border-rose-500/20">
                  3
                </div>
                <div className="space-y-1.5 flex-1">
                  <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                    <Ticket className="h-4 w-4 text-rose-400" />
                    Select Booking Format / Type
                  </h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    On the theatre listing page, select the specific type/format of booking you need like (<strong className="text-foreground font-semibold">English 2D</strong>, <strong className="text-foreground font-semibold">English 3D</strong>, <strong className="text-foreground font-semibold">Tamil 2D</strong>, <strong className="text-foreground font-semibold">IMAX</strong>, <strong className="text-foreground font-semibold">EPIQ</strong>, etc.).
                  </p>
                </div>
              </div>

              {/* Step 4 */}
              <div className="bg-card border border-border/70 rounded-xl p-4 sm:p-5 flex gap-4 transition-all hover:border-border">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-rose-500/10 text-rose-400 font-bold text-sm border border-rose-500/20">
                  4
                </div>
                <div className="space-y-2 flex-1">
                  <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                    <Globe className="h-4 w-4 text-rose-400" />
                    Copy the URL from Address Bar
                  </h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Now copy the full URL directly from your browser's address bar. This is the exact URL you will provide to TicketRadar in the <strong className="text-foreground font-semibold">Movie Ticket Page Link</strong> input field.
                  </p>
                  <div className="bg-muted/30 border border-border/60 rounded-lg p-2.5 text-[11px] font-mono text-rose-300 break-all select-all flex items-center justify-between">
                    <span>Example: https://in.bookmyshow.com/buytickets/avatar-fire-and-ash-chennai/movie-chen-ET00392811-MT/20260724</span>
                  </div>
                </div>
              </div>

              {/* Step 5 */}
              <div className="bg-card border border-border/70 rounded-xl p-4 sm:p-5 flex gap-4 transition-all hover:border-border">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-rose-500/10 text-rose-400 font-bold text-sm border border-rose-500/20">
                  5
                </div>
                <div className="space-y-1.5 flex-1">
                  <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-rose-400" />
                    Select Target Date
                  </h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    In TicketRadar, select the target show date you want us to monitor.
                  </p>
                </div>
              </div>

              {/* Step 6 */}
              <div className="bg-card border border-border/70 rounded-xl p-4 sm:p-5 flex gap-4 transition-all hover:border-border">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-rose-500/10 text-rose-400 font-bold text-sm border border-rose-500/20">
                  6
                </div>
                <div className="space-y-2 flex-1">
                  <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                    <Building2 className="h-4 w-4 text-rose-400" />
                    Provide Preferred Theatre Names (Case-Sensitive)
                  </h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Provide the list of theatres/cinemas you want to look for.
                  </p>
                  <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200 space-y-1">
                    <div className="font-semibold flex items-center gap-1.5 text-amber-300">
                      <AlertCircle className="h-4 w-4 shrink-0" />
                      <span>Case Sensitivity Warning</span>
                    </div>
                    <p className="text-[11px] leading-relaxed opacity-90">
                      This field is <strong>case-sensitive</strong>! Enter the exact name of the theatre as it appears on the BookMyShow site (e.g. <code className="bg-black/30 px-1 py-0.5 rounded text-amber-100">PVR Forum Mall</code> or <code className="bg-black/30 px-1 py-0.5 rounded text-amber-100">Cinepolis Nexus</code>).
                    </p>
                  </div>
                </div>
              </div>

              {/* Step 7 */}
              <div className="bg-card border border-border/70 rounded-xl p-4 sm:p-5 flex gap-4 transition-all hover:border-border">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-rose-500/10 text-rose-400 font-bold text-sm border border-rose-500/20">
                  7
                </div>
                <div className="space-y-1.5 flex-1">
                  <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                    <Bell className="h-4 w-4 text-rose-400" />
                    Choose Notification Method
                  </h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Select how you want us to notify you, either by <strong className="text-foreground font-semibold">Email</strong> or by <strong className="text-foreground font-semibold">Discord Webhook</strong>, and provide your email address or Discord webhook URL accordingly.
                  </p>
                </div>
              </div>

              {/* Step 8 */}
              <div className="bg-card border border-border/70 rounded-xl p-4 sm:p-5 flex gap-4 transition-all hover:border-border">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-rose-500/10 text-rose-400 font-bold text-sm border border-rose-500/20">
                  8
                </div>
                <div className="space-y-1.5 flex-1">
                  <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                    <Clock className="h-4 w-4 text-rose-400" />
                    Choose Check Frequency
                  </h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Choose how often TicketRadar checks for updates. Minimum is <strong className="text-foreground font-semibold">1 minute</strong>.
                  </p>
                </div>
              </div>

              {/* Step 9 */}
              <div className="bg-card border border-border/70 rounded-xl p-4 sm:p-5 flex gap-4 transition-all hover:border-border">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-rose-500/10 text-rose-400 font-bold text-sm border border-rose-500/20">
                  9
                </div>
                <div className="space-y-1.5 flex-1">
                  <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                    <MousePointerClick className="h-4 w-4 text-rose-400" />
                    Complete CAPTCHA & Start Alert
                  </h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Then click the <strong className="text-foreground font-semibold">"I am not a robot"</strong> reCAPTCHA button and click on the <strong className="text-foreground font-semibold">"Start Alert"</strong> button — and you are done!
                  </p>
                </div>
              </div>

            </div>
          </section>

          {/* SECTION: FUTURE PROVIDERS PLACEHOLDER */}
          <section className="bg-muted/10 border border-dashed border-border/60 rounded-2xl p-6 text-center space-y-3">
            <div className="h-10 w-10 rounded-full bg-muted/40 text-muted-foreground flex items-center justify-center mx-auto">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-foreground">More Providers Coming Soon</h3>
              <p className="text-xs text-muted-foreground max-w-md mx-auto mt-1 leading-relaxed">
                Instructions for additional booking platforms (District, PVR INOX, TicketNew, etc.) will be added as integrations are rolled out.
              </p>
            </div>
          </section>

        </CardContent>
      </Card>
    </main>
  );
}
