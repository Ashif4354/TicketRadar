import { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import ReCAPTCHA from 'react-google-recaptcha';
import {
  ArrowLeft, User, Wallet, Bell, Phone, Mail, MessageSquare, PhoneCall,
  ShieldCheck, AlertCircle, Plus, Send, RefreshCw, CheckCircle2, RotateCcw
} from 'lucide-react';
import { Card, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { authenticatedFetch } from '../utils/api';
import { isPaymentsDisabled } from '../utils/payments';
import { isSecurityDisabled } from '../utils/security';
import type { UserProfileData, WalletBalance, WalletTransaction, AppConfig, PricingConfig } from '../types';

interface ProfilePageProps {
  config?: AppConfig | null;
}

export function ProfilePage({ config }: ProfilePageProps = {}) {
  const [profile, setProfile] = useState<UserProfileData | null>(null);
  const [wallet, setWallet] = useState<WalletBalance | null>(null);
  const [transactions, setTransactions] = useState<WalletTransaction[]>([]);
  const [appConfig, setAppConfig] = useState<AppConfig | null>(config || null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Email, Phone and Webhook form states
  const [emailInput, setEmailInput] = useState('');
  const [phoneInput, setPhoneInput] = useState('');
  const [discordInput, setDiscordInput] = useState('');
  const [updatingProfile, setUpdatingProfile] = useState(false);

  // Top-up Modal State
  const [topupModalOpen, setTopupModalOpen] = useState(false);
  const [topupAmount, setTopupAmount] = useState('10'); // default ₹10
  const [topupLoading, setTopupLoading] = useState(false);

  // Consent Confirmation Dialog State
  const [consentDialog, setConsentDialog] = useState<{
    open: boolean;
    channel: 'sms' | 'whatsapp' | 'call' | 'email' | 'discord';
    action: 'opt_in' | 'opt_out';
  }>({ open: false, channel: 'sms', action: 'opt_in' });

  // Test Alert State
  const [testingMedium, setTestingMedium] = useState<string | null>(null);
  const [prices, setPrices] = useState<PricingConfig | null>(null);

  const effectiveConfig = config || appConfig;
  const securityDisabled = isSecurityDisabled(effectiveConfig);
  const paymentsDisabled = isPaymentsDisabled(effectiveConfig);
  const hideWallet = securityDisabled || paymentsDisabled;
  const siteKeyVal = import.meta.env.VITE_RECAPTCHA_V2_SITE_KEY;

  const consentRecaptchaRef = useRef<ReCAPTCHA>(null);
  const testAlertRecaptchaRef = useRef<ReCAPTCHA>(null);
  const [testAlertDialog, setTestAlertDialog] = useState<{
    open: boolean;
    medium: string;
  }>({ open: false, medium: '' });

  const fetchProfileData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // 1. Fetch App Config
      let cfg: AppConfig | null = config || appConfig;
      if (!config) {
        const configRes = await authenticatedFetch('/api/config');
        if (configRes.ok) {
          cfg = await configRes.json();
          setAppConfig(cfg);
        }
      }

      // 2. Fetch User Profile
      const profRes = await authenticatedFetch('/api/profile');
      if (!profRes.ok) throw new Error('Failed to load profile details.');
      const profData: UserProfileData = await profRes.json();
      setProfile(profData);
      setPhoneInput(profData.phone_number || '');
      setDiscordInput(profData.discord_webhook_url || '');
      setEmailInput(profData.email_medium_address || profData.preferences?.email_address || profData.email || '');

      // 3. Fetch Wallet data if payments and security are enabled
      const isSecDisabled = isSecurityDisabled(cfg || effectiveConfig);
      const isPayDisabled = isPaymentsDisabled(cfg || effectiveConfig) || profRes.headers.get('x-payments-disabled') === 'true';
      if (!isSecDisabled && !isPayDisabled) {
        const wRes = await authenticatedFetch('/api/wallet/balance');
        if (wRes.ok) {
          const wData = await wRes.json();
          setWallet(wData);
        }

        const tRes = await authenticatedFetch('/api/wallet/transactions');
        if (tRes.ok) {
          const tData = await tRes.json();
          setTransactions(tData);
        }
      } else {
        setWallet(null);
        setTransactions([]);
      }

      // 4. Fetch notification pricing configuration
      try {
        const pRes = await authenticatedFetch('/api/payments/prices');
        if (pRes.ok) {
          const pData = await pRes.json();
          if (pData && !pData.detail) {
            setPrices(pData);
          }
        }
      } catch (pErr) {
        console.error('Failed to load prices in profile:', pErr);
      }
    } catch (err: any) {
      setError(err?.message || 'Error loading profile data');
    } finally {
      setLoading(false);
    }
  }, [config, appConfig, effectiveConfig]);

  useEffect(() => {
    fetchProfileData();
  }, [fetchProfileData]);

  const handleSaveContactDetails = async () => {
    setError(null);
    setSuccessMsg(null);
    setUpdatingProfile(true);

    try {
      const res = await authenticatedFetch('/api/profile/preferences', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          phone_number: phoneInput.trim() || null,
          discord_webhook_url: discordInput.trim() || null,
          email_address: emailInput.trim() || null,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to update contact details.');

      setSuccessMsg('Saved Successfully');
      fetchProfileData();
    } catch (err: any) {
      setError(err?.message || 'Failed to save contact information.');
    } finally {
      setUpdatingProfile(false);
    }
  };

  const handleConsentToggle = (channel: 'sms' | 'whatsapp' | 'call' | 'email' | 'discord', currentConsented: boolean) => {
    setConsentDialog({
      open: true,
      channel,
      action: currentConsented ? 'opt_out' : 'opt_in',
    });
  };

  const executeConsentAction = async () => {
    const { channel, action } = consentDialog;
    setError(null);
    setSuccessMsg(null);

    let token = "";
    if (action === 'opt_in' && !securityDisabled) {
      token = consentRecaptchaRef.current?.getValue() || "";
      if (!token) {
        setError("Please complete the reCAPTCHA challenge before confirming consent opt-in.");
        return;
      }
    }

    setConsentDialog({ ...consentDialog, open: false });

    try {
      const endpoint = `/api/consent/${channel}/${action === 'opt_in' ? 'opt-in' : 'opt-out'}`;
      const payload: any = { recaptcha_token: token };
      if (channel === 'email') {
        payload.email_address = emailInput.trim() || profile?.email || undefined;
      } else if (channel === 'discord') {
        payload.webhook_url = discordInput.trim() || undefined;
      } else {
        payload.phone_number = phoneInput.trim() || undefined;
      }

      const res = await authenticatedFetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Consent update failed.');

      try { consentRecaptchaRef.current?.reset(); } catch {}
      setSuccessMsg(`Successfully ${action === 'opt_in' ? 'opted in to' : 'opted out of'} ${channel.toUpperCase()} alerts.`);
      fetchProfileData();
    } catch (err: any) {
      setError(err?.message || 'Error updating consent.');
    }
  };

  const getMediumPricePaise = (mediumName: string): number => {
    const m = mediumName.trim().toLowerCase();
    if (!prices) {
      if (m.includes('email')) return 0;
      if (m.includes('discord')) return 0;
      if (m.includes('sms')) return 50;
      if (m.includes('whatsapp')) return 100;
      if (m.includes('call') || m.includes('phone')) return 150;
      return 0;
    }
    if (m.includes('sms')) return prices.sms_paise ?? 50;
    if (m.includes('whatsapp')) return prices.whatsapp_paise ?? 100;
    if (m.includes('call') || m.includes('phone')) return prices.phone_call_paise ?? 150;
    if (m.includes('email')) return prices.email_paise ?? 0;
    if (m.includes('discord')) return prices.discord_paise ?? 0;
    return 0;
  };

  const isMediumFree = (mediumName: string): boolean => {
    return getMediumPricePaise(mediumName) === 0;
  };

  const getTestAlertTarget = (medium: string) => {
    if (medium === 'Email') return emailInput.trim() || profile?.email || '';
    if (medium === 'Discord') return discordInput.trim() || profile?.discord_webhook_url || '';
    return phoneInput.trim() || profile?.phone_number || '';
  };

  const handleOpenTestAlert = (medium: string) => {
    setError(null);
    setSuccessMsg(null);
    if (!isMediumFree(medium)) {
      setError(`Test notifications are only supported for free mediums (₹0) defined by the administrator.`);
      return;
    }
    setTestAlertDialog({ open: true, medium });
  };

  const executeSendTestAlert = async () => {
    const medium = testAlertDialog.medium;
    setError(null);
    setSuccessMsg(null);

    if (!isMediumFree(medium)) {
      setError(`Test notifications are only supported for free mediums (₹0) defined by the administrator.`);
      return;
    }

    let token = "";
    if (!securityDisabled) {
      token = testAlertRecaptchaRef.current?.getValue() || "";
      if (!token) {
        setError("Please complete the reCAPTCHA challenge before sending a test alert.");
        return;
      }
    }

    const recipient = getTestAlertTarget(medium);
    if (!recipient) {
      setError(`No contact destination configured for ${medium}. Please save your contact details first.`);
      return;
    }

    setTestingMedium(medium);
    try {
      const res = await authenticatedFetch('/api/test-notification', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          medium: medium.toLowerCase(),
          target: recipient,
          recaptcha_token: token,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Test alert failed.');

      try { testAlertRecaptchaRef.current?.reset(); } catch {}
      setTestAlertDialog({ open: false, medium: '' });
      setSuccessMsg(`Test alert for ${medium} dispatched successfully!`);
    } catch (err: any) {
      setError(err?.message || `Failed to send test alert for ${medium}.`);
    } finally {
      setTestingMedium(null);
    }
  };

  const handleAcceptTermsInProfile = async () => {
    try {
      const res = await authenticatedFetch('/api/terms/accept', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ version: '2.0' }),
      });
      if (res.ok) {
        setSuccessMsg('Terms v2.0 accepted successfully!');
        setProfile((prev) => (prev ? { ...prev, terms_accepted: true, terms_version_accepted: '2.0' } : prev));
        fetchProfileData();
      } else {
        const d = await res.json();
        setError(d.detail || 'Failed to accept terms.');
      }
    } catch (err: any) {
      setError(err?.message || 'Error accepting terms.');
    }
  };

  const handleTopup = async () => {
    if (hideWallet) {
      setError('Payment features are disabled.');
      return;
    }
    const amountNum = parseFloat(topupAmount);
    if (isNaN(amountNum) || amountNum < 1) {
      setError('Minimum top-up amount is ₹1.00');
      return;
    }
    setTopupLoading(true);
    setError(null);
    try {
      const amountPaise = Math.round(amountNum * 100);
      const res = await authenticatedFetch('/api/wallet/topup/initiate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount_paise: amountPaise }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to initiate wallet topup.');

      const paymentSessionId = data.session_token || data.payment_session_id;
      if (!paymentSessionId) {
        throw new Error('No checkout session token returned by gateway.');
      }

      if (data.checkout_url && !paymentSessionId) {
        window.location.href = data.checkout_url;
        return;
      }

      // Load gateway SDK dynamically if not loaded
      if (typeof (window as any).Cashfree === 'undefined') {
        const script = document.createElement('script');
        script.src = 'https://sdk.cashfree.com/js/v3/cashfree.js';
        script.onload = () => {
          initiateGatewayCheckout(paymentSessionId);
        };
        document.body.appendChild(script);
      } else {
        initiateGatewayCheckout(paymentSessionId);
      }
    } catch (err: any) {
      setError(err?.message || 'Error processing top-up');
      setTopupLoading(false);
    }
  };

  const initiateGatewayCheckout = (paymentSessionId: string) => {
    try {
      const isDev = appConfig?.environment === 'development';
      const cashfree = (window as any).Cashfree({
        mode: isDev ? 'sandbox' : 'production',
      });
      cashfree.checkout({
        paymentSessionId,
        redirectTarget: '_modal',
      }).then((result: any) => {
        if (result.error) {
          setError(result.error.message || 'Payment window closed or failed.');
        } else if (result.paymentDetails) {
          setSuccessMsg('Payment completed! Updating wallet...');
          setTimeout(() => fetchProfileData(), 2000);
        }
        setTopupModalOpen(false);
        setTopupLoading(false);
      });
    } catch (err: any) {
      setError('Error initiating payment modal: ' + err?.message);
      setTopupLoading(false);
    }
  };

  if (loading) {
    return (
      <main className="flex-1 container mx-auto max-w-5xl px-4 py-10 flex flex-col items-center justify-center min-h-[50vh]">
        <RefreshCw className="h-8 w-8 text-rose-500 animate-spin" />
        <p className="mt-4 text-xs font-semibold text-muted-foreground uppercase tracking-widest">
          Loading Profile & Settings...
        </p>
      </main>
    );
  }

  return (
    <main className="flex-1 container mx-auto max-w-5xl px-4 py-10 sm:px-6 space-y-8">
      <div className="flex items-center justify-between">
        <Link
          to="/app"
          className="inline-flex items-center gap-2 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors bg-muted/30 px-3 py-1.5 rounded-lg border border-border/50"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Dashboard
        </Link>
        <div className="flex items-center gap-2">
          {profile?.terms_accepted ? (
            <Badge className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[11px] font-semibold flex items-center gap-1.5 px-2.5 py-1">
              <ShieldCheck className="h-3.5 w-3.5" />
              Terms {profile.terms_version_accepted || 'v2.0'} Accepted
            </Badge>
          ) : (
            <button
              onClick={handleAcceptTermsInProfile}
              className="bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/20 text-[11px] font-semibold px-2.5 py-1 rounded-full cursor-pointer transition-colors flex items-center gap-1.5"
              title="Click to accept Terms v2.0"
            >
              <AlertCircle className="h-3.5 w-3.5" />
              Terms Pending (Click to Accept v2.0)
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2.5">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {successMsg && (
        <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center gap-2.5">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Profile Header Card */}
      <Card className="border border-border/80 glassmorphism p-6 sm:p-8 rounded-2xl">
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-5 justify-between">
          <div className="flex items-center gap-4">
            <div className="h-16 w-16 rounded-2xl bg-gradient-to-tr from-rose-500 to-pink-500 text-white flex items-center justify-center font-bold text-2xl shadow-xl shadow-rose-500/20">
              {profile?.email?.charAt(0).toUpperCase() || <User className="h-8 w-8" />}
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-bold text-foreground flex items-center gap-2">
                User Profile
              </h1>
              <p className="text-xs text-muted-foreground mt-0.5">{profile?.email}</p>
              <p className="text-[11px] text-muted-foreground/70 font-mono mt-0.5">UID: {profile?.uid}</p>
            </div>
          </div>

          {!hideWallet && wallet && (
            <div className="w-full sm:w-auto flex items-center justify-between sm:justify-end gap-4 p-4 rounded-xl border border-rose-500/20 bg-rose-500/5">
              <div>
                <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider block">Wallet Balance</span>
                <span className="text-2xl font-black text-rose-400">₹{wallet.balance_inr.toFixed(2)}</span>
              </div>
              <Button
                onClick={() => setTopupModalOpen(true)}
                className="h-9 px-4 text-xs font-semibold bg-rose-500 hover:bg-rose-600 flex items-center gap-1.5 cursor-pointer shadow-md shadow-rose-500/20"
              >
                <Plus className="h-3.5 w-3.5" />
                Top Up
              </Button>
            </div>
          )}
        </div>
      </Card>

      {/* Notification Mediums & Preferences */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-foreground flex items-center gap-2">
              <Bell className="h-5 w-5 text-rose-400" />
              Configured Notification Mediums
            </h2>
            <p className="text-xs text-muted-foreground">
              Manage your verified channels, explicit opt-in consents, and contact endpoints.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Medium 1: Email */}
          <Card className="border border-border/70 glassmorphism p-5 rounded-xl space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="h-8 w-8 rounded-lg bg-blue-500/10 text-blue-400 flex items-center justify-center">
                  <Mail className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-foreground">Email Alert</h3>
                  <p className="text-[11px] text-muted-foreground truncate max-w-[200px]">
                    {emailInput || profile?.email || 'Email not set'}
                  </p>
                </div>
              </div>
              {profile?.consents?.email_consented ? (
                <Badge className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px]">
                  Opted In
                </Badge>
              ) : (
                <Badge className="bg-muted text-muted-foreground border border-border text-[10px]">
                  Opted Out
                </Badge>
              )}
            </div>

            <div className="space-y-2 pt-2 border-t border-border/40">
              <div className="flex gap-2 items-center">
                <Input
                  type="email"
                  placeholder={profile?.email || "your-email@example.com"}
                  value={emailInput}
                  onChange={(e) => setEmailInput(e.target.value)}
                  className="h-8 text-xs bg-muted/20 flex-1"
                />
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setEmailInput(profile?.email || '')}
                  title="Reset to primary account email"
                  className="h-8 px-2 text-[11px] flex items-center gap-1 text-muted-foreground hover:text-foreground cursor-pointer"
                >
                  <RotateCcw className="h-3 w-3" />
                  <span className="hidden sm:inline">Reset</span>
                </Button>
              </div>

              <div className="flex items-center justify-between text-xs pt-1">
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleSaveContactDetails}
                    disabled={updatingProfile}
                    className="h-7 text-[11px] cursor-pointer"
                  >
                    Save Email
                  </Button>
                  <Button
                    size="sm"
                    variant={profile?.consents?.email_consented ? "outline" : "default"}
                    onClick={() => handleConsentToggle('email', !!profile?.consents?.email_consented)}
                    className="h-7 text-[11px] cursor-pointer"
                  >
                    {profile?.consents?.email_consented ? 'Revoke Consent' : 'Opt-In'}
                  </Button>
                </div>

                {isMediumFree('Email') ? (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={testingMedium === 'Email'}
                    onClick={() => handleOpenTestAlert('Email')}
                    className="h-7 text-[11px] flex items-center gap-1 cursor-pointer"
                  >
                    <Send className="h-3 w-3" />
                    {testingMedium === 'Email' ? 'Sending...' : 'Test Alert'}
                  </Button>
                ) : (
                  <span className="text-[10px] text-muted-foreground italic">
                    Paid medium (₹{(getMediumPricePaise('Email') / 100).toFixed(2)}) — test alerts unavailable
                  </span>
                )}
              </div>
            </div>
          </Card>

          {/* Medium 2: Discord Webhook */}
          <Card className="border border-border/70 glassmorphism p-5 rounded-xl space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="h-8 w-8 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
                  <MessageSquare className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-foreground">Discord Webhook</h3>
                  <p className="text-[11px] text-muted-foreground font-mono truncate max-w-[200px] sm:max-w-xs">
                    {profile?.discord_webhook_url || 'Webhook URL not configured'}
                  </p>
                </div>
              </div>
              {profile?.consents?.discord_consented ? (
                <Badge className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px]">
                  Opted In
                </Badge>
              ) : (
                <Badge className="bg-muted text-muted-foreground border border-border text-[10px]">
                  Opted Out
                </Badge>
              )}
            </div>

            <div className="space-y-2 pt-2 border-t border-border/40">
              <div className="flex gap-2 items-center">
                <Input
                  placeholder="https://discord.com/api/webhooks/..."
                  value={discordInput}
                  onChange={(e) => setDiscordInput(e.target.value)}
                  className="h-8 text-xs bg-muted/20 flex-1"
                />
                {discordInput && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setDiscordInput('')}
                    title="Clear webhook URL"
                    className="h-8 px-2 text-[11px] flex items-center gap-1 text-muted-foreground hover:text-foreground cursor-pointer"
                  >
                    <RotateCcw className="h-3 w-3" />
                    <span className="hidden sm:inline">Clear</span>
                  </Button>
                )}
              </div>
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleSaveContactDetails}
                    disabled={updatingProfile}
                    className="h-7 text-[11px] cursor-pointer"
                  >
                    Save Webhook
                  </Button>
                  <Button
                    size="sm"
                    variant={profile?.consents?.discord_consented ? "outline" : "default"}
                    onClick={() => handleConsentToggle('discord', !!profile?.consents?.discord_consented)}
                    className="h-7 text-[11px] cursor-pointer"
                  >
                    {profile?.consents?.discord_consented ? 'Revoke Consent' : 'Opt-In'}
                  </Button>
                </div>
                {discordInput.trim() && (
                  isMediumFree('Discord') ? (
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={testingMedium === 'Discord'}
                      onClick={() => handleOpenTestAlert('Discord')}
                      className="h-7 text-[11px] flex items-center gap-1 cursor-pointer"
                    >
                      <Send className="h-3 w-3" />
                      {testingMedium === 'Discord' ? 'Sending...' : 'Test Alert'}
                    </Button>
                  ) : (
                    <span className="text-[10px] text-muted-foreground italic">
                      Paid medium (₹{(getMediumPricePaise('Discord') / 100).toFixed(2)}) — test alerts unavailable
                    </span>
                  )
                )}
              </div>
            </div>
          </Card>

          {/* Medium 3: SMS Alerts */}
          <Card className="border border-border/70 glassmorphism p-5 rounded-xl space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="h-8 w-8 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
                  <Phone className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-foreground">SMS Alert</h3>
                  <p className="text-[11px] text-muted-foreground font-mono">
                    {profile?.phone_number || 'Phone not set'}
                  </p>
                </div>
              </div>
              {profile?.consents.sms_consented ? (
                <Badge className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px]">
                  Opted In
                </Badge>
              ) : (
                <Badge className="bg-muted text-muted-foreground border border-border text-[10px]">
                  Opted Out
                </Badge>
              )}
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-border/40 text-xs">
              <span className="text-muted-foreground">Requires +91 phone number</span>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant={profile?.consents.sms_consented ? "outline" : "default"}
                  onClick={() => handleConsentToggle('sms', !!profile?.consents.sms_consented)}
                  className="h-7 text-[11px] cursor-pointer"
                >
                  {profile?.consents.sms_consented ? 'Revoke Consent' : 'Opt-In to SMS'}
                </Button>
                {profile?.phone_number && profile?.consents.sms_consented && (
                  isMediumFree('SMS') ? (
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={testingMedium === 'SMS'}
                      onClick={() => handleOpenTestAlert('SMS')}
                      className="h-7 text-[11px] flex items-center gap-1 cursor-pointer"
                    >
                      <Send className="h-3 w-3" />
                      {testingMedium === 'SMS' ? 'Sending...' : 'Test'}
                    </Button>
                  ) : (
                    <span className="text-[10px] text-muted-foreground italic">
                      Paid medium (₹{(getMediumPricePaise('SMS') / 100).toFixed(2)}) — test alerts unavailable
                    </span>
                  )
                )}
              </div>
            </div>
          </Card>

          {/* Medium 4: WhatsApp Alerts */}
          <Card className="border border-border/70 glassmorphism p-5 rounded-xl space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="h-8 w-8 rounded-lg bg-green-500/10 text-green-400 flex items-center justify-center">
                  <MessageSquare className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-foreground">WhatsApp Alert</h3>
                  <p className="text-[11px] text-muted-foreground font-mono">
                    {profile?.phone_number || 'Phone not set'}
                  </p>
                </div>
              </div>
              {profile?.consents.whatsapp_consented ? (
                <Badge className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px]">
                  Opted In
                </Badge>
              ) : (
                <Badge className="bg-muted text-muted-foreground border border-border text-[10px]">
                  Opted Out
                </Badge>
              )}
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-border/40 text-xs">
              <span className="text-muted-foreground">Registered business templates</span>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant={profile?.consents.whatsapp_consented ? "outline" : "default"}
                  onClick={() => handleConsentToggle('whatsapp', !!profile?.consents.whatsapp_consented)}
                  className="h-7 text-[11px] cursor-pointer"
                >
                  {profile?.consents.whatsapp_consented ? 'Revoke Consent' : 'Opt-In to WhatsApp'}
                </Button>
                {profile?.phone_number && profile?.consents.whatsapp_consented && (
                  isMediumFree('WhatsApp') ? (
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={testingMedium === 'WhatsApp'}
                      onClick={() => handleOpenTestAlert('WhatsApp')}
                      className="h-7 text-[11px] flex items-center gap-1 cursor-pointer"
                    >
                      <Send className="h-3 w-3" />
                      {testingMedium === 'WhatsApp' ? 'Sending...' : 'Test'}
                    </Button>
                  ) : (
                    <span className="text-[10px] text-muted-foreground italic">
                      Paid medium (₹{(getMediumPricePaise('WhatsApp') / 100).toFixed(2)}) — test alerts unavailable
                    </span>
                  )
                )}
              </div>
            </div>
          </Card>

          {/* Medium 5: Automated Phone Call */}
          <Card className="border border-border/70 glassmorphism p-5 rounded-xl space-y-3 md:col-span-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="h-8 w-8 rounded-lg bg-rose-500/10 text-rose-400 flex items-center justify-center">
                  <PhoneCall className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-foreground">Automated Phone Call</h3>
                  <p className="text-[11px] text-muted-foreground font-mono">
                    {profile?.phone_number || 'Phone not set'} • Automated voice carrier network (Polly.Aditi TTS)
                  </p>
                </div>
              </div>
              {profile?.consents.call_consented ? (
                <Badge className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px]">
                  Opted In
                </Badge>
              ) : (
                <Badge className="bg-muted text-muted-foreground border border-border text-[10px]">
                  Opted Out
                </Badge>
              )}
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-border/40 text-xs">
              <span className="text-muted-foreground">Automated voice carrier network with 3 immediate retry attempts on failure. Unanswered calls logged as policy-exempt.</span>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant={profile?.consents.call_consented ? "outline" : "default"}
                  onClick={() => handleConsentToggle('call', !!profile?.consents.call_consented)}
                  className="h-7 text-[11px] cursor-pointer"
                >
                  {profile?.consents.call_consented ? 'Revoke Consent' : 'Opt-In to Calls'}
                </Button>
                {profile?.phone_number && profile?.consents.call_consented && (
                  isMediumFree('Phone Call') ? (
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={testingMedium === 'Phone Call'}
                      onClick={() => handleOpenTestAlert('Phone Call')}
                      className="h-7 text-[11px] flex items-center gap-1 cursor-pointer"
                    >
                      <Send className="h-3 w-3" />
                      {testingMedium === 'Phone Call' ? 'Calling...' : 'Test Call'}
                    </Button>
                  ) : (
                    <span className="text-[10px] text-muted-foreground italic">
                      Paid medium (₹{(getMediumPricePaise('Phone Call') / 100).toFixed(2)}) — test alerts unavailable
                    </span>
                  )
                )}
              </div>
            </div>
          </Card>
        </div>

        {/* Update Phone Number Bar */}
        <Card className="border border-border/70 glassmorphism p-5 rounded-xl">
          <h3 className="text-sm font-semibold text-foreground mb-1">Update Primary Phone Number</h3>
          <p className="text-xs text-muted-foreground mb-3">
            Used across SMS, WhatsApp, and Voice Call alerts. Indian 10-digit mobile numbers only.
          </p>
          <div className="flex flex-col sm:flex-row items-center gap-3">
            <Input
              placeholder="+91 98765 43210"
              value={phoneInput}
              onChange={(e) => setPhoneInput(e.target.value)}
              className="h-9 text-xs bg-muted/20"
            />
            <Button
              onClick={handleSaveContactDetails}
              disabled={updatingProfile}
              className="w-full sm:w-auto h-9 px-5 text-xs font-semibold bg-rose-500 hover:bg-rose-600 cursor-pointer"
            >
              {updatingProfile ? 'Saving...' : 'Update Phone'}
            </Button>
          </div>
        </Card>


      </div>

      {/* Wallet Transaction Ledger (when payments and security are enabled) */}
      {!hideWallet && (
        <Card className="border border-border/80 glassmorphism p-6 rounded-2xl space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Wallet className="h-5 w-5 text-rose-400" />
              <CardTitle className="text-base font-bold">Wallet Transaction Ledger</CardTitle>
            </div>
            <span className="text-xs text-muted-foreground">Immutable audit records</span>
          </div>

          {transactions.length === 0 ? (
            <p className="text-xs text-muted-foreground py-4 text-center">No wallet transactions recorded yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-border/50 text-muted-foreground font-semibold">
                    <th className="pb-2.5">Date / Time</th>
                    <th className="pb-2.5">Type</th>
                    <th className="pb-2.5">Description</th>
                    <th className="pb-2.5 text-right">Amount</th>
                    <th className="pb-2.5 text-right">Balance</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/30">
                  {transactions.map((tx) => (
                    <tr key={tx.id} className="hover:bg-muted/10 transition-colors">
                      <td className="py-2.5 text-muted-foreground whitespace-nowrap">
                        {tx.created_at ? new Date(tx.created_at).toLocaleString() : '—'}
                      </td>
                      <td className="py-2.5">
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-muted/40 border border-border">
                          {tx.type}
                        </span>
                      </td>
                      <td className="py-2.5 text-foreground max-w-xs truncate">{tx.description}</td>
                      <td className={`py-2.5 text-right font-bold ${tx.direction === 'CREDIT' ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {tx.direction === 'CREDIT' ? '+' : '-'}₹{(tx.amount_paise / 100).toFixed(2)}
                      </td>
                      <td className="py-2.5 text-right text-muted-foreground font-mono">
                        ₹{(tx.balance_after_paise / 100).toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {/* Top-Up Modal */}
      {!hideWallet && topupModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="relative w-full max-w-md rounded-2xl border border-rose-500/30 bg-[#121217] p-6 shadow-2xl text-left space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-border/50">
              <h3 className="text-base font-bold text-foreground flex items-center gap-2">
                <Wallet className="h-5 w-5 text-rose-400" />
                Top Up TicketRadar Wallet
              </h3>
              <button
                onClick={() => setTopupModalOpen(false)}
                className="text-muted-foreground hover:text-foreground text-sm cursor-pointer"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-muted-foreground">
              Add funds to your wallet via online payment (UPI, Netbanking, Cards). Funds are non-withdrawable and used exclusively for ticket notification alerts.
            </p>

            <div className="grid grid-cols-4 gap-2 pt-1">
              {['5', '10', '25', '50'].map((amt) => (
                <button
                  key={amt}
                  type="button"
                  onClick={() => setTopupAmount(amt)}
                  className={`h-9 rounded-lg border text-xs font-semibold cursor-pointer transition-colors ${
                    topupAmount === amt
                      ? 'border-rose-500 bg-rose-500/10 text-rose-400 font-bold'
                      : 'border-border bg-muted/20 text-muted-foreground hover:bg-muted/40'
                  }`}
                >
                  ₹{amt}
                </button>
              ))}
            </div>

            <div className="space-y-1">
              <label className="text-xs font-medium text-foreground">Custom Amount (₹)</label>
              <Input
                type="number"
                min="1"
                step="1"
                value={topupAmount}
                onChange={(e) => setTopupAmount(e.target.value)}
                className="h-10 text-sm bg-muted/20"
                placeholder="10"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-border/50">
              <Button
                variant="outline"
                onClick={() => setTopupModalOpen(false)}
                className="h-9 text-xs cursor-pointer"
              >
                Cancel
              </Button>
              <Button
                onClick={handleTopup}
                disabled={topupLoading}
                className="h-9 px-5 text-xs font-semibold bg-rose-500 hover:bg-rose-600 cursor-pointer"
              >
                {topupLoading ? 'Redirecting...' : `Pay ₹${topupAmount}`}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Consent Confirmation Dialog */}
      {consentDialog.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="relative w-full max-w-md rounded-2xl border border-rose-500/30 bg-[#121217] p-6 shadow-2xl text-left space-y-4">
            <div className="flex items-center gap-3 pb-3 border-b border-border/50">
              <div className="h-9 w-9 rounded-xl bg-rose-500/10 text-rose-400 flex items-center justify-center">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <h3 className="text-base font-bold text-foreground">
                {consentDialog.action === 'opt_in' ? 'Consent Opt-In' : 'Revoke Consent'}
              </h3>
            </div>

            <p className="text-xs text-muted-foreground leading-relaxed">
              {consentDialog.action === 'opt_in' ? (
                <>
                  By opting in, you give express affirmative consent to receive automated{' '}
                  <strong className="text-foreground uppercase">{consentDialog.channel}</strong> ticket availability
                  alerts. You may revoke this consent anytime in your Profile.
                </>
              ) : (
                <>
                  Are you sure you want to revoke consent for{' '}
                  <strong className="text-foreground uppercase">{consentDialog.channel}</strong> alerts? You will no
                  longer receive automated alerts via this channel.
                </>
              )}
            </p>

            {!securityDisabled && consentDialog.action === 'opt_in' && (
              <div className="flex justify-center py-2">
                <div className="g-recaptcha-premium-container">
                  <ReCAPTCHA
                    ref={consentRecaptchaRef}
                    sitekey={siteKeyVal}
                    theme="dark"
                  />
                </div>
              </div>
            )}

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-border/50">
              <Button
                variant="outline"
                onClick={() => setConsentDialog({ ...consentDialog, open: false })}
                className="h-9 text-xs cursor-pointer"
              >
                Cancel
              </Button>
              <Button
                onClick={executeConsentAction}
                className={`h-9 px-5 text-xs font-semibold cursor-pointer ${
                  consentDialog.action === 'opt_in'
                    ? 'bg-rose-500 hover:bg-rose-600'
                    : 'bg-destructive hover:bg-destructive/90 text-white'
                }`}
              >
                {consentDialog.action === 'opt_in' ? 'Confirm Opt-In' : 'Revoke Consent'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Test Alert Confirmation Dialog */}
      {testAlertDialog.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="relative w-full max-w-md rounded-2xl border border-rose-500/30 bg-[#121217] p-6 shadow-2xl text-left space-y-4">
            <div className="flex items-center gap-3 pb-3 border-b border-border/50">
              <div className="h-9 w-9 rounded-xl bg-rose-500/10 text-rose-400 flex items-center justify-center">
                <Send className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-foreground">
                  Send Test {testAlertDialog.medium} Alert
                </h3>
                <p className="text-xs text-muted-foreground">
                  Verify notification delivery to your configured address/phone
                </p>
              </div>
            </div>

            <p className="text-xs text-muted-foreground leading-relaxed">
              We will dispatch a sample ticket alert to verify your{' '}
              <strong className="text-foreground uppercase">{testAlertDialog.medium}</strong> channel:{' '}
              <span className="font-mono text-foreground font-semibold">
                {getTestAlertTarget(testAlertDialog.medium) || '(Not configured)'}
              </span>
            </p>

            {!getTestAlertTarget(testAlertDialog.medium) && (
              <div className="rounded-lg bg-destructive/10 border border-destructive/20 p-2.5 text-xs text-destructive flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>Please configure and save your {testAlertDialog.medium} contact details before testing.</span>
              </div>
            )}

            {!isMediumFree(testAlertDialog.medium) && (
              <div className="rounded-lg bg-destructive/10 border border-destructive/20 p-2.5 text-xs text-destructive flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>Test notifications are only supported for free mediums (₹0) defined by the administrator.</span>
              </div>
            )}

            {!securityDisabled && (
              <div className="flex justify-center py-2">
                <div className="g-recaptcha-premium-container">
                  <ReCAPTCHA
                    ref={testAlertRecaptchaRef}
                    sitekey={siteKeyVal}
                    theme="dark"
                  />
                </div>
              </div>
            )}

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-border/50">
              <Button
                variant="outline"
                onClick={() => {
                  try { testAlertRecaptchaRef.current?.reset(); } catch {}
                  setTestAlertDialog({ open: false, medium: '' });
                }}
                disabled={!!testingMedium}
                className="h-9 text-xs cursor-pointer"
              >
                Cancel
              </Button>
              <Button
                onClick={executeSendTestAlert}
                disabled={!getTestAlertTarget(testAlertDialog.medium) || !isMediumFree(testAlertDialog.medium) || !!testingMedium}
                className="h-9 px-5 text-xs font-semibold bg-rose-500 hover:bg-rose-600 text-white cursor-pointer flex items-center gap-1.5"
              >
                {testingMedium ? (
                  <>
                    <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                    Dispatching...
                  </>
                ) : (
                  <>
                    <Send className="h-3.5 w-3.5" />
                    Send Test Alert
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
