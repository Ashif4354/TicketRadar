import React, { useState, useEffect, useCallback, useRef } from 'react';
import ReCAPTCHA from 'react-google-recaptcha';
import { 
  Film, Calendar, MessageSquare, Clock, 
  Play, Pause, Trash2, Sliders, Plus, Send, 
  AlertTriangle, CheckCircle2, ChevronDown, ChevronUp,
  ExternalLink, RefreshCw, Timer, Power
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';

import { authenticatedFetch } from '../utils/api';
import { formatBmsDate, formatTimestamp } from '../utils/formatters';
import type { Job, AppConfig } from '../types';

export function AppDashboard() {
  // App Config and Jobs state
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Global Config inputs
  const [serviceProvider] = useState("BookMyShow");
  const [medium, setMedium] = useState<"Email" | "Discord Webhook">("Email");
  const [email, setEmail] = useState("");
  const [webhook, setWebhook] = useState("");
  const [intervalSec, setIntervalSec] = useState(30);

  // New Monitor Form inputs
  const [url, setUrl] = useState("");
  const [targetDate, setTargetDate] = useState("");
  const [theatres, setTheatres] = useState("");
  const [formErrors, setFormErrors] = useState<string[]>([]);
  const [formSuccess, setFormSuccess] = useState<string | null>(null);

  // Test alerts connection inputs
  const [testExpanded, setTestExpanded] = useState(false);
  const [testMedium, setTestMedium] = useState<"Email" | "Discord Webhook">("Email");
  const [testTarget, setTestTarget] = useState("");
  const [testLoading, setTestLoading] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  // reCAPTCHA ref
  const recaptchaRef = useRef<ReCAPTCHA>(null);
  const mainRecaptchaRef = useRef<ReCAPTCHA>(null);

  const [refreshing, setRefreshing] = useState(false);

  // Helper: Fetch App Configuration status
  const fetchConfig = useCallback(async () => {
    try {
      const res = await authenticatedFetch('/api/config');
      if (res.ok) {
        const data = await res.json();
        setConfig(data);
        if (data.default_check_interval) {
          setIntervalSec(Math.max(30, data.default_check_interval));
        }
      }
    } catch (err) {
      console.error("Failed to fetch API config:", err);
    }
  }, []);

  // Helper: Fetch all jobs status
  const fetchJobs = useCallback(async () => {
    setRefreshing(true);
    try {
      const res = await authenticatedFetch('/api/jobs');
      if (res.ok) {
        const data = await res.json();
        setJobs(data);
      }
    } catch (err) {
      console.error("Failed to fetch jobs:", err);
    } finally {
      setRefreshing(false);
    }
  }, []);

  // Initial loads
  useEffect(() => {
    fetchConfig();
    fetchJobs();
    
    // Set default date picker value to today
    const today = new Date();
    const pad = (n: number) => n.toString().padStart(2, '0');
    setTargetDate(`${today.getFullYear()}-${pad(today.getMonth() + 1)}-${pad(today.getDate())}`);
  }, [fetchConfig, fetchJobs]);

  // Auto-refresh dashboard every 10 seconds when enabled
  useEffect(() => {
    if (!autoRefresh) return;

    const intervalId = setInterval(() => {
      fetchJobs();
    }, 10000);

    return () => clearInterval(intervalId);
  }, [autoRefresh, fetchJobs]);

  // Test alerts connection submit handler
  const handleTestAlertSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const token = recaptchaRef.current?.getValue() || "";
    if (!token) {
      setTestResult({ success: false, message: "Please complete the reCAPTCHA challenge first." });
      return;
    }

    setTestLoading(true);
    setTestResult(null);

    try {
      const res = await authenticatedFetch('/api/test-notification', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          medium: testMedium,
          target: testTarget,
          recaptcha_token: token
        })
      });
      const data = await res.json();
      if (res.ok) {
        setTestResult({ success: data.success, message: data.message });
      } else {
        setTestResult({ success: false, message: data.detail || "An error occurred." });
      }
    } catch (err: any) {
      setTestResult({ success: false, message: err.message || "Failed to reach server." });
    } finally {
      setTestLoading(false);
      try {
        recaptchaRef.current?.reset();
      } catch (err) {
        console.error("Failed to reset reCAPTCHA:", err);
      }
    }
  };

  // Register New Monitor Task submit handler
  const handleCreateMonitorSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormErrors([]);
    setFormSuccess(null);

    const token = mainRecaptchaRef.current?.getValue() || "";
    const errors: string[] = [];

    if (!token) {
      errors.push("Please complete the reCAPTCHA challenge first.");
    }

    if (!url.trim()) {
      errors.push("Movie Page URL is required.");
    } else if (!url.trim().startsWith("http")) {
      errors.push("Enter a valid HTTP/HTTPS URL.");
    }

    if (!targetDate) {
      errors.push("Target date is required.");
    }

    const parsedTheatres = theatres
      .split('\n')
      .map(t => t.trim())
      .filter(t => t.length > 0);

    if (parsedTheatres.length === 0) {
      errors.push("At least one theatre name is required.");
    }

    if (medium === "Email" && !email.trim()) {
      errors.push("Recipient email address is required.");
    }

    if (medium === "Discord Webhook" && !webhook.trim()) {
      errors.push("Discord Webhook URL is required.");
    }

    if (intervalSec < 30) {
      errors.push("Check frequency cannot be less than 30 seconds.");
    }

    if (errors.length > 0) {
      setFormErrors(errors);
      return;
    }

    const dateFormatted = targetDate.replace(/-/g, '');

    const payload = {
      service_provider: serviceProvider,
      notification_medium: medium,
      notification_config: medium === "Email" 
        ? { recipient_email: email.trim() } 
        : { webhook_url: webhook.trim() },
      check_interval: intervalSec,
      recaptcha_token: token,
      params: {
        url: url.trim(),
        date_str: dateFormatted,
        theatres: parsedTheatres
      }
    };

    try {
      const res = await authenticatedFetch('/api/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok) {
        setFormSuccess(`Successfully registered monitor #${data.id}! Ticket tracker started.`);
        setUrl("");
        setTheatres("");
        fetchJobs();
      } else {
        setFormErrors([data.detail || "Failed to create monitoring job."]);
      }
    } catch (err: any) {
      setFormErrors([err.message || "Failed to reach server."]);
    } finally {
      try {
        mainRecaptchaRef.current?.reset();
      } catch (err) {
        console.error("Failed to reset main reCAPTCHA:", err);
      }
    }
  };

  // Card Controls
  const handleStartJob = async (jobId: string) => {
    try {
      const res = await authenticatedFetch(`/api/jobs/${jobId}/start`, { method: 'POST' });
      if (res.ok) {
        fetchJobs();
      }
    } catch (err) {
      console.error("Failed to start job:", err);
    }
  };

  const handleStopJob = async (jobId: string) => {
    try {
      const res = await authenticatedFetch(`/api/jobs/${jobId}/stop`, { method: 'POST' });
      if (res.ok) {
        fetchJobs();
      }
    } catch (err) {
      console.error("Failed to stop job:", err);
    }
  };

  const handleDeleteJob = async (jobId: string) => {
    try {
      const res = await authenticatedFetch(`/api/jobs/${jobId}`, { method: 'DELETE' });
      if (res.ok) {
        fetchJobs();
      }
    } catch (err) {
      console.error("Failed to delete job:", err);
    }
  };

  const getStatusBadgeVariant = (status: string) => {
    const s = status.toLowerCase();
    if (s === 'running') return 'running';
    if (s === 'success') return 'success';
    if (s === 'error') return 'destructive';
    if (s === 'stopped') return 'secondary';
    return 'warning';
  };

  const siteKeyVal = config?.recaptcha_site || import.meta.env.VITE_RECAPTCHA_V2_SITE_KEY;

  return (
    <main className="flex-1 container mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Config Error Banner */}
      {config?.config_error && (
        <div className="mb-8 rounded-xl border border-destructive/20 bg-destructive/10 p-5 text-destructive flex gap-4 shadow-lg glow-primary text-left">
          <AlertTriangle className="h-6 w-6 shrink-0 mt-0.5" />
          <div className="flex-1 space-y-2">
            <h4 className="font-semibold text-foreground text-sm flex items-center gap-2">
              Setup Configuration Issue
            </h4>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Some settings are missing. Please check if your <code>.env</code> configuration file is set up correctly.
            </p>
            <pre className="text-xs font-mono bg-black/40 border border-border/50 p-3 rounded-lg overflow-x-auto text-rose-400">
              {config.config_error}
            </pre>
          </div>
        </div>
      )}

      {/* Top Control Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-8 bg-card border border-border/80 p-4 rounded-xl shadow-sm text-left">
        <div className="flex items-center gap-3">
          <Sliders className="h-4.5 w-4.5 text-rose-500" />
          <span className="text-sm font-semibold tracking-tight">Ticket Tracker Dashboard</span>
        </div>

        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2.5 cursor-pointer select-none text-xs text-muted-foreground font-medium hover:text-foreground transition-colors">
            <input 
              type="checkbox" 
              checked={autoRefresh} 
              onChange={(e) => setAutoRefresh(e.target.checked)} 
              className="rounded border-input bg-muted/30 text-rose-500 focus:ring-rose-500 focus:ring-offset-background h-4 w-4 accent-rose-500 cursor-pointer"
            />
            Auto Update Page
          </label>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={fetchJobs}
            disabled={refreshing}
            className="text-xs font-semibold h-8"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh Status
          </Button>
        </div>
      </div>

      {/* Dashboard Split Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start text-left">
        
        {/* Left Column - Configurations */}
        <div className="space-y-6 lg:col-span-1">
          
          {/* Create Monitor Form Card */}
          <Card className="border border-border/80 shadow-md glassmorphism glow-card-hover hover:border-border hover:shadow-xl transition-all duration-300">
            <CardHeader className="border-b border-border/30 pb-4">
              <CardTitle className="text-base font-bold tracking-tight flex items-center gap-2.5">
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-rose-500/10 text-rose-400">
                  <Plus className="h-4 w-4" />
                </div>
                Set Up New Ticket Alert
              </CardTitle>
              <CardDescription className="text-xs text-muted-foreground leading-relaxed">
                Enter your movie link, show date, and preferred theatres/cinemas to get notified when tickets open.
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-5">
              <form onSubmit={handleCreateMonitorSubmit} className="space-y-4">
                
                {/* Form Errors Banner */}
                {formErrors.length > 0 && (
                  <div className="rounded-lg border border-destructive/20 bg-destructive/10 p-3.5 text-xs text-destructive space-y-1">
                    <div className="font-semibold flex items-center gap-1.5 mb-1 text-[11px] uppercase tracking-wider">
                      <AlertTriangle className="h-4 w-4 shrink-0" />
                      <span>Registration Failed</span>
                    </div>
                    <ul className="list-disc pl-4 space-y-0.5">
                      {formErrors.map((err, idx) => (
                        <li key={idx} className="leading-normal">{err}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Form Success Banner */}
                {formSuccess && (
                  <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 p-3.5 text-xs text-emerald-400 flex gap-2.5">
                    <CheckCircle2 className="h-4.5 w-4.5 shrink-0 mt-0.5" />
                    <div>
                      <h5 className="font-bold text-[11px] uppercase tracking-wider mb-1">Tracker Activated</h5>
                      <p className="leading-relaxed">{formSuccess}</p>
                    </div>
                  </div>
                )}

                {/* Booking Provider selection */}
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Booking Platform</label>
                  <Select value={serviceProvider} disabled className="h-9.5 text-xs bg-muted/20 border-border/80">
                    <option value="BookMyShow">BookMyShow</option>
                  </Select>
                </div>

                {/* Movie url page input */}
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Movie Ticket Page Link</label>
                  <Input 
                    type="text" 
                    placeholder="https://in.bookmyshow.com/buytickets/..." 
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    className="h-9.5 text-xs bg-muted/10 border-border/80 placeholder:text-muted-foreground/50 focus:border-rose-500/40"
                  />
                  <p className="text-[10px] text-muted-foreground leading-normal">
                    Paste the BookMyShow ticket booking page link for your movie.
                  </p>
                </div>

                {/* Target Date selection */}
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Show Date</label>
                  <Input 
                    type="date" 
                    value={targetDate}
                    onChange={(e) => setTargetDate(e.target.value)}
                    className="h-9.5 text-xs bg-muted/10 border-border/80 focus:border-rose-500/40"
                  />
                </div>

                {/* Target Theatre name filters */}
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Preferred Theatres/Cinemas</label>
                  <Textarea 
                    placeholder="PVR Director's Cut
Cinepolis Nexus
Inox Forum Mall" 
                    value={theatres}
                    onChange={(e) => setTheatres(e.target.value)}
                    className="min-h-[90px] max-h-[140px] text-xs bg-muted/10 border-border/80 placeholder:text-muted-foreground/40 focus:border-rose-500/40 leading-relaxed"
                  />
                  <p className="text-[10px] text-muted-foreground leading-normal">
                    Type the names of your preferred theatres/cinemas (one per line). Example: PVR Forum, INOX Nexus.
                  </p>
                </div>

                {/* Notification configuration */}
                <div className="space-y-3.5 border-t border-border/30 pt-4 mt-2">
                  <div className="flex items-center justify-between">
                    <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Where should we notify you?</label>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => setMedium("Email")}
                        className={`text-[10px] font-bold px-2 py-1 rounded-md border transition-all cursor-pointer ${
                          medium === "Email" 
                            ? "bg-rose-500/10 text-rose-400 border-rose-500/25" 
                            : "bg-muted/10 text-muted-foreground border-transparent hover:text-foreground"
                        }`}
                      >
                        Email
                      </button>
                      <button
                        type="button"
                        onClick={() => setMedium("Discord Webhook")}
                        className={`text-[10px] font-bold px-2 py-1 rounded-md border transition-all cursor-pointer ${
                          medium === "Discord Webhook" 
                            ? "bg-rose-500/10 text-rose-400 border-rose-500/25" 
                            : "bg-muted/10 text-muted-foreground border-transparent hover:text-foreground"
                        }`}
                      >
                        Discord
                      </button>
                    </div>
                  </div>

                  {medium === "Email" ? (
                    <div className="space-y-1.5">
                      <Input 
                        type="email" 
                        placeholder="your-email@gmail.com" 
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="h-9.5 text-xs bg-muted/10 border-border/80 focus:border-rose-500/40"
                      />
                    </div>
                  ) : (
                    <div className="space-y-1.5">
                      <Input 
                        type="text" 
                        placeholder="Paste your Discord Webhook Link" 
                        value={webhook}
                        onChange={(e) => setWebhook(e.target.value)}
                        className="h-9.5 text-xs bg-muted/10 border-border/80 focus:border-rose-500/40"
                      />
                    </div>
                  )}
                </div>

                {/* Scan Interval Config */}
                <div className="space-y-1.5 border-t border-border/30 pt-4">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                      <Timer className="h-3.5 w-3.5 text-rose-500" />
                      Check Frequency
                    </span>
                    <span className="font-mono text-foreground/80">{intervalSec}s</span>
                  </div>
                  <input 
                    type="range" 
                    min="30" 
                    max="120" 
                    step="5"
                    value={intervalSec} 
                    onChange={(e) => setIntervalSec(Math.max(30, parseInt(e.target.value, 10)))} 
                    className="w-full h-1 bg-muted rounded-lg appearance-none cursor-pointer accent-rose-500"
                  />
                  <div className="flex justify-between text-[9px] text-muted-foreground/60 font-semibold px-0.5">
                    <span>Every 30s (Fastest)</span>
                    <span>Every 60s</span>
                    <span>Every 2 min</span>
                  </div>
                </div>

                {/* Google reCAPTCHA Verification container */}
                <div className="space-y-1.5 border-t border-border/30 pt-4 flex flex-col items-center">
                  <div className="g-recaptcha-premium-container">
                    <ReCAPTCHA
                      ref={mainRecaptchaRef}
                      sitekey={siteKeyVal}
                      theme="dark"
                    />
                  </div>
                </div>

                {/* Submit button */}
                <Button 
                  type="submit" 
                  className="w-full h-10 text-xs font-bold bg-rose-500 hover:bg-rose-600 text-white cursor-pointer rounded-lg mt-2"
                >
                  Start Ticket Alert
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* Test Alert connection card */}
          <Card className="border border-border/80 shadow-sm glassmorphism">
            <CardContent className="p-4">
              <button
                onClick={() => setTestExpanded(!testExpanded)}
                className="w-full flex items-center justify-between text-xs font-bold text-muted-foreground hover:text-foreground transition-colors outline-none cursor-pointer"
              >
                <span className="flex items-center gap-2">
                  <Power className="h-4 w-4 text-rose-500" />
                  Send Test Notification
                </span>
                {testExpanded ? (
                  <ChevronUp className="h-4 w-4" />
                ) : (
                  <ChevronDown className="h-4 w-4" />
                )}
              </button>

              {testExpanded && (
                <form onSubmit={handleTestAlertSubmit} className="mt-4 space-y-3.5 border-t border-border/30 pt-4 text-left">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Notification Method</span>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => setTestMedium("Email")}
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-md border transition-all cursor-pointer ${
                          testMedium === "Email" 
                            ? "bg-rose-500/10 text-rose-400 border-rose-500/25" 
                            : "bg-muted/10 text-muted-foreground border-transparent hover:text-foreground"
                        }`}
                      >
                        Email
                      </button>
                      <button
                        type="button"
                        onClick={() => setTestMedium("Discord Webhook")}
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-md border transition-all cursor-pointer ${
                          testMedium === "Discord Webhook" 
                            ? "bg-rose-500/10 text-rose-400 border-rose-500/25" 
                            : "bg-muted/10 text-muted-foreground border-transparent hover:text-foreground"
                        }`}
                      >
                        Discord
                      </button>
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <Input 
                      type="text" 
                      placeholder={testMedium === "Email" ? "your-email@gmail.com" : "Paste your Discord Webhook Link"}
                      value={testTarget}
                      onChange={(e) => setTestTarget(e.target.value)}
                      className="h-9 text-xs bg-muted/10 border-border/80"
                    />
                  </div>

                  {/* ReCAPTCHA for testing alerts */}
                  <div className="flex flex-col items-center py-1">
                    <div className="g-recaptcha-premium-container">
                      <ReCAPTCHA
                        ref={recaptchaRef}
                        sitekey={siteKeyVal}
                        theme="dark"
                      />
                    </div>
                  </div>

                  <Button 
                    type="submit" 
                    disabled={testLoading}
                    className="w-full h-8.5 text-xs font-bold bg-rose-500 hover:bg-rose-600 text-white cursor-pointer"
                  >
                    {testLoading ? (
                      <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <>
                        <Send className="h-3.5 w-3.5" />
                        Send Test Message
                      </>
                    )}
                  </Button>

                  {testResult && (
                    <div className={`mt-3 rounded-lg border p-3.5 text-xs flex gap-2.5 leading-relaxed ${
                      testResult.success 
                        ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-400' 
                        : 'border-destructive/20 bg-destructive/10 text-destructive'
                    }`}>
                      {testResult.success ? (
                        <CheckCircle2 className="h-4.5 w-4.5 shrink-0 mt-0.5" />
                      ) : (
                        <AlertTriangle className="h-4.5 w-4.5 shrink-0 mt-0.5" />
                      )}
                      <div>
                        <h6 className="font-bold text-[10px] uppercase tracking-wider mb-0.5">
                          {testResult.success ? 'Success' : 'Failed'}
                        </h6>
                        <p>{testResult.message}</p>
                      </div>
                    </div>
                  )}
                </form>
              )}
            </CardContent>
          </Card>

        </div>

        {/* Right Column - Monitor Jobs List */}
        <div className="space-y-6 lg:col-span-2">
          
          <div className="space-y-5">
            {jobs.length === 0 ? (
              <div className="border border-border/80 bg-card rounded-2xl p-10 text-center glassmorphism min-h-[350px] flex flex-col items-center justify-center space-y-4">
                <div className="h-14 w-14 rounded-2xl bg-muted/40 text-muted-foreground flex items-center justify-center shadow-inner">
                  <Film className="h-7 w-7" />
                </div>
                <div className="space-y-1.5">
                  <h3 className="text-base font-bold tracking-tight text-foreground">No Active Ticket Trackers</h3>
                  <p className="text-xs text-muted-foreground max-w-sm mx-auto leading-relaxed">
                    Set up a new ticket alert using the form on the left to start tracking tickets.
                  </p>
                </div>
              </div>
            ) : (
              jobs.map((job) => {
                const getStatusText = (status: string) => {
                  const s = status.toLowerCase();
                  if (s === 'running') return 'Active';
                  if (s === 'stopped') return 'Paused';
                  if (s === 'success') return 'Tickets Found!';
                  return status;
                };

                return (
                  <Card key={job.id} className="border border-border/80 bg-card shadow-sm hover:shadow-md transition-shadow rounded-2xl overflow-hidden glassmorphism">
                    
                    {/* Card Upper Header */}
                    <CardHeader className="px-5 py-4 border-b border-border/30 bg-muted/10 flex flex-row items-center justify-between gap-4 flex-wrap">
                      <div className="space-y-1">
                        <CardTitle className="text-sm font-bold flex items-center gap-1.5">
                          <Film className="h-4 w-4 text-rose-500 shrink-0" />
                          {job.movie_name}
                        </CardTitle>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider">Tracker #{job.id}</span>
                          <span className="text-border/60">•</span>
                          <span className="text-[10px] text-muted-foreground">Checks every {job.check_interval}s</span>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2.5">
                        <Badge variant={getStatusBadgeVariant(job.status)} className="text-[10px] font-extrabold uppercase px-2.5 py-0.5 rounded-full tracking-wider">
                          {getStatusText(job.status)}
                        </Badge>
                      </div>
                    </CardHeader>

                    {/* Card content Details */}
                    <CardContent className="p-5 space-y-5">
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                        <div className="space-y-3">
                          <div className="flex items-center gap-2 text-muted-foreground">
                            <Calendar className="h-4 w-4 text-rose-500 shrink-0" />
                            <span>Show Date:</span>
                            <span className="font-semibold text-foreground/80">
                              {formatBmsDate(job.date_str)}
                            </span>
                          </div>

                          <div className="flex items-center gap-2 text-muted-foreground">
                            <Clock className="h-4 w-4 text-rose-500 shrink-0" />
                            <span>Last Checked:</span>
                            <span className="font-semibold text-foreground/80">
                              {formatTimestamp(job.last_checked_at)}
                            </span>
                          </div>

                          <div className="flex items-center gap-2 text-muted-foreground">
                            <MessageSquare className="h-4 w-4 text-rose-500 shrink-0" />
                            <span>Notify Via:</span>
                            <Badge variant="outline" className="text-[9px] font-bold px-2 py-0.5 bg-muted/30">
                              {job.notification_medium.toUpperCase()}
                            </Badge>
                          </div>
                        </div>

                        <div className="space-y-2">
                          <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
                            Movie Ticket Link
                          </div>
                          <a 
                            href={job.url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="flex items-center gap-1 text-xs text-rose-400 hover:text-rose-300 font-medium truncate max-w-xs cursor-pointer"
                          >
                            View on BookMyShow
                            <ExternalLink className="h-3 w-3 shrink-0" />
                          </a>
                        </div>
                      </div>

                      {/* Targeted Cinemas HALL keywords list */}
                      <div className="border-t border-border/30 pt-4 space-y-2">
                        <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
                          Selected Cinemas
                        </div>
                        <div className="text-xs text-foreground/80 flex flex-wrap gap-1.5">
                          {job.theatres.map((th, idx) => (
                            <Badge key={idx} variant="secondary" className="text-[10px] font-medium border border-border/50 px-2 py-0.5">
                              {th}
                            </Badge>
                          ))}
                        </div>
                      </div>

                      <div className="bg-muted/10 border border-border/20 rounded-lg p-3 text-xs">
                        <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider block mb-1">
                          Latest Status
                        </span>
                        <div className="font-mono text-muted-foreground text-[11px] leading-relaxed break-all bg-black/35 border border-border/30 rounded-md p-2 shadow-inner">
                          {job.last_result}
                        </div>
                      </div>

                    </CardContent>

                    {/* Control Panel Buttons Row */}
                    <div className="bg-muted/20 px-5 py-3.5 flex items-center justify-between border-t border-border/30 gap-4">
                      <div className="flex items-center gap-2">
                        {job.status === "Running" ? (
                          <Button 
                            onClick={() => handleStopJob(job.id)} 
                            variant="secondary"
                            size="sm"
                            className="h-8 text-xs font-semibold"
                          >
                            <Pause className="h-3.5 w-3.5 text-amber-400" />
                            Pause Alert
                          </Button>
                        ) : (
                          <Button 
                            onClick={() => handleStartJob(job.id)} 
                            variant="secondary"
                            size="sm"
                            className="h-8 text-xs font-semibold"
                          >
                            <Play className="h-3.5 w-3.5 text-emerald-400" />
                            Resume Alert
                          </Button>
                        )}
                      </div>
                      
                      <Button 
                        onClick={() => handleDeleteJob(job.id)} 
                        variant="ghost"
                        size="sm"
                        className="h-8 text-xs font-semibold text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 border border-transparent hover:border-rose-500/20"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        Remove Alert
                      </Button>
                    </div>

                  </Card>
                );
              })
            )}
          </div>

        </div>

      </div>

    </main>
  );
}
