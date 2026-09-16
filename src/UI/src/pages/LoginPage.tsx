import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Radar, AlertTriangle, CheckCircle2, RefreshCw, Shield } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { loginWithGoogle } from '../lib/firebase';
import { isSecurityDisabled } from '../utils/security';
import type { AppConfig } from '../types';

interface LoginPageProps {
  config?: AppConfig | null;
}

export function LoginPage({ config }: LoginPageProps = {}) {
  const securityDisabled = isSecurityDisabled(config);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [acceptedTC, setAcceptedTC] = useState(() => isSecurityDisabled(config));
  const navigate = useNavigate();

  useEffect(() => {
    if (securityDisabled) {
      setAcceptedTC(true);
    }
  }, [securityDisabled]);

  const handleLogin = async () => {
    if (!acceptedTC) return;
    setLoading(true);
    setError(null);
    try {
      await loginWithGoogle();
      navigate('/app');
    } catch (err: any) {
      console.error("Google sign in failed:", err);
      setError(err.message || "Failed to log in with Google.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex-1 flex items-center justify-center px-4 py-16">
      <Card className="w-full max-w-md border border-border/80 shadow-2xl glassmorphism glow-primary p-6 rounded-2xl text-center space-y-6">
        <CardHeader className="space-y-2 p-0">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-tr from-rose-500 to-pink-500 text-white shadow-lg shadow-rose-500/20 mb-2">
            <Radar className="h-6 w-6" />
          </div>
          <CardTitle className="text-2xl font-extrabold tracking-tight">Log in to TicketRadar</CardTitle>
          <CardDescription className="text-xs text-muted-foreground">
            {securityDisabled 
              ? "Authentication is bypassed (DISABLE_SECURITY=true)." 
              : "Sign in with your Google account to set up ticket alerts."}
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4 p-0">
          {securityDisabled ? (
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3.5 text-xs text-amber-300 flex flex-col gap-2.5 text-left">
              <div className="flex items-center gap-2 font-semibold text-amber-300">
                <Shield className="h-4 w-4 text-amber-400 shrink-0" />
                <span>Security Bypassed</span>
              </div>
              <p className="text-[11px] text-amber-200/80 leading-relaxed">
                Authentication and authorization checks are disabled. You can enter the dashboard directly without signing in.
              </p>
              <div className="flex items-center gap-2 pt-1">
                <Button
                  onClick={() => navigate('/app')}
                  className="w-full bg-amber-500 hover:bg-amber-600 text-black font-bold text-xs h-8 cursor-pointer rounded-lg"
                >
                  Enter App
                </Button>
              </div>
            </div>
          ) : (
            <>
              {error && (
                <div className="rounded-xl border border-destructive/20 bg-destructive/10 p-3 text-xs text-destructive flex items-center gap-2 text-left">
                  <AlertTriangle className="h-4.5 w-4.5 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <div className="flex items-start space-x-3 text-left bg-muted/20 border border-border/60 p-3.5 rounded-xl transition-colors hover:border-border">
                <input
                  type="checkbox"
                  id="tc-checkbox"
                  checked={acceptedTC}
                  onChange={(e) => setAcceptedTC(e.target.checked)}
                  className="mt-0.5 h-4 w-4 rounded border-border text-primary focus:ring-primary accent-rose-500 cursor-pointer shrink-0"
                />
                <label htmlFor="tc-checkbox" className="text-xs text-muted-foreground leading-relaxed cursor-pointer select-none">
                  I agree to the{' '}
                  <Link to="/tc" target="_blank" className="text-primary font-semibold hover:underline">
                    Terms & Conditions
                  </Link>
                  ,{' '}
                  <Link to="/pp" target="_blank" className="text-primary font-semibold hover:underline">
                    Privacy Policy
                  </Link>
                  , and{' '}
                  <Link to="/refund" target="_blank" className="text-primary font-semibold hover:underline">
                    Refund Policy
                  </Link>
                  .
                </label>
              </div>

              <Button
                onClick={handleLogin}
                disabled={!acceptedTC || loading}
                className={`w-full h-11 bg-white hover:bg-gray-100 text-gray-900 font-semibold text-sm flex items-center justify-center gap-3 border border-gray-200 transition-all shadow-sm rounded-xl ${
                  !acceptedTC ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:shadow-md'
                }`}
              >
                {loading ? (
                  <RefreshCw className="h-4 w-4 animate-spin text-gray-900" />
                ) : (
                  <img src="/google.svg" alt="Google logo" className="h-5 w-5 mr-1 inline-block shrink-0" />
                )}
                Sign in with Google
              </Button>

              {!acceptedTC ? (
                <p className="text-[11px] text-amber-500/90 font-medium text-center">
                  Check the agreement box above to enable Google sign-in.
                </p>
              ) : (
                <p className="text-[11px] text-emerald-500/90 font-medium text-center flex items-center justify-center gap-1">
                  <CheckCircle2 className="h-3 w-3 inline" /> Terms & Privacy accepted.
                </p>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </main>
  );
}
