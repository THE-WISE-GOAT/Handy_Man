import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const socialLinks = [
  { label: 'Google', glyph: 'G' },
  { label: 'Facebook', glyph: 'f' },
  { label: 'GitHub', glyph: 'GH' },
  { label: 'LinkedIn', glyph: 'in' }
];

const benefits = [
  { icon: '⏱', title: 'Fast Dispatch' },
  { icon: '🛠', title: 'Specialized Trades' },
  { icon: '★', title: 'Verified Reviews' },
  { icon: '🛡', title: 'Licensed & Insured' } 
];

export default function LoginPage({ initialMode = 'login', onNavigate }) {
  const { login } = useAuth();
  const [activeMode, setActiveMode] = useState(initialMode === 'signup' ? 'signup' : 'login');
  const [identity, setIdentity] = useState('');
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [statusMessage, setStatusMessage] = useState('');
  const [statusType, setStatusType] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    setActiveMode(initialMode === 'signup' ? 'signup' : 'login');
  }, [initialMode]);

  const activateMode = (mode) => {
    setActiveMode(mode);
    onNavigate?.(mode);
  };

  const handleSignInSubmit = async (event) => {
    event.preventDefault();

    const trimmedIdentity = identity.trim();
    const trimmedPassword = password.trim();

    if (!trimmedIdentity || !trimmedPassword) {
      setStatusType('error');
      setStatusMessage('Please enter username and password.');
      return;
    }

    setIsSubmitting(true);
    setStatusType('');
    setStatusMessage('');

    try {
      const formBody = new URLSearchParams();
      formBody.append('username', trimmedIdentity);
      formBody.append('password', trimmedPassword);

      const response = await fetch(`${API_BASE_URL}/login/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: formBody.toString()
      });

      const data = await response.json();

      if (!response.ok) {
        setStatusType('error');
        setStatusMessage(`Error: ${data.detail || 'Could not log in.'}`);
        return;
      }

      await login({
        token: data.access_token,
        type: data.token_type,
        usernameValue: trimmedIdentity
      });
      setStatusType('success');
      setStatusMessage('Login successful. Loading your profile...');
      onNavigate?.('customer_dashboard', { replace: true });
    } catch (error) {
      setStatusType('error');
      setStatusMessage(error?.message || 'Error connecting to backend server. Make sure FastAPI is running and CORS is enabled.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSignUpSubmit = async (event) => {
    event.preventDefault();

    const trimmedUsername = username.trim();
    const trimmedEmail = email.trim();
    const trimmedPassword = password.trim();

    if (!trimmedUsername || !trimmedEmail || !trimmedPassword) {
      setStatusType('error');
      setStatusMessage('Please fill in all fields.');
      return;
    }

    setIsSubmitting(true);
    setStatusType('');
    setStatusMessage('');

    try {
      const response = await fetch(`${API_BASE_URL}/users/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          username: trimmedUsername,
          email: trimmedEmail,
          password: trimmedPassword
        })
      });

      const data = await response.json();

      if (!response.ok) {
        setStatusType('error');
        setStatusMessage(`Error: ${data.detail || 'Could not register user.'}`);
        return;
      }

      setStatusType('success');
      setStatusMessage(`Account Created Successfully! Welcome aboard, ${data.username}. Your account ID is #${data.id}.`);
      setIdentity(data.username);
      setPassword('');
      setActiveMode('login');
      onNavigate?.('login', { replace: true });
    } catch (error) {
      setStatusType('error');
      setStatusMessage('Error connecting to backend server. Make sure FastAPI is running and CORS is enabled.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="ind-page ind-auth-page">
      <div className={`auth-shell ${activeMode === 'signup' ? 'is-signup' : ''}`}>
        <aside className="auth-shell__intro">
          <div className="auth-shell__brand">
            <span className="auth-shell__mark">HM</span>
            <div>
              <p className="auth-shell__eyebrow">Handy Man Dispatch</p>
              <h1>Instant access to verified local experts.</h1>
            </div>
          </div>

          <p className="auth-shell__lead">
            Book pre-vetted professionals for repairs, maintenance, and tech installs.
          </p>

          <ul className="auth-shell__benefits" aria-label="Platform benefits">
            {benefits.map((benefit) => (
              <li key={benefit.title} className="auth-shell__benefit">
                <span className="auth-shell__benefit-icon" aria-hidden="true">{benefit.icon}</span>
                <span className="auth-shell__benefit-title">{benefit.title}</span>
              </li>
            ))}
          </ul>

          <div className="auth-shell__cta-wrap">
            <button type="button" className="auth-shell__cta" onClick={() => activateMode('signup')}>
              GET STARTED
            </button>
          </div>
        </aside>

        <section className="auth-shell__panel">
          <div className="auth-shell__tabs" role="tablist" aria-label="Authentication mode">
            <button type="button" className={`auth-shell__tab ${activeMode === 'login' ? 'is-active' : ''}`} onClick={() => activateMode('login')}>
              Sign In
            </button>
            <button type="button" className={`auth-shell__tab ${activeMode === 'signup' ? 'is-active' : ''}`} onClick={() => activateMode('signup')}>
              Create Account
            </button>
          </div>

          <div className="auth-stage">
            <form
              name="signup-form"
              className={`auth-form auth-form--signup ${activeMode === 'signup' ? 'is-active' : ''}`}
              onSubmit={handleSignUpSubmit}
            >
              <div className="auth-form__heading">
                <h2>Create Account</h2>
                <p>Register with username, email, and password.</p>
              </div>

              <div className="auth-socials" aria-label="Social signup options">
                {socialLinks.map((link) => (
                  <a key={link.label} href="#" className="auth-socials__icon" onClick={(event) => event.preventDefault()} aria-label={link.label}>
                    <span>{link.glyph}</span>
                  </a>
                ))}
              </div>

              <span className="auth-form__hint">or use your email for registration</span>
              <input type="text" name="username" placeholder="Username" value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="off" required />
              <input type="email" name="email" placeholder="Email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="off" required />
              <input type="password" name="password" placeholder="Password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="new-password" required />

              <div className="auth-submit-stack" aria-label="Create account actions">
                <button
                  type="submit"
                  className="auth-submit-stack__button auth-submit-stack__button--primary"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? 'CREATING...' : 'CREATE MY ACCOUNT'}
                </button>
              </div>

              <p className="auth-form__footer-copy">
                Already have an account? <button type="button" className="auth-form__link-button" onClick={() => activateMode('login')}>Switch to Sign In</button>
              </p>
            </form>

            <form
              name="signin-form"
              className={`auth-form auth-form--signin ${activeMode === 'login' ? 'is-active' : ''}`}
              onSubmit={handleSignInSubmit}
            >
              <div className="auth-form__heading">
                <h2>Sign In</h2>
                <p>Access the dashboard with your email or phone number and password.</p>
              </div>

              <div className="auth-socials" aria-label="Social sign in options">
                {socialLinks.map((link) => (
                  <a key={link.label} href="#" className="auth-socials__icon" onClick={(event) => event.preventDefault()} aria-label={link.label}>
                    <span>{link.glyph}</span>
                  </a>
                ))}
              </div>

              <span className="auth-form__hint">or use your email password</span>
              <input type="text" name="identity" placeholder="Username" value={identity} onChange={(event) => setIdentity(event.target.value)} autoComplete="username" required />
              <input type="password" name="password" placeholder="Password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required />

              <a className="auth-form__link" href="#forgot" onClick={(event) => event.preventDefault()}>
                Forgot Your Password?
              </a>

              <div className="auth-signin-actions" aria-label="Sign in actions">
                <button type="submit" disabled={isSubmitting}>{isSubmitting ? 'SIGNING IN...' : 'SIGN IN'}</button>
                <button type="button" className="auth-signin-actions__secondary" onClick={() => activateMode('signup')}>
                  NEED AN ACCOUNT? SIGN UP
                </button>
              </div>
            </form>

            <div className="auth-status-slot">
              {statusMessage ? (
                <div
                  key={`${activeMode}-${statusType || 'neutral'}`}
                  role="status"
                  aria-live="polite"
                  style={{
                    marginTop: '1rem',
                    padding: '12px 14px',
                    borderRadius: '8px',
                    backgroundColor: statusType === 'success' ? '#eafaf1' : '#eee',
                    color: statusType === 'success' ? '#27ae60' : '#333',
                    borderLeft: statusType === 'success' ? 'none' : '5px solid #dc3545',
                    textAlign: statusType === 'success' ? 'center' : 'left',
                    lineHeight: '1.5',
                    gridColumn: '1 / -1'
                  }}
                >
                  {statusMessage}
                </div>
              ) : null}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
