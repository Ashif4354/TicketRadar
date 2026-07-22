import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Radar } from 'lucide-react';

import { Header } from './components/layout/Header';
import { Footer } from './components/layout/Footer';

import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { TermsPage } from './pages/TermsPage';
import { PrivacyPage } from './pages/PrivacyPage';
import { BlockedPage } from './pages/BlockedPage';
import { UnauthorizedPage } from './pages/UnauthorizedPage';
import { AppDashboard } from './pages/AppDashboard';
import { AdminDashboard } from './pages/AdminDashboard';

import { auth, getAppCheckToken } from './lib/firebase';
import { onAuthStateChanged } from 'firebase/auth';
import type { User } from 'firebase/auth';

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [claims, setClaims] = useState<any>(null);
  const [authLoading, setAuthLoading] = useState(true);

  useEffect(() => {
    return onAuthStateChanged(auth, async (currentUser) => {
      if (currentUser) {
        setUser(currentUser);
        try {
          const tokenResult = await currentUser.getIdTokenResult(true);
          setClaims(tokenResult.claims);

          // Record login event for admin Discord notification
          const idToken = tokenResult.token;
          const appCheckToken = await getAppCheckToken();
          fetch('/api/users/login-event', {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${idToken}`,
              'X-Firebase-AppCheck': appCheckToken,
              'Content-Type': 'application/json'
            }
          }).catch(err => console.error("Error sending login event:", err));
        } catch (err) {
          console.error("Error fetching custom claims:", err);
        }
      } else {
        setUser(null);
        setClaims(null);
      }
      setAuthLoading(false);
    });
  }, []);

  if (authLoading) {
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

  const isAuthorized = claims?.authorized === true;
  const isAdmin = claims?.role === 'admin';
  const isBlocked = claims?.blocked === true;

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-background text-foreground flex flex-col antialiased">
        <Header user={user} claims={claims} />
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/tc" element={<TermsPage />} />
          <Route path="/pp" element={<PrivacyPage />} />
          <Route path="/login" element={
            user ? <Navigate to="/" replace /> : <LoginPage />
          } />
          <Route path="/app" element={
            !user ? <Navigate to="/login" replace /> :
            isBlocked ? <BlockedPage /> :
            !isAuthorized ? <UnauthorizedPage /> :
            <AppDashboard />
          } />
          <Route path="/admin" element={
            !user ? <Navigate to="/login" replace /> :
            !isAdmin ? <Navigate to="/app" replace /> :
            <AdminDashboard />
          } />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <Footer />
      </div>
    </BrowserRouter>
  );
}
