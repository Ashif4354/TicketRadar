// src/UI/src/lib/firebase.ts

import { initializeApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider, signInWithPopup, signOut } from 'firebase/auth';
import { initializeAppCheck, ReCaptchaV3Provider, getToken } from 'firebase/app-check';

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || (import.meta.env.VITE_FIREBASE_PROJECT_ID ? `${import.meta.env.VITE_FIREBASE_PROJECT_ID}.firebaseapp.com` : undefined),
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
  ...(import.meta.env.VITE_FIREBASE_STORAGE_BUCKET && { storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET }),
  ...(import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID && { messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID }),
  ...(import.meta.env.VITE_FIREBASE_MEASUREMENT_ID && { measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID })
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Auth
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();

import { isSecurityDisabled as checkSecurityDisabled, getEnvironment } from '../utils/security';

const isSecurityDisabled = checkSecurityDisabled();
const environment = getEnvironment();
const isProduction = environment === 'production' && !isSecurityDisabled;

// In DEV mode, set the debug token BEFORE initializeAppCheck so the SDK
// uses the debug flow instead of attempting a real reCAPTCHA exchange.
if (!isProduction && !isSecurityDisabled) {
  (self as any).FIREBASE_APPCHECK_DEBUG_TOKEN = import.meta.env.VITE_APP_CHECK_DEBUG_TOKEN || true;
}

const siteKey = import.meta.env.VITE_APP_CHECK_SITE_KEY;

// Only initialize App Check with ReCaptchaV3Provider in production when security is enabled.
export const appCheck = (isProduction && siteKey) ? initializeAppCheck(app, {
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
