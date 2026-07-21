import React, { useState, useEffect, useCallback } from 'react';
import ReCAPTCHA from 'react-google-recaptcha';
import { 
  Radar, Film, Calendar, Mail, MessageSquare, Clock, 
  Play, Pause, Trash2, Sliders, Plus, Send, 
  AlertTriangle, CheckCircle2, Terminal, ChevronDown, ChevronUp,
  ExternalLink, Timer, Power, RefreshCw, Sparkles
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';

interface Job {
  id: string;
  params: {
    url: string;
    date_str: string;
    theatres: string[];
  };
  url: string;
  movie_name: string;
  date_str: string;
  theatres: string[];
  service_provider: string;
  notification_medium: string;
  notification_config: {
    recipient_email?: string;
    webhook_url?: string;
  };
  check_interval: number;
  created_at: string;
  status: string;
  last_checked_at: string | null;
  last_result: string;
}

interface AppConfig {
  config_error: string | null;
  smtp_server: string | null;
  smtp_email: string | null;
  default_check_interval: number;
}

function formatBmsDate(dateStr: string): string {
  if (!dateStr || dateStr.length !== 8) return dateStr;
  const y = dateStr.substring(0, 4);
  const m = dateStr.substring(4, 6);
  const d = dateStr.substring(6, 8);
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const mIdx = parseInt(m, 10) - 1;
  const mName = months[mIdx] || m;
  return `${parseInt(d, 10)} ${mName} ${y}`;
}

function formatTimestamp(ts: string | null): string {
  if (!ts) return "Never";
  try {
    const d = new Date(ts);
    if (isNaN(d.getTime())) return ts;
    const pad = (n: number) => n.toString().padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  } catch (e) {
    return ts;
  }
}

export default function App() {
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
  const recaptchaRef = React.useRef<ReCAPTCHA>(null);
  const mainRecaptchaRef = React.useRef<ReCAPTCHA>(null);

  // Logs state
  const [expandedLogs, setExpandedLogs] = useState<{ [jobId: string]: boolean }>({});
  const [jobLogs, setJobLogs] = useState<{ [jobId: string]: string }>({});
  const [refreshing, setRefreshing] = useState(false);

  // Helper: Fetch App Configuration status
  const fetchConfig = useCallback(async () => {
    try {
      const res = await fetch('/api/config');
      if (res.ok) {
        const data = await res.json();
        setConfig(data);
        if (data.default_check_interval) {
          setIntervalSec(data.default_check_interval);
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
      const res = await fetch('/api/jobs');
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

  // Helper: Fetch logs for a specific job
  const fetchLogs = useCallback(async (jobId: string) => {
    try {
      const res = await fetch(`/api/jobs/${jobId}/logs`);
      if (res.ok) {
        const data = await res.json();
        setJobLogs(prev => ({ ...prev, [jobId]: data.logs }));
      }
    } catch (err) {
      console.error(`Failed to fetch logs for job ${jobId}:`, err);
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

  // Polling for auto-refresh dashboard
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      fetchJobs();
    }, 10000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchJobs]);

  // Polling logs for expanded cards
  useEffect(() => {
    const activeJobIds = Object.keys(expandedLogs).filter(id => expandedLogs[id]);
    if (activeJobIds.length === 0) return;

    const interval = setInterval(() => {
      activeJobIds.forEach(id => {
        const jobExists = jobs.some(j => j.id === id);
        if (jobExists) {
          fetchLogs(id);
        }
      });
    }, 5000);

    return () => clearInterval(interval);
  }, [expandedLogs, jobs, fetchLogs]);

  // Toggle log accordion
  const toggleLogs = (jobId: string) => {
    const isExpanding = !expandedLogs[jobId];
    setExpandedLogs(prev => ({ ...prev, [jobId]: isExpanding }));
    if (isExpanding) {
      fetchLogs(jobId);
    }
  };

  // Test alerts connection submit handler
  const handleTestAlertSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Get reCAPTCHA response token from react-google-recaptcha ref
    const token = recaptchaRef.current?.getValue() || "";

    if (!token) {
      setTestResult({ success: false, message: "Please complete the reCAPTCHA challenge first." });
      return;
    }

    setTestLoading(true);
    setTestResult(null);

    try {
      const res = await fetch('/api/test-notification', {
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
      // Reset reCAPTCHA after submission attempt
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
      const res = await fetch('/api/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok) {
        setFormSuccess(`Successfully registered monitor #${data.id}! Radar daemon started.`);
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
      const res = await fetch(`/api/jobs/${jobId}/start`, { method: 'POST' });
      if (res.ok) {
        fetchJobs();
      }
    } catch (err) {
      console.error("Failed to start job:", err);
    }
  };

  const handleStopJob = async (jobId: string) => {
    try {
      const res = await fetch(`/api/jobs/${jobId}/stop`, { method: 'POST' });
      if (res.ok) {
        fetchJobs();
      }
    } catch (err) {
      console.error("Failed to stop job:", err);
    }
  };

  const handleDeleteJob = async (jobId: string) => {
    try {
      const res = await fetch(`/api/jobs/${jobId}`, { method: 'DELETE' });
      if (res.ok) {
        fetchJobs();
        setExpandedLogs(prev => {
          const updated = { ...prev };
          delete updated[jobId];
          return updated;
        });
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

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col antialiased">
      {/* Top Navbar */}
      <header className="sticky top-0 z-40 w-full border-b border-border glassmorphism">
        <div className="container mx-auto max-w-7xl flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-2.5">
            <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-rose-500 to-pink-500 text-white shadow-lg shadow-rose-500/20">
              <Radar className="h-5.5 w-5.5 animate-pulse" />
            </div>
            <div>
              <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-white via-slate-200 to-rose-400 bg-clip-text text-transparent flex items-center gap-1.5">
                TicketRadar
              </span>
              <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider -mt-0.5">
                Automated Showwatch Daemon
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 container mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        
        {/* Config Error Banner */}
        {config?.config_error && (
          <div className="mb-8 rounded-xl border border-destructive/20 bg-destructive/10 p-5 text-destructive flex gap-4 shadow-lg glow-primary">
            <AlertTriangle className="h-6 w-6 shrink-0 mt-0.5" />
            <div className="flex-1 space-y-2">
              <h4 className="font-semibold text-foreground text-sm flex items-center gap-2">
                Configuration Validation Error
              </h4>
              <p className="text-xs text-muted-foreground leading-relaxed">
                The radar engine detects missing settings in your local environment. Check if your <code>.env</code> file is configured correctly.
              </p>
              <pre className="text-xs font-mono bg-black/40 border border-border/50 p-3 rounded-lg overflow-x-auto text-rose-400">
                {config.config_error}
              </pre>
            </div>
          </div>
        )}

        {/* Top Control Bar */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-8 bg-card border border-border/80 p-4 rounded-xl shadow-sm">
          <div className="flex items-center gap-3">
            <Sliders className="h-4.5 w-4.5 text-rose-500" />
            <span className="text-sm font-semibold tracking-tight">Radar Dashboard Panel</span>
          </div>

          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2.5 cursor-pointer select-none text-xs text-muted-foreground font-medium hover:text-foreground transition-colors">
              <input 
                type="checkbox" 
                checked={autoRefresh} 
                onChange={(e) => setAutoRefresh(e.target.checked)} 
                className="rounded border-input bg-muted/30 text-rose-500 focus:ring-rose-500 focus:ring-offset-background h-4 w-4 accent-rose-500 cursor-pointer"
              />
              Auto Refresh (10s)
            </label>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={fetchJobs}
              disabled={refreshing}
              className="text-xs font-semibold h-8"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} />
              Sync Dashboard
            </Button>
          </div>
        </div>

        {/* Dashboard Split Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
          
          {/* Left Column - Configurations */}
          <div className="space-y-6 lg:col-span-1">
            
            {/* Form Card */}
            <Card className="border-border">
              <CardHeader className="border-b border-border/50 pb-4">
                <CardTitle className="text-base font-bold flex items-center gap-2">
                  <Sparkles className="h-4.5 w-4.5 text-rose-500" />
                  Add New Monitor
                </CardTitle>
                <CardDescription className="text-xs">
                  Deploy a background watch daemon to track movie ticket releases.
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-6 space-y-4">
                <form onSubmit={handleCreateMonitorSubmit} className="space-y-4">
                  
                  {/* Provider (readonly) */}
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                      Service Provider
                    </label>
                    <Select value={serviceProvider} disabled className="opacity-80">
                      <option value="BookMyShow">BookMyShow</option>
                    </Select>
                  </div>

                  {/* Notification Medium */}
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                      Alert Dispatcher
                    </label>
                    <Select 
                      value={medium} 
                      onChange={(e) => setMedium(e.target.value as any)}
                    >
                      <option value="Email">Email Address</option>
                      <option value="Discord Webhook">Discord Webhook</option>
                    </Select>
                  </div>

                  {/* Recipient Address */}
                  {medium === "Email" ? (
                    <div className="space-y-1.5">
                      <label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground flex justify-between">
                        Recipient Email Address
                        <Mail className="h-3.5 w-3.5 text-muted-foreground/60" />
                      </label>
                      <Input 
                        type="email" 
                        placeholder="yourname@gmail.com" 
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="bg-muted/10 border-input"
                      />
                      <p className="text-[10px] text-muted-foreground/80 leading-normal">
                        Receive instant alert notification at this address.
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-1.5">
                      <label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground flex justify-between">
                        Webhook URL
                        <MessageSquare className="h-3.5 w-3.5 text-muted-foreground/60" />
                      </label>
                      <Input 
                        type="text" 
                        placeholder="https://discord.com/api/webhooks/..." 
                        value={webhook}
                        onChange={(e) => setWebhook(e.target.value)}
                        className="bg-muted/10 border-input"
                      />
                      <p className="text-[10px] text-muted-foreground/80 leading-normal">
                        Receive a custom Rich Embed inside your Discord channel.
                      </p>
                    </div>
                  )}

                  {/* Interval Seconds */}
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground flex justify-between">
                      Check Interval
                      <Timer className="h-3.5 w-3.5 text-muted-foreground/60" />
                    </label>
                    <Input 
                      type="number" 
                      min={10} 
                      max={3600} 
                      step={5}
                      value={intervalSec}
                      onChange={(e) => setIntervalSec(parseInt(e.target.value, 10) || 30)}
                      className="bg-muted/10 border-input"
                    />
                    <p className="text-[10px] text-muted-foreground/80 leading-normal">
                      Scan delay in seconds. Minimum interval: 10 seconds.
                    </p>
                  </div>

                  <hr className="border-border/50 my-4" />

                  {/* Movie Page URL */}
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                      Movie Page URL
                    </label>
                    <Input 
                      type="text" 
                      placeholder="https://in.bookmyshow.com/buytickets/movie-name/..." 
                      value={url}
                      onChange={(e) => setUrl(e.target.value)}
                      className="bg-muted/10 border-input"
                    />
                    <p className="text-[10px] text-muted-foreground/80 leading-normal">
                      The exact URL containing the ticket scheduling panel.
                    </p>
                  </div>

                  {/* Target Date */}
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                      Target Date
                    </label>
                    <Input 
                      type="date" 
                      value={targetDate}
                      onChange={(e) => setTargetDate(e.target.value)}
                      className="bg-muted/10 border-input cursor-pointer"
                    />
                    <p className="text-[10px] text-muted-foreground/80 leading-normal">
                      The date of the show you want to monitor.
                    </p>
                  </div>

                  {/* Target Theatres List */}
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                      Target Theatres
                    </label>
                    <Textarea 
                      placeholder="PVR: ECX Chanakyapuri&#10;INOX: Insignia Epicuria"
                      value={theatres}
                      onChange={(e) => setTheatres(e.target.value)}
                      className="bg-muted/10 border-input min-h-[90px]"
                    />
                    <p className="text-[10px] text-muted-foreground/80 leading-normal">
                      Add one name per line. Support substring match (case-sensitive).
                    </p>
                  </div>

                  {/* Error & Success States */}
                  {formErrors.length > 0 && (
                    <div className="rounded-lg border border-destructive/20 bg-destructive/10 p-3 text-xs text-destructive space-y-1">
                      {formErrors.map((err, i) => (
                        <div key={i} className="flex gap-1.5 items-center">
                          <AlertTriangle className="h-3 w-3 shrink-0" />
                          <span>{err}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {formSuccess && (
                    <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 p-3 text-xs text-emerald-400 flex gap-1.5 items-center shadow-sm">
                      <CheckCircle2 className="h-4 w-4 shrink-0" />
                      <span>{formSuccess}</span>
                    </div>
                  )}

                  {/* reCAPTCHA Checkbox Container */}
                  <div className="flex justify-center py-1">
                    <div className="g-recaptcha-premium-container">
                      <ReCAPTCHA
                        ref={mainRecaptchaRef}
                        sitekey="6LfUdl0tAAAAALD21Jd3geQFRavY8xeWMbadKybZ"
                        theme="dark"
                      />
                    </div>
                  </div>

                  <Button type="submit" variant="premium" className="w-full">
                    <Plus className="h-4 w-4" />
                    Launch Radar Daemon
                  </Button>
                </form>
              </CardContent>
            </Card>

            {/* Test Connection Collapsible */}
            <Card className="border-border">
              <button 
                onClick={() => setTestExpanded(!testExpanded)}
                className="w-full flex items-center justify-between p-5 text-sm font-semibold hover:bg-muted/20 transition-colors rounded-xl outline-none"
              >
                <span className="flex items-center gap-2 text-foreground">
                  <Send className="h-4 w-4 text-rose-500" />
                  Test Dispatcher Link
                </span>
                {testExpanded ? (
                  <ChevronUp className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                )}
              </button>
              
              {testExpanded && (
                <CardContent className="pt-0 pb-6 px-5 space-y-4">
                  <form onSubmit={handleTestAlertSubmit} className="space-y-4">
                    <div className="space-y-1.5">
                      <label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                        Test Medium
                      </label>
                      <Select 
                        value={testMedium} 
                        onChange={(e) => setTestMedium(e.target.value as any)}
                      >
                        <option value="Email">Email</option>
                        <option value="Discord Webhook">Discord Webhook</option>
                      </Select>
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                        {testMedium === "Email" ? "Test Email Destination" : "Test Webhook URL"}
                      </label>
                      <Input 
                        type="text" 
                        placeholder={testMedium === "Email" ? "user@gmail.com" : "https://discord.com/api/webhooks/..."} 
                        value={testTarget}
                        onChange={(e) => setTestTarget(e.target.value)}
                        required
                        className="bg-muted/10 border-input"
                      />
                    </div>

                    {/* reCAPTCHA Checkbox Container */}
                    <div className="flex justify-center py-1">
                      <div className="g-recaptcha-premium-container">
                        <ReCAPTCHA
                          ref={recaptchaRef}
                          sitekey="6LfUdl0tAAAAALD21Jd3geQFRavY8xeWMbadKybZ"
                          theme="dark"
                        />
                      </div>
                    </div>

                    <Button type="submit" variant="secondary" className="w-full" disabled={testLoading}>
                      {testLoading ? (
                        <>
                          <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                          Sending test alert...
                        </>
                      ) : (
                        <>
                          <Send className="h-3.5 w-3.5" />
                          Dispatch Verification
                        </>
                      )}
                    </Button>

                    {testResult && (
                      <div className={`rounded-lg border p-3 text-xs flex gap-1.5 items-center ${
                        testResult.success 
                          ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-400" 
                          : "border-destructive/20 bg-destructive/10 text-destructive"
                      }`}>
                        {testResult.success ? (
                          <CheckCircle2 className="h-4 w-4 shrink-0" />
                        ) : (
                          <AlertTriangle className="h-4 w-4 shrink-0" />
                        )}
                        <span className="leading-snug">{testResult.message}</span>
                      </div>
                    )}
                  </form>
                </CardContent>
              )}
            </Card>

          </div>

          {/* Right Column - Monitor List */}
          <div className="lg:col-span-2 space-y-6">
            
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold tracking-tight flex items-center gap-2">
                <Power className="h-4.5 w-4.5 text-rose-500" />
                Active Monitor Daemons
                <Badge variant="outline" className="ml-1 bg-muted/20 border-border">
                  {jobs.length} Active
                </Badge>
              </h3>
            </div>

            <div className="space-y-4">
              {jobs.length === 0 ? (
                <Card className="border-dashed border-border/80 py-12 flex flex-col items-center justify-center text-center px-4 bg-muted/5">
                  <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center text-muted-foreground/60 mb-4">
                    <Radar className="h-6 w-6" />
                  </div>
                  <h4 className="text-sm font-semibold text-foreground mb-1">No Active Radar Daemons</h4>
                  <p className="text-xs text-muted-foreground max-w-sm">
                    No tasks are registered. Set up target movie parameters in the sidebar to initiate tracking operations.
                  </p>
                </Card>
              ) : (
                jobs.map((job) => {
                  const isExpanded = !!expandedLogs[job.id];
                  
                  return (
                    <Card key={job.id} className="border-border overflow-hidden bg-card/60">
                      
                      {/* Top Header Row */}
                      <div className="p-5 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-border/40">
                        <div className="space-y-1">
                          <div className="flex items-center flex-wrap gap-2">
                            <span className="font-semibold text-foreground text-sm tracking-tight flex items-center gap-1.5">
                              <Film className="h-4 w-4 text-rose-500" />
                              {job.movie_name}
                            </span>
                            <span className="text-[10px] font-mono text-muted-foreground bg-muted/40 border border-border px-2 py-0.5 rounded">
                              ID: #{job.id}
                            </span>
                          </div>
                          
                          <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
                            <span>Service: BookMyShow</span>
                            <span>•</span>
                            <a 
                              href={job.url} 
                              target="_blank" 
                              rel="noopener noreferrer"
                              className="text-rose-400 hover:text-rose-300 inline-flex items-center gap-0.5 hover:underline"
                            >
                              Show Booking Link
                              <ExternalLink className="h-3 w-3" />
                            </a>
                          </div>
                        </div>

                        <div className="flex sm:self-center self-stretch gap-2.5 shrink-0">
                          <Badge variant={getStatusBadgeVariant(job.status)}>
                            {job.status}
                          </Badge>
                        </div>
                      </div>

                      {/* Info Panel Details */}
                      <CardContent className="p-5 space-y-4">
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5">
                          
                          <div className="bg-muted/15 border border-border/30 rounded-lg p-2.5 flex flex-col gap-0.5">
                            <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-1">
                              <Calendar className="h-3 w-3 text-rose-400" />
                              Target Date
                            </span>
                            <span className="text-xs font-semibold text-foreground/90">
                              {formatBmsDate(job.date_str)}
                            </span>
                          </div>

                          <div className="bg-muted/15 border border-border/30 rounded-lg p-2.5 flex flex-col gap-0.5">
                            <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-1">
                              {job.notification_medium.toLowerCase() === 'email' ? (
                                <Mail className="h-3 w-3 text-blue-400" />
                              ) : (
                                <MessageSquare className="h-3 w-3 text-violet-400" />
                              )}
                              Dispatcher
                            </span>
                            <span className="text-xs font-semibold text-foreground/90 truncate">
                              {job.notification_medium.toUpperCase()}
                            </span>
                          </div>

                          <div className="bg-muted/15 border border-border/30 rounded-lg p-2.5 flex flex-col gap-0.5">
                            <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-1">
                              <Clock className="h-3 w-3 text-amber-400" />
                              Last Checked
                            </span>
                            <span className="text-xs font-semibold text-foreground/90 truncate">
                              {formatTimestamp(job.last_checked_at)}
                            </span>
                          </div>

                          <div className="bg-muted/15 border border-border/30 rounded-lg p-2.5 flex flex-col gap-0.5">
                            <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-1">
                              <Timer className="h-3 w-3 text-emerald-400" />
                              Interval
                            </span>
                            <span className="text-xs font-semibold text-foreground/90">
                              {job.check_interval}s delay
                            </span>
                          </div>

                        </div>

                        {/* Wide Fields */}
                        <div className="space-y-3.5">
                          <div className="bg-muted/10 border border-border/20 rounded-lg p-3 text-xs leading-normal">
                            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider block mb-1">
                              Target Theatre Substrings
                            </span>
                            <span className="font-semibold text-foreground/80">
                              {job.theatres.join(', ')}
                            </span>
                          </div>

                          <div className="bg-muted/10 border border-border/20 rounded-lg p-3 text-xs">
                            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider block mb-1">
                              Latest Engine Status Message
                            </span>
                            <div className="font-mono text-muted-foreground text-[11px] leading-relaxed break-all bg-black/35 border border-border/30 rounded-md p-2 shadow-inner">
                              {job.last_result}
                            </div>
                          </div>
                        </div>

                        {/* Interactive Logs Console */}
                        <div className="border-t border-border/30 pt-4">
                          <button 
                            onClick={() => toggleLogs(job.id)}
                            className="flex items-center gap-1.5 text-xs font-bold text-muted-foreground hover:text-foreground transition-colors outline-none cursor-pointer"
                          >
                            <Terminal className="h-3.5 w-3.5 text-rose-400" />
                            <span>Daemon Trace Terminal</span>
                            {isExpanded ? (
                              <ChevronUp className="h-3 w-3 ml-0.5" />
                            ) : (
                              <ChevronDown className="h-3 w-3 ml-0.5" />
                            )}
                          </button>
                          
                          {isExpanded && (
                            <div className="mt-3 rounded-lg border border-border bg-black text-emerald-400 font-mono text-[11px] p-4 max-h-[180px] overflow-y-auto shadow-inner leading-relaxed text-left border-l-3 border-l-rose-500">
                              {jobLogs[job.id] ? (
                                <pre className="whitespace-pre-wrap">{jobLogs[job.id]}</pre>
                              ) : (
                                <div className="flex items-center gap-2 text-muted-foreground">
                                  <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                                  <span>Reading daemon logs...</span>
                                </div>
                              )}
                            </div>
                          )}
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
                              Pause Tracking
                            </Button>
                          ) : (
                            <Button 
                              onClick={() => handleStartJob(job.id)} 
                              variant="secondary"
                              size="sm"
                              className="h-8 text-xs font-semibold"
                            >
                              <Play className="h-3.5 w-3.5 text-emerald-400" />
                              Resume Tracking
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
                          Decommission
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

      {/* Footer */}
      <footer className="mt-auto border-t border-border/80 bg-card py-6 text-xs text-muted-foreground">
        <div className="container mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p>© 2026 TicketRadar Daemon Engine. Monitoring active BookMyShow showtimes continuously.</p>
          <div className="flex items-center gap-2 bg-muted/30 border border-border/50 px-3 py-1.5 rounded-lg font-medium text-foreground">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-muted-foreground">Server Connection:</span>
            <span>Active</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
