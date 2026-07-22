import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Radar, AlertTriangle, CheckCircle2, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { loginWithGoogle } from '../lib/firebase';

export function LoginPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [acceptedTC, setAcceptedTC] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async () => {
    if (!acceptedTC) return;
    setLoading(true);
    setError(null);
    try {
      await loginWithGoogle();
      navigate('/');
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
            Sign in with your Google account to set up ticket alerts.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4 p-0">
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
              </Link>{' '}
              and{' '}
              <Link to="/pp" target="_blank" className="text-primary font-semibold hover:underline">
                Privacy Policy
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
              <svg className="h-4.5 w-4.5 mr-2 inline-block" viewBox="0 0 24 24" width="24" height="24" xmlns="http://www.w3.org/2000/svg">
                <path d="M21.35,11.1H12v2.7h5.38C17.15,15.54,14.88,17,12,17c-2.94,0-5.46-2.06-6.38-4.83a7.3,7.3,0,0,1,0-4.34C6.54,5.06,9.06,3,12,3a6.88,6.88,0,0,1,4.9,2.06l2.12-2.12A9.82,9.82,0,0,0,12,0C6.93,0,2.61,4.24,1.21,9.75a10,10,0,0,0,0,4.5C2.61,19.76,6.93,24,12,24a9.83,9.83,0,0,0,7.18-2.92C22.18,18.3,23.3,13.86,22.18,11.1Z" fill="#EA4335" />
              </svg>
            )}
            Sign in with Google
          </Button>

          {!acceptedTC ? (
            <p className="text-[11px] text-amber-500/90 font-medium text-center">
              Please check the agreement box above to enable Google sign-in.
            </p>
          ) : (
            <p className="text-[11px] text-emerald-500/90 font-medium text-center flex items-center justify-center gap-1">
              <CheckCircle2 className="h-3 w-3 inline" /> Terms & Privacy accepted.
            </p>
          )}
        </CardContent>
      </Card>
    </main>
  );
}
