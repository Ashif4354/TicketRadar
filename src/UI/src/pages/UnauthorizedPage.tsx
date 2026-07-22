import React, { useState, useRef } from 'react';
import ReCAPTCHA from 'react-google-recaptcha';
import { Lock, AlertTriangle, CheckCircle2, RefreshCw, Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { authenticatedFetch } from '../utils/api';

export function UnauthorizedPage() {
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
