import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { 
  Shield, AlertTriangle, RefreshCw, Film, Calendar, Clock, Radio, Bell, Info, 
  LayoutGrid, Table as TableIcon, User as UserIcon, CheckCircle, XCircle, Lock, 
  ExternalLink, Search, X, DollarSign, Wallet, RotateCcw, FileText, CheckCircle2 
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { authenticatedFetch } from '../utils/api';
import { formatBmsDate, formatTimestamp } from '../utils/formatters';
import { ConfirmModal } from '@/components/ui/confirm-modal';
import { isPaymentsDisabled } from '../utils/payments';
import type { AppConfig } from '../types';

/**
 * Provides an administrative interface for managing access requests, user accounts, and ticket-monitoring jobs.
 */
export function AdminDashboard() {
  const [activeTab, setActiveTab] = useState<'requests' | 'users' | 'jobs' | 'pricing' | 'wallets' | 'refunds' | 'audit_logs'>('requests');
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');
  const [requests, setRequests] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [jobs, setJobs] = useState<any[]>([]);
  const [jobSearch, setJobSearch] = useState('');
  const [counts, setCounts] = useState<{ requests: number; users: number; jobs: number } | null>(null);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [jobToStop, setJobToStop] = useState<any | null>(null);
  const [jobToDelete, setJobToDelete] = useState<any | null>(null);

  // Pricing states
  const [pricingConfig, setPricingConfig] = useState<any>(null);
  const [pricingHistory, setPricingHistory] = useState<any[]>([]);
  const [smsPaise, setSmsPaise] = useState('50');
  const [whatsappPaise, setWhatsappPaise] = useState('100');
  const [phoneCallPaise, setPhoneCallPaise] = useState('150');
  const [pricingNote, setPricingNote] = useState('');
  const [pricingUpdating, setPricingUpdating] = useState(false);
  const [pricingMsg, setPricingMsg] = useState<string | null>(null);

  // Wallet states
  const [walletSearchUid, setWalletSearchUid] = useState('');
  const [searchedWallet, setSearchedWallet] = useState<any>(null);
  const [walletAdjustAmount, setWalletAdjustAmount] = useState('100');
  const [walletAdjustDirection, setWalletAdjustDirection] = useState<'CREDIT' | 'DEBIT'>('CREDIT');
  const [walletAdjustReason, setWalletAdjustReason] = useState('');
  const [walletAdjusting, setWalletAdjusting] = useState(false);
  const [walletMsg, setWalletMsg] = useState<string | null>(null);

  // Cashfree refund states
  const [refundOrderId, setRefundOrderId] = useState('');
  const [refundAmountPaise, setRefundAmountPaise] = useState('');
  const [refundReason, setRefundReason] = useState('');
  const [refunding, setRefunding] = useState(false);
  const [refundMsg, setRefundMsg] = useState<string | null>(null);

  // Audit logs
  const [auditLogs, setAuditLogs] = useState<any[]>([]);

  // App Config & Payment status
  const [appConfig, setAppConfig] = useState<AppConfig | null>(null);
  const paymentsDisabled = isPaymentsDisabled(appConfig);

  const fetchCounts = useCallback(async () => {
    try {
      const res = await authenticatedFetch('/admin/counts');
      if (res.ok) {
        const data = await res.json();
        setCounts(data);
      }
    } catch {
      // ignore count fetch error
    }
  }, []);

  const fetchConfig = useCallback(async () => {
    try {
      const res = await authenticatedFetch('/api/config');
      if (res.ok) {
        const data: AppConfig = await res.json();
        setAppConfig(data);
      }
    } catch {
      // ignore config fetch error
    }
  }, []);

  useEffect(() => {
    fetchCounts();
    fetchConfig();
  }, [fetchCounts, fetchConfig]);

  useEffect(() => {
    if (paymentsDisabled && (activeTab === 'pricing' || activeTab === 'wallets' || activeTab === 'refunds')) {
      setActiveTab('requests');
    }
  }, [paymentsDisabled, activeTab]);

  const fetchData = useCallback(async () => {
    if (paymentsDisabled && (activeTab === 'pricing' || activeTab === 'wallets' || activeTab === 'refunds')) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      if (activeTab === 'requests') {
        const res = await authenticatedFetch('/admin/requests');
        if (res.ok) {
          const data = await res.json();
          // Exclude approved requests
          setRequests(data.filter((r: any) => r.status !== 'approved'));
        } else {
          setError("Failed to fetch access requests.");
        }
      } else if (activeTab === 'users') {
        const res = await authenticatedFetch('/admin/users');
        if (res.ok) setUsers(await res.json());
        else setError("Failed to fetch user list.");
      } else if (activeTab === 'jobs') {
        const res = await authenticatedFetch('/api/jobs?all=true');
        if (res.ok) setJobs(await res.json());
        else setError("Failed to fetch jobs.");
      } else if (activeTab === 'pricing') {
        const res = await authenticatedFetch('/admin/pricing');
        if (res.ok) {
          const data = await res.json();
          setPricingConfig(data.current);
          setPricingHistory(data.history || []);
          if (data.current) {
            setSmsPaise(String(data.current.sms_paise ?? 50));
            setWhatsappPaise(String(data.current.whatsapp_paise ?? 100));
            setPhoneCallPaise(String(data.current.phone_call_paise ?? 150));
          }
        } else {
          setError("Failed to fetch pricing configuration.");
        }
      } else if (activeTab === 'audit_logs') {
        const res = await authenticatedFetch('/admin/audit-logs');
        if (res.ok) setAuditLogs(await res.json());
        else setError("Failed to fetch admin audit logs.");
      }
    } catch (e: any) {
      setError(e.message || "An error occurred fetching admin data.");
    } finally {
      setLoading(false);
    }
  }, [activeTab, paymentsDisabled]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleApproveRequest = async (uid: string) => {
    setActionLoading(uid);
    try {
      const res = await authenticatedFetch(`/admin/requests/${uid}/approve`, { method: 'POST' });
      if (res.ok) {
        setRequests(prev => prev.filter(r => r.uid !== uid));
      } else {
        const data = await res.json();
        alert(data.detail || "Failed to approve request.");
      }
    } catch (e: any) {
      alert("Error approving request: " + e.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleDenyRequest = async (uid: string) => {
    setActionLoading(uid);
    try {
      const res = await authenticatedFetch(`/admin/requests/${uid}/deny`, { method: 'POST' });
      if (res.ok) {
        setRequests(prev => prev.map(r => r.uid === uid ? { ...r, status: 'denied' } : r));
      } else {
        const data = await res.json();
        alert(data.detail || "Failed to deny request.");
      }
    } catch (e: any) {
      alert("Error denying request: " + e.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleToggleBlock = async (uid: string, currentlyBlocked: boolean) => {
    setActionLoading(uid);
    try {
      const endpoint = currentlyBlocked ? `/admin/users/${uid}/unblock` : `/admin/users/${uid}/block`;
      const res = await authenticatedFetch(endpoint, { method: 'POST' });
      if (res.ok) {
        setUsers(prev => prev.map(u => u.uid === uid ? {
          ...u,
          custom_claims: { ...u.custom_claims, blocked: !currentlyBlocked }
        } : u));
      } else {
        const data = await res.json();
        alert(data.detail || "Failed to toggle block status.");
      }
    } catch (e: any) {
      alert("Error toggling block: " + e.message);
    } finally {
      setActionLoading(null);
    }
  };


  const handleAdminStopJob = async (jobId: string) => {
    setActionLoading(jobId);
    try {
      const res = await authenticatedFetch(`/admin/jobs/${jobId}/stop`, { method: 'POST' });
      if (res.ok) {
        setJobs(prev => prev.map(j => j.id === jobId ? { ...j, status: 'Stopped', last_result: 'Stopped by Admin' } : j));
      } else {
        const data = await res.json();
        alert(data.detail || "Failed to stop job.");
      }
    } catch (e: any) {
      alert("Error stopping job: " + e.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleAdminDeleteJob = async (jobId: string) => {
    setActionLoading(jobId);
    try {
      const res = await authenticatedFetch(`/admin/jobs/${jobId}`, { method: 'DELETE' });
      if (res.ok) {
        setJobs(prev => prev.filter(j => j.id !== jobId));
      } else {
        const data = await res.json();
        alert(data.detail || "Failed to delete job.");
      }
    } catch (e: any) {
      alert("Error deleting job: " + e.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleUpdatePricing = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pricingNote.trim()) {
      setPricingMsg("Audit reason note is required for updating prices.");
      return;
    }
    setPricingUpdating(true);
    setPricingMsg(null);
    try {
      const res = await authenticatedFetch('/admin/pricing', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sms_paise: parseInt(smsPaise, 10),
          whatsapp_paise: parseInt(whatsappPaise, 10),
          phone_call_paise: parseInt(phoneCallPaise, 10),
          note: pricingNote.trim(),
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setPricingMsg("Pricing updated and audit logged successfully!");
        setPricingConfig(data.config);
        setPricingNote('');
        fetchData();
      } else {
        setPricingMsg(data.detail || "Failed to update pricing.");
      }
    } catch (e: any) {
      setPricingMsg(e.message || "Failed to update pricing.");
    } finally {
      setPricingUpdating(false);
    }
  };

  const handleSearchUserWallet = async () => {
    if (!walletSearchUid.trim()) return;
    setWalletAdjusting(true);
    setWalletMsg(null);
    try {
      const res = await authenticatedFetch(`/admin/wallets/${walletSearchUid.trim()}`);
      const data = await res.json();
      if (res.ok) {
        setSearchedWallet(data);
      } else {
        setWalletMsg(data.detail || "Failed to find user wallet.");
      }
    } catch (e: any) {
      setWalletMsg(e.message || "Error searching wallet.");
    } finally {
      setWalletAdjusting(false);
    }
  };

  const handleAdjustWallet = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!walletSearchUid.trim() || !walletAdjustReason.trim()) {
      setWalletMsg("UID and mandatory audit explanation are required.");
      return;
    }
    setWalletAdjusting(true);
    setWalletMsg(null);
    try {
      const res = await authenticatedFetch(`/admin/wallets/${walletSearchUid.trim()}/adjust`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          amount_paise: parseInt(walletAdjustAmount, 10),
          direction: walletAdjustDirection,
          reason: walletAdjustReason.trim(),
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setWalletMsg(`Successfully ${walletAdjustDirection === 'CREDIT' ? 'credited' : 'debited'} ₹${(parseInt(walletAdjustAmount, 10)/100).toFixed(2)}.`);
        setWalletAdjustReason('');
        handleSearchUserWallet();
      } else {
        setWalletMsg(data.detail || "Wallet adjustment failed.");
      }
    } catch (e: any) {
      setWalletMsg(e.message || "Wallet adjustment error.");
    } finally {
      setWalletAdjusting(false);
    }
  };

  const handleProcessCashfreeRefund = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!refundOrderId.trim() || !refundReason.trim()) {
      setRefundMsg("Cashfree Order ID and audit reason are required.");
      return;
    }
    setRefunding(true);
    setRefundMsg(null);
    try {
      const res = await authenticatedFetch('/admin/refunds/cashfree', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          order_id: refundOrderId.trim(),
          amount_paise: parseInt(refundAmountPaise, 10),
          reason: refundReason.trim(),
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setRefundMsg(`Refund initiated successfully! Provider Refund ID: ${data.provider_refund_id || data.refund_id}`);
        setRefundOrderId('');
        setRefundAmountPaise('');
        setRefundReason('');
      } else {
        setRefundMsg(data.detail || "Refund failed.");
      }
    } catch (e: any) {
      setRefundMsg(e.message || "Error processing refund.");
    } finally {
      setRefunding(false);
    }
  };

  // Derived: search-filtered + Running-first sorted jobs
  const filteredJobs = jobs
    .filter(j => {
      if (!jobSearch.trim()) return true;
      const q = jobSearch.trim().toLowerCase();
      return [
        j.movie_name,
        j.id,
        j.status,
        j.service_provider,
        j.notification_medium,
        j.user_name,
        j.user_email,
        j.created_by,
        j.date_str,
        j.url,
        j.last_result,
        j.notification_config?.webhook_url,
        j.notification_config?.recipient_email,
        ...(j.theatres || []),
      ]
        .filter(Boolean)
        .some((v: any) => String(v).toLowerCase().includes(q));
    })
    .sort((a, b) => {
      const aRunning = a.status?.toLowerCase() === 'running' ? 0 : 1;
      const bRunning = b.status?.toLowerCase() === 'running' ? 0 : 1;
      return aRunning - bRunning;
    });

  // Derived request buckets
  const pendingRequests = requests.filter((r: any) => r.status !== 'denied');
  const deniedRequests = requests.filter((r: any) => r.status === 'denied');

  return (
    <main className="w-full max-w-6xl mx-auto px-3 sm:px-6 py-6 sm:py-8 space-y-6 overflow-x-hidden">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/60 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <Shield className="h-6 w-6 text-rose-500 shrink-0" />
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">Admin Control Panel</h1>
          </div>
          <p className="text-xs text-muted-foreground mt-1">Manage pending access requests, user accounts, and active ticket monitors.</p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <Button
            onClick={fetchData}
            disabled={loading}
            variant="outline"
            size="sm"
            className="text-xs gap-1.5"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>

          <Link to="/app">
            <Button variant="ghost" size="sm" className="text-xs">
              Back to App
            </Button>
          </Link>
        </div>
      </div>

      {error && (
        <Card className="border-rose-500/30 bg-rose-500/10">
          <CardContent className="p-4 flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-rose-500 shrink-0" />
            <div className="text-xs text-rose-400 font-medium">{error}</div>
          </CardContent>
        </Card>
      )}

      {/* Navigation Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border/40 pb-2">
        <div className="flex flex-wrap gap-2">
          <Button
            onClick={() => setActiveTab('requests')}
            variant={activeTab === 'requests' ? 'default' : 'ghost'}
            size="sm"
            className="text-xs font-semibold gap-1.5"
          >
            <UserIcon className="h-3.5 w-3.5" />
            Requests
            {pendingRequests.length > 0 && (
              <span className="ml-0.5 bg-amber-500/20 text-amber-400 border border-amber-500/30 text-[10px] font-bold px-1.5 py-0.5 rounded-full leading-none">
                {pendingRequests.length}
              </span>
            )}
          </Button>
          <Button
            onClick={() => setActiveTab('users')}
            variant={activeTab === 'users' ? 'default' : 'ghost'}
            size="sm"
            className="text-xs font-semibold gap-1.5"
          >
            <Shield className="h-3.5 w-3.5" />
            Users ({users.length > 0 ? users.length : (counts ? counts.users : 0)})
          </Button>
          <Button
            onClick={() => setActiveTab('jobs')}
            variant={activeTab === 'jobs' ? 'default' : 'ghost'}
            size="sm"
            className="text-xs font-semibold gap-1.5"
          >
            <Film className="h-3.5 w-3.5" />
            Ticket Trackers ({jobs.length > 0 ? jobs.length : (counts ? counts.jobs : 0)})
          </Button>
          {!paymentsDisabled && (
            <>
              <Button
                onClick={() => setActiveTab('pricing')}
                variant={activeTab === 'pricing' ? 'default' : 'ghost'}
                size="sm"
                className="text-xs font-semibold gap-1.5"
              >
                <DollarSign className="h-3.5 w-3.5 text-rose-400" />
                Pricing
              </Button>
              <Button
                onClick={() => setActiveTab('wallets')}
                variant={activeTab === 'wallets' ? 'default' : 'ghost'}
                size="sm"
                className="text-xs font-semibold gap-1.5"
              >
                <Wallet className="h-3.5 w-3.5 text-rose-400" />
                Wallets
              </Button>
              <Button
                onClick={() => setActiveTab('refunds')}
                variant={activeTab === 'refunds' ? 'default' : 'ghost'}
                size="sm"
                className="text-xs font-semibold gap-1.5"
              >
                <RotateCcw className="h-3.5 w-3.5 text-rose-400" />
                Refunds
              </Button>
            </>
          )}
          <Button
            onClick={() => setActiveTab('audit_logs')}
            variant={activeTab === 'audit_logs' ? 'default' : 'ghost'}
            size="sm"
            className="text-xs font-semibold gap-1.5"
          >
            <FileText className="h-3.5 w-3.5 text-rose-400" />
            Audit Logs
          </Button>
        </div>

        {/* View Switcher + Search for Jobs */}
        {activeTab === 'jobs' && (
          <div className="flex flex-wrap items-center gap-2 self-start sm:self-auto">
            {/* Search input */}
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
              <input
                type="text"
                value={jobSearch}
                onChange={e => setJobSearch(e.target.value)}
                placeholder="Search jobs…"
                className="bg-black/40 border border-border/60 rounded-lg pl-7 pr-7 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-rose-500/50 w-48"
              />
              {jobSearch && (
                <button
                  onClick={() => setJobSearch('')}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                >
                  <X className="h-3 w-3" />
                </button>
              )}
            </div>

            {/* Grid / Table toggle */}
            <div className="flex items-center gap-1 bg-black/40 border border-border/60 p-1 rounded-lg">
              <button
                onClick={() => setViewMode('grid')}
                className={`p-1.5 rounded-md text-xs flex items-center gap-1 transition-all ${
                  viewMode === 'grid' ? 'bg-rose-500/20 text-rose-400 font-semibold' : 'text-muted-foreground hover:text-foreground'
                }`}
                title="Card Grid View"
              >
                <LayoutGrid className="h-3.5 w-3.5" />
                <span>Grid</span>
              </button>
              <button
                onClick={() => setViewMode('table')}
                className={`p-1.5 rounded-md text-xs flex items-center gap-1 transition-all ${
                  viewMode === 'table' ? 'bg-rose-500/20 text-rose-400 font-semibold' : 'text-muted-foreground hover:text-foreground'
                }`}
                title="Table View"
              >
                <TableIcon className="h-3.5 w-3.5" />
                <span>Table</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {loading ? (
        <div className="py-16 text-center text-xs text-muted-foreground animate-pulse flex flex-col items-center gap-2">
          <RefreshCw className="h-6 w-6 animate-spin text-rose-500" />
          <span>Loading admin panel records...</span>
        </div>
      ) : (
        <>
          {activeTab === 'requests' && (
            <div className="space-y-4">

              {/* --- PENDING --- */}
              <div>
                <div className="flex items-center gap-2 mb-2 px-1">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-amber-400">Pending</span>
                  <span className="text-[10px] text-muted-foreground">({pendingRequests.length})</span>
                </div>
                <Card className="border-border/60 bg-black/20 backdrop-blur-md overflow-hidden">
                  <CardContent className="p-0">
                    <div className="overflow-x-auto w-full">
                      <table className="w-full text-left text-xs border-collapse min-w-[550px]">
                        <thead>
                          <tr className="border-b border-border/50 text-muted-foreground font-bold bg-muted/20">
                            <th className="py-3 px-4">User Details</th>
                            <th className="py-3 px-4">Requested At</th>
                            <th className="py-3 px-4 text-right">Actions</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border/30">
                          {pendingRequests.length === 0 ? (
                            <tr>
                              <td colSpan={3} className="py-10 text-center text-muted-foreground">
                                No pending access requests.
                              </td>
                            </tr>
                          ) : (
                            pendingRequests.map(r => {
                              const userName = r.name || r.displayName || (r.email ? r.email.split('@')[0] : 'User');
                              return (
                                <tr key={r.uid} className="hover:bg-muted/10 transition-colors">
                                  <td className="py-3.5 px-4">
                                    <div className="flex items-center gap-2.5">
                                      {r.photoUrl ? (
                                        <img src={r.photoUrl} className="h-8 w-8 rounded-full border border-border" alt="" />
                                      ) : (
                                        <div className="h-8 w-8 rounded-full bg-amber-500/10 text-amber-400 flex items-center justify-center font-bold text-xs">
                                          {userName.charAt(0).toUpperCase()}
                                        </div>
                                      )}
                                      <div>
                                        <div className="font-semibold text-foreground">{userName}</div>
                                        <div className="text-[11px] text-muted-foreground">{r.email}</div>
                                        <div className="text-[10px] text-muted-foreground/60 font-mono">UID: {r.uid}</div>
                                      </div>
                                    </div>
                                  </td>
                                  <td className="py-3.5 px-4 text-muted-foreground text-[11px]">
                                    {r.requested_at ? formatTimestamp(r.requested_at, true) : 'N/A'}
                                  </td>
                                  <td className="py-3.5 px-4 text-right space-x-2">
                                    <Button
                                      onClick={() => handleApproveRequest(r.uid)}
                                      disabled={actionLoading !== null}
                                      size="sm"
                                      className="h-7 text-[11px] bg-emerald-600 hover:bg-emerald-500 text-white font-bold gap-1 w-24 justify-center"
                                    >
                                      <CheckCircle className="h-3 w-3" /> Approve
                                    </Button>
                                    <Button
                                      onClick={() => handleDenyRequest(r.uid)}
                                      disabled={actionLoading !== null}
                                      variant="destructive"
                                      size="sm"
                                      className="h-7 text-[11px] font-bold gap-1 w-24 justify-center"
                                    >
                                      <XCircle className="h-3 w-3" /> Deny
                                    </Button>
                                  </td>
                                </tr>
                              );
                            })
                          )}
                        </tbody>
                      </table>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* --- DENIED --- */}
              <div>
                <div className="flex items-center gap-2 mb-2 px-1">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-rose-400">Denied</span>
                  <span className="text-[10px] text-muted-foreground">({deniedRequests.length})</span>
                </div>
                <Card className="border-border/60 bg-black/20 backdrop-blur-md overflow-hidden">
                  <CardContent className="p-0">
                    <div className="overflow-x-auto w-full">
                      <table className="w-full text-left text-xs border-collapse min-w-[550px]">
                        <thead>
                          <tr className="border-b border-border/50 text-muted-foreground font-bold bg-muted/20">
                            <th className="py-3 px-4">User Details</th>
                            <th className="py-3 px-4">Requested At</th>
                            <th className="py-3 px-4 text-right">Actions</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border/30">
                          {deniedRequests.length === 0 ? (
                            <tr>
                              <td colSpan={3} className="py-10 text-center text-muted-foreground">
                                No denied access requests.
                              </td>
                            </tr>
                          ) : (
                            deniedRequests.map(r => {
                              const userName = r.name || r.displayName || (r.email ? r.email.split('@')[0] : 'User');
                              return (
                                <tr key={r.uid} className="hover:bg-rose-500/5 transition-colors">
                                  <td className="py-3.5 px-4">
                                    <div className="flex items-center gap-2.5">
                                      {r.photoUrl ? (
                                        <img src={r.photoUrl} className="h-8 w-8 rounded-full border border-rose-500/20 opacity-60" alt="" />
                                      ) : (
                                        <div className="h-8 w-8 rounded-full bg-rose-500/10 text-rose-400 flex items-center justify-center font-bold text-xs opacity-60">
                                          {userName.charAt(0).toUpperCase()}
                                        </div>
                                      )}
                                      <div>
                                        <div className="font-semibold text-foreground/70">{userName}</div>
                                        <div className="text-[11px] text-muted-foreground/70">{r.email}</div>
                                        <div className="text-[10px] text-muted-foreground/50 font-mono">UID: {r.uid}</div>
                                      </div>
                                    </div>
                                  </td>
                                  <td className="py-3.5 px-4 text-muted-foreground/70 text-[11px]">
                                    {r.requested_at ? formatTimestamp(r.requested_at, true) : 'N/A'}
                                  </td>
                                  <td className="py-3.5 px-4 text-right">
                                    <Button
                                      onClick={() => handleApproveRequest(r.uid)}
                                      disabled={actionLoading !== null}
                                      size="sm"
                                      className="h-7 text-[11px] bg-emerald-600 hover:bg-emerald-500 text-white font-bold gap-1 w-24 justify-center"
                                    >
                                      <CheckCircle className="h-3 w-3" /> Approve
                                    </Button>
                                  </td>
                                </tr>
                              );
                            })
                          )}
                        </tbody>
                      </table>
                    </div>
                  </CardContent>
                </Card>
              </div>

            </div>
          )}

          {/* TAB 2: USER MANAGEMENT */}
          {activeTab === 'users' && (
            <Card className="border-border/60 bg-black/20 backdrop-blur-md overflow-hidden">
              <CardContent className="p-0">
                <div className="overflow-x-auto w-full">
                  <table className="w-full text-left text-xs border-collapse min-w-[600px]">
                    <thead>
                      <tr className="border-b border-border/50 text-muted-foreground font-bold bg-muted/20">
                        <th className="py-3 px-4">User</th>
                        <th className="py-3 px-4">Role</th>
                        <th className="py-3 px-4">Access Status</th>
                        <th className="py-3 px-4 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/30">
                      {users.length === 0 ? (
                        <tr>
                          <td colSpan={4} className="py-12 text-center text-muted-foreground">
                            No registered users found.
                          </td>
                        </tr>
                      ) : (
                        users.map(u => {
                          const claims = u.custom_claims || {};
                          const isAdmin = claims.role === 'admin';
                          const isBlocked = claims.blocked === true;

                          return (
                            <tr key={u.uid} className="hover:bg-muted/10 transition-colors">
                              <td className="py-3.5 px-4">
                                <div className="flex items-center gap-2.5">
                                  {u.photoUrl ? (
                                    <img src={u.photoUrl} className="h-8 w-8 rounded-full border border-border" alt="" />
                                  ) : (
                                    <div className="h-8 w-8 rounded-full bg-rose-500/10 text-rose-500 flex items-center justify-center font-bold text-xs">
                                      {u.displayName ? u.displayName.charAt(0).toUpperCase() : "U"}
                                    </div>
                                  )}
                                  <div>
                                    <div className="font-semibold text-foreground flex items-center gap-1.5">
                                      {u.displayName || "Unknown User"}
                                      {isAdmin && <Shield className="h-3 w-3 text-rose-500 shrink-0" />}
                                    </div>
                                    <div className="text-[11px] text-muted-foreground">{u.email}</div>
                                    <div className="text-[10px] text-muted-foreground/60 font-mono">UID: {u.uid}</div>
                                  </div>
                                </div>
                              </td>
                              <td className="py-3.5 px-4">
                                {isAdmin ? (
                                  <Badge className="w-16 inline-flex justify-center bg-rose-500/10 text-rose-400 border border-rose-500/20 text-[10px] font-bold px-2 py-0.5 rounded-full">Admin</Badge>
                                ) : (
                                  <Badge className="w-16 inline-flex justify-center bg-muted text-muted-foreground border border-border text-[10px] font-semibold px-2 py-0.5 rounded-full">User</Badge>
                                )}
                              </td>
                              <td className="py-3.5 px-4">
                                {u.access_status === 'blocked' ? (
                                  <Badge className="w-32 inline-flex justify-center bg-rose-500/10 text-rose-400 border border-rose-500/20 text-[10px] font-bold px-2 py-0.5 rounded-full">Blocked</Badge>
                                ) : u.access_status === 'authorized' ? (
                                  <Badge className="w-32 inline-flex justify-center bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-bold px-2 py-0.5 rounded-full">Authorized</Badge>
                                ) : u.access_status === 'pending' ? (
                                  <Badge className="w-32 inline-flex justify-center bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[10px] font-bold px-2 py-0.5 rounded-full">Pending</Badge>
                                ) : u.access_status === 'denied' ? (
                                  <Badge className="w-32 inline-flex justify-center bg-rose-500/10 text-rose-400 border border-rose-500/20 text-[10px] font-bold px-2 py-0.5 rounded-full">Denied</Badge>
                                ) : (
                                  <Badge className="w-32 inline-flex justify-center bg-slate-500/10 text-slate-400 border border-slate-500/20 text-[10px] font-bold px-2 py-0.5 rounded-full">Not Yet Requested</Badge>
                                )}
                              </td>

                              <td className="py-3.5 px-4 text-right space-x-2">
                                {isAdmin ? (
                                  <span className="text-[10px] text-muted-foreground/60 font-medium flex items-center justify-end gap-1">
                                    <Lock className="h-3 w-3 text-muted-foreground/40" /> Protected Admin
                                  </span>
                                ) : (
                                  <>
                                    {u.access_status === 'pending' && (
                                      <Button
                                        onClick={() => handleApproveRequest(u.uid)}
                                        disabled={actionLoading !== null}
                                        size="sm"
                                        className="h-7 text-[11px] bg-emerald-600 hover:bg-emerald-500 text-white font-bold gap-1 w-24 justify-center"
                                      >
                                        <CheckCircle className="h-3 w-3" /> Approve
                                      </Button>
                                    )}
                                    <Button
                                      onClick={() => handleToggleBlock(u.uid, isBlocked)}
                                      disabled={actionLoading !== null}
                                      variant={isBlocked ? "outline" : "destructive"}
                                      size="sm"
                                      className="h-7 text-[11px] font-bold w-24 justify-center"
                                    >
                                      {isBlocked ? "Unblock" : "Block User"}
                                    </Button>
                                  </>
                                )}
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* TAB 3: ALL TICKET TRACKERS */}
          {activeTab === 'jobs' && (
            <>
              {jobs.length === 0 ? (
                <Card className="border-border/60 bg-black/20 backdrop-blur-md p-12 text-center text-muted-foreground">
                  No active monitor tasks found.
                </Card>
              ) : filteredJobs.length === 0 ? (
                <Card className="border-border/60 bg-black/20 backdrop-blur-md p-12 text-center text-muted-foreground">
                  No jobs match your search.
                </Card>
              ) : viewMode === 'grid' ? (
                /* RESPONSIVE GRID CARD VIEW */
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full">
                  {filteredJobs.map(j => {
                    const notifConfStr = j.notification_config?.webhook_url
                      ? j.notification_config.webhook_url
                      : j.notification_config?.recipient_email
                      ? j.notification_config.recipient_email
                      : JSON.stringify(j.notification_config || {});

                    return (
                      <Card key={j.id} className="border border-border/60 bg-black/30 backdrop-blur-md hover:border-rose-500/30 transition-all rounded-xl overflow-hidden flex flex-col justify-between w-full">
                        <div>
                          {/* Header */}
                          <div className="p-3.5 sm:p-4 border-b border-border/40 bg-muted/10">
                            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
                              <div className="min-w-0 flex-1">
                                <div className="flex items-center gap-1.5">
                                  <Film className="h-4 w-4 text-rose-400 shrink-0" />
                                  {j.url ? (
                                    <a
                                      href={j.url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="font-bold text-foreground text-sm leading-snug break-words hover:text-rose-400 transition-colors flex items-center gap-1 group"
                                      title={j.url}
                                    >
                                      {j.movie_name}
                                      <ExternalLink className="h-3 w-3 shrink-0 opacity-0 group-hover:opacity-70 transition-opacity" />
                                    </a>
                                  ) : (
                                    <h3 className="font-bold text-foreground text-sm leading-snug break-words">{j.movie_name}</h3>
                                  )}
                                </div>
                                <div className="flex flex-wrap items-center gap-2 mt-1.5 text-[11px] text-muted-foreground">
                                  <span className="font-mono bg-muted/40 px-1.5 py-0.5 rounded text-[10px]">#{j.id}</span>
                                  <span className="flex items-center gap-1">
                                    <Clock className="h-3 w-3 text-muted-foreground/70" />
                                    {formatTimestamp(j.created_at, true)}
                                  </span>
                                  {(j.language || j.params?.language || j.format || j.params?.format) && (
                                    <div className="flex items-center gap-1">
                                      {(j.language || j.params?.language) && (
                                        <Badge variant="outline" className="text-[9px] font-bold border-rose-500/30 text-rose-400 bg-rose-500/10 px-1.5 py-0.5">
                                          {j.language || j.params?.language}
                                        </Badge>
                                      )}
                                      {(j.format || j.params?.format) && (
                                        <Badge variant="outline" className="text-[9px] font-extrabold border-amber-500/30 text-amber-400 bg-amber-500/10 px-1.5 py-0.5">
                                          {j.format || j.params?.format}
                                        </Badge>
                                      )}
                                    </div>
                                  )}
                                </div>
                              </div>

                              <div className="flex items-center gap-2 self-start sm:self-auto shrink-0">
                                <Badge className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ${
                                  j.status.toLowerCase() === 'running' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                                  j.status.toLowerCase() === 'success' ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' :
                                  j.status.toLowerCase() === 'stopped' ? 'bg-muted text-muted-foreground border border-border' :
                                  'bg-rose-500/10 text-rose-400 border-rose-500/20'
                                }`}>
                                  {j.status}
                                </Badge>

                                {j.status === 'Running' && (
                                  <Button
                                    onClick={() => setJobToStop(j)}
                                    disabled={actionLoading !== null}
                                    variant="secondary"
                                    size="sm"
                                    className="h-7 px-2.5 text-[10px] font-bold cursor-pointer"
                                  >
                                    Stop
                                  </Button>
                                )}
                                <Button
                                  onClick={() => setJobToDelete(j)}
                                  disabled={actionLoading !== null}
                                  variant="destructive"
                                  size="sm"
                                  className="h-7 px-2.5 text-[10px] font-bold cursor-pointer"
                                >
                                  Delete
                                </Button>
                              </div>
                            </div>
                          </div>

                          {/* Body */}
                          <div className="p-3.5 sm:p-4 space-y-3 text-xs">
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                              {/* Creator */}
                              <div className="bg-muted/20 p-2.5 rounded-lg border border-border/30 overflow-hidden">
                                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground/70 block mb-0.5">Creator</span>
                                <div className="font-semibold text-foreground truncate">{j.user_name || "Unknown User"}</div>
                                {j.user_email && <div className="text-[11px] text-muted-foreground truncate">{j.user_email}</div>}
                                <div className="text-[10px] text-muted-foreground/60 font-mono mt-0.5 truncate">UID: {j.created_by || "System"}</div>
                              </div>

                              {/* Channel & Provider */}
                              <div className="bg-muted/20 p-2.5 rounded-lg border border-border/30 space-y-0.5 overflow-hidden">
                                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground/70 block mb-0.5">Notification Channel</span>
                                <div className="flex items-center gap-1.5 text-foreground font-semibold text-[11px] capitalize">
                                  <Radio className="h-3 w-3 text-rose-400 shrink-0" />
                                  <span>{j.service_provider || "bookmyshow"}</span>
                                </div>
                                <div className="flex items-center gap-1.5 text-muted-foreground text-[11px] capitalize">
                                  <Bell className="h-3 w-3 text-emerald-400 shrink-0" />
                                  <span>{j.notification_medium || "email"}</span>
                                </div>
                                <div className="text-[10px] text-muted-foreground/70 truncate font-mono" title={notifConfStr}>
                                  {notifConfStr}
                                </div>
                              </div>
                            </div>

                            {/* Target Date & Monitored Theatres */}
                            <div className="bg-muted/10 p-2.5 rounded-lg border border-border/30 space-y-1">
                              <div className="flex items-center justify-between text-muted-foreground">
                                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground/70">Target Date & Theatres</span>
                                <span className="flex items-center gap-1 text-[11px] text-foreground font-semibold">
                                  <Calendar className="h-3.5 w-3.5 text-rose-400 shrink-0" />
                                  {formatBmsDate(j.date_str)}
                                </span>
                              </div>
                              <div className="text-[11px] text-muted-foreground leading-relaxed break-words">
                                {j.theatres?.join(', ') || "All Theatres"}
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* Footer: Last Check Result */}
                        <div className="p-3.5 sm:p-4 pt-0">
                          <div className="bg-black/50 p-2.5 rounded-lg border border-border/40 text-[11px]">
                            <div className="flex items-center justify-between text-muted-foreground mb-1">
                              <span className="text-[10px] font-bold uppercase tracking-wider flex items-center gap-1 text-muted-foreground">
                                <Info className="h-3 w-3 text-rose-400 shrink-0" /> Last Checked
                              </span>
                              <span className="text-[10px] text-muted-foreground">{formatTimestamp(j.last_checked_at, true)}</span>
                            </div>
                            <div className="text-foreground/90 font-mono text-[11px] leading-snug break-all">
                              {j.last_result || "No checks performed yet."}
                            </div>
                          </div>
                        </div>
                      </Card>
                    );
                  })}
                </div>
              ) : (
                /* RESPONSIVE TABLE VIEW (SCROLLABLE) */
                <Card className="border-border/60 bg-black/20 backdrop-blur-md overflow-hidden">
                  <CardContent className="p-0">
                    <div className="overflow-x-auto w-full">
                      <table className="w-full text-left text-xs border-collapse min-w-[850px]">
                        <thead>
                          <tr className="border-b border-border/50 text-muted-foreground font-bold bg-muted/20">
                            <th className="py-3 px-4">Movie & Created</th>
                            <th className="py-3 px-4">Creator</th>
                            <th className="py-3 px-4">Channel</th>
                            <th className="py-3 px-4">Target Date & Theatres</th>
                            <th className="py-3 px-4">Last Check & Result</th>
                            <th className="py-3 px-4 text-right">Actions</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border/30">
                          {filteredJobs.map(j => {
                            const notifConfStr = j.notification_config?.webhook_url
                              ? j.notification_config.webhook_url
                              : j.notification_config?.recipient_email
                              ? j.notification_config.recipient_email
                              : JSON.stringify(j.notification_config || {});

                            return (
                              <tr key={j.id} className="hover:bg-muted/10 transition-colors">
                                <td className="py-3.5 px-4 space-y-1">
                                  <div className="font-semibold text-foreground flex items-center gap-1.5">
                                    <Film className="h-3.5 w-3.5 text-rose-400 shrink-0" />
                                    {j.url ? (
                                      <a
                                        href={j.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="hover:text-rose-400 transition-colors flex items-center gap-1 group"
                                        title={j.url}
                                      >
                                        {j.movie_name}
                                        <ExternalLink className="h-3 w-3 shrink-0 opacity-0 group-hover:opacity-70 transition-opacity" />
                                      </a>
                                    ) : (
                                      j.movie_name
                                    )}
                                  </div>
                                  <div className="text-[10px] font-mono text-muted-foreground flex items-center gap-1.5 flex-wrap">
                                    <span>Job #{j.id}</span>
                                    {(j.language || j.params?.language) && (
                                      <Badge variant="outline" className="text-[9px] font-bold border-rose-500/30 text-rose-400 bg-rose-500/10 px-1.5 py-0.5">
                                        {j.language || j.params?.language}
                                      </Badge>
                                    )}
                                    {(j.format || j.params?.format) && (
                                      <Badge variant="outline" className="text-[9px] font-extrabold border-amber-500/30 text-amber-400 bg-amber-500/10 px-1.5 py-0.5">
                                        {j.format || j.params?.format}
                                      </Badge>
                                    )}
                                  </div>
                                  <div className="text-[10px] text-muted-foreground flex items-center gap-1">
                                    <Clock className="h-3 w-3 shrink-0" />
                                    <span>{formatTimestamp(j.created_at, true)}</span>
                                  </div>
                                </td>
                                <td className="py-3.5 px-4 space-y-0.5">
                                  <div className="font-semibold text-foreground">{j.user_name || "Unknown User"}</div>
                                  {j.user_email && <div className="text-[11px] text-muted-foreground">{j.user_email}</div>}
                                  <div className="text-[10px] text-muted-foreground/60 font-mono">UID: {j.created_by || "System"}</div>
                                </td>
                                <td className="py-3.5 px-4 space-y-1">
                                  <div className="flex items-center gap-1.5 text-foreground font-medium capitalize">
                                    <Radio className="h-3 w-3 text-rose-400 shrink-0" />
                                    <span>{j.service_provider || "bookmyshow"}</span>
                                  </div>
                                  <div className="flex items-center gap-1.5 text-muted-foreground text-[10px] capitalize">
                                    <Bell className="h-3 w-3 text-emerald-400 shrink-0" />
                                    <span>{j.notification_medium || "email"}</span>
                                  </div>
                                  <div className="text-[9px] text-muted-foreground/70 truncate max-w-[150px]" title={notifConfStr}>
                                    {notifConfStr}
                                  </div>
                                </td>
                                <td className="py-3.5 px-4 text-muted-foreground space-y-1">
                                  <div className="flex items-center gap-1.5 text-foreground font-medium">
                                    <Calendar className="h-3 w-3 shrink-0 text-rose-400" />
                                    {formatBmsDate(j.date_str)}
                                  </div>
                                  <div className="truncate max-w-[180px] text-[11px]" title={j.theatres?.join(', ')}>
                                    {j.theatres?.join(', ')}
                                  </div>
                                </td>
                                <td className="py-3.5 px-4 space-y-1">
                                  <Badge className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                                    j.status.toLowerCase() === 'running' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                                    j.status.toLowerCase() === 'success' ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' :
                                    j.status.toLowerCase() === 'stopped' ? 'bg-muted text-muted-foreground border border-border' :
                                    'bg-rose-500/10 text-rose-400 border-rose-500/20'
                                  }`}>
                                    {j.status}
                                  </Badge>
                                  <div className="text-[10px] text-muted-foreground">
                                    Checked: {formatTimestamp(j.last_checked_at, true)}
                                  </div>
                                  <div className="text-[10px] text-muted-foreground/90 font-mono truncate max-w-[180px]" title={j.last_result}>
                                    {j.last_result || "N/A"}
                                  </div>
                                </td>
                                <td className="py-3.5 px-4 text-right space-x-2">
                                  {j.status === 'Running' && (
                                    <Button
                                      onClick={() => setJobToStop(j)}
                                      disabled={actionLoading !== null}
                                      variant="secondary"
                                      size="sm"
                                      className="h-7 text-[10px] font-bold cursor-pointer"
                                    >
                                      Stop
                                    </Button>
                                  )}
                                  <Button
                                    onClick={() => setJobToDelete(j)}
                                    disabled={actionLoading !== null}
                                    variant="destructive"
                                    size="sm"
                                    className="h-7 text-[10px] font-bold cursor-pointer"
                                  >
                                    Delete
                                  </Button>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </>
      )}

      {/* Tab: Pricing Configuration */}
      {!paymentsDisabled && activeTab === 'pricing' && (
        <div className="space-y-6">
          {pricingMsg && (
            <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 shrink-0" />
              <span>{pricingMsg}</span>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="border border-border/80 glassmorphism p-5 rounded-xl">
              <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider block">SMS Price</span>
              <span className="text-2xl font-bold text-foreground">₹{((pricingConfig?.sms_paise ?? 50) / 100).toFixed(2)}</span>
              <span className="text-[11px] text-muted-foreground block">({pricingConfig?.sms_paise ?? 50} paise)</span>
            </Card>
            <Card className="border border-border/80 glassmorphism p-5 rounded-xl">
              <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider block">WhatsApp Price</span>
              <span className="text-2xl font-bold text-emerald-400">₹{((pricingConfig?.whatsapp_paise ?? 100) / 100).toFixed(2)}</span>
              <span className="text-[11px] text-muted-foreground block">({pricingConfig?.whatsapp_paise ?? 100} paise)</span>
            </Card>
            <Card className="border border-border/80 glassmorphism p-5 rounded-xl">
              <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider block">Phone Call Price</span>
              <span className="text-2xl font-bold text-rose-400">₹{((pricingConfig?.phone_call_paise ?? 150) / 100).toFixed(2)}</span>
              <span className="text-[11px] text-muted-foreground block">({pricingConfig?.phone_call_paise ?? 150} paise)</span>
            </Card>
          </div>

          <Card className="border border-border/80 glassmorphism p-6 rounded-2xl">
            <CardHeader className="p-0 pb-4 border-b border-border/40 mb-4">
              <CardTitle className="text-base font-bold flex items-center gap-2">
                <DollarSign className="h-4 w-4 text-rose-400" />
                Update Notification Pricing Schedule
              </CardTitle>
              <p className="text-xs text-muted-foreground">
                Price changes atomically supersede current rates and require a mandatory audit explanation.
              </p>
            </CardHeader>

            <form onSubmit={handleUpdatePricing} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">SMS (paise)</label>
                  <Input
                    type="number"
                    min="0"
                    value={smsPaise}
                    onChange={(e) => setSmsPaise(e.target.value)}
                    className="h-9 text-xs bg-muted/20"
                    placeholder="50"
                  />
                  <span className="text-[10px] text-muted-foreground">₹{((parseInt(smsPaise, 10) || 0) / 100).toFixed(2)}</span>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">WhatsApp (paise)</label>
                  <Input
                    type="number"
                    min="0"
                    value={whatsappPaise}
                    onChange={(e) => setWhatsappPaise(e.target.value)}
                    className="h-9 text-xs bg-muted/20"
                    placeholder="100"
                  />
                  <span className="text-[10px] text-muted-foreground">₹{((parseInt(whatsappPaise, 10) || 0) / 100).toFixed(2)}</span>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">Phone Call (paise)</label>
                  <Input
                    type="number"
                    min="0"
                    value={phoneCallPaise}
                    onChange={(e) => setPhoneCallPaise(e.target.value)}
                    className="h-9 text-xs bg-muted/20"
                    placeholder="150"
                  />
                  <span className="text-[10px] text-muted-foreground">₹{((parseInt(phoneCallPaise, 10) || 0) / 100).toFixed(2)}</span>
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground">Audit Reason Note (Mandatory)</label>
                <Input
                  value={pricingNote}
                  onChange={(e) => setPricingNote(e.target.value)}
                  placeholder="e.g., Telecom operator tariff revision for Q3"
                  className="h-9 text-xs bg-muted/20"
                  required
                />
              </div>

              <Button
                type="submit"
                disabled={pricingUpdating}
                className="h-9 px-5 text-xs font-semibold bg-rose-500 hover:bg-rose-600 cursor-pointer"
              >
                {pricingUpdating ? 'Updating...' : 'Save & Log Audit'}
              </Button>
            </form>
          </Card>

          {/* Pricing History */}
          <Card className="border border-border/80 glassmorphism p-6 rounded-2xl space-y-4">
            <h3 className="text-sm font-bold text-foreground">Historical Pricing Configurations</h3>
            {pricingHistory.length === 0 ? (
              <p className="text-xs text-muted-foreground">No historical records found.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-border/50 text-muted-foreground">
                      <th className="pb-2">Effective From</th>
                      <th className="pb-2">SMS</th>
                      <th className="pb-2">WhatsApp</th>
                      <th className="pb-2">Call</th>
                      <th className="pb-2">Status</th>
                      <th className="pb-2">Audit Reason</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/30">
                    {pricingHistory.map((item) => (
                      <tr key={item.id} className="hover:bg-muted/10">
                        <td className="py-2.5 text-muted-foreground whitespace-nowrap">
                          {item.effective_from ? new Date(item.effective_from).toLocaleString() : 'System Seed'}
                        </td>
                        <td className="py-2.5">₹{(item.sms_paise / 100).toFixed(2)}</td>
                        <td className="py-2.5">₹{(item.whatsapp_paise / 100).toFixed(2)}</td>
                        <td className="py-2.5">₹{(item.phone_call_paise / 100).toFixed(2)}</td>
                        <td className="py-2.5">
                          {item.is_current ? (
                            <Badge className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[9px]">
                              Active
                            </Badge>
                          ) : (
                            <Badge variant="outline" className="text-[9px] text-muted-foreground">
                              Superseded
                            </Badge>
                          )}
                        </td>
                        <td className="py-2.5 text-muted-foreground">{item.note || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Tab: User Wallets & Adjustments */}
      {!paymentsDisabled && activeTab === 'wallets' && (
        <div className="space-y-6">
          <Card className="border border-border/80 glassmorphism p-6 rounded-2xl space-y-4">
            <h3 className="text-sm font-bold text-foreground">User Wallet Lookup & Adjustment</h3>
            <div className="flex flex-col sm:flex-row items-center gap-3">
              <Input
                placeholder="Enter User Firebase UID..."
                value={walletSearchUid}
                onChange={(e) => setWalletSearchUid(e.target.value)}
                className="h-9 text-xs bg-muted/20"
              />
              <Button
                onClick={handleSearchUserWallet}
                disabled={walletAdjusting}
                className="w-full sm:w-auto h-9 px-5 text-xs font-semibold bg-rose-500 hover:bg-rose-600 cursor-pointer"
              >
                Search Wallet
              </Button>
            </div>

            {walletMsg && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs">
                {walletMsg}
              </div>
            )}

            {searchedWallet && (
              <div className="pt-4 border-t border-border/40 space-y-4">
                <div className="flex items-center justify-between p-4 rounded-xl border border-rose-500/20 bg-rose-500/5">
                  <div>
                    <span className="text-[10px] font-bold text-muted-foreground uppercase">Current Balance</span>
                    <span className="text-2xl font-bold text-rose-400 block">₹{searchedWallet.balance_inr.toFixed(2)}</span>
                    <span className="text-[11px] text-muted-foreground">({searchedWallet.balance_paise} paise)</span>
                  </div>
                  <Badge className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs">
                    UID: {searchedWallet.uid}
                  </Badge>
                </div>

                <form onSubmit={handleAdjustWallet} className="space-y-3 pt-2">
                  <h4 className="text-xs font-bold text-foreground uppercase tracking-wider">Adjust Balance</h4>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div className="space-y-1">
                      <label className="text-xs text-muted-foreground">Action</label>
                      <select
                        value={walletAdjustDirection}
                        onChange={(e) => setWalletAdjustDirection(e.target.value as any)}
                        className="w-full h-9 rounded-lg border border-border bg-[#121217] px-3 text-xs text-foreground"
                      >
                        <option value="CREDIT">CREDIT (Add funds)</option>
                        <option value="DEBIT">DEBIT (Deduct funds)</option>
                      </select>
                    </div>

                    <div className="space-y-1">
                      <label className="text-xs text-muted-foreground">Amount (paise)</label>
                      <Input
                        type="number"
                        min="1"
                        value={walletAdjustAmount}
                        onChange={(e) => setWalletAdjustAmount(e.target.value)}
                        className="h-9 text-xs bg-muted/20"
                        placeholder="100"
                      />
                      <span className="text-[10px] text-muted-foreground">₹{((parseInt(walletAdjustAmount, 10) || 0) / 100).toFixed(2)}</span>
                    </div>

                    <div className="space-y-1">
                      <label className="text-xs text-muted-foreground">Reason (Mandatory Audit)</label>
                      <Input
                        value={walletAdjustReason}
                        onChange={(e) => setWalletAdjustReason(e.target.value)}
                        placeholder="e.g. Customer loyalty bonus"
                        className="h-9 text-xs bg-muted/20"
                        required
                      />
                    </div>
                  </div>

                  <Button
                    type="submit"
                    disabled={walletAdjusting}
                    className="h-9 px-5 text-xs font-semibold bg-rose-500 hover:bg-rose-600 cursor-pointer"
                  >
                    {walletAdjusting ? 'Processing...' : 'Submit Balance Adjustment'}
                  </Button>
                </form>

                {/* Ledger for user */}
                <div className="pt-4 border-t border-border/40 space-y-2">
                  <h4 className="text-xs font-bold text-foreground">Transaction History ({searchedWallet.transactions?.length || 0})</h4>
                  {searchedWallet.transactions?.length === 0 ? (
                    <p className="text-xs text-muted-foreground">No transactions found for this user.</p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className="border-b border-border/50 text-muted-foreground">
                            <th className="pb-2">Date</th>
                            <th className="pb-2">Type</th>
                            <th className="pb-2">Description</th>
                            <th className="pb-2 text-right">Amount</th>
                            <th className="pb-2 text-right">Balance</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border/30">
                          {searchedWallet.transactions.map((tx: any) => (
                            <tr key={tx.id} className="hover:bg-muted/10">
                              <td className="py-2 text-muted-foreground whitespace-nowrap">
                                {tx.created_at ? new Date(tx.created_at).toLocaleString() : '—'}
                              </td>
                              <td className="py-2">
                                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-muted/40">
                                  {tx.type}
                                </span>
                              </td>
                              <td className="py-2 text-foreground truncate max-w-xs">{tx.description}</td>
                              <td className={`py-2 text-right font-bold ${tx.direction === 'CREDIT' ? 'text-emerald-400' : 'text-rose-400'}`}>
                                {tx.direction === 'CREDIT' ? '+' : '-'}₹{(tx.amount_paise / 100).toFixed(2)}
                              </td>
                              <td className="py-2 text-right font-mono text-muted-foreground">
                                ₹{(tx.balance_after_paise / 100).toFixed(2)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Tab: Cashfree Refunds */}
      {!paymentsDisabled && activeTab === 'refunds' && (
        <Card className="border border-border/80 glassmorphism p-6 rounded-2xl space-y-4">
          <CardHeader className="p-0 pb-4 border-b border-border/40">
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <RotateCcw className="h-4 w-4 text-rose-400" />
              Initiate Cashfree Gateway Refund
            </CardTitle>
            <p className="text-xs text-muted-foreground">
              Directly refunds a customer's original payment method via Cashfree API.
            </p>
          </CardHeader>

          {refundMsg && (
            <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 shrink-0" />
              <span>{refundMsg}</span>
            </div>
          )}

          <form onSubmit={handleProcessCashfreeRefund} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground">Cashfree Order ID</label>
                <Input
                  value={refundOrderId}
                  onChange={(e) => setRefundOrderId(e.target.value)}
                  placeholder="e.g. order_12345678"
                  className="h-9 text-xs bg-muted/20"
                  required
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground">Refund Amount (paise)</label>
                <Input
                  type="number"
                  min="1"
                  value={refundAmountPaise}
                  onChange={(e) => setRefundAmountPaise(e.target.value)}
                  placeholder="e.g. 500 (₹5.00)"
                  className="h-9 text-xs bg-muted/20"
                  required
                />
                <span className="text-[10px] text-muted-foreground">
                  ₹{((parseInt(refundAmountPaise, 10) || 0) / 100).toFixed(2)}
                </span>
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-foreground">Audit Reason</label>
              <Input
                value={refundReason}
                onChange={(e) => setRefundReason(e.target.value)}
                placeholder="e.g., Customer requested gateway refund due to duplicate payment"
                className="h-9 text-xs bg-muted/20"
                required
              />
            </div>

            <Button
              type="submit"
              disabled={refunding}
              className="h-9 px-5 text-xs font-semibold bg-rose-500 hover:bg-rose-600 cursor-pointer"
            >
              {refunding ? 'Processing Refund...' : 'Initiate Gateway Refund'}
            </Button>
          </form>
        </Card>
      )}

      {/* Tab: Admin Audit Logs */}
      {activeTab === 'audit_logs' && (
        <Card className="border border-border/80 glassmorphism p-6 rounded-2xl space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
              <FileText className="h-4 w-4 text-rose-400" />
              Immutable Administrative & Financial Audit Logs
            </h3>
            <span className="text-xs text-muted-foreground">{auditLogs.length} events logged</span>
          </div>

          {auditLogs.length === 0 ? (
            <p className="text-xs text-muted-foreground py-6 text-center">No audit logs found.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-border/50 text-muted-foreground font-semibold">
                    <th className="pb-2.5">Date & Time</th>
                    <th className="pb-2.5">Admin Email</th>
                    <th className="pb-2.5">Action</th>
                    <th className="pb-2.5">Target UID</th>
                    <th className="pb-2.5">Amount</th>
                    <th className="pb-2.5">Reason</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/30">
                  {auditLogs.map((log) => (
                    <tr key={log.id} className="hover:bg-muted/10">
                      <td className="py-2.5 text-muted-foreground whitespace-nowrap">
                        {log.created_at ? new Date(log.created_at).toLocaleString() : '—'}
                      </td>
                      <td className="py-2.5 text-foreground">{log.admin_email}</td>
                      <td className="py-2.5">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-muted/40 border border-border">
                          {log.action_type}
                        </span>
                      </td>
                      <td className="py-2.5 text-muted-foreground font-mono">{log.target_uid || '—'}</td>
                      <td className="py-2.5 font-bold text-foreground">
                        {log.amount_paise ? `₹${(log.amount_paise / 100).toFixed(2)}` : '—'}
                      </td>
                      <td className="py-2.5 text-muted-foreground max-w-xs truncate">{log.reason || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {/* Confirm Admin Stop Job Modal */}
      <ConfirmModal
        isOpen={!!jobToStop}
        onClose={() => setJobToStop(null)}
        onConfirm={async () => {
          if (jobToStop) {
            await handleAdminStopJob(jobToStop.id);
            setJobToStop(null);
          }
        }}
        title="Stop Monitoring Job"
        description={
          <>Are you sure you want to stop job <strong className="text-foreground font-mono">#{jobToStop?.id}</strong> ({jobToStop?.movie_name || 'Movie Tracker'})?</>
        }
        confirmText="Stop Job"
        cancelText="Cancel"
        variant="warning"
        icon="stop"
        isLoading={actionLoading === jobToStop?.id}
      />

      {/* Confirm Admin Delete Job Modal */}
      <ConfirmModal
        isOpen={!!jobToDelete}
        onClose={() => setJobToDelete(null)}
        onConfirm={async () => {
          if (jobToDelete) {
            await handleAdminDeleteJob(jobToDelete.id);
            setJobToDelete(null);
          }
        }}
        title="Delete Monitoring Job"
        description={
          <>Are you sure you want to permanently delete job <strong className="text-foreground font-mono">#{jobToDelete?.id}</strong> ({jobToDelete?.movie_name || 'Movie Tracker'})? This action cannot be undone.</>
        }
        confirmText="Delete Job"
        cancelText="Cancel"
        variant="danger"
        icon="delete"
        isLoading={actionLoading === jobToDelete?.id}
      />

    </main>
  );
}
