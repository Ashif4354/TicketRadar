import React, { useState } from 'react';
import { ShieldCheck, ExternalLink, CheckCircle2 } from 'lucide-react';
import { Button } from './button';

interface TermsModalProps {
  isOpen: boolean;
  onAccept: () => Promise<void> | void;
}

export const TermsModal: React.FC<TermsModalProps> = ({ isOpen, onAccept }) => {
  const [agreed, setAgreed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleAccept = async () => {
    if (!agreed) return;
    setLoading(true);
    setError(null);
    try {
      await onAccept();
    } catch (err: any) {
      setError(err?.message || 'Failed to record terms acceptance. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-xl rounded-2xl border border-rose-500/30 bg-[#121217] p-6 shadow-2xl text-left overflow-hidden">
        <div className="flex items-center gap-3 pb-4 border-b border-border/50">
          <div className="h-10 w-10 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-500 flex items-center justify-center">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-foreground">Updated Terms of Service (v2.0)</h2>
            <p className="text-xs text-muted-foreground">Please review and accept our updated terms to proceed</p>
          </div>
        </div>

        <div className="mt-4 space-y-3 max-h-[60vh] overflow-y-auto pr-1 text-xs text-muted-foreground leading-relaxed">
          <p>
            TicketRadar has introduced multi-channel notifications (SMS, WhatsApp, and Automated Phone Calls) and an integrated user wallet.
            Before continuing, please review these key policy terms:
          </p>

          <div className="rounded-xl border border-border/60 bg-muted/20 p-3 space-y-2.5">
            <div className="flex gap-2">
              <CheckCircle2 className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-foreground">Multi-Channel Alerts:</span> Alerts are delivered via Email, Discord, SMS, WhatsApp, and Voice calls powered by Twilio and Amazon Polly.
              </div>
            </div>

            <div className="flex gap-2">
              <CheckCircle2 className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-foreground">Consent & Opt-In:</span> SMS, WhatsApp, and automated calls require your affirmative consent, which you may manage or revoke anytime in your Profile.
              </div>
            </div>

            <div className="flex gap-2">
              <CheckCircle2 className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-foreground">User Wallet & Credits:</span> 1 Credit = ₹1.00 (100 paise). Wallet credits are strictly non-withdrawable and non-redeemable for physical cash or payout.
              </div>
            </div>

            <div className="flex gap-2">
              <CheckCircle2 className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-foreground">Refund & Delivery Policy:</span> Pre-notification cancellations and confirmed delivery failures receive an immediate 100% wallet refund. Phone calls that remain unanswered or busy after 3 immediate attempts are deemed policy-exempt deliveries accompanied by a fallback email, and are not refunded.
              </div>
            </div>
          </div>

          <div className="pt-2 flex items-center justify-between text-xs">
            <a
              href="/tc"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-rose-400 hover:text-rose-300 underline font-medium"
            >
              Read full Terms of Service <ExternalLink className="h-3 w-3" />
            </a>
            <a
              href="/pp"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-rose-400 hover:text-rose-300 underline font-medium"
            >
              Read Privacy Policy <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </div>

        {error && (
          <div className="mt-3 p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs">
            {error}
          </div>
        )}

        <div className="mt-6 pt-4 border-t border-border/50 flex flex-col sm:flex-row items-center justify-between gap-4">
          <label className="flex items-center gap-2 text-xs text-foreground cursor-pointer select-none">
            <input
              type="checkbox"
              checked={agreed}
              onChange={(e) => setAgreed(e.target.checked)}
              className="h-4 w-4 rounded border-border text-rose-500 focus:ring-rose-500/40 bg-muted/30"
            />
            <span>I have read and agree to the Terms of Service v2.0 & Privacy Policy</span>
          </label>

          <Button
            onClick={handleAccept}
            disabled={!agreed || loading}
            className="w-full sm:w-auto h-10 px-6 text-xs font-semibold bg-rose-500 hover:bg-rose-600 cursor-pointer disabled:opacity-50"
          >
            {loading ? 'Recording...' : 'Accept & Continue'}
          </Button>
        </div>
      </div>
    </div>
  );
};
