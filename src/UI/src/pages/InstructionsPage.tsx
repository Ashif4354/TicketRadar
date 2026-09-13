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
  ChevronRight,
  MousePointerClick,
  MapPin,
  Search,
  PlusCircle,
  CheckCircle2,
  Sliders
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
                    BookMyShow (BMS) Setup Guide
                  </h2>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    How to configure radar alerts using interactive city search or direct booking URLs
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

            {/* Mode Overview Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-rose-500/5 border border-rose-500/20 rounded-xl p-4 space-y-2">
                <div className="flex items-center gap-2">
                  <Badge className="bg-rose-500/20 text-rose-300 border border-rose-500/30 text-[10px] font-bold uppercase">
                    Interactive Mode • Recommended
                  </Badge>
                </div>
                <h3 className="text-sm font-bold text-foreground flex items-center gap-1.5">
                  <MapPin className="h-4 w-4 text-rose-400" />
                  City & Movie Search
                </h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Select your city, pick a movie from live posters, choose your format and screening theatres directly. Zero manual URL copy-pasting required!
                </p>
              </div>

              <div className="bg-card/60 border border-border/70 rounded-xl p-4 space-y-2">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-[10px] font-medium border-border/80 text-muted-foreground uppercase">
                    Manual Mode • Advanced
                  </Badge>
                </div>
                <h3 className="text-sm font-bold text-foreground flex items-center gap-1.5">
                  <Globe className="h-4 w-4 text-rose-400" />
                  Direct Showtimes URL
                </h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Already have the BookMyShow buy-tickets URL open in your browser? Switch to manual mode and paste the link directly.
                </p>
              </div>
            </div>

            {/* Step-by-Step Instructions */}
            <div className="space-y-4">
              
              {/* Step 1 */}
              <div className="bg-card border border-border/70 rounded-xl p-4 sm:p-5 flex gap-4 transition-all hover:border-border">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-rose-500/10 text-rose-400 font-bold text-sm border border-rose-500/20">
                  1
                </div>
                <div className="space-y-2 flex-1">
                  <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                    <MapPin className="h-4 w-4 text-rose-400" />
                    Select Your City & Movie (Interactive Mode)
                  </h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Choose your target city from over <strong className="text-foreground font-semibold">2,000+ Indian cities and regions</strong>. TicketRadar will immediately fetch currently screening and upcoming movies with live posters.
                  </p>
                  <div className="bg-muted/20 border border-border/60 rounded-lg p-3 text-xs space-y-1.5 text-muted-foreground">
                    <div className="flex items-center gap-1.5 font-semibold text-foreground">
                      <Ticket className="h-3.5 w-3.5 text-rose-400" />
                      Pick Format / Language
                    </div>
                    <p className="text-[11px] leading-relaxed">
                      Select your desired screening format (e.g. <strong className="text-foreground font-semibold">IMAX 2D</strong>, <strong className="text-foreground font-semibold">Tamil 2D</strong>, <strong className="text-foreground font-semibold">Hindi 3D</strong>, <strong className="text-foreground font-semibold">4DX</strong>, or <strong className="text-foreground font-semibold">EPIQ</strong>). TicketRadar automatically maps the correct BookMyShow event code.
                    </p>
                  </div>
                </div>
              </div>

              {/* Step 2 */}
              <div className="bg-card border border-border/70 rounded-xl p-4 sm:p-5 flex gap-4 transition-all hover:border-border">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-rose-500/10 text-rose-400 font-bold text-sm border border-rose-500/20">
                  2
                </div>
                <div className="space-y-1.5 flex-1">
                  <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-rose-400" />
                    Select Target Date
                  </h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Pick the exact date you want TicketRadar to monitor for ticket openings.
                  </p>
                </div>
              </div>

              {/* Step 3 - THEATRES DEEP DIVE */}
              <div className="bg-card border border-border/70 rounded-xl p-4 sm:p-5 flex gap-4 transition-all hover:border-border">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-rose-500/10 text-rose-400 font-bold text-sm border border-rose-500/20">
                  3
                </div>
                <div className="space-y-3.5 flex-1">
                  <div>
                    <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                      <Building2 className="h-4 w-4 text-rose-400" />
                      Select Preferred Theatres (Smart City-Filtered Matching)
                    </h3>
                    <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                      TicketRadar provides three intuitive ways to pick your cinemas without cross-city confusion:
                    </p>
                  </div>

                  {/* Feature 1: Available in City Quick-Select */}
                  <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 p-3.5 space-y-2 text-xs">
                    <div className="font-semibold flex items-center gap-2 text-rose-300">
                      <CheckCircle2 className="h-4 w-4 text-rose-400 shrink-0" />
                      <span>1. "Available in [City]" Quick-Select & "+ Add All"</span>
                    </div>
                    <p className="text-[11px] text-muted-foreground leading-relaxed">
                      When a movie has active showtimes in your selected city, TicketRadar automatically loads all screening venues as interactive badges.
                    </p>
                    <ul className="text-[11px] text-muted-foreground list-disc list-inside space-y-1 pl-1">
                      <li>Click individual cinema badges to instantly add or remove them from your alert.</li>
                      <li>Click the <strong className="text-foreground font-semibold">+ Add All</strong> button to monitor every screening theatre in that city simultaneously.</li>
                    </ul>
                  </div>

                  {/* Feature 2: City-Filtered Autocomplete */}
                  <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-3.5 space-y-2 text-xs">
                    <div className="font-semibold flex items-center gap-2 text-blue-300">
                      <Search className="h-4 w-4 text-blue-400 shrink-0" />
                      <span>2. City-Filtered Theatre Search</span>
                    </div>
                    <p className="text-[11px] text-muted-foreground leading-relaxed">
                      Searching for popular chains like <strong className="text-foreground font-semibold">PVR</strong>, <strong className="text-foreground font-semibold">INOX</strong>, or <strong className="text-foreground font-semibold">Cinepolis</strong>? Start typing in the search bar. Autocomplete results are <strong className="text-foreground font-semibold">strictly filtered to your selected city</strong>—cross-city cinemas in other states or metros are automatically excluded to prevent accidental false alerts.
                    </p>
                  </div>

                  {/* Feature 3: Add as Custom Cinema */}
                  <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3.5 space-y-2 text-xs">
                    <div className="font-semibold flex items-center gap-2 text-amber-300">
                      <PlusCircle className="h-4 w-4 text-amber-400 shrink-0" />
                      <span>3. "Add as custom cinema"</span>
                    </div>
                    <p className="text-[11px] text-muted-foreground leading-relaxed">
                      If your cinema is an independent single screen, a newly opened venue, or hasn't been indexed by BookMyShow's dynamic search yet:
                    </p>
                    <ul className="text-[11px] text-muted-foreground list-disc list-inside space-y-1 pl-1">
                      <li>Type the cinema name or shorthand keyword into the search bar.</li>
                      <li>Click <strong className="text-foreground font-semibold">"Add as custom cinema"</strong> (or hit <kbd className="bg-black/40 px-1 py-0.5 rounded text-[10px] text-amber-200">Enter</kbd>).</li>
                      <li>You don't need the full address—concise keywords like <code className="bg-black/30 px-1 py-0.5 rounded text-amber-200">Sathyam</code>, <code className="bg-black/30 px-1 py-0.5 rounded text-amber-200">Luxe</code>, or <code className="bg-black/30 px-1 py-0.5 rounded text-amber-200">Rohini</code> work reliably.</li>
                    </ul>
                  </div>

                  {/* Substring Matching Explained */}
                  <div className="rounded-xl border border-border/80 bg-muted/30 p-3.5 space-y-2 text-xs">
                    <div className="font-semibold flex items-center gap-2 text-foreground">
                      <Sliders className="h-4 w-4 text-rose-400 shrink-0" />
                      <span>How Matching Works (Case-Insensitive Substring)</span>
                    </div>
                    <p className="text-[11px] text-muted-foreground leading-relaxed">
                      When BookMyShow opens bookings for your date, TicketRadar scans the candidate venue names on the page using <strong>case-insensitive substring matching</strong>:
                    </p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1 font-mono text-[11px]">
                      <div className="bg-black/40 p-2 rounded-lg border border-border/40">
                        <span className="text-muted-foreground block text-[10px] uppercase font-sans">Your Keyword:</span>
                        <span className="text-rose-300">Sathyam</span>
                        <span className="text-emerald-400 block text-[10px] mt-1 font-sans">✓ Matches "SPI: Sathyam Cinemas, Royapettah"</span>
                      </div>
                      <div className="bg-black/40 p-2 rounded-lg border border-border/40">
                        <span className="text-muted-foreground block text-[10px] uppercase font-sans">Your Keyword:</span>
                        <span className="text-rose-300">pvr forum</span>
                        <span className="text-emerald-400 block text-[10px] mt-1 font-sans">✓ Matches "PVR: Forum Mall, Koramangala"</span>
                      </div>
                    </div>
                    <p className="text-[10px] text-muted-foreground italic">
                      Note: You can add multiple theatres to a single alert. TicketRadar will trigger as soon as <strong>any</strong> of your selected cinemas open bookings!
                    </p>
                  </div>
                </div>
              </div>

              {/* Step 4: Manual URL Fallback */}
              <div className="bg-card border border-border/70 rounded-xl p-4 sm:p-5 flex gap-4 transition-all hover:border-border">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-rose-500/10 text-rose-400 font-bold text-sm border border-rose-500/20">
                  4
                </div>
                <div className="space-y-2 flex-1">
                  <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                    <Globe className="h-4 w-4 text-rose-400" />
                    Alternative: Manual URL Mode
                  </h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    If you prefer browsing BookMyShow directly in your browser:
                  </p>
                  <ol className="text-[11px] text-muted-foreground list-decimal list-inside space-y-1 pl-1">
                    <li>Visit <a href="https://in.bookmyshow.com" target="_blank" rel="noopener noreferrer" className="text-rose-400 hover:underline">in.bookmyshow.com</a>, search for your movie, and click <strong className="text-foreground font-semibold">Book Tickets</strong>.</li>
                    <li>Select your format (e.g. IMAX 2D, Tamil 3D) to reach the showtimes listing page.</li>
                    <li>Copy the full URL from your browser's address bar.</li>
                    <li>Switch to the <strong className="text-foreground font-semibold">Manual URL</strong> tab in TicketRadar and paste the link into the <strong className="text-foreground font-semibold">Movie Ticket Page Link</strong> field.</li>
                  </ol>
                  <div className="bg-muted/30 border border-border/60 rounded-lg p-2.5 text-[11px] font-mono text-rose-300 break-all select-all">
                    https://in.bookmyshow.com/buytickets/avatar-fire-and-ash-chennai/movie-chen-ET00392811-MT/20260724
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
                    <Bell className="h-4 w-4 text-rose-400" />
                    Choose Notification Method
                  </h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Select how you want us to notify you: either by <strong className="text-foreground font-semibold">Email</strong> (HTML alerts with direct booking buttons) or by <strong className="text-foreground font-semibold">Discord Webhook</strong> (rich embeds with movie poster, showtimes, and direct links).
                  </p>
                </div>
              </div>

              {/* Step 6 */}
              <div className="bg-card border border-border/70 rounded-xl p-4 sm:p-5 flex gap-4 transition-all hover:border-border">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-rose-500/10 text-rose-400 font-bold text-sm border border-rose-500/20">
                  6
                </div>
                <div className="space-y-1.5 flex-1">
                  <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                    <Clock className="h-4 w-4 text-rose-400" />
                    Choose Check Frequency
                  </h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Choose how often TicketRadar checks for ticket updates (from <strong className="text-foreground font-semibold">1 minute</strong> to <strong className="text-foreground font-semibold">30 minutes</strong>).
                  </p>
                </div>
              </div>

              {/* Step 7 */}
              <div className="bg-card border border-border/70 rounded-xl p-4 sm:p-5 flex gap-4 transition-all hover:border-border">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-rose-500/10 text-rose-400 font-bold text-sm border border-rose-500/20">
                  7
                </div>
                <div className="space-y-1.5 flex-1">
                  <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                    <MousePointerClick className="h-4 w-4 text-rose-400" />
                    Complete Verification & Start Radar
                  </h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Complete the human verification reCAPTCHA (automatically bypassed when running locally with security disabled) and click <strong className="text-foreground font-semibold">"Start Radar"</strong>. You can pause, edit, restart, or stream live scraping logs from the dashboard at any time!
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
