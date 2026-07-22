import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Shield, AlertTriangle, RefreshCw, Film, Calendar } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { authenticatedFetch } from '../utils/api';
import { formatBmsDate } from '../utils/formatters';

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
