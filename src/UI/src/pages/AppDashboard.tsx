import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import ReCAPTCHA from 'react-google-recaptcha';
import { 
  Film, Calendar, MessageSquare, Clock, 
  Play, Pause, Trash2, Sliders, Plus, 
  AlertTriangle, CheckCircle2, 
  ExternalLink, RefreshCw, Timer, BookOpen, Pencil, X
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';

import { DatePicker } from '@/components/ui/date-picker';
import { ConfirmModal } from '@/components/ui/confirm-modal';
import { authenticatedFetch } from '../utils/api';
import { formatBmsDate, formatTimestamp, formatInterval } from '../utils/formatters';
import { isSecurityDisabled } from '../utils/security';
import { isPaymentsDisabled } from '../utils/payments';
import type { Job, AppConfig, UserClaims } from '../types';
import { auth } from '../lib/firebase';
import { hasProviderSearch } from '../utils/providerSearch';
import { MoviePicker, type CityEntry } from '../components/ui/movie-picker';
import { TheatreSearch } from '../components/ui/theatre-search';
import { FormatPicker, type FormatOption, type ShowDateOption, type AvailableTheatre } from '../components/ui/format-picker';

/**
 * Renders the ticket-tracker dashboard for creating, editing, and managing notification jobs.
 *
 * @returns The ticket-tracker dashboard interface
 */
export function AppDashboard() {
  const [claims, setClaims] = useState<UserClaims | null>(null);
  const [selectedCity, setSelectedCity] = useState<CityEntry | null>(null);
  const [smartMovieUrl, setSmartMovieUrl] = useState("");
  const [smartTheatres, setSmartTheatres] = useState<string[]>([]);
  const [smartEventCode, setSmartEventCode] = useState("");
  const [selectedFormat, setSelectedFormat] = useState<FormatOption | null>(null);
  const [availableShowDates, setAvailableShowDates] = useState<ShowDateOption[]>([]);
  const [availableTheatres, setAvailableTheatres] = useState<AvailableTheatre[]>([]);

  const handleSelectSmartMovie = (ctaUrl: string, _title: string, eventCode?: string) => {
    setSmartMovieUrl(ctaUrl);
    setSelectedFormat(null);
    setAvailableShowDates([]);
    setAvailableTheatres([]);
    setSmartTheatres([]);
    let code = eventCode || "";
    if (!code && ctaUrl) {
      const match = ctaUrl.match(/(ET\d{8})/i);
      if (match) code = match[1].toUpperCase();
    }
    setSmartEventCode(code);
  };

  useEffect(() => {
    const unsubscribe = auth.onAuthStateChanged(async (user) => {
      if (user) {
        try {
          const res = await user.getIdTokenResult();
          setClaims(res.claims as UserClaims);
        } catch (err) {
          console.error("Error fetching claims:", err);
          setClaims(null);
        }
      } else {
        setClaims(null);
      }
    });
    return () => unsubscribe();
  }, []);

  // App Config and Jobs state
  const [config, setConfig] = useState<AppConfig | null>(null);
  const paymentsDisabled = isPaymentsDisabled(config);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [jobToDelete, setJobToDelete] = useState<Job | null>(null);

  // Global Config inputs
  const [serviceProvider] = useState("BookMyShow");
  const [medium, setMedium] = useState<"Email" | "Discord Webhook" | "SMS" | "WhatsApp" | "Phone Call">("Email");
  const [email, setEmail] = useState("");
  const [webhook, setWebhook] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [smsConsent, setSmsConsent] = useState(false);
  const [whatsappConsent, setWhatsappConsent] = useState(false);
  const [callConsent, setCallConsent] = useState(false);
  const [emailConsent, setEmailConsent] = useState(false);
  const [discordConsent, setDiscordConsent] = useState(false);
  const [userProfile, setUserProfile] = useState<any>(null);
  const [userWallet, setUserWallet] = useState<any>(null);
  const [prices, setPrices] = useState<any>(null);
  const [intervalSec, setIntervalSec] = useState(60);

  // New Monitor Form inputs
  const [url, setUrl] = useState("");
  const [targetDate, setTargetDate] = useState("");
  const [theatres, setTheatres] = useState("");
  const [formErrors, setFormErrors] = useState<string[]>([]);
  const [formSuccess, setFormSuccess] = useState<string | null>(null);

  // reCAPTCHA ref
  const mainRecaptchaRef = useRef<ReCAPTCHA>(null);

  // Edit Job State
  const [editingJob, setEditingJob] = useState<Job | null>(null);
  const [editUrl, setEditUrl] = useState("");
  const [editDate, setEditDate] = useState("");
  const [editTheatres, setEditTheatres] = useState("");
  const [editMedium, setEditMedium] = useState<"Email" | "Discord Webhook" | "SMS" | "WhatsApp" | "Phone Call">("Email");
  const [editEmail, setEditEmail] = useState("");
  const [editWebhook, setEditWebhook] = useState("");
  const [editPhone, setEditPhone] = useState("");
  const [paymentMethod, setPaymentMethod] = useState<"wallet" | "cashfree">("wallet");
  const [submittingCashfree, setSubmittingCashfree] = useState(false);
  const [editIntervalSec, setEditIntervalSec] = useState(60);
  const [editLoading, setEditLoading] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  // Smart Edit States
  const [editSmartMovieUrl, setEditSmartMovieUrl] = useState("");
  const [editSmartEventCode, setEditSmartEventCode] = useState("");
  const [editSelectedFormat, setEditSelectedFormat] = useState<FormatOption | null>(null);
  const [editSmartTheatres, setEditSmartTheatres] = useState<string[]>([]);
  const [editAvailableShowDates, setEditAvailableShowDates] = useState<ShowDateOption[]>([]);
  const [editAvailableTheatres, setEditAvailableTheatres] = useState<AvailableTheatre[]>([]);

  const handleOpenEdit = (job: Job) => {
    setEditingJob(job);
    const rawUrl = job.url || job.params?.url || "";
    setEditUrl(rawUrl);
    setEditSmartMovieUrl(rawUrl);
    setEditAvailableTheatres([]);
    setEditAvailableShowDates([]);

    let code = "";
    const match = rawUrl.match(/(ET\d{8})/i);
    if (match) code = match[1].toUpperCase();
    setEditSmartEventCode(code);

    const savedLang = job.language || job.params?.language || "";
    if (code) {
      setEditSelectedFormat({
        label: job.format || job.params?.format || "Standard",
        eventCode: code,
        eventUrl: "",
        refEventCode: code,
        language: savedLang || "English",
      });
    } else {
      setEditSelectedFormat(null);
    }

    const dateStr = job.date_str || job.params?.date_str || "";
    if (dateStr.length === 8) {
      setEditDate(`${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`);
    } else {
      setEditDate(dateStr);
    }

    const theatresArr = job.theatres || job.params?.theatres || [];
    const listTheatres = Array.isArray(theatresArr) ? theatresArr : String(theatresArr).split("\n").filter(Boolean);
    setEditTheatres(listTheatres.join("\n"));
    setEditSmartTheatres(listTheatres);

    let normalizedMedium: "Email" | "Discord Webhook" | "SMS" | "WhatsApp" | "Phone Call" = "Email";
    const jm = (job.notification_medium || "").toLowerCase();
    if (jm.includes("discord") || jm.includes("webhook")) normalizedMedium = "Discord Webhook";
    else if (jm.includes("sms")) normalizedMedium = "SMS";
    else if (jm.includes("whatsapp")) normalizedMedium = "WhatsApp";
    else if (jm.includes("call") || jm.includes("phone")) normalizedMedium = "Phone Call";
    else normalizedMedium = "Email";
    setEditMedium(normalizedMedium);

    setEditEmail(job.notification_config?.recipient_email || "");
    setEditWebhook(job.notification_config?.webhook_url || "");
    setEditPhone(job.phone_number || job.notification_config?.phone_number || "");
    setEditIntervalSec(job.check_interval || 60);
    setEditError(null);
  };

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingJob) return;

    setEditError(null);

    const isSmartActive = hasProviderSearch(editingJob.service_provider || serviceProvider, claims);
    let finalUrl = editUrl.trim();
    let finalTheatres = editTheatres
      .split('\n')
      .map(t => t.trim())
      .filter(t => t.length > 0);

    if (isSmartActive) {
      if (!editSmartMovieUrl.trim()) {
        setEditError("Please select a movie.");
        return;
      }
      if (!editSelectedFormat) {
        setEditError("Please select a movie language and format.");
        return;
      }
      let citySlug = "city";
      const urlCityMatch = editSmartMovieUrl.match(/\/movies\/([^/]+)\//i);
      if (urlCityMatch) {
        citySlug = urlCityMatch[1].toLowerCase();
      } else if (selectedCity?.RegionSlug) {
        citySlug = selectedCity.RegionSlug.toLowerCase();
      }
      const eventUrl = editSelectedFormat.eventUrl || "movie";
      const fCode = editSelectedFormat.eventCode || editSmartEventCode;
      const dateFormatted = editDate.replace(/-/g, '');
      const refCode = editSelectedFormat.refEventCode || fCode;

      finalUrl = `https://in.bookmyshow.com/movies/${citySlug}/${eventUrl}/buytickets/${fCode}/${dateFormatted}?etCodes=${fCode}&language=${encodeURIComponent(editSelectedFormat.language.toLowerCase())}&refEventCode=${refCode}`;
      finalTheatres = editSmartTheatres;
    }

    const bmsPattern = /^https:\/\/(?:[a-zA-Z0-9-]+\.)*bookmyshow\.com\/(?:movies\/[^/]+\/[^/]+|buytickets\/[^/]+)/;
    if (!finalUrl.trim() || !finalUrl.trim().startsWith("https://")) {
      setEditError("Enter a valid HTTPS URL.");
      return;
    } else if ((editingJob.service_provider || "BookMyShow").toLowerCase().includes("bookmyshow") && !bmsPattern.test(finalUrl.trim())) {
      setEditError("Enter a valid BookMyShow movie link.");
      return;
    }

    if (!editDate) {
      setEditError("Target date is required.");
      return;
    }

    if (finalTheatres.length === 0) {
      setEditError("At least one theatre is required.");
      return;
    }

    if (editMedium === "Email" && !editEmail.trim()) {
      setEditError("Recipient email address is required.");
      return;
    }

    if (editMedium === "Discord Webhook" && !editWebhook.trim()) {
      setEditError("Discord Webhook URL is required.");
      return;
    }

    if (["SMS", "WhatsApp", "Phone Call"].includes(editMedium) && !editPhone.trim()) {
      setEditError("A valid Indian mobile number (+91) is required for this alert medium.");
      return;
    }

    if (editIntervalSec < 60) {
      setEditError("Check frequency cannot be less than 1 minute (60 seconds).");
      return;
    }

    const dateFormatted = editDate.replace(/-/g, '');

    let editNotifConfig: any = {};
    if (editMedium === "Email") editNotifConfig = { recipient_email: editEmail.trim() };
    else if (editMedium === "Discord Webhook") editNotifConfig = { webhook_url: editWebhook.trim() };
    else editNotifConfig = { phone_number: editPhone.trim() };

    const payload = {
      service_provider: editingJob.service_provider || "BookMyShow",
      notification_medium: editMedium,
      notification_config: editNotifConfig,
      phone_number: ["SMS", "WhatsApp", "Phone Call"].includes(editMedium) ? editPhone.trim() : undefined,
      check_interval: editIntervalSec,
      params: {
        url: finalUrl.trim(),
        date_str: dateFormatted,
        theatres: finalTheatres,
        language: editSelectedFormat?.language || editingJob.language || editingJob.params?.language || "",
        format: editSelectedFormat?.label || editingJob.format || editingJob.params?.format || ""
      }
    };

    setEditLoading(true);
    try {
      const res = await authenticatedFetch(`/api/jobs/${editingJob.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok) {
        setEditingJob(null);
        fetchJobs();
      } else {
        setEditError(data.detail || "Failed to update job.");
      }
    } catch (err: any) {
      setEditError(err.message || "Failed to reach server.");
    } finally {
      setEditLoading(false);
    }
  };

  const [refreshing, setRefreshing] = useState(false);

  // Helper: Fetch App Configuration status
  const fetchConfig = useCallback(async () => {
    try {
      const res = await authenticatedFetch('/api/config');
      if (res.ok) {
        const data = await res.json();
        setConfig(data);
        if (data.default_check_interval) {
          setIntervalSec(Math.max(60, data.default_check_interval));
        }
        if (!isPaymentsDisabled(data)) {
          authenticatedFetch('/api/wallet/balance')
            .then(r => r.json())
            .then(w => { if (w && !w.detail) setUserWallet(w); })
            .catch(err => console.error("Failed to load wallet in dashboard:", err));
        } else {
          setUserWallet(null);
        }
        authenticatedFetch('/api/payments/prices')
          .then(r => r.json())
          .then(p => { if (p && !p.detail) setPrices(p); })
          .catch(err => console.error("Failed to load prices in dashboard:", err));
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

    // Fetch user profile and wallet
    authenticatedFetch('/api/profile')
      .then(res => res.json())
      .then(prof => {
        if (prof && !prof.detail) {
          setUserProfile(prof);
          const savedEmail = prof.email_medium_address || prof.preferences?.email_address || prof.email || "";
          const savedDiscord = prof.discord_webhook_url || prof.preferences?.discord_webhook_url || "";
          if (prof.phone_number) setPhoneNumber(prof.phone_number);
          if (savedEmail) setEmail(savedEmail);
          if (savedDiscord) setWebhook(savedDiscord);
          if (prof.consents?.sms_consented) setSmsConsent(true);
          if (prof.consents?.whatsapp_consented) setWhatsappConsent(true);
          if (prof.consents?.call_consented) setCallConsent(true);
          if (prof.consents?.email_consented) setEmailConsent(true);
          if (prof.consents?.discord_consented) setDiscordConsent(true);
        }
      })
      .catch(err => console.error("Failed to load profile in dashboard:", err));
    
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

  const getMediumPricePaise = (m: string) => {
    if (!prices) return 0;
    if (m === "SMS") return prices.sms_paise ?? 50;
    if (m === "WhatsApp") return prices.whatsapp_paise ?? 100;
    if (m === "Phone Call") return prices.phone_call_paise ?? 150;
    if (m === "Email") return prices.email_paise ?? 0;
    if (m === "Discord Webhook") return prices.discord_paise ?? 0;
    return 0;
  };

  const initiateCashfreeJobPayment = async (jobPayload: any) => {
    setSubmittingCashfree(true);
    setFormErrors([]);
    try {
      const res = await authenticatedFetch('/api/payments/job/initiate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...jobPayload, payment_method: 'cashfree' }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to initiate Cashfree payment.');
      }

      const sessionToken = data.session_token || data.gateway_session_id;
      const paymentId = data.payment_id;

      const launchModal = (sessId: string) => {
        const isDev = config?.environment === 'development';
        const cashfree = (window as any).Cashfree({
          mode: isDev ? 'sandbox' : 'production',
        });
        cashfree.checkout({
          paymentSessionId: sessId,
          redirectTarget: '_modal',
        }).then((result: any) => {
          if (result.error) {
            setFormErrors([result.error.message || 'Payment window closed or cancelled.']);
            setSubmittingCashfree(false);
          } else {
            setFormSuccess('Payment submitted! Verifying transaction and starting ticket tracker...');
            let attempts = 0;
            const pollInterval = setInterval(async () => {
              attempts += 1;
              try {
                const sRes = await authenticatedFetch(`/api/payments/${paymentId}/status`);
                if (sRes.ok) {
                  const sData = await sRes.json();
                  if (sData.status === 'success' && sData.job_id) {
                    clearInterval(pollInterval);
                    setFormSuccess(`Successfully registered monitor #${sData.job_id}! Ticket tracker started.`);
                    setUrl("");
                    setTheatres("");
                    setSmartMovieUrl("");
                    setSmartTheatres([]);
                    setSmartEventCode("");
                    setSelectedFormat(null);
                    setAvailableShowDates([]);
                    fetchJobs();
                    setSubmittingCashfree(false);
                    return;
                  } else if (sData.status === 'failed') {
                    clearInterval(pollInterval);
                    setFormErrors(['Payment failed on gateway.']);
                    setSubmittingCashfree(false);
                    return;
                  }
                }
              } catch (pollErr) {
                console.warn("Poll error:", pollErr);
              }
              if (attempts > 12) {
                clearInterval(pollInterval);
                fetchJobs();
                setSubmittingCashfree(false);
              }
            }, 2000);
          }
        });
      };

      if (typeof (window as any).Cashfree === 'undefined') {
        const script = document.createElement('script');
        script.src = 'https://sdk.cashfree.com/js/v3/cashfree.js';
        script.onload = () => launchModal(sessionToken);
        document.body.appendChild(script);
      } else {
        launchModal(sessionToken);
      }
    } catch (err: any) {
      setFormErrors([err?.message || 'Error processing Cashfree job payment.']);
      setSubmittingCashfree(false);
    }
  };

  // Register New Monitor Task submit handler
  const handleCreateMonitorSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormErrors([]);
    setFormSuccess(null);

    const token = mainRecaptchaRef.current?.getValue() || "";
    const errors: string[] = [];

    if (!isSecurityDisabled(config) && !token) {
      errors.push("Complete the reCAPTCHA challenge first.");
    }

    const isSmartActive = hasProviderSearch(serviceProvider, claims);
    let effectiveUrl = url.trim();
    const effectiveTheatres = isSmartActive
      ? smartTheatres
      : theatres.split('\n').map(t => t.trim()).filter(t => t.length > 0);

    if (isSmartActive) {
      if (!smartMovieUrl.trim()) {
        errors.push("Please select a movie from the movie list above.");
      } else if (!selectedFormat) {
        errors.push("Please select a movie language and format (e.g. 2D, 3D).");
      } else {
        const citySlug = (selectedCity?.RegionSlug || "city").toLowerCase();
        const eventUrl = selectedFormat.eventUrl || "movie";
        const fCode = selectedFormat.eventCode || smartEventCode;
        const dateFormatted = targetDate ? targetDate.replace(/-/g, '') : '';
        const refCode = selectedFormat.refEventCode || fCode;

        effectiveUrl = `https://in.bookmyshow.com/movies/${citySlug}/${eventUrl}/buytickets/${fCode}/${dateFormatted}?etCodes=${fCode}&language=${encodeURIComponent(selectedFormat.language.toLowerCase())}&refEventCode=${refCode}`;
      }
    }

    const bmsPattern = /^https:\/\/(?:[a-zA-Z0-9-]+\.)*bookmyshow\.com\/(?:movies\/[^/]+\/[^/]+|buytickets\/[^/]+)/;
    if (!effectiveUrl.trim()) {
      errors.push(isSmartActive ? "Please select a movie and format." : "Movie Page URL is required.");
    } else if (!effectiveUrl.trim().startsWith("https://")) {
      errors.push("Enter a valid HTTPS URL.");
    } else if (serviceProvider.toLowerCase().includes("bookmyshow") && !bmsPattern.test(effectiveUrl.trim())) {
      errors.push("Enter a valid BookMyShow movie link.");
    }

    if (!targetDate) {
      errors.push("Target date is required.");
    }

    if (effectiveTheatres.length === 0) {
      errors.push(isSmartActive ? "Please search and add at least one theatre." : "At least one theatre name is required.");
    }

    if (medium === "Email") {
      if (!email.trim()) {
        errors.push("Recipient email address is required.");
      }
      if (!emailConsent) {
        errors.push("Please check the Email consent box to receive automated email alerts.");
      }
    }

    if (medium === "Discord Webhook") {
      if (!webhook.trim()) {
        errors.push("Discord Webhook URL is required.");
      }
      if (!discordConsent) {
        errors.push("Please check the Discord consent box to receive automated discord notifications.");
      }
    }

    if (["SMS", "WhatsApp", "Phone Call"].includes(medium)) {
      if (!phoneNumber.trim()) {
        errors.push("A valid Indian mobile number (+91) is required for this alert medium.");
      }
      if (medium === "SMS" && !smsConsent) {
        errors.push("Please check the SMS consent box to receive automated SMS alerts.");
      }
      if (medium === "WhatsApp" && !whatsappConsent) {
        errors.push("Please check the WhatsApp consent box to receive automated WhatsApp alerts.");
      }
      if (medium === "Phone Call" && !callConsent) {
        errors.push("Please check the Phone Call consent box to receive automated voice alerts.");
      }
    }

    if (intervalSec < 60) {
      errors.push("Check frequency cannot be less than 1 minute (60 seconds).");
    }

    if (errors.length > 0) {
      setFormErrors(errors);
      return;
    }

    const dateFormatted = targetDate.replace(/-/g, '');

    let notifConfig: any = {};
    if (medium === "Email") notifConfig = { recipient_email: email.trim() };
    else if (medium === "Discord Webhook") notifConfig = { webhook_url: webhook.trim() };
    else notifConfig = { phone_number: phoneNumber.trim() };

    const activePricePaise = getMediumPricePaise(medium);

    const payload = {
      service_provider: serviceProvider,
      notification_medium: medium,
      notification_config: notifConfig,
      phone_number: ["SMS", "WhatsApp", "Phone Call"].includes(medium) ? phoneNumber.trim() : undefined,
      sms_consent: medium === "SMS" ? smsConsent : false,
      whatsapp_consent: medium === "WhatsApp" ? whatsappConsent : false,
      call_consent: medium === "Phone Call" ? callConsent : false,
      email_consent: medium === "Email" ? emailConsent : false,
      discord_consent: medium === "Discord Webhook" ? discordConsent : false,
      payment_method: paymentsDisabled || activePricePaise === 0 ? "free" : (paymentMethod === "cashfree" ? "cashfree" : "wallet"),
      check_interval: intervalSec,
      recaptcha_token: token,
      params: {
        url: effectiveUrl.trim(),
        date_str: dateFormatted,
        theatres: effectiveTheatres,
        language: selectedFormat?.language || "",
        format: selectedFormat?.label || ""
      }
    };

    if (!paymentsDisabled && activePricePaise > 0) {
      const walletPaise = userWallet?.balance_paise || 0;
      if (paymentMethod === "cashfree" || walletPaise < activePricePaise) {
        await initiateCashfreeJobPayment(payload);
        return;
      }
    }

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
        setSmartMovieUrl("");
        setSmartTheatres([]);
        setSmartEventCode("");
        setSelectedFormat(null);
        setAvailableShowDates([]);
        setWebhook(userProfile?.discord_webhook_url || userProfile?.preferences?.discord_webhook_url || "");
        fetchJobs();

        // Refresh wallet balance
        if (!paymentsDisabled) {
          authenticatedFetch('/api/wallet/balance')
            .then(r => r.json())
            .then(w => { if (w && !w.detail) setUserWallet(w); })
            .catch(() => {});
        }
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
        if (!paymentsDisabled) {
          authenticatedFetch('/api/wallet/balance')
            .then(r => r.json())
            .then(w => { if (w && !w.detail) setUserWallet(w); })
            .catch(() => {});
        }
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
              Some settings are missing. Check if your <code>.env</code> configuration file is set up correctly.
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
                  <div className="flex items-center justify-between">
                    <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Booking Platform</label>
                  </div>
                  <Select value={serviceProvider} disabled className="h-9.5 text-xs bg-muted/20 border-border/80">
                    <option value="BookMyShow">BookMyShow</option>
                  </Select>
                  <div className="pt-0.5">
                    <Link 
                      to={`/instructions#${serviceProvider.toLowerCase().replace(/[^a-z0-9]/g, '')}`}
                      className="text-[11px] text-rose-400 hover:text-rose-300 font-semibold flex items-center gap-1.5 hover:underline transition-colors"
                    >
                      <BookOpen className="h-3 w-3" />
                      <span>View {serviceProvider} setup instructions & guide →</span>
                    </Link>
                  </div>
                </div>

                {hasProviderSearch(serviceProvider, claims) ? (
                  <>
                    <MoviePicker
                      selectedCity={selectedCity}
                      onCityChange={(c) => {
                        setSelectedCity(c);
                        setSmartMovieUrl("");
                        setSmartEventCode("");
                        setSelectedFormat(null);
                        setAvailableShowDates([]);
                        setAvailableTheatres([]);
                        setSmartTheatres([]);
                      }}
                      selectedMovieUrl={smartMovieUrl}
                      onSelectMovie={handleSelectSmartMovie}
                    />

                    {smartEventCode && (
                      <FormatPicker
                        eventCode={smartEventCode}
                        movieCtaUrl={smartMovieUrl}
                        regionCode={selectedCity?.RegionCode}
                        regionSlug={selectedCity?.RegionSlug}
                        lat={selectedCity?.Lat}
                        lon={selectedCity?.Long}
                        geohash={selectedCity?.GeoHash}
                        selectedFormat={selectedFormat}
                        onSelectFormat={setSelectedFormat}
                        onAvailableDatesFetched={setAvailableShowDates}
                        onTheatresFetched={setAvailableTheatres}
                      />
                    )}

                    {/* Target Date selection with Shadcn DatePicker */}
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Show Date 📅</label>
                        {availableShowDates.length > 0 && (
                          <span className="text-[10px] font-semibold text-emerald-400">
                            {availableShowDates.filter(d => !d.isDisabled).length} show dates available
                          </span>
                        )}
                      </div>
                      <DatePicker 
                        value={targetDate}
                        onChange={(dateStr) => setTargetDate(dateStr)}
                        placeholder="Select show date"
                      />
                    </div>

                    <TheatreSearch
                      cityName={selectedCity?.RegionName}
                      regionCode={selectedCity?.RegionCode}
                      regionSlug={selectedCity?.RegionSlug}
                      lat={selectedCity?.Lat}
                      lon={selectedCity?.Long}
                      geohash={selectedCity?.GeoHash}
                      availableTheatres={availableTheatres}
                      selectedTheatres={smartTheatres}
                      onChangeTheatres={setSmartTheatres}
                    />
                  </>
                ) : (
                  <>
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

                    {/* Target Date selection with Shadcn DatePicker */}
                    <div className="space-y-1.5">
                      <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Show Date</label>
                      <DatePicker 
                        value={targetDate}
                        onChange={(dateStr) => setTargetDate(dateStr)}
                        placeholder="Select show date"
                      />
                    </div>

                    {/* Target Theatre name filters */}
                    <div className="space-y-1.5">
                      <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Preferred Theatres/Cinemas</label>
                      <Textarea 
                        placeholder="PVR Director's Cut&#10;Cinepolis Nexus&#10;Inox Forum Mall" 
                        value={theatres}
                        onChange={(e) => setTheatres(e.target.value)}
                        className="min-h-[90px] max-h-[140px] text-xs bg-muted/10 border-border/80 placeholder:text-muted-foreground/40 focus:border-rose-500/40 leading-relaxed"
                      />
                      <p className="text-[10px] text-muted-foreground leading-normal">
                        Type the names of your preferred theatres/cinemas (one per line). Example: PVR Forum, INOX Nexus.
                      </p>
                    </div>
                  </>
                )}


                {/* Notification configuration */}
                <div className="space-y-3.5 border-t border-border/30 pt-4 mt-2">
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Where should we notify you?</label>
                    <div className="flex gap-1.5 flex-wrap">
                      {(["Email", "Discord Webhook", "SMS", "WhatsApp", "Phone Call"] as const).map((m) => {
                        const isFree = paymentsDisabled || getMediumPricePaise(m) === 0;
                        return (
                          <button
                            key={m}
                            type="button"
                            onClick={() => {
                              setMedium(m);
                              if (m === "Email" && !email) {
                                const se = userProfile?.email_medium_address || userProfile?.preferences?.email_address || userProfile?.email || "";
                                if (se) setEmail(se);
                              } else if (m === "Discord Webhook" && !webhook) {
                                const sw = userProfile?.discord_webhook_url || userProfile?.preferences?.discord_webhook_url || "";
                                if (sw) setWebhook(sw);
                              }
                            }}
                            className={`text-[10px] font-bold px-2.5 py-1 rounded-md border transition-all cursor-pointer flex items-center gap-1.5 ${
                              medium === m
                                ? "bg-rose-500/10 text-rose-400 border-rose-500/25"
                                : "bg-muted/10 text-muted-foreground border-transparent hover:text-foreground"
                            }`}
                          >
                            <span>{m === "Discord Webhook" ? "Discord" : m}</span>
                            {isFree ? (
                              <span className="text-[9px] px-1 py-0.2 rounded bg-emerald-500/15 text-emerald-400 font-semibold uppercase">Free</span>
                            ) : (
                              <span className="text-[9px] opacity-70">₹{(getMediumPricePaise(m) / 100).toFixed(2)}</span>
                            )}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {medium === "Email" && (
                    <div className="space-y-2.5">
                      <Input 
                        type="email" 
                        placeholder="your-email@gmail.com" 
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="h-9.5 text-xs bg-muted/10 border-border/80 focus:border-rose-500/40"
                      />
                      <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer select-none">
                        <input
                          type="checkbox"
                          checked={emailConsent}
                          onChange={(e) => setEmailConsent(e.target.checked)}
                          className="h-3.5 w-3.5 rounded border-border text-rose-500"
                        />
                        <span>I consent to receiving automated ticket alert emails.</span>
                      </label>
                    </div>
                  )}

                  {medium === "Discord Webhook" && (
                    <div className="space-y-2.5">
                      <Input 
                        type="text" 
                        placeholder="Paste your Discord Webhook Link" 
                        value={webhook}
                        onChange={(e) => setWebhook(e.target.value)}
                        className="h-9.5 text-xs bg-muted/10 border-border/80 focus:border-rose-500/40"
                      />
                      <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer select-none">
                        <input
                          type="checkbox"
                          checked={discordConsent}
                          onChange={(e) => setDiscordConsent(e.target.checked)}
                          className="h-3.5 w-3.5 rounded border-border text-rose-500"
                        />
                        <span>I consent to receiving automated ticket alerts via Discord webhook.</span>
                      </label>
                    </div>
                  )}

                  {["SMS", "WhatsApp", "Phone Call"].includes(medium) && (
                    <div className="space-y-2.5">
                      <Input 
                        type="text" 
                        placeholder="+91 98765 43210 (Indian Mobile Number)" 
                        value={phoneNumber}
                        onChange={(e) => setPhoneNumber(e.target.value)}
                        className="h-9.5 text-xs bg-muted/10 border-border/80 focus:border-rose-500/40"
                      />
                      
                      {medium === "SMS" && (
                        <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer select-none">
                          <input
                            type="checkbox"
                            checked={smsConsent}
                            onChange={(e) => setSmsConsent(e.target.checked)}
                            className="h-3.5 w-3.5 rounded border-border text-rose-500"
                          />
                          <span>I consent to receiving automated ticket alert SMS messages.</span>
                        </label>
                      )}

                      {medium === "WhatsApp" && (
                        <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer select-none">
                          <input
                            type="checkbox"
                            checked={whatsappConsent}
                            onChange={(e) => setWhatsappConsent(e.target.checked)}
                            className="h-3.5 w-3.5 rounded border-border text-rose-500"
                          />
                          <span>I consent to receiving automated WhatsApp ticket alerts via template.</span>
                        </label>
                      )}

                      {medium === "Phone Call" && (
                        <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer select-none">
                          <input
                            type="checkbox"
                            checked={callConsent}
                            onChange={(e) => setCallConsent(e.target.checked)}
                            className="h-3.5 w-3.5 rounded border-border text-rose-500"
                          />
                          <span>I consent to receiving automated phone calls (Polly.Aditi TTS).</span>
                        </label>
                      )}
                    </div>
                  )}

                  {paymentsDisabled || getMediumPricePaise(medium) === 0 ? (
                    <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-2.5 text-xs flex items-center justify-between">
                      <span className="text-muted-foreground font-medium">Alert Cost:</span>
                      <Badge className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[11px] font-semibold">
                        Free {paymentsDisabled ? "(Self-Hosted Mode)" : ""}
                      </Badge>
                    </div>
                  ) : (
                    <div className="rounded-lg border border-rose-500/20 bg-rose-500/5 p-3 space-y-2.5 text-xs">
                      <div className="flex items-center justify-between">
                        <div>
                          <span className="text-[10px] uppercase font-bold text-muted-foreground block">Cost & Balance</span>
                          <span className="font-semibold text-foreground">
                            ₹{(getMediumPricePaise(medium) / 100).toFixed(2)} / alert
                          </span>
                          <span className="text-muted-foreground text-[11px] ml-1.5">
                            (Wallet: ₹{userWallet ? userWallet.balance_inr.toFixed(2) : "0.00"})
                          </span>
                        </div>
                        <Link to="/profile" className="text-[11px] font-semibold text-rose-400 hover:underline">
                          Manage Wallet →
                        </Link>
                      </div>

                      <div className="border-t border-border/40 pt-2 space-y-1.5">
                        <span className="text-[10px] uppercase font-bold text-muted-foreground block">Payment Method</span>
                        <div className="grid grid-cols-2 gap-2">
                          <button
                            type="button"
                            onClick={() => setPaymentMethod("wallet")}
                            disabled={((userWallet?.balance_paise || 0) < getMediumPricePaise(medium))}
                            className={`p-2 rounded-lg border text-left transition-all ${
                              paymentMethod === "wallet"
                                ? "border-rose-500 bg-rose-500/10 text-rose-400 font-semibold"
                                : "border-border bg-muted/20 text-muted-foreground hover:bg-muted/40"
                            } ${((userWallet?.balance_paise || 0) < getMediumPricePaise(medium)) ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
                          >
                            <div className="text-[11px] font-bold">Pay from Wallet</div>
                            <div className="text-[10px] opacity-80">
                              {((userWallet?.balance_paise || 0) < getMediumPricePaise(medium))
                                ? "Insufficient Balance"
                                : `₹${(userWallet?.balance_inr || 0).toFixed(2)} available`}
                            </div>
                          </button>
                          <button
                            type="button"
                            onClick={() => setPaymentMethod("cashfree")}
                            className={`p-2 rounded-lg border text-left cursor-pointer transition-all ${
                              paymentMethod === "cashfree"
                                ? "border-rose-500 bg-rose-500/10 text-rose-400 font-semibold"
                                : "border-border bg-muted/20 text-muted-foreground hover:bg-muted/40"
                            }`}
                          >
                            <div className="text-[11px] font-bold">Pay via Cashfree</div>
                            <div className="text-[10px] opacity-80">Cards / UPI / Netbanking</div>
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Scan Interval Config */}
                <div className="space-y-2.5 border-t border-border/30 pt-4">
                  <div className="flex items-center justify-between gap-2 text-xs">
                    <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5 shrink-0">
                      <Timer className="h-3.5 w-3.5 text-rose-500" />
                      Check Frequency
                    </span>
                    <div className="flex items-center gap-1.5">
                      <Input
                        type="number"
                        min="1"
                        step="1"
                        placeholder="Mins"
                        value={intervalSec > 0 ? Math.round(intervalSec / 60) : ''}
                        onChange={(e) => {
                          const val = parseInt(e.target.value, 10);
                          if (!isNaN(val)) {
                            setIntervalSec(val * 60);
                          } else {
                            setIntervalSec(0);
                          }
                        }}
                        className="w-20 h-7 text-xs font-mono font-semibold bg-muted/20 text-right pr-2 border-border/80 focus:border-rose-500/40"
                      />
                      <span className="text-[11px] font-medium text-muted-foreground shrink-0">min</span>
                      <span className="text-[10px] text-muted-foreground/60 font-mono">({formatInterval(intervalSec)})</span>
                    </div>
                  </div>

                  {/* Quick Preset Buttons */}
                  <div className="flex items-center gap-1.5 flex-wrap py-0.5">
                    {[
                      { label: '1m', value: 60 },
                      { label: '5m', value: 300 },
                      { label: '15m', value: 900 },
                      { label: '30m', value: 1800 },
                      { label: '1h', value: 3600 },
                      { label: '2h', value: 7200 },
                    ].map((preset) => (
                      <button
                        key={preset.value}
                        type="button"
                        onClick={() => setIntervalSec(preset.value)}
                        className={`text-[10px] px-2 py-0.5 rounded-md font-medium transition-colors cursor-pointer ${
                          intervalSec === preset.value
                            ? 'bg-rose-500 text-white font-bold'
                            : 'bg-muted/40 hover:bg-muted text-muted-foreground hover:text-foreground'
                        }`}
                      >
                        {preset.label}
                      </button>
                    ))}
                  </div>

                  {/* Range Slider for 1m (60s) to 30m (1800s) in 1-minute steps */}
                  <input 
                    type="range" 
                    min="60" 
                    max="1800" 
                    step="60"
                    value={Math.min(1800, Math.max(60, Math.round(intervalSec / 60) * 60))} 
                    onChange={(e) => setIntervalSec(parseInt(e.target.value, 10))} 
                    className="w-full h-1 bg-muted rounded-lg appearance-none cursor-pointer accent-rose-500"
                  />
                  <div className="flex justify-between text-[9px] text-muted-foreground/60 font-semibold px-0.5">
                    <span>1m (Min)</span>
                    <span>10m</span>
                    <span>20m</span>
                    <span>30m (Slider max)</span>
                  </div>
                  <p className="text-[10px] text-muted-foreground leading-normal">
                    Drag slider for 1m–30m, or type custom minutes in the text field (e.g. 45m, 60m, 120m). Minimum is 1 min.
                  </p>
                </div>

                {/* Google reCAPTCHA Verification container */}
                {!isSecurityDisabled(config) && (
                  <div className="space-y-1.5 border-t border-border/30 pt-4 flex flex-col items-center">
                    <div className="g-recaptcha-premium-container">
                      <ReCAPTCHA
                        ref={mainRecaptchaRef}
                        sitekey={siteKeyVal}
                        theme="dark"
                      />
                    </div>
                  </div>
                )}

                {/* Registration Failed Errors (Relocated right above Start Ticket Alert button) */}
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

                {/* Submit button */}
                <Button 
                  type="submit" 
                  disabled={submittingCashfree}
                  className="w-full h-10 text-xs font-bold bg-rose-500 hover:bg-rose-600 text-white cursor-pointer rounded-lg mt-2"
                >
                  {submittingCashfree ? "Processing Payment..." : "Start Ticket Alert"}
                </Button>
              </form>
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
                          <span className="text-[10px] text-muted-foreground">Checks every {formatInterval(job.check_interval)}</span>
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
                            <Sliders className="h-4 w-4 text-rose-500 shrink-0" />
                            <span>Format & Language:</span>
                            <span className="font-semibold text-foreground/80 flex items-center gap-1.5">
                              <Badge variant="outline" className="text-[10px] font-bold border-rose-500/30 text-rose-400 bg-rose-500/10 px-2 py-0.5">
                                {job.language || job.params?.language || '—'}
                              </Badge>
                              <Badge variant="outline" className="text-[10px] font-extrabold border-amber-500/30 text-amber-400 bg-amber-500/10 px-2 py-0.5">
                                {job.format || job.params?.format || '—'}
                              </Badge>
                            </span>
                          </div>

                          <div className="flex items-center gap-2 text-muted-foreground">
                            <Clock className="h-4 w-4 text-rose-500 shrink-0" />
                            <span>Created:</span>
                            <span className="font-semibold text-foreground/80">
                              {formatTimestamp(job.created_at)}
                            </span>
                          </div>

                          <div className="flex items-center gap-2 text-muted-foreground">
                            <RefreshCw className="h-4 w-4 text-rose-500 shrink-0" />
                            <span>Last Checked:</span>
                            <span className="font-semibold text-foreground/80">
                              {formatTimestamp(job.last_checked_at)}
                            </span>
                          </div>

                          <div className="flex items-center gap-2 text-muted-foreground flex-wrap">
                            <MessageSquare className="h-4 w-4 text-rose-500 shrink-0" />
                            <span>Notify Via:</span>
                            <Badge variant="outline" className="text-[9px] font-bold px-2 py-0.5 bg-muted/30">
                              {job.notification_medium.toUpperCase()}
                            </Badge>
                            {job.notification_status === 'sent' || job.notification_status === 'delivered' ? (
                              <Badge className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[9px] font-bold px-2 py-0.5">
                                Delivered
                              </Badge>
                            ) : job.notification_status === 'policy_exempt' ? (
                              <Badge className="bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-[9px] font-bold px-2 py-0.5">
                                Policy Exempt (3x Unanswered)
                              </Badge>
                            ) : job.notification_status === 'failed' ? (
                              <Badge className="bg-rose-500/10 text-rose-400 border border-rose-500/20 text-[9px] font-bold px-2 py-0.5">
                                Failed
                              </Badge>
                            ) : null}
                            {job.refund_issued && !paymentsDisabled && (
                              <Badge className="bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[9px] font-bold px-2 py-0.5">
                                ₹{((job.price_paise || 0)/100).toFixed(2)} Refunded
                              </Badge>
                            )}
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
                    <div className="bg-muted/20 px-5 py-3.5 flex items-center justify-between border-t border-border/30 gap-4 flex-wrap">
                      <div className="flex items-center gap-2 flex-wrap">
                        {job.status === "Running" ? (
                          <Button 
                            onClick={() => handleStopJob(job.id)} 
                            variant="secondary"
                            size="sm"
                            className="h-8 text-xs font-semibold cursor-pointer"
                          >
                            <Pause className="h-3.5 w-3.5 text-amber-400" />
                            Pause Alert
                          </Button>
                        ) : (
                          <Button 
                            onClick={() => handleStartJob(job.id)} 
                            variant="secondary"
                            size="sm"
                            className="h-8 text-xs font-semibold cursor-pointer"
                          >
                            <Play className="h-3.5 w-3.5 text-emerald-400" />
                            Resume Alert
                          </Button>
                        )}
                        <Button
                          onClick={() => handleOpenEdit(job)}
                          variant="outline"
                          size="sm"
                          className="h-8 text-xs font-semibold gap-1.5 border-border/60 hover:border-rose-500/40 cursor-pointer"
                        >
                          <Pencil className="h-3.5 w-3.5 text-rose-400" />
                          Edit Job
                        </Button>
                      </div>
                      
                      <Button 
                        onClick={() => setJobToDelete(job)} 
                        variant="ghost"
                        size="sm"
                        className="h-8 text-xs font-semibold text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 border border-transparent hover:border-rose-500/20 cursor-pointer"
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

      {/* Edit Job Modal Overlay */}
      {editingJob && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-in fade-in duration-200 overflow-y-auto">
          <div className="relative w-full max-w-lg bg-slate-900 border border-border/80 rounded-2xl p-6 shadow-2xl space-y-5 my-8">
            <div className="flex items-center justify-between border-b border-border/40 pb-4">
              <div className="flex items-center gap-2">
                <Pencil className="h-5 w-5 text-rose-500" />
                <h3 className="text-base font-bold text-foreground">Edit Job #{editingJob.id}</h3>
              </div>
              <button
                type="button"
                onClick={() => setEditingJob(null)}
                className="text-muted-foreground hover:text-foreground p-1 rounded-lg transition-colors cursor-pointer"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {editError && (
              <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                <span>{editError}</span>
              </div>
            )}

            <form onSubmit={handleSaveEdit} className="space-y-4 text-xs">
              {hasProviderSearch(editingJob.service_provider || serviceProvider, claims) ? (
                <>
                  <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl flex items-center justify-between">
                    <div>
                      <span className="text-[10px] font-bold text-rose-400 uppercase tracking-wider block">Movie Target</span>
                      <h4 className="font-bold text-sm text-foreground">{editingJob.movie_name || 'BookMyShow Movie'}</h4>
                    </div>
                  </div>

                  {editSmartEventCode && (
                    <FormatPicker
                      eventCode={editSmartEventCode}
                      movieCtaUrl={editSmartMovieUrl}
                      regionCode={selectedCity?.RegionCode}
                      regionSlug={selectedCity?.RegionSlug}
                      lat={selectedCity?.Lat}
                      lon={selectedCity?.Long}
                      geohash={selectedCity?.GeoHash}
                      selectedFormat={editSelectedFormat}
                      onSelectFormat={setEditSelectedFormat}
                      onAvailableDatesFetched={setEditAvailableShowDates}
                      onTheatresFetched={setEditAvailableTheatres}
                    />
                  )}

                  {/* Target Date selection */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Show Date 📅</label>
                      {editAvailableShowDates.length > 0 && (
                        <span className="text-[10px] font-semibold text-emerald-400">
                          {editAvailableShowDates.filter(d => !d.isDisabled).length} show dates available
                        </span>
                      )}
                    </div>
                    <DatePicker 
                      value={editDate}
                      onChange={(dateStr) => setEditDate(dateStr)}
                      placeholder="Select show date"
                    />
                  </div>

                  <TheatreSearch
                    cityName={selectedCity?.RegionName}
                    regionCode={selectedCity?.RegionCode}
                    regionSlug={selectedCity?.RegionSlug}
                    lat={selectedCity?.Lat}
                    lon={selectedCity?.Long}
                    geohash={selectedCity?.GeoHash}
                    availableTheatres={editAvailableTheatres}
                    selectedTheatres={editSmartTheatres}
                    onChangeTheatres={setEditSmartTheatres}
                  />
                </>
              ) : (
                <>
                  {/* Fallback URL Input */}
                  <div className="space-y-1.5">
                    <label className="font-bold text-muted-foreground uppercase tracking-wider text-[10px]">
                      Movie Booking Page URL 🔗
                    </label>
                    <Input
                      type="text"
                      value={editUrl}
                      onChange={(e) => setEditUrl(e.target.value)}
                      placeholder="https://in.bookmyshow.com/buytickets/..."
                      className="h-9.5 text-xs bg-muted/10 border-border/80 focus:border-rose-500/40"
                    />
                  </div>

                  {/* Date */}
                  <div className="space-y-1.5">
                    <label className="font-bold text-muted-foreground uppercase tracking-wider text-[10px]">
                      Target Show Date 📅
                    </label>
                    <DatePicker
                      value={editDate}
                      onChange={(val) => setEditDate(val)}
                      placeholder="Select Date"
                    />
                  </div>

                  {/* Theatres */}
                  <div className="space-y-1.5">
                    <label className="font-bold text-muted-foreground uppercase tracking-wider text-[10px]">
                      Target Cinemas 🏢 (One per line)
                    </label>
                    <Textarea
                      value={editTheatres}
                      onChange={(e) => setEditTheatres(e.target.value)}
                      rows={3}
                      placeholder="PVR ECX Chanakyapuri&#10;INOX Insignia Epicuria"
                      className="text-xs bg-muted/10 border-border/80 focus:border-rose-500/40"
                    />
                  </div>
                </>
              )}

              {/* Notification Medium */}
              <div className="space-y-1.5 border-t border-border/30 pt-3">
                <div className="flex items-center justify-between">
                  <label className="font-bold text-muted-foreground uppercase tracking-wider text-[10px]">
                    Notification Medium
                  </label>
                  <div className="flex gap-1.5 flex-wrap">
                    {(["Email", "Discord Webhook", "SMS", "WhatsApp", "Phone Call"] as const).map((m) => (
                      <button
                        key={m}
                        type="button"
                        onClick={() => setEditMedium(m)}
                        className={`text-[10px] font-bold px-2 py-1 rounded-md border transition-all cursor-pointer ${
                          editMedium === m
                            ? "bg-rose-500/10 text-rose-400 border-rose-500/25"
                            : "bg-muted/10 text-muted-foreground border-transparent hover:text-foreground"
                        }`}
                      >
                        {m === "Discord Webhook" ? "Discord" : m}
                      </button>
                    ))}
                  </div>
                </div>

                {editMedium === "Email" && (
                  <Input
                    type="email"
                    value={editEmail}
                    onChange={(e) => setEditEmail(e.target.value)}
                    placeholder="your-email@gmail.com"
                    className="h-9.5 text-xs bg-muted/10 border-border/80 focus:border-rose-500/40"
                  />
                )}

                {editMedium === "Discord Webhook" && (
                  <Input
                    type="text"
                    value={editWebhook}
                    onChange={(e) => setEditWebhook(e.target.value)}
                    placeholder="Paste Discord Webhook URL"
                    className="h-9.5 text-xs bg-muted/10 border-border/80 focus:border-rose-500/40"
                  />
                )}

                {["SMS", "WhatsApp", "Phone Call"].includes(editMedium) && (
                  <Input
                    type="text"
                    value={editPhone}
                    onChange={(e) => setEditPhone(e.target.value)}
                    placeholder="+91 98765 43210 (Indian Mobile Number)"
                    className="h-9.5 text-xs bg-muted/10 border-border/80 focus:border-rose-500/40"
                  />
                )}
              </div>

              {/* Check Frequency */}
              <div className="space-y-2 border-t border-border/30 pt-3">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-muted-foreground uppercase tracking-wider text-[10px]">
                    Check Frequency
                  </span>
                  <div className="flex items-center gap-1.5">
                    <Input
                      type="number"
                      min="1"
                      value={editIntervalSec > 0 ? Math.round(editIntervalSec / 60) : ''}
                      onChange={(e) => {
                        const val = parseInt(e.target.value, 10);
                        setEditIntervalSec(isNaN(val) ? 0 : val * 60);
                      }}
                      className="w-16 h-7 text-xs font-mono text-right bg-muted/20 text-foreground"
                    />
                    <span className="text-[11px] text-muted-foreground">min</span>
                  </div>
                </div>
              </div>

              {/* Modal Buttons */}
              <div className="flex justify-end gap-2 border-t border-border/30 pt-4 mt-4">
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => setEditingJob(null)}
                  disabled={editLoading}
                  className="h-9 text-xs"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={editLoading}
                  className="h-9 text-xs font-bold bg-rose-500 hover:bg-rose-600 text-white gap-1.5 cursor-pointer"
                >
                  {editLoading ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : "Save Job Changes"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* In-App Confirmation Modal for Delete Tracker */}
      <ConfirmModal
        isOpen={!!jobToDelete}
        onClose={() => setJobToDelete(null)}
        onConfirm={async () => {
          if (jobToDelete) {
            await handleDeleteJob(jobToDelete.id);
            setJobToDelete(null);
          }
        }}
        title="Remove Ticket Tracker"
        description={
          <>
            Are you sure you want to remove ticket tracker <strong className="text-foreground font-mono">#{jobToDelete?.id}</strong> ({jobToDelete?.movie_name})? This action cannot be undone.
            {!paymentsDisabled && jobToDelete?.price_paise && jobToDelete.price_paise > 0 && jobToDelete.notification_status !== 'delivered' && jobToDelete.notification_status !== 'sent' && (
              <span className="block mt-2 font-medium text-emerald-400">
                💰 Cancelling before booking opens will immediately refund ₹{(jobToDelete.price_paise / 100).toFixed(2)} to your wallet.
              </span>
            )}
          </>
        }
        confirmText="Remove Alert"
        cancelText="Cancel"
        variant="danger"
        icon="delete"
      />

    </main>
  );
}
