import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowLeft, User, Wallet, Bell, Phone, Mail, MessageSquare, PhoneCall,
  ShieldCheck, AlertCircle, Plus, Send, RefreshCw, CheckCircle2
} from 'lucide-react';
import { Card, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { authenticatedFetch } from '../utils/api';
import type { UserProfileData, WalletBalance, WalletTransaction, AppConfig } from '../types';

export function ProfilePage() {
  const [profile, setProfile] = useState<UserProfileData | null>(null);
  const [wallet, setWallet] = useState<WalletBalance | null>(null);
  const [transactions, setTransactions] = useState<WalletTransaction[]>([]);
  const [appConfig, setAppConfig] = useState<AppConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Phone and Webhook form states
  const [phoneInput, setPhoneInput] = useState('');
  const [discordInput, setDiscordInput] = useState('');
  const [updatingProfile, setUpdatingProfile] = useState(false);

  // Top-up Modal State
  const [topupModalOpen, setTopupModalOpen] = useState(false);
  const [topupAmount, setTopupAmount] = useState('100'); // default ₹100
  const [topupLoading, setTopupLoading] = useState(false);

  // Consent Confirmation Dialog State
  const [consentDialog, setConsentDialog] = useState<{
    open: boolean;
    channel: 'sms' | 'whatsapp' | 'call';
    action: 'opt_in' | 'opt_out';
  }>({ open: false, channel: 'sms', action: 'opt_in' });

  // Test Alert State
  const [testingMedium, setTestingMedium] = useState<string | null>(null);

  const fetchProfileData = async () => {
    try {
      setLoading(true);
      setError(null);

      // 1. Fetch App Config
      const configRes = await authenticatedFetch('/api/config');
      if (configRes.ok) {
        const cfg = await configRes.json();
        setAppConfig(cfg);
      }

      // 2. Fetch User Profile
      const profRes = await authenticatedFetch('/api/profile');
      if (!profRes.ok) throw new Error('Failed to load profile details.');
      const profData: UserProfileData = await profRes.json();
      setProfile(profData);
      setPhoneInput(profData.phone_number || '');
      setDiscordInput(profData.discord_webhook_url || '');

      // 3. Fetch Wallet data if payments are enabled
      const paymentsDisabled = profRes.headers.get('x-payments-disabled') === 'true';
      if (!paymentsDisabled) {
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
      }
    } catch (err: any) {
      setError(err?.message || 'Error loading profile data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfileData();
  }, []);

  const handleSaveContactDetails = async () => {
    setUpdatingProfile(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await authenticatedFetch('/api/profile/preferences', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          phone_number: phoneInput.trim() || null,
          discord_webhook_url: discordInput.trim() || null,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to update contact details.');

      setSuccessMsg('Contact information updated successfully!');
      fetchProfileData();
    } catch (err: any) {
      setError(err?.message || 'Failed to save contact information.');
    } finally {
      setUpdatingProfile(false);
    }
  };

  const handleConsentToggle = (channel: 'sms' | 'whatsapp' | 'call', currentConsented: boolean) => {
    setConsentDialog({
      open: true,
      channel,
      action: currentConsented ? 'opt_out' : 'opt_in',
    });
  };

  const executeConsentAction = async () => {
    const { channel, action } = consentDialog;
    setConsentDialog({ ...consentDialog, open: false });
    setError(null);
    setSuccessMsg(null);

    try {
      const endpoint = `/api/consent/${channel}/${action === 'opt_in' ? 'opt-in' : 'opt-out'}`;
      const res = await authenticatedFetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          phone_number: phoneInput.trim() || undefined,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Consent update failed.');

      setSuccessMsg(`Successfully ${action === 'opt_in' ? 'opted in to' : 'opted out of'} ${channel.toUpperCase()} alerts.`);
      fetchProfileData();
    } catch (err: any) {
      setError(err?.message || 'Error updating consent.');
    }
  };

  const handleSendTestAlert = async (medium: string) => {
    setTestingMedium(medium);
    setError(null);
    setSuccessMsg(null);
    try {
      let recipient = '';
      if (medium === 'Email') recipient = profile?.email || '';
      else if (medium === 'Discord') recipient = discordInput.trim() || profile?.discord_webhook_url || '';
      else recipient = phoneInput.trim() || profile?.phone_number || '';

      const res = await authenticatedFetch('/api/test-notification', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          medium: medium.toLowerCase(),
          target: recipient,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Test alert failed.');

      setSuccessMsg(`Test alert for ${medium} dispatched successfully!`);
    } catch (err: any) {
      setError(err?.message || `Failed to send test alert for ${medium}.`);
    } finally {
      setTestingMedium(null);
    }
  };

  const handleTopup = async () => {
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

      // Load Cashfree SDK dynamically if not loaded
      if (typeof (window as any).Cashfree === 'undefined') {
        const script = document.createElement('script');
        script.src = 'https://sdk.cashfree.com/js/v3/cashfree.js';
        script.onload = () => {
          initiateCashfreeCheckout(paymentSessionId);
        };
        document.body.appendChild(script);
      } else {
        initiateCashfreeCheckout(paymentSessionId);
      }
    } catch (err: any) {
      setError(err?.message || 'Error processing top-up');
      setTopupLoading(false);
    }
  };

  const initiateCashfreeCheckout = (paymentSessionId: string) => {
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
      setError('Error initiating Cashfree modal: ' + err?.message);
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

  const paymentsDisabled = appConfig?.disable_payments === true;

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
            <Badge className="bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[11px] font-semibold">
              Terms Pending
            </Badge>
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

          {!paymentsDisabled && wallet && (
            <div className="w-full sm:w-auto flex items-center justify-between sm:justify-end gap-4 p-4 rounded-xl border border-rose-500/20 bg-rose-500/5">
              <div>
                <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider block">Wallet Balance</span>
                <span className="text-2xl font-black text-rose-400">₹{wallet.balance_inr.toFixed(2)}</span>
                <span className="text-[10px] text-muted-foreground block">({wallet.balance_paise} credits)</span>
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
                  <p className="text-[11px] text-muted-foreground">{profile?.email}</p>
                </div>
              </div>
              <Badge className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px]">
                Free / Active
              </Badge>
            </div>
            <div className="flex items-center justify-between pt-2 border-t border-border/40 text-xs">
              <span className="text-muted-foreground">Account primary email</span>
              <Button
                size="sm"
                variant="outline"
                disabled={testingMedium === 'Email'}
                onClick={() => handleSendTestAlert('Email')}
                className="h-7 text-[11px] flex items-center gap-1 cursor-pointer"
              >
                <Send className="h-3 w-3" />
                {testingMedium === 'Email' ? 'Sending...' : 'Test Alert'}
              </Button>
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
                  <p className="text-[11px] text-muted-foreground">
                    {profile?.discord_webhook_url ? 'Configured' : 'Not configured'}
                  </p>
                </div>
              </div>
              <Badge className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px]">
                Free / Active
              </Badge>
            </div>
            <div className="space-y-2 pt-2 border-t border-border/40">
              <Input
                placeholder="https://discord.com/api/webhooks/..."
                value={discordInput}
                onChange={(e) => setDiscordInput(e.target.value)}
                className="h-8 text-xs bg-muted/20"
              />
              <div className="flex items-center justify-between text-xs">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleSaveContactDetails}
                  disabled={updatingProfile}
                  className="h-7 text-[11px] cursor-pointer"
                >
                  Save Webhook
                </Button>
                {profile?.discord_webhook_url && (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={testingMedium === 'Discord'}
                    onClick={() => handleSendTestAlert('Discord')}
                    className="h-7 text-[11px] flex items-center gap-1 cursor-pointer"
                  >
                    <Send className="h-3 w-3" />
                    {testingMedium === 'Discord' ? 'Sending...' : 'Test Alert'}
                  </Button>
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
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={testingMedium === 'SMS'}
                    onClick={() => handleSendTestAlert('SMS')}
                    className="h-7 text-[11px] flex items-center gap-1 cursor-pointer"
                  >
                    <Send className="h-3 w-3" />
                    {testingMedium === 'SMS' ? 'Sending...' : 'Test'}
                  </Button>
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
              <span className="text-muted-foreground">Pre-approved templates</span>
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
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={testingMedium === 'WhatsApp'}
                    onClick={() => handleSendTestAlert('WhatsApp')}
                    className="h-7 text-[11px] flex items-center gap-1 cursor-pointer"
                  >
                    <Send className="h-3 w-3" />
                    {testingMedium === 'WhatsApp' ? 'Sending...' : 'Test'}
                  </Button>
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
                    {profile?.phone_number || 'Phone not set'} • Polly.Aditi Indian English TTS
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
              <span className="text-muted-foreground">3 immediate retry attempts on failure. Unanswered calls logged as policy-exempt.</span>
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
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={testingMedium === 'Phone Call'}
                    onClick={() => handleSendTestAlert('Phone Call')}
                    className="h-7 text-[11px] flex items-center gap-1 cursor-pointer"
                  >
                    <Send className="h-3 w-3" />
                    {testingMedium === 'Phone Call' ? 'Calling...' : 'Test Call'}
                  </Button>
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

      {/* Wallet Transaction Ledger (when payments enabled) */}
      {!paymentsDisabled && (
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
      {topupModalOpen && (
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
              Add credits to your wallet via Cashfree (UPI, Netbanking, Cards). 1 Credit = ₹1.00 = 100 paise. Wallet credits are non-withdrawable.
            </p>

            <div className="grid grid-cols-4 gap-2 pt-1">
              {['50', '100', '200', '500'].map((amt) => (
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
                placeholder="100"
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
                  alerts at your registered phone number. You may revoke this consent anytime in your Profile.
                </>
              ) : (
                <>
                  Are you sure you want to revoke consent for{' '}
                  <strong className="text-foreground uppercase">{consentDialog.channel}</strong> alerts? You will no
                  longer receive automated alerts via this channel.
                </>
              )}
            </p>

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
    </main>
  );
}
