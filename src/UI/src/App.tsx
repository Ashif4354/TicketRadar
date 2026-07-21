// src/UI/src/App.tsx

import React, { useState, useEffect, useCallback } from 'react';

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
    // Format as YYYY-MM-DD HH:MM:SS
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

  // Logs state
  const [expandedLogs, setExpandedLogs] = useState<{ [jobId: string]: boolean }>({});
  const [jobLogs, setJobLogs] = useState<{ [jobId: string]: string }>({});

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
    try {
      const res = await fetch('/api/jobs');
      if (res.ok) {
        const data = await res.json();
        setJobs(data);
      }
    } catch (err) {
      console.error("Failed to fetch jobs:", err);
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
        // Only poll logs if the job is still running/exists
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
    setTestLoading(true);
    setTestResult(null);

    try {
      const res = await fetch('/api/test-notification', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          medium: testMedium,
          target: testTarget
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
    }
  };

  // Register New Monitor Task submit handler
  const handleCreateMonitorSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormErrors([]);
    setFormSuccess(null);

    const errors: string[] = [];

    // Validations
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

    // Convert date string from YYYY-MM-DD to YYYYMMDD
    const dateFormatted = targetDate.replace(/-/g, '');

    const payload = {
      service_provider: serviceProvider,
      notification_medium: medium,
      notification_config: medium === "Email" 
        ? { recipient_email: email.trim() } 
        : { webhook_url: webhook.trim() },
      check_interval: intervalSec,
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
        setFormSuccess(`Successfully registered monitor #${data.id}! Daemon thread is now active.`);
        setUrl("");
        setTheatres("");
        fetchJobs();
      } else {
        setFormErrors([data.detail || "Failed to create monitoring job."]);
      }
    } catch (err: any) {
      setFormErrors([err.message || "Failed to reach server."]);
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
        // Remove from expanded logs tracker
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

  return (
    <div className="app-container">
      {/* Header */}
      <header className="header">
        <h1 className="gradient-title">🍿 TicketRadar</h1>
        <p className="subtitle">
          Continuously watch movie ticket booking availability for a specific date and theatre list, and receive notifications via Email or Discord Webhook.
        </p>
      </header>

      {/* Config Validation Banner */}
      {config?.config_error && (
        <div className="alert-error" style={{ marginBottom: '2rem' }}>
          <h4 style={{ fontWeight: 600, marginBottom: '0.25rem' }}>⚠️ Configuration Validation Error</h4>
          <pre style={{ margin: '0.5rem 0', background: 'rgba(0,0,0,0.2)', padding: '0.75rem', borderRadius: '8px', fontSize: '0.8rem', overflowX: 'auto' }}>
            {config.config_error}
          </pre>
          <p style={{ fontSize: '0.85rem' }}>
            Verify that your <code>.env</code> file exists and contains all required variables: <code>SMTP_SERVER</code>, <code>SMTP_PORT</code>, <code>SMTP_EMAIL</code>, <code>SMTP_PASSWORD</code>.
          </p>
        </div>
      )}

      {/* System Controls Bar */}
      <div className="system-controls">
        <div className="sys-control-group">
          <span style={{ fontWeight: 600, color: 'white' }}>⚙️ System Controls</span>
          <label className="checkbox-label">
            <input 
              type="checkbox" 
              checked={autoRefresh} 
              onChange={(e) => setAutoRefresh(e.target.checked)} 
            />
            Auto Refresh Dashboard (10s) 🔄
          </label>
        </div>
        <div className="sys-buttons">
          <button onClick={fetchJobs} className="btn-secondary sys-btn-refresh">
            Force Refresh Now 🔄
          </button>
        </div>
      </div>

      {/* Split Dashboard Layout */}
      <div className="dashboard-grid">
        {/* Left Column: Form & Panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          <div className="form-panel">
            <h3 className="section-title" style={{ margin: 0 }}>⚙️ Global Configuration</h3>
            
            <div className="form-group">
              <label className="form-label">Service Provider 🍿</label>
              <select className="form-select" value={serviceProvider} disabled>
                <option value="BookMyShow">BookMyShow</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Notification Medium 📢</label>
              <select 
                className="form-select" 
                value={medium} 
                onChange={(e) => setMedium(e.target.value as any)}
              >
                <option value="Email">Email</option>
                <option value="Discord Webhook">Discord Webhook</option>
              </select>
            </div>

            {medium === "Email" ? (
              <div className="form-group">
                <label className="form-label">Your Email Address 📧</label>
                <input 
                  type="email" 
                  className="form-input" 
                  placeholder="yourname@gmail.com" 
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
                <span className="form-help">You will receive alerts on this email.</span>
              </div>
            ) : (
              <div className="form-group">
                <label className="form-label">Discord Webhook URL 🔗</label>
                <input 
                  type="text" 
                  className="form-input" 
                  placeholder="https://discord.com/api/webhooks/..." 
                  value={webhook}
                  onChange={(e) => setWebhook(e.target.value)}
                />
                <span className="form-help">Enter your Discord channel webhook URL.</span>
              </div>
            )}

            <div className="form-group">
              <label className="form-label">Check Interval (Seconds) ⏱️</label>
              <input 
                type="number" 
                className="form-input" 
                min={10} 
                max={3600} 
                step={5}
                value={intervalSec}
                onChange={(e) => setIntervalSec(parseInt(e.target.value, 10) || 30)}
              />
              <span className="form-help">Time to wait before refreshing the page. Minimum 10 seconds.</span>
            </div>

            <hr style={{ border: 'none', borderTop: '1px solid rgba(255,255,255,0.05)' }} />

            <h3 className="section-title" style={{ margin: 0 }}>➕ Create New Monitor Task</h3>
            
            <form onSubmit={handleCreateMonitorSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              <div className="form-group">
                <label className="form-label">Movie Page URL 🔗</label>
                <input 
                  type="text" 
                  className="form-input" 
                  placeholder="https://in.bookmyshow.com/buytickets/movie-name/..." 
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                />
                <span className="form-help">Copy the exact URL of the movie booking page containing the date selectors.</span>
              </div>

              <div className="form-group">
                <label className="form-label">Target Date 📅</label>
                <input 
                  type="date" 
                  className="form-input" 
                  value={targetDate}
                  onChange={(e) => setTargetDate(e.target.value)}
                />
                <span className="form-help">Select the date you want to monitor.</span>
              </div>

              <div className="form-group">
                <label className="form-label">Target Theatre Name(s) 🏢</label>
                <textarea 
                  className="form-textarea" 
                  placeholder="PVR: ECX Chanakyapuri&#10;INOX: Insignia Epicuria"
                  value={theatres}
                  onChange={(e) => setTheatres(e.target.value)}
                />
                <span className="form-help">Enter one theatre name per line. Substring match is supported, but it is case-sensitive!</span>
              </div>

              {formErrors.length > 0 && (
                <div className="alert-error" style={{ padding: '0.75rem' }}>
                  {formErrors.map((err, i) => (
                    <div key={i}>• {err}</div>
                  ))}
                </div>
              )}

              {formSuccess && (
                <div className="alert-success" style={{ padding: '0.75rem' }}>
                  {formSuccess}
                </div>
              )}

              <button type="submit" className="btn-primary">
                Start Radar
              </button>
            </form>

            {/* Test alert sidebar expander */}
            <div className="tester-panel">
              <div className="tester-header" onClick={() => setTestExpanded(!testExpanded)}>
                <span>📬 Test Alerts Connection</span>
                <span>{testExpanded ? '▲' : '▼'}</span>
              </div>
              {testExpanded && (
                <form onSubmit={handleTestAlertSubmit} className="tester-content">
                  <div className="form-group">
                    <label className="form-label">Alert Type</label>
                    <select 
                      className="form-select" 
                      value={testMedium} 
                      onChange={(e) => setTestMedium(e.target.value as any)}
                    >
                      <option value="Email">Email</option>
                      <option value="Discord Webhook">Discord Webhook</option>
                    </select>
                  </div>
                  
                  <div className="form-group">
                    <label className="form-label">
                      {testMedium === "Email" ? "Test Recipient Email" : "Test Webhook URL"}
                    </label>
                    <input 
                      type="text" 
                      className="form-input" 
                      placeholder={testMedium === "Email" ? "user@gmail.com" : "https://discord.com/api/webhooks/..."} 
                      value={testTarget}
                      onChange={(e) => setTestTarget(e.target.value)}
                      required
                    />
                  </div>

                  <button type="submit" className="btn-secondary" disabled={testLoading}>
                    {testLoading ? (
                      <>
                        <span className="spinner"></span> Sending...
                      </>
                    ) : (
                      testMedium === "Email" ? "Send Test Email 📨" : "Send Test Webhook 💬"
                    )}
                  </button>

                  {testResult && (
                    <div className={testResult.success ? "alert-success" : "alert-error"} style={{ padding: '0.75rem', marginTop: '0.25rem' }}>
                      {testResult.message}
                    </div>
                  )}
                </form>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Monitors List */}
        <div>
          <h3 className="section-title">🖥️ Active Monitor Daemons</h3>
          
          <div className="monitors-container">
            {jobs.length === 0 ? (
              <div className="alert-info">
                No active monitors registered yet. Use the panel on the left to add a new monitoring agent!
              </div>
            ) : (
              jobs.map((job) => {
                const isExpanded = !!expandedLogs[job.id];
                const badgeClass = `badge badge-${job.status.toLowerCase()}`;
                
                return (
                  <div key={job.id} className="job-card-wrapper">
                    {/* Left Column: Details */}
                    <div className="card-details">
                      <div className="card-header">
                        <span className="card-title">
                          🎬 <strong>{job.movie_name}</strong>{' '}
                          <span className="card-id">(ID: #{job.id})</span>
                        </span>
                        <span className={badgeClass}>{job.status}</span>
                      </div>

                      <div className="info-grid">
                        <div className="info-item">
                          <div className="info-label">Movie Link</div>
                          <div className="info-value">
                            <a href={job.url} target="_blank" rel="noopener noreferrer">
                              Link 🔗
                            </a>
                          </div>
                        </div>

                        <div className="info-item">
                          <div className="info-label">Date (YYYYMMDD)</div>
                          <div className="info-value">
                            📅 {formatBmsDate(job.date_str)}
                          </div>
                        </div>

                        <div className="info-item">
                          <div className="info-label">Alert Channel</div>
                          <div className="info-value">
                            📢 {job.notification_medium.toUpperCase()}
                          </div>
                        </div>

                        <div className="info-item">
                          <div className="info-label">Last Checked</div>
                          <div className="info-value">
                            ⏱️ {formatTimestamp(job.last_checked_at)}
                          </div>
                        </div>
                      </div>

                      <div className="card-wide-info">
                        <div className="info-label">Target Theatres</div>
                        <div className="info-value">
                          🏢 {job.theatres.join(', ')}
                        </div>
                      </div>

                      <div className="card-wide-info">
                        <div className="info-label">Latest Status</div>
                        <div className="info-value-mono">
                          {job.last_result}
                        </div>
                      </div>

                      {/* Expandable activity log Accordion */}
                      <div className="log-accordion">
                        <div className="log-trigger" onClick={() => toggleLogs(job.id)}>
                          <span>📄 Activity Log</span>
                          <span>{isExpanded ? '▲' : '▼'}</span>
                        </div>
                        {isExpanded && (
                          <div className="logs-console">
                            {jobLogs[job.id] || "Loading activity log..."}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Right Column: Controls */}
                    <div className="card-controls">
                      {job.status === "Running" ? (
                        <button 
                          onClick={() => handleStopJob(job.id)} 
                          className="btn-secondary"
                        >
                          Stop ⏸️
                        </button>
                      ) : (
                        <button 
                          onClick={() => handleStartJob(job.id)} 
                          className="btn-secondary"
                        >
                          Start ▶️
                        </button>
                      )}
                      <button 
                        onClick={() => handleDeleteJob(job.id)} 
                        className="btn-secondary"
                        style={{ color: '#f87171', borderColor: 'rgba(239, 68, 68, 0.2)' }}
                      >
                        Delete 🗑️
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
