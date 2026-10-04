import { FirebaseError } from 'firebase/app';
import { ArrowRight, ShieldCheck, Stethoscope } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useSession } from '../auth/Session';
import { firebaseConfigError } from '../firebase';

export function LoginPage() {
  const { user, initializing, signIn } = useSession();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? '/patients';

  if (!initializing && user) return <Navigate to={from} replace />;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      await signIn(email.trim(), password);
    } catch (reason) {
      setError(reason instanceof FirebaseError && reason.code === 'auth/invalid-credential'
        ? 'The email or password was not recognized.'
        : 'Sign-in could not be completed. Check your connection and try again.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-aside">
        <div className="login-brand"><span className="brand-symbol"><Stethoscope size={21} /></span><span><strong>DermCare</strong><small>CLINICAL WORKSPACE</small></span></div>
        <div className="login-intro"><p className="eyebrow">SECURE CLINICAL ACCESS</p><h1>Care records,<br />in clear view.</h1><p>Authorized access to patient summaries, prescriptions, and procedure history.</p></div>
        <div className="login-privacy"><ShieldCheck size={17} /><span>Protected by your organization's sign-in policy</span></div>
      </section>
      <section className="login-form-wrap">
        <form className="login-form" onSubmit={submit}>
          <p className="eyebrow">STAFF SIGN IN</p>
          <h2>Welcome back</h2>
          <p className="form-subtitle">Use your clinical account to continue.</p>
          {firebaseConfigError && <p className="form-error" role="alert">{firebaseConfigError}</p>}
          {error && <p className="form-error" role="alert">{error}</p>}
          <label htmlFor="email">Work email</label>
          <input id="email" type="email" autoComplete="username" required value={email} onChange={(event) => setEmail(event.target.value)} />
          <label htmlFor="password">Password</label>
          <input id="password" type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} />
          <button className="primary-button" type="submit" disabled={busy || initializing || Boolean(firebaseConfigError)}>{busy ? 'Signing in...' : 'Sign in'} <ArrowRight size={17} /></button>
        </form>
      </section>
    </main>
  );
}
