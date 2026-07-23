// src/UI/src/lib/firebase.ts

import { initializeApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider, signInWithPopup, signOut } from 'firebase/auth';
import { initializeAppCheck, ReCaptchaV3Provider, getToken } from 'firebase/app-check';

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Auth
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();

const isSecurityDisabled = import.meta.env.VITE_DISABLE_SECURITY === 'true' || import.meta.env.DISABLE_SECURITY === 'true';

// In DEV mode, set the debug token BEFORE initializeAppCheck so the SDK
// uses the debug flow instead of attempting a real reCAPTCHA exchange.
// Do NOT combine the global debug token flag with ReCaptchaV3Provider —
// that causes `apps/undefined` 400 errors because the SDK gets confused
// between the debug and production code paths.
if (import.meta.env.DEV && !isSecurityDisabled) {
  (self as any).FIREBASE_APPCHECK_DEBUG_TOKEN = import.meta.env.VITE_APP_CHECK_DEBUG_TOKEN || true;
}

const siteKey = import.meta.env.VITE_APP_CHECK_SITE_KEY;

// Only initialize App Check with ReCaptchaV3Provider in production.
// In DEV mode the FIREBASE_APPCHECK_DEBUG_TOKEN on `self` handles it.
export const appCheck = (!isSecurityDisabled && !import.meta.env.DEV && siteKey) ? initializeAppCheck(app, {
  provider: new ReCaptchaV3Provider(siteKey),
  isTokenAutoRefreshEnabled: true
}) : null;

export const loginWithGoogle = () => {
  return signInWithPopup(auth, googleProvider);
};

export const logout = () => {
  return signOut(auth);
};

export const getAppCheckToken = async (): Promise<string> => {
  if (!appCheck) return "";
  try {
    const result = await getToken(appCheck, false);
    return result.token;
  } catch (err) {
    console.error("Failed to get App Check token:", err);
    return "";
  }
};

export const getAuthToken = async (forceRefresh: boolean = false): Promise<string> => {
  if (!auth.currentUser) {
    try {
      await auth.authStateReady();
    } catch (e) {
      // ignore authStateReady error
    }
  }
  if (!auth.currentUser) return "";
  try {
    return await auth.currentUser.getIdToken(forceRefresh);
  } catch (err) {
    console.error("Failed to get ID token:", err);
    return "";
  }
};
