import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Shield, AlertTriangle, RefreshCw, Film, Calendar, Clock, Radio, Bell, Info } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { authenticatedFetch } from '../utils/api';
import { formatBmsDate, formatTimestamp } from '../utils/formatters';

export function AdminDashboard() {
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
        setRequests(prev => prev.filter(r => r.uid !== uid));
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

  const handleRoleChange = async (uid: string, newRole: string) => {
    setActionLoading(uid);
    try {
      const res = await authenticatedFetch(`/admin/users/${uid}/role`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: newRole })
      });
      if (res.ok) {
        setUsers(prev => prev.map(u => u.uid === uid ? { ...u, custom_claims: { ...u.custom_claims, role: newRole } } : u));
      } else {
        const data = await res.json();
        alert(data.detail || "Failed to update role.");
      }
    } catch (e: any) {
      alert("Error updating role: " + e.message);
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
    <main className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border/60 pb-6">
        <div>
          <div className="flex items-center gap-2">
            <Shield className="h-6 w-6 text-rose-500" />
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Admin Control Panel</h1>
          </div>
          <p className="text-xs text-muted-foreground">Manage user access and active ticket trackers.</p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            onClick={fetchData}
            disabled={loading}
            variant="outline"
            size="sm"
            className="text-xs gap-1.5"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh Data
          </Button>

          <Button asChild variant="ghost" size="sm" className="text-xs">
            <Link to="/app">Back to App</Link>
          </Button>
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

      <div className="flex gap-2 border-b border-border/40 pb-2">
        <Button
          onClick={() => setActiveTab('requests')}
          variant={activeTab === 'requests' ? 'default' : 'ghost'}
          size="sm"
          className="text-xs font-semibold"
        >
          Access Requests ({requests.length})
        </Button>
        <Button
          onClick={() => setActiveTab('users')}
          variant={activeTab === 'users' ? 'default' : 'ghost'}
          size="sm"
          className="text-xs font-semibold"
        >
          User Management ({users.length})
        </Button>
        <Button
          onClick={() => setActiveTab('jobs')}
          variant={activeTab === 'jobs' ? 'default' : 'ghost'}
          size="sm"
          className="text-xs font-semibold"
        >
          All Ticket Trackers ({jobs.length})
        </Button>
      </div>

      {loading ? (
        <div className="py-16 text-center text-xs text-muted-foreground animate-pulse">
          Loading administration records...
        </div>
      ) : (
        <Card className="border-border/60 bg-black/20 backdrop-blur-md">
          <CardContent className="p-6">
            {activeTab === 'requests' && (
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-border/50 text-muted-foreground font-bold">
                    <th className="pb-3">User</th>
                    <th className="pb-3">UID</th>
                    <th className="pb-3">Requested At</th>
                    <th className="pb-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/30">
                  {requests.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="py-8 text-center text-muted-foreground">No pending access requests.</td>
                    </tr>
                  ) : (
                    requests.map(r => (
                      <tr key={r.uid} className="hover:bg-muted/10">
                        <td className="py-3.5 flex items-center gap-2">
                          {r.photoUrl ? (
                            <img src={r.photoUrl} className="h-7 w-7 rounded-full border border-border" alt="" />
                          ) : (
                            <div className="h-7 w-7 rounded-full bg-rose-500/10 text-rose-500 flex items-center justify-center font-bold text-xs">
                              {r.name ? r.name.charAt(0).toUpperCase() : "U"}
                            </div>
                          )}
                          <div>
                            <div className="font-semibold text-foreground">{r.name}</div>
                            <div className="text-[10px] text-muted-foreground">{r.email}</div>
                          </div>
                        </td>
                        <td className="py-3.5 text-muted-foreground font-mono text-[10px]">{r.uid}</td>
                        <td className="py-3.5 text-muted-foreground text-[11px]">
                          {r.requested_at ? new Date(r.requested_at).toLocaleString() : 'N/A'}
                        </td>
                        <td className="py-3.5 text-right space-x-2">
                          <Button
                            onClick={() => handleApproveRequest(r.uid)}
                            disabled={actionLoading !== null}
                            size="sm"
                            className="h-7 text-[10px] bg-emerald-600 hover:bg-emerald-500 text-white font-bold"
                          >
                            Approve
                          </Button>
                          <Button
                            onClick={() => handleDenyRequest(r.uid)}
                            disabled={actionLoading !== null}
                            variant="destructive"
                            size="sm"
                            className="h-7 text-[10px] font-bold"
                          >
                            Deny
                          </Button>
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
                    <th className="pb-3">Flags</th>
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
                              <div className="font-semibold text-foreground">{u.displayName || "Unknown"}</div>
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
                    <th className="pb-3">Movie & Job Info</th>
                    <th className="pb-3">Creator</th>
                    <th className="pb-3">Provider & Medium</th>
                    <th className="pb-3">Target & Theatres</th>
                    <th className="pb-3">Status & Last Check</th>
                    <th className="pb-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/30">
                  {jobs.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-muted-foreground">No active monitor tasks found.</td>
                    </tr>
                  ) : (
                    jobs.map(j => {
                      const notifConfStr = j.notification_config?.webhook_url
                        ? `Webhook: ${j.notification_config.webhook_url.substring(0, 25)}...`
                        : j.notification_config?.recipient_email
                        ? `Email: ${j.notification_config.recipient_email}`
                        : JSON.stringify(j.notification_config || {});

                      return (
                        <tr key={j.id} className="hover:bg-muted/10">
                          <td className="py-3.5 space-y-1">
                            <div className="font-semibold text-foreground flex items-center gap-1.5">
                              <Film className="h-3.5 w-3.5 text-rose-400 shrink-0" />
                              {j.movie_name}
                            </div>
                            <div className="text-[10px] text-muted-foreground font-mono">Job #{j.id}</div>
                            <div className="text-[10px] text-muted-foreground flex items-center gap-1">
                              <Clock className="h-3 w-3 text-muted-foreground/70 shrink-0" />
                              <span>Created: {formatTimestamp(j.created_at)}</span>
                            </div>
                          </td>
                          <td className="py-3.5 space-y-0.5">
                            <div className="font-semibold text-foreground">{j.user_name || "Unknown User"}</div>
                            {j.user_email && <div className="text-[10px] text-muted-foreground">{j.user_email}</div>}
                            <div className="text-[10px] text-muted-foreground/70 font-mono">UID: {j.created_by || "System"}</div>
                          </td>
                          <td className="py-3.5 space-y-1">
                            <div className="flex items-center gap-1.5">
                              <Radio className="h-3 w-3 text-rose-400 shrink-0" />
                              <span className="font-semibold capitalize text-foreground">{j.service_provider || "bookmyshow"}</span>
                            </div>
                            <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                              <Bell className="h-3 w-3 text-emerald-400 shrink-0" />
                              <span className="capitalize">{j.notification_medium || "email"}</span>
                            </div>
                            <div className="text-[9px] text-muted-foreground/70 truncate max-w-[160px]" title={notifConfStr}>
                              {notifConfStr}
                            </div>
                          </td>
                          <td className="py-3.5 text-muted-foreground space-y-0.5">
                            <div className="flex items-center gap-1.5">
                              <Calendar className="h-3 w-3 shrink-0" />
                              {formatBmsDate(j.date_str)}
                            </div>
                            <div className="truncate max-w-[180px]" title={j.theatres?.join(', ')}>
                              {j.theatres?.join(', ')}
                            </div>
                          </td>
                          <td className="py-3.5 space-y-1">
                            <Badge className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                              j.status.toLowerCase() === 'running' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                              j.status.toLowerCase() === 'success' ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' :
                              j.status.toLowerCase() === 'stopped' ? 'bg-muted text-muted-foreground border border-border' :
                              'bg-rose-500/10 text-rose-400 border-rose-500/20'
                            }`}>
                              {j.status}
                            </Badge>
                            <div className="text-[10px] text-muted-foreground flex items-center gap-1">
                              <Info className="h-3 w-3 text-muted-foreground/70 shrink-0" />
                              <span>Checked: {formatTimestamp(j.last_checked_at)}</span>
                            </div>
                            <div className="text-[10px] text-muted-foreground/80 truncate max-w-[170px]" title={j.last_result}>
                              {j.last_result || "N/A"}
                            </div>
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
                      );
                    })
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
