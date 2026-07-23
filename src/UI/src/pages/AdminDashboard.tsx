import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Shield, AlertTriangle, RefreshCw, Film, Calendar, Clock, Radio, Bell, Info, LayoutGrid, Table as TableIcon, User as UserIcon, CheckCircle, XCircle, Lock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { authenticatedFetch } from '../utils/api';
import { formatBmsDate, formatTimestamp } from '../utils/formatters';

export function AdminDashboard() {
  const [activeTab, setActiveTab] = useState<'requests' | 'users' | 'jobs'>('requests');
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');
  const [requests, setRequests] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [jobs, setJobs] = useState<any[]>([]);
  const [counts, setCounts] = useState<{ requests: number; users: number; jobs: number } | null>(null);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchCounts = useCallback(async () => {
    try {
      const res = await authenticatedFetch('/admin/counts');
      if (res.ok) {
        const data = await res.json();
        setCounts(data);
      }
    } catch (e) {
      // ignore count fetch error
    }
  }, []);

  useEffect(() => {
    fetchCounts();
  }, [fetchCounts]);

  const fetchData = useCallback(async () => {
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
        const res = await authenticatedFetch('/api/jobs');
        if (res.ok) setJobs(await res.json());
        else setError("Failed to fetch jobs.");
      }
    } catch (e: any) {
      setError(e.message || "An error occurred fetching admin data.");
    } finally {
      setLoading(false);
    }
  }, [activeTab]);

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
    if (!confirm(`Are you sure you want to delete job #${jobId}?`)) return;
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
            Pending Requests ({requests.length > 0 ? requests.length : (counts ? counts.requests : 0)})
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
        </div>

        {/* View Switcher for Jobs */}
        {activeTab === 'jobs' && (
          <div className="flex items-center gap-1 bg-black/40 border border-border/60 p-1 rounded-lg self-start sm:self-auto">
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
        )}
      </div>

      {loading ? (
        <div className="py-16 text-center text-xs text-muted-foreground animate-pulse flex flex-col items-center gap-2">
          <RefreshCw className="h-6 w-6 animate-spin text-rose-500" />
          <span>Loading admin panel records...</span>
        </div>
      ) : (
        <>
          {/* TAB 1: PENDING / DENIED ACCESS REQUESTS */}
          {activeTab === 'requests' && (
            <Card className="border-border/60 bg-black/20 backdrop-blur-md overflow-hidden">
              <CardContent className="p-0">
                <div className="overflow-x-auto w-full">
                  <table className="w-full text-left text-xs border-collapse min-w-[550px]">
                    <thead>
                      <tr className="border-b border-border/50 text-muted-foreground font-bold bg-muted/20">
                        <th className="py-3 px-4">User Details</th>
                        <th className="py-3 px-4">Status</th>
                        <th className="py-3 px-4">Requested At</th>
                        <th className="py-3 px-4 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/30">
                      {requests.length === 0 ? (
                        <tr>
                          <td colSpan={4} className="py-12 text-center text-muted-foreground">
                            No pending or denied access requests found.
                          </td>
                        </tr>
                      ) : (
                        requests.map(r => {
                          const isDenied = r.status === 'denied';
                          const userName = r.name || r.displayName || (r.email ? r.email.split('@')[0] : 'User');

                          return (
                            <tr key={r.uid} className="hover:bg-muted/10 transition-colors">
                              <td className="py-3.5 px-4">
                                <div className="flex items-center gap-2.5">
                                  {r.photoUrl ? (
                                    <img src={r.photoUrl} className="h-8 w-8 rounded-full border border-border" alt="" />
                                  ) : (
                                    <div className="h-8 w-8 rounded-full bg-rose-500/10 text-rose-500 flex items-center justify-center font-bold text-xs">
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
                              <td className="py-3.5 px-4">
                                {isDenied ? (
                                  <Badge className="w-32 inline-flex justify-center bg-rose-500/10 text-rose-400 border border-rose-500/20 text-[10px] font-bold px-2 py-0.5 rounded-full">Denied</Badge>
                                ) : (
                                  <Badge className="w-32 inline-flex justify-center bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[10px] font-bold px-2 py-0.5 rounded-full">Pending</Badge>
                                )}
                              </td>
                              <td className="py-3.5 px-4 text-muted-foreground text-[11px]">
                                {r.requested_at ? formatTimestamp(r.requested_at) : 'N/A'}
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
                                {!isDenied && (
                                  <Button
                                    onClick={() => handleDenyRequest(r.uid)}
                                    disabled={actionLoading !== null}
                                    variant="destructive"
                                    size="sm"
                                    className="h-7 text-[11px] font-bold gap-1 w-24 justify-center"
                                  >
                                    <XCircle className="h-3 w-3" /> Deny
                                  </Button>
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
              ) : viewMode === 'grid' ? (
                /* RESPONSIVE GRID CARD VIEW */
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full">
                  {jobs.map(j => {
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
                                  <h3 className="font-bold text-foreground text-sm leading-snug break-words">{j.movie_name}</h3>
                                </div>
                                <div className="flex flex-wrap items-center gap-2 mt-1.5 text-[11px] text-muted-foreground">
                                  <span className="font-mono bg-muted/40 px-1.5 py-0.5 rounded text-[10px]">#{j.id}</span>
                                  <span className="flex items-center gap-1">
                                    <Clock className="h-3 w-3 text-muted-foreground/70" />
                                    {formatTimestamp(j.created_at)}
                                  </span>
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
                                    onClick={() => handleAdminStopJob(j.id)}
                                    disabled={actionLoading !== null}
                                    variant="secondary"
                                    size="sm"
                                    className="h-7 px-2.5 text-[10px] font-bold"
                                  >
                                    Stop
                                  </Button>
                                )}
                                <Button
                                  onClick={() => handleAdminDeleteJob(j.id)}
                                  disabled={actionLoading !== null}
                                  variant="destructive"
                                  size="sm"
                                  className="h-7 px-2.5 text-[10px] font-bold"
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
                              <span className="text-[10px] text-muted-foreground">{formatTimestamp(j.last_checked_at)}</span>
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
                          {jobs.map(j => {
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
                                    {j.movie_name}
                                  </div>
                                  <div className="text-[10px] font-mono text-muted-foreground">Job #{j.id}</div>
                                  <div className="text-[10px] text-muted-foreground flex items-center gap-1">
                                    <Clock className="h-3 w-3 shrink-0" />
                                    <span>{formatTimestamp(j.created_at)}</span>
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
                                    Checked: {formatTimestamp(j.last_checked_at)}
                                  </div>
                                  <div className="text-[10px] text-muted-foreground/90 font-mono truncate max-w-[180px]" title={j.last_result}>
                                    {j.last_result || "N/A"}
                                  </div>
                                </td>
                                <td className="py-3.5 px-4 text-right space-x-2">
                                  {j.status === 'Running' && (
                                    <Button
                                      onClick={() => handleAdminStopJob(j.id)}
                                      disabled={actionLoading !== null}
                                      variant="secondary"
                                      size="sm"
                                      className="h-7 text-[10px] font-bold"
                                    >
                                      Stop
                                    </Button>
                                  )}
                                  <Button
                                    onClick={() => handleAdminDeleteJob(j.id)}
                                    disabled={actionLoading !== null}
                                    variant="destructive"
                                    size="sm"
                                    className="h-7 text-[10px] font-bold"
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
    </main>
  );
}
