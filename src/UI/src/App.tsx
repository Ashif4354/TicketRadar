// src/UI/src/App.tsx

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { BrowserRouter, Routes, Route, useNavigate, Navigate, Link } from 'react-router-dom';
import ReCAPTCHA from 'react-google-recaptcha';
import { 
  Radar, Film, Calendar, MessageSquare, Clock, 
  Play, Pause, Trash2, Sliders, Plus, Send, 
  AlertTriangle, CheckCircle2, ChevronDown, ChevronUp,
  ExternalLink, RefreshCw, Sparkles, LogOut, Shield, Lock, Timer, Power
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';

import { auth, loginWithGoogle, logout, getAuthToken, getAppCheckToken } from './lib/firebase';
import { onAuthStateChanged } from 'firebase/auth';
import type { User } from 'firebase/auth';

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
  created_by?: string;
}

interface AppConfig {
  config_error: string | null;
  smtp_server: string | null;
  smtp_email: string | null;
  default_check_interval: number;
  recaptcha_site?: string;
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

// Authenticated Fetch utility wrapper that appends Auth and App Check tokens
const authenticatedFetch = async (url: string, options: RequestInit = {}): Promise<Response> => {
  const headers = { ...(options.headers || {}) } as Record<string, string>;
  
  const idToken = await getAuthToken();
  if (idToken) {
    headers['Authorization'] = `Bearer ${idToken}`;
  }
  
  const appCheckToken = await getAppCheckToken();
  if (appCheckToken) {
    headers['X-Firebase-AppCheck'] = appCheckToken;
  }
  
  let targetUrl = url;
  if (url.startsWith('/')) {
    const backendUrl = import.meta.env.VITE_BACKEND_URL || '';
    const cleanBackendUrl = backendUrl.endsWith('/') ? backendUrl.slice(0, -1) : backendUrl;
    targetUrl = `${cleanBackendUrl}${url}`;
  }
  
  return fetch(targetUrl, {
    ...options,
    headers
  });
};

// Global Footer Component
function Footer() {
  return (
    <footer className="mt-auto border-t border-border/80 bg-card py-6 text-xs text-muted-foreground">
      <div className="container mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
        <p>© 2026 TicketRadar. Checking active BookMyShow showtimes continuously.</p>
        <div className="flex items-center gap-2 bg-muted/30 border border-border/50 px-3 py-1.5 rounded-lg font-medium text-foreground">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span className="text-muted-foreground">Status:</span>
          <span>Ready & Active</span>
        </div>
      </div>
    </footer>
  );
}

// Global Header Component with User Info Dropdown
interface HeaderProps {
  user: User | null;
  claims: any;
}

function Header({ user, claims }: HeaderProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const handleLogout = async () => {
    setDropdownOpen(false);
    await logout();
    navigate('/login');
  };

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const isAdmin = claims?.role === 'admin';

  return (
    <header className="sticky top-0 z-40 w-full border-b border-border glassmorphism">
      <div className="container mx-auto max-w-7xl flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link to="/" className="flex items-center gap-2.5">
          <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-rose-500 to-pink-500 text-white shadow-lg shadow-rose-500/20">
            <Radar className="h-5.5 w-5.5" />
          </div>
          <div className="text-left">
            <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-white via-slate-200 to-rose-400 bg-clip-text text-transparent flex items-center gap-1.5">
              TicketRadar
            </span>
            <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider -mt-0.5">
              Movie Ticket Alerts
            </p>
          </div>
        </Link>

        <div className="flex items-center gap-4">
          {user ? (
            <div className="relative" ref={dropdownRef}>
              <button
                onClick={() => setDropdownOpen(!dropdownOpen)}
                className="flex items-center gap-2 outline-none focus:outline-none cursor-pointer"
              >
                {user.photoURL ? (
                  <img
                    src={user.photoURL}
                    alt={user.displayName || "User profile"}
                    className="h-9 w-9 rounded-full border border-rose-500/30 object-cover shadow-sm hover:border-rose-500/80 transition-colors"
                  />
                ) : (
                  <div className="h-9 w-9 rounded-full bg-rose-500/10 border border-rose-500/30 text-rose-500 flex items-center justify-center font-bold text-sm shadow-sm hover:border-rose-500/80 transition-colors">
                    {user.displayName ? user.displayName.charAt(0).toUpperCase() : user.email?.charAt(0).toUpperCase()}
                  </div>
                )}
              </button>

              {dropdownOpen && (
                <div className="absolute right-0 mt-2 w-64 rounded-xl border border-border/80 bg-card p-4 shadow-xl glassmorphism text-left animate-in fade-in slide-in-from-top-2 duration-150">
                  <div className="flex items-center gap-3 border-b border-border/40 pb-3 mb-3">
                    {user.photoURL ? (
                      <img src={user.photoURL} className="h-10 w-10 rounded-full border border-border" alt="" />
                    ) : (
                      <div className="h-10 w-10 rounded-full bg-rose-500/10 text-rose-500 flex items-center justify-center font-bold text-sm">
                        {user.displayName ? user.displayName.charAt(0).toUpperCase() : "U"}
                      </div>
                    )}
                    <div className="overflow-hidden">
                      <p className="text-xs font-semibold text-foreground truncate">{user.displayName || "User"}</p>
                      <p className="text-[10px] text-muted-foreground truncate">{user.email}</p>
                    </div>
                  </div>

                  <div className="space-y-2">
                    {claims?.authorized && (
                      <div className="flex items-center justify-between text-xs py-1 border-b border-border/40 pb-2">
                        <span className="text-muted-foreground">Status:</span>
                        <Badge className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-bold px-2 py-0.5 rounded-full">
                          AUTHORIZED
                        </Badge>
                      </div>
                    )}

                    {isAdmin && (
                      <Link
                        to="/admin"
                        onClick={() => setDropdownOpen(false)}
                        className="flex w-full items-center gap-2 rounded-lg bg-rose-500/10 hover:bg-rose-500/25 text-rose-400 text-xs font-semibold px-3 py-2 border border-rose-500/20 transition-colors cursor-pointer justify-center"
                      >
                        <Shield className="h-3.5 w-3.5" />
                        Admin Panel
                      </Link>
                    )}

                    <Button
                      onClick={handleLogout}
                      variant="outline"
                      className="w-full text-xs font-semibold h-9 flex items-center justify-center gap-2 hover:bg-rose-500/10 hover:text-rose-400 border-border hover:border-rose-500/20"
                    >
                      <LogOut className="h-3.5 w-3.5" />
                      Log Out
                    </Button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <Link to="/login">
              <Button size="sm" className="h-9 px-4 text-xs font-semibold bg-rose-500 hover:bg-rose-600 cursor-pointer">
                Sign In
              </Button>
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}

// Landing Page Route Component
function LandingPage() {
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
              Provide your movie link, date, and preferred cinemas. TicketRadar checks for open seats every few seconds.
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

// Login Route Page
function LoginPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleLogin = async () => {
    setLoading(true);
    setError(null);
    try {
      await loginWithGoogle();
      navigate('/');
    } catch (err: any) {
      console.error("Google sign in failed:", err);
      setError(err.message || "Failed to log in with Google.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex-1 flex items-center justify-center px-4 py-16">
      <Card className="w-full max-w-md border border-border/80 shadow-2xl glassmorphism glow-primary p-6 rounded-2xl text-center space-y-6">
        <CardHeader className="space-y-2 p-0">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-tr from-rose-500 to-pink-500 text-white shadow-lg shadow-rose-500/20 mb-2">
            <Radar className="h-6 w-6" />
          </div>
          <CardTitle className="text-2xl font-extrabold tracking-tight">Log in to TicketRadar</CardTitle>
          <CardDescription className="text-xs text-muted-foreground">
            Sign in with your Google account to set up ticket alerts.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4 p-0">
          {error && (
            <div className="rounded-xl border border-destructive/20 bg-destructive/10 p-3 text-xs text-destructive flex items-center gap-2 text-left">
              <AlertTriangle className="h-4.5 w-4.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <Button
            onClick={handleLogin}
            disabled={loading}
            className="w-full h-11 bg-white hover:bg-gray-100 text-gray-900 font-semibold text-sm flex items-center justify-center gap-3 border border-gray-200 transition-colors shadow-sm rounded-xl cursor-pointer"
          >
            {loading ? (
              <RefreshCw className="h-4 w-4 animate-spin text-gray-900" />
            ) : (
              <svg className="h-4.5 w-4.5 mr-2 inline-block" viewBox="0 0 24 24" width="24" height="24" xmlns="http://www.w3.org/2000/svg">
                <path d="M21.35,11.1H12v2.7h5.38C17.15,15.54,14.88,17,12,17c-2.94,0-5.46-2.06-6.38-4.83a7.3,7.3,0,0,1,0-4.34C6.54,5.06,9.06,3,12,3a6.88,6.88,0,0,1,4.9,2.06l2.12-2.12A9.82,9.82,0,0,0,12,0C6.93,0,2.61,4.24,1.21,9.75a10,10,0,0,0,0,4.5C2.61,19.76,6.93,24,12,24a9.83,9.83,0,0,0,7.18-2.92C22.18,18.3,23.3,13.86,22.18,11.1Z" fill="#EA4335" />
              </svg>
            )}
            Sign in with Google
          </Button>

          <div className="text-[10px] text-muted-foreground pt-2">
            By signing in, you agree to the terms of service.
          </div>
        </CardContent>
      </Card>
    </main>
  );
}

// Blocked Route Screen
function BlockedPage() {
  return (
    <main className="flex-1 flex items-center justify-center px-4 py-16">
      <Card className="w-full max-w-md border border-destructive/20 shadow-2xl bg-destructive/5 p-6 rounded-2xl text-center space-y-6">
        <CardHeader className="space-y-2 p-0 text-destructive text-center">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-xl bg-destructive/10 text-destructive shadow-lg mb-2">
            <Lock className="h-7 w-7" />
          </div>
          <CardTitle className="text-2xl font-extrabold tracking-tight">Access Blocked</CardTitle>
          <CardDescription className="text-xs text-destructive-foreground/75">
            You are blocked and cannot access the app content.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <p className="text-xs text-muted-foreground leading-relaxed">
            Your account has been blocked by an administrator. If you believe this is a mistake, please contact the support desk.
          </p>
        </CardContent>
      </Card>
    </main>
  );
}

// Unauthorized Route Screen with Request Access Form
function UnauthorizedPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const recaptchaRef = useRef<ReCAPTCHA>(null);

  const handleRequestAccess = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    const token = recaptchaRef.current?.getValue() || "";
    if (!token) {
      setError("Please complete the security check first.");
      return;
    }

    setLoading(true);
    try {
      const res = await authenticatedFetch('/api/request-access', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ recaptcha_token: token })
      });
      const data = await res.json();
      if (res.ok) {
        setSuccess("Your access request was submitted successfully! An administrator will review it.");
      } else {
        setError(data.detail || "Failed to submit access request.");
      }
    } catch (err: any) {
      setError(err.message || "Failed to submit request.");
    } finally {
      setLoading(false);
      try {
        recaptchaRef.current?.reset();
      } catch (err) {
        console.error("Failed to reset reCAPTCHA:", err);
      }
    }
  };

  return (
    <main className="flex-1 flex items-center justify-center px-4 py-16">
      <Card className="w-full max-w-md border border-amber-500/20 shadow-2xl glassmorphism p-6 rounded-2xl text-center space-y-6">
        <CardHeader className="space-y-2 p-0">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-xl bg-amber-500/10 text-amber-500 shadow-lg mb-2">
            <Lock className="h-7 w-7" />
          </div>
          <CardTitle className="text-2xl font-extrabold tracking-tight">Access Required</CardTitle>
          <CardDescription className="text-xs text-muted-foreground">
            Your account needs approval before setting up ticket alerts.
          </CardDescription>
        </CardHeader>
        
        <CardContent className="space-y-4 p-0">
          <p className="text-xs text-muted-foreground leading-relaxed">
            Your Google account is signed in, but needs approval before you can create ticket alerts. Please request access below.
          </p>

          {error && (
            <div className="rounded-xl border border-destructive/20 bg-destructive/10 p-3 text-xs text-destructive flex items-center gap-2 text-left">
              <AlertTriangle className="h-4.5 w-4.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {success ? (
            <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-xs text-emerald-400 flex items-center gap-2.5 text-left">
              <CheckCircle2 className="h-5 w-5 shrink-0" />
              <span>{success}</span>
            </div>
          ) : (
            <form onSubmit={handleRequestAccess} className="space-y-4 flex flex-col items-center">
              <div className="g-recaptcha-premium-container">
                <ReCAPTCHA
                  ref={recaptchaRef}
                  sitekey={import.meta.env.VITE_RECAPTCHA_V2_SITE_KEY}
                  theme="dark"
                />
              </div>

              <Button
                type="submit"
                disabled={loading}
                className="w-full h-11 bg-amber-500 hover:bg-amber-600 text-white font-semibold text-sm flex items-center justify-center gap-2 rounded-xl cursor-pointer"
              >
                {loading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                Request Access
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </main>
  );
}

// Admin Panel Dashboard Component (Admin Users, Claims, access requests, jobs monitors)
function AdminDashboard() {
  const [activeTab, setActiveTab] = useState<'requests' | 'users' | 'jobs'>('requests');
  const [requests, setRequests] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [jobs, setJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (activeTab === 'requests') {
        const res = await authenticatedFetch('/admin/requests');
        if (res.ok) setRequests(await res.json());
        else setError("Failed to fetch access requests.");
      } else if (activeTab === 'users') {
        const res = await authenticatedFetch('/admin/users');
        if (res.ok) setUsers(await res.json());
        else setError("Failed to fetch user list.");
      } else if (activeTab === 'jobs') {
        const res = await authenticatedFetch('/api/jobs');
        if (res.ok) setJobs(await res.json());
        else setError("Failed to fetch all jobs.");
      }
    } catch (err: any) {
      setError(err.message || "Failed to load data.");
    } finally {
      setLoading(false);
    }
  }, [activeTab]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleApprove = async (uid: string) => {
    setActionLoading(`approve-${uid}`);
    try {
      const res = await authenticatedFetch(`/admin/requests/${uid}/approve`, { method: 'POST' });
      if (res.ok) {
        setRequests(prev => prev.map(r => r.uid === uid ? { ...r, status: 'approved' } : r));
      } else {
        const data = await res.json();
        alert(data.detail || "Failed to approve request.");
      }
    } catch (err: any) {
      alert(err.message || "An error occurred.");
    } finally {
      setActionLoading(null);
    }
  };

  const handleDeny = async (uid: string) => {
    setActionLoading(`deny-${uid}`);
    try {
      const res = await authenticatedFetch(`/admin/requests/${uid}/deny`, { method: 'POST' });
      if (res.ok) {
        setRequests(prev => prev.map(r => r.uid === uid ? { ...r, status: 'denied' } : r));
      } else {
        const data = await res.json();
        alert(data.detail || "Failed to deny request.");
      }
    } catch (err: any) {
      alert(err.message || "An error occurred.");
    } finally {
      setActionLoading(null);
    }
  };

  const handleToggleBlock = async (uid: string, currentlyBlocked: boolean) => {
    setActionLoading(`block-${uid}`);
    const endpoint = currentlyBlocked ? `/admin/users/${uid}/unblock` : `/admin/users/${uid}/block`;
    try {
      const res = await authenticatedFetch(endpoint, { method: 'POST' });
      if (res.ok) {
        setUsers(prev => prev.map(u => {
          if (u.uid === uid) {
            const claims = { ...u.custom_claims, blocked: !currentlyBlocked };
            return { ...u, custom_claims: claims };
          }
          return u;
        }));
      } else {
        const data = await res.json();
        alert(data.detail || "Failed to toggle block state.");
      }
    } catch (err: any) {
      alert(err.message || "An error occurred.");
    } finally {
      setActionLoading(null);
    }
  };

  const handleRoleChange = async (uid: string, newRole: string) => {
    setActionLoading(`role-${uid}`);
    try {
      const res = await authenticatedFetch(`/admin/users/${uid}/role`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: newRole })
      });
      if (res.ok) {
        setUsers(prev => prev.map(u => {
          if (u.uid === uid) {
            const claims = { ...u.custom_claims, role: newRole };
            return { ...u, custom_claims: claims };
          }
          return u;
        }));
      } else {
        const data = await res.json();
        alert(data.detail || "Failed to update role.");
      }
    } catch (err: any) {
      alert(err.message || "An error occurred.");
    } finally {
      setActionLoading(null);
    }
  };

  const handleAdminStopJob = async (jobId: string) => {
    setActionLoading(`stop-${jobId}`);
    try {
      const res = await authenticatedFetch(`/admin/jobs/${jobId}/stop`, { method: 'POST' });
      if (res.ok) {
        setJobs(prev => prev.map(j => j.id === jobId ? { ...j, status: 'Stopped', last_result: 'Stopped by Admin' } : j));
      } else {
        alert("Failed to stop job.");
      }
    } catch (err: any) {
      alert(err.message || "An error occurred.");
    } finally {
      setActionLoading(null);
    }
  };

  const handleAdminDeleteJob = async (jobId: string) => {
    if (!confirm("Are you sure you want to delete this job?")) return;
    setActionLoading(`delete-${jobId}`);
    try {
      const res = await authenticatedFetch(`/admin/jobs/${jobId}`, { method: 'DELETE' });
      if (res.ok) {
        setJobs(prev => prev.filter(j => j.id !== jobId));
      } else {
        alert("Failed to delete job.");
      }
    } catch (err: any) {
      alert(err.message || "An error occurred.");
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <main className="flex-1 container mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div className="text-left">
          <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-100 to-rose-400 bg-clip-text text-transparent flex items-center gap-2">
            <Shield className="h-8 w-8 text-rose-500 shrink-0" />
            Admin Panel
          </h1>
          <p className="text-xs text-muted-foreground">Manage user access and active ticket trackers.</p>
        </div>
        <Link to="/app">
          <Button variant="outline" size="sm" className="h-9 px-4 text-xs font-semibold">
            Back to Dashboard
          </Button>
        </Link>
      </div>

      <div className="flex gap-2 border-b border-border/60 pb-3 mb-6 overflow-x-auto">
        <button
          onClick={() => setActiveTab('requests')}
          className={`px-4 py-2 text-xs font-bold rounded-lg border transition-all cursor-pointer ${
            activeTab === 'requests'
              ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
              : 'text-muted-foreground border-transparent hover:text-foreground'
          }`}
        >
          Access Requests
        </button>
        <button
          onClick={() => setActiveTab('users')}
          className={`px-4 py-2 text-xs font-bold rounded-lg border transition-all cursor-pointer ${
            activeTab === 'users'
              ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
              : 'text-muted-foreground border-transparent hover:text-foreground'
          }`}
        >
          Registered Users
        </button>
        <button
          onClick={() => setActiveTab('jobs')}
          className={`px-4 py-2 text-xs font-bold rounded-lg border transition-all cursor-pointer ${
            activeTab === 'jobs'
              ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
              : 'text-muted-foreground border-transparent hover:text-foreground'
          }`}
        >
          All Ticket Trackers
        </button>
      </div>

      {error && (
        <div className="mb-6 rounded-xl border border-destructive/20 bg-destructive/10 p-4 text-xs text-destructive flex items-center gap-2 text-left">
          <AlertTriangle className="h-5 w-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 gap-3">
          <RefreshCw className="h-8 w-8 animate-spin text-rose-500" />
          <span className="text-xs text-muted-foreground font-semibold uppercase tracking-wider animate-pulse">Loading panel data...</span>
        </div>
      ) : (
        <Card className="border border-border/80 glassmorphism p-5 rounded-2xl text-left">
          <CardContent className="p-0 overflow-x-auto">
            {activeTab === 'requests' && (
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-border/50 text-muted-foreground font-bold">
                    <th className="pb-3">User</th>
                    <th className="pb-3">Email</th>
                    <th className="pb-3">Requested At</th>
                    <th className="pb-3">Status</th>
                    <th className="pb-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/30">
                  {requests.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-muted-foreground">No access requests found.</td>
                    </tr>
                  ) : (
                    requests.map(r => (
                      <tr key={r.uid} className="hover:bg-muted/10">
                        <td className="py-3.5 font-semibold text-foreground">{r.displayName || "Unknown User"}</td>
                        <td className="py-3.5 text-muted-foreground">{r.email}</td>
                        <td className="py-3.5 text-muted-foreground">{r.requested_at ? new Date(r.requested_at).toLocaleString() : "N/A"}</td>
                        <td className="py-3.5">
                          {r.status === 'approved' ? (
                            <Badge className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-bold px-2 py-0.5 rounded-full">Approved</Badge>
                          ) : r.status === 'denied' ? (
                            <Badge className="bg-rose-500/10 text-rose-400 border border-rose-500/20 text-[10px] font-bold px-2 py-0.5 rounded-full">Denied</Badge>
                          ) : (
                            <Badge className="bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[10px] font-bold px-2 py-0.5 rounded-full">Pending</Badge>
                          )}
                        </td>
                        <td className="py-3.5 text-right space-x-2">
                          {r.status === 'pending' && (
                            <>
                              <Button
                                onClick={() => handleApprove(r.uid)}
                                disabled={actionLoading !== null}
                                size="sm"
                                className="bg-emerald-500 hover:bg-emerald-600 text-white font-bold h-7 text-[10px]"
                              >
                                Approve
                              </Button>
                              <Button
                                onClick={() => handleDeny(r.uid)}
                                disabled={actionLoading !== null}
                                variant="destructive"
                                size="sm"
                                className="h-7 text-[10px] font-bold"
                              >
                                Deny
                              </Button>
                            </>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            )}

            {activeTab === 'users' && (
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-border/50 text-muted-foreground font-bold">
                    <th className="pb-3">User</th>
                    <th className="pb-3">UID</th>
                    <th className="pb-3">Role</th>
                    <th className="pb-3">Status</th>
                    <th className="pb-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/30">
                  {users.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-muted-foreground">No registered users found.</td>
                    </tr>
                  ) : (
                    users.map(u => {
                      const claims = u.custom_claims || {};
                      const role = claims.role || 'user';
                      const isBlocked = claims.blocked === true;
                      const isAuthorized = claims.authorized === true;

                      return (
                        <tr key={u.uid} className="hover:bg-muted/10">
                          <td className="py-3.5 flex items-center gap-2">
                            {u.photoUrl ? (
                              <img src={u.photoUrl} className="h-7 w-7 rounded-full border border-border" alt="" />
                            ) : (
                              <div className="h-7 w-7 rounded-full bg-rose-500/10 text-rose-500 flex items-center justify-center font-bold text-xs">
                                {u.displayName ? u.displayName.charAt(0).toUpperCase() : "U"}
                              </div>
                            )}
                            <div>
                              <div className="font-semibold text-foreground">{u.displayName || "Unknown User"}</div>
                              <div className="text-[10px] text-muted-foreground">{u.email}</div>
                            </div>
                          </td>
                          <td className="py-3.5 text-muted-foreground font-mono text-[10px]">{u.uid}</td>
                          <td className="py-3.5">
                            <select
                              value={role}
                              onChange={(e) => handleRoleChange(u.uid, e.target.value)}
                              disabled={actionLoading !== null}
                              className="bg-black/40 border border-border/80 text-foreground text-xs rounded-lg px-2 py-1 outline-none"
                            >
                              <option value="user">User</option>
                              <option value="admin">Admin</option>
                            </select>
                          </td>
                          <td className="py-3.5 space-x-1">
                            {isBlocked && (
                              <Badge className="bg-rose-500/10 text-rose-400 border border-rose-500/20 text-[9px] font-bold px-1.5 py-0.5 rounded-full">Blocked</Badge>
                            )}
                            {isAuthorized && (
                              <Badge className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[9px] font-bold px-1.5 py-0.5 rounded-full">Authorized</Badge>
                            )}
                          </td>
                          <td className="py-3.5 text-right">
                            <Button
                              onClick={() => handleToggleBlock(u.uid, isBlocked)}
                              disabled={actionLoading !== null}
                              variant={isBlocked ? "outline" : "destructive"}
                              size="sm"
                              className="h-7 text-[10px] font-bold"
                            >
                              {isBlocked ? "Unblock" : "Block"}
                            </Button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            )}

            {activeTab === 'jobs' && (
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-border/50 text-muted-foreground font-bold">
                    <th className="pb-3">Movie</th>
                    <th className="pb-3">Created By (Owner UID)</th>
                    <th className="pb-3">Details</th>
                    <th className="pb-3">Status</th>
                    <th className="pb-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/30">
                  {jobs.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-muted-foreground">No active monitor tasks found.</td>
                    </tr>
                  ) : (
                    jobs.map(j => (
                      <tr key={j.id} className="hover:bg-muted/10">
                        <td className="py-3.5">
                          <div className="font-semibold text-foreground flex items-center gap-1.5">
                            <Film className="h-3.5 w-3.5 text-rose-400 shrink-0" />
                            {j.movie_name}
                          </div>
                          <div className="text-[10px] text-muted-foreground font-mono">Job #{j.id}</div>
                        </td>
                        <td className="py-3.5 text-muted-foreground font-mono text-[10px]">{j.created_by || "System"}</td>
                        <td className="py-3.5 text-muted-foreground space-y-0.5">
                          <div className="flex items-center gap-1.5">
                            <Calendar className="h-3 w-3 shrink-0" />
                            {formatBmsDate(j.date_str)}
                          </div>
                          <div className="truncate max-w-[200px]" title={j.theatres.join(', ')}>
                            {j.theatres.join(', ')}
                          </div>
                        </td>
                        <td className="py-3.5">
                          <Badge className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                            j.status.toLowerCase() === 'running' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                            j.status.toLowerCase() === 'success' ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' :
                            j.status.toLowerCase() === 'stopped' ? 'bg-muted text-muted-foreground border border-border' :
                            'bg-rose-500/10 text-rose-400 border-rose-500/20'
                          }`}>
                            {j.status}
                          </Badge>
                        </td>
                        <td className="py-3.5 text-right space-x-2">
                          {j.status === 'Running' && (
                            <Button
                              onClick={() => handleAdminStopJob(j.id)}
                              disabled={actionLoading !== null}
                              variant="secondary"
                              size="sm"
                              className="h-7 text-[10px] font-bold cursor-pointer"
                            >
                              Stop
                            </Button>
                          )}
                          <Button
                            onClick={() => handleAdminDeleteJob(j.id)}
                            disabled={actionLoading !== null}
                            variant="destructive"
                            size="sm"
                            className="h-7 text-[10px] font-bold cursor-pointer"
                          >
                            Delete
                          </Button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
      )}
    </main>
  );
}

// App Dashboard Component (Contains original monitor layout)
function AppDashboard() {
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
                Enter your movie link, show date, and preferred cinemas to get notified when tickets open.
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
                  <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Preferred Cinemas</label>
                  <Textarea 
                    placeholder="PVR Director's Cut
Cinepolis Nexus
Inox Forum Mall" 
                    value={theatres}
                    onChange={(e) => setTheatres(e.target.value)}
                    className="min-h-[90px] max-h-[140px] text-xs bg-muted/10 border-border/80 placeholder:text-muted-foreground/40 focus:border-rose-500/40 leading-relaxed"
                  />
                  <p className="text-[10px] text-muted-foreground leading-normal">
                    Type the names of your preferred cinemas (one per line). Example: PVR Forum, INOX Nexus.
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

// Main App Component with router setup
export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [claims, setClaims] = useState<any>(null);
  const [authLoading, setAuthLoading] = useState(true);

  useEffect(() => {
    return onAuthStateChanged(auth, async (currentUser) => {
      if (currentUser) {
        setUser(currentUser);
        try {
          const tokenResult = await currentUser.getIdTokenResult(true);
          setClaims(tokenResult.claims);
        } catch (err) {
          console.error("Error fetching custom claims:", err);
        }
      } else {
        setUser(null);
        setClaims(null);
      }
      setAuthLoading(false);
    });
  }, []);

  if (authLoading) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center">
        <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-tr from-rose-500 to-pink-500 text-white shadow-xl shadow-rose-500/20">
          <Radar className="h-8 w-8 animate-spin" />
        </div>
        <p className="mt-4 text-xs font-semibold text-muted-foreground uppercase tracking-widest animate-pulse">
          Initializing TicketRadar...
        </p>
      </div>
    );
  }

  const isAuthorized = claims?.authorized === true;
  const isAdmin = claims?.role === 'admin';
  const isBlocked = claims?.blocked === true;

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-background text-foreground flex flex-col antialiased">
        <Header user={user} claims={claims} />
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={
            user ? <Navigate to="/" replace /> : <LoginPage />
          } />
          <Route path="/app" element={
            !user ? <Navigate to="/login" replace /> :
            isBlocked ? <BlockedPage /> :
            !isAuthorized ? <UnauthorizedPage /> :
            <AppDashboard />
          } />
          <Route path="/admin" element={
            !user ? <Navigate to="/login" replace /> :
            !isAdmin ? <Navigate to="/app" replace /> :
            <AdminDashboard />
          } />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <Footer />
      </div>
    </BrowserRouter>
  );
}
