import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Radar } from 'lucide-react';

import { Header } from './components/layout/Header';
import { Footer } from './components/layout/Footer';

import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { TermsPage } from './pages/TermsPage';
import { PrivacyPage } from './pages/PrivacyPage';
import { InstructionsPage } from './pages/InstructionsPage';
import { BlockedPage } from './pages/BlockedPage';
import { UnauthorizedPage } from './pages/UnauthorizedPage';
import { AppDashboard } from './pages/AppDashboard';
import { AdminDashboard } from './pages/AdminDashboard';
import { ProfilePage } from './pages/ProfilePage';
import { TermsModal } from './components/ui/terms-modal';

import { auth } from './lib/firebase';
import { authenticatedFetch } from './utils/api';
import { isSecurityDisabled, setSecurityConfig } from './utils/security';
import { onAuthStateChanged } from 'firebase/auth';
import type { User } from 'firebase/auth';
import type { AppConfig } from './types';

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [claims, setClaims] = useState<any>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [configLoading, setConfigLoading] = useState(true);
  const [termsPending, setTermsPending] = useState(false);

  useEffect(() => {
    authenticatedFetch('/api/config')
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (data) {
          setConfig(data);
          setSecurityConfig(data);
        }
      })
      .catch(err => console.error("Error fetching config:", err))
      .finally(() => setConfigLoading(false));
  }, []);

  useEffect(() => {
    return onAuthStateChanged(auth, async (currentUser) => {
      if (currentUser) {
        setUser(currentUser);
        try {
          const tokenResult = await currentUser.getIdTokenResult(true);
          setClaims(tokenResult.claims);

          // Record login event for admin Discord notification
          authenticatedFetch('/api/users/login-event', { method: 'POST' })
            .catch(err => console.error("Error sending login event:", err));

          // Check terms acceptance
          if (tokenResult.claims?.authorized) {
            authenticatedFetch('/api/terms/status')
              .then(res => res.json())
              .then(data => {
                if (data && data.accepted === false) {
                  setTermsPending(true);
                }
              })
              .catch(err => console.error("Error checking terms status:", err));
          }
        } catch (err) {
          console.error("Error fetching custom claims:", err);
        }
      } else {
        setUser(null);
        setClaims(null);
        setTermsPending(false);
      }
      setAuthLoading(false);
    });
  }, []);

  const handleAcceptTerms = async () => {
    const res = await authenticatedFetch('/api/terms/accept', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ version: 'v2.0' }),
    });
    if (!res.ok) throw new Error('Failed to record acceptance.');
    setTermsPending(false);
  };

  const securityDisabled = isSecurityDisabled(config);

  if (!securityDisabled && (authLoading || configLoading)) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center">
        <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-tr from-rose-500 to-pink-500 text-white shadow-xl shadow-rose-500/20">
          <Radar className="h-8 w-8 animate-spin" />
        </div>
        <p className="mt-4 text-xs font-semibold text-muted-foreground uppercase tracking-widest animate-pulse">
          Initializing TicketRadar...
        </p>
      </div>
    );
  }

  const isAuthorized = securityDisabled || claims?.authorized === true;
  const isAdmin = securityDisabled || claims?.role === 'admin';
  const isBlocked = !securityDisabled && claims?.blocked === true;

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-background text-foreground flex flex-col antialiased">
        <Header user={user} claims={claims} config={config} />
        <TermsModal isOpen={!securityDisabled && termsPending} onAccept={handleAcceptTerms} />
        <Routes>
          <Route path="/" element={<LandingPage config={config} />} />
          <Route path="/tc" element={<TermsPage />} />
          <Route path="/pp" element={<PrivacyPage />} />
          <Route path="/instructions" element={<InstructionsPage />} />
          <Route path="/instruction" element={<InstructionsPage />} />
          <Route path="/login" element={
            user ? <Navigate to="/app" replace /> : <LoginPage config={config} />
          } />
          <Route path="/profile" element={
            (!user && !securityDisabled) ? <Navigate to="/login" replace /> :
            isBlocked ? <BlockedPage /> :
            !isAuthorized ? <UnauthorizedPage /> :
            <ProfilePage config={config} />
          } />
          <Route path="/app" element={
            (!user && !securityDisabled) ? <Navigate to="/login" replace /> :
            isBlocked ? <BlockedPage /> :
            !isAuthorized ? <UnauthorizedPage /> :
            <AppDashboard />
          } />
          <Route path="/admin" element={
            (!user && !securityDisabled) ? <Navigate to="/login" replace /> :
            !isAdmin ? <Navigate to="/app" replace /> :
            <AdminDashboard config={config} />
          } />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <Footer />
      </div>
    </BrowserRouter>
  );
}
