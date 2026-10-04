import { getApp, getApps, initializeApp } from 'firebase/app';
import { getAuth, type Auth } from 'firebase/auth';
import { validateFirebaseConfig } from './firebaseConfig';

const isTest = import.meta.env.MODE === 'test';

const validation = validateFirebaseConfig({
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
});

export const firebaseConfigError = validation.config
  ? ''
  : `Firebase sign-in is unavailable. Configure the missing settings: ${validation.missing
    .map((field) => `VITE_FIREBASE_${field.replace(/[A-Z]/g, (letter) => `_${letter}`).toUpperCase()}`)
    .join(', ')}.`;

export const auth: Auth | null = isTest || !validation.config
  ? null
  : getAuth(getApps().length ? getApp() : initializeApp(validation.config));
