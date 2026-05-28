import React, { useEffect, useState } from 'react';

const socialLinks = [
  { label: 'Google', glyph: 'G' },
  { label: 'Facebook', glyph: 'f' },
  { label: 'GitHub', glyph: 'GH' },
  { label: 'LinkedIn', glyph: 'in' }
];

const benefits = [
  { icon: '⏱', title: '2-Hr Dispatch' },
  { icon: '🛠', title: 'Specialized Trades' },
  { icon: '★', title: 'Verified Reviews' },
  { icon: '🛡', title: 'Licensed & Insured' }
];

export default function LoginPage({ initialMode = 'login', onNavigate }) {
  const [activeMode, setActiveMode] = useState(initialMode === 'signup' ? 'signup' : 'login');
  const [identity, setIdentity] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [accountType, setAccountType] = useState('customer');

  useEffect(() => {
    setActiveMode(initialMode === 'signup' ? 'signup' : 'login');
  }, [initialMode]);

  const activateMode = (mode) => {
    setActiveMode(mode);
    onNavigate?.(mode);
  };

  const handleSignInSubmit = (event) => {
    event.preventDefault();

    /* ====== TEMP ROLE ROUTING: client/client -> customer_dashboard, worker/worker -> worker_dashboard, admin/admin -> admin_dashboard.
       Remove this block when backend session-based auth and role resolution are wired in.
    ====== */
    const normalizedIdentity = identity.trim().toLowerCase();
    const normalizedPassword = password.trim().toLowerCase();

    if (normalizedIdentity === 'client' && normalizedPassword === 'client') {
      onNavigate?.('customer_dashboard');
      return;
    }

    if (normalizedIdentity === 'worker' && normalizedPassword === 'worker') {
      onNavigate?.('worker_dashboard');
      return;
    }

    if (normalizedIdentity === 'admin' && normalizedPassword === 'admin') {
      onNavigate?.('admin_dashboard');
      return;
    }
    /* ====== END TEMP ROLE ROUTING ====== */

    console.log('Login submission requested:', { identity });
  };

  const handleSignUpSubmit = (event) => {
    event.preventDefault();

    /* ====== BACKEND INTEGRATION PLACEHOLDER: Insert API endpoint/Auth payload here ======
       - POST the signup payload to the database-backed account endpoint.
       - Include full name, contact details, password hash, and selected role here.
       - Handle verification, duplicate checks, and onboarding routing here.
    ====== */

    console.log('Signup submission requested:', { fullName, phone, email, accountType });
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
            <form className={`auth-form auth-form--signup ${activeMode === 'signup' ? 'is-active' : ''}`} onSubmit={handleSignUpSubmit}>
              <div className="auth-form__heading">
                <h2>Create Account</h2>
                <p>Register with your name, contact info, and role preference.</p>
              </div>

              <div className="auth-socials" aria-label="Social signup options">
                {socialLinks.map((link) => (
                  <a key={link.label} href="#" className="auth-socials__icon" onClick={(event) => event.preventDefault()} aria-label={link.label}>
                    <span>{link.glyph}</span>
                  </a>
                ))}
              </div>

              <span className="auth-form__hint">or use your email for registration</span>
              <input type="text" placeholder="Name" value={fullName} onChange={(event) => setFullName(event.target.value)} autoComplete="name" required />
              <input type="tel" placeholder="Phone" value={phone} onChange={(event) => setPhone(event.target.value)} autoComplete="tel" required />
              <input type="email" placeholder="Email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" required />
              <input type="password" placeholder="Password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="new-password" required />

              <div className="auth-submit-stack" aria-label="Create account actions">
                <div className="auth-submit-stack__row">
                  <button
                    type="button"
                    className={`auth-submit-stack__button ${accountType === 'customer' ? 'is-active' : ''}`}
                    onClick={() => setAccountType('customer')}
                  >
                    Sign Up as Customer
                  </button>
                  <button
                    type="button"
                    className={`auth-submit-stack__button ${accountType === 'provider' ? 'is-active' : ''}`}
                    onClick={() => setAccountType('provider')}
                  >
                    Sign Up as Provider
                  </button>
                </div>

                <button
                  type="submit"
                  className="auth-submit-stack__button auth-submit-stack__button--primary"
                  onClick={() => {
                    /* ====== BACKEND INTEGRATION PLACEHOLDER: Insert API endpoint/Auth payload here ======
                       - Choose accountType, role, and contact details here.
                       - POST to your account-creation endpoint for customer or handyman profile creation.
                       - Return auth/session state and route the user after success.
                    ====== */
                  }}
                >
                  CREATE MY ACCOUNT
                </button>
              </div>

              <p className="auth-form__footer-copy">
                Already have an account? <button type="button" className="auth-form__link-button" onClick={() => activateMode('login')}>Switch to Sign In</button>
              </p>
            </form>

            <form className={`auth-form auth-form--signin ${activeMode === 'login' ? 'is-active' : ''}`} onSubmit={handleSignInSubmit}>
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
              <input type="text" placeholder="Name or Email" value={identity} onChange={(event) => setIdentity(event.target.value)} autoComplete="username" required />
              <input type="password" placeholder="Password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required />

              <a className="auth-form__link" href="#forgot" onClick={(event) => event.preventDefault()}>
                Forgot Your Password?
              </a>

              <div className="auth-signin-actions" aria-label="Sign in actions">
                <button type="submit">SIGN IN</button>
                <button type="button" className="auth-signin-actions__secondary" onClick={() => activateMode('signup')}>
                  NEED AN ACCOUNT? SIGN UP
                </button>
              </div>
            </form>
          </div>
        </section>
      </div>
    </div>
  );
}
