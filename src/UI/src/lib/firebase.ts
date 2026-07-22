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

// Enable debug token in development mode for local testing
if (import.meta.env.DEV) {
  (self as any).FIREBASE_APPCHECK_DEBUG_TOKEN = import.meta.env.VITE_APP_CHECK_DEBUG_TOKEN || true;
}

const siteKey = import.meta.env.VITE_APP_CHECK_SITE_KEY || '6Ldf_dummy_key_for_dev_mode';

// Initialize App Check
export const appCheck = siteKey ? initializeAppCheck(app, {
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

export const getAuthToken = async (): Promise<string> => {
  if (!auth.currentUser) return "";
  try {
    return await auth.currentUser.getIdToken();
  } catch (err) {
    console.error("Failed to get ID token:", err);
    return "";
  }
};
