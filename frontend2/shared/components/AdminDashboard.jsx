import React from 'react';

const metricCards = [
  {
    label: 'Earnings Monthly',
    value: '$40,000',
    icon: '💰',
    accent: 'is-blue'
  },
  {
    label: 'Earnings Annual',
    value: '$215,000',
    icon: '📈',
    accent: 'is-green'
  },
  {
    label: 'Tasks / Completion',
    value: '50%',
    icon: '✅',
    accent: 'is-cyan',
    progress: 50
  },
  {
    label: 'Pending Requests',
    value: '18',
    icon: '🕒',
    accent: 'is-yellow'
  }
];

const projectRows = [
  { name: 'Server Migration', value: 20, tone: 'is-danger' },
  { name: 'Sales Tracking', value: 40, tone: 'is-warning' },
  { name: 'Customer Database', value: 60, tone: 'is-success' },
  { name: 'Payout Details', value: 80, tone: 'is-info' },
  { name: 'Account Setup', value: 100, tone: 'is-complete' }
];

export default function AdminDashboard() {
  return (
    <div className="theme-dashboard">
      <aside className="dash-sidebar">
        <div className="dash-brand">
          <div className="dash-brand__mark">D</div>
          <div className="dash-brand__copy">
            <div className="dash-brand__name">Handy Man Admin</div>
            <div className="dash-brand__sub">Analytics Control Panel</div>
          </div>
        </div>

        <nav className="dash-nav" aria-label="Sidebar navigation">
          <a className="dash-nav__item is-active" href="#dashboard">
            <span className="dash-nav__icon">▣</span>
            <span>Dashboard</span>
          </a>
          <a className="dash-nav__item" href="#components">
            <span className="dash-nav__icon">◫</span>
            <span>Components</span>
            <span className="dash-nav__chev">▾</span>
          </a>
          <a className="dash-nav__item" href="#utilities">
            <span className="dash-nav__icon">◌</span>
            <span>Utilities</span>
            <span className="dash-nav__chev">▾</span>
          </a>
          <a className="dash-nav__item" href="#pages">
            <span className="dash-nav__icon">▤</span>
            <span>Pages</span>
            <span className="dash-nav__chev">▾</span>
          </a>
          <a className="dash-nav__item" href="#charts">
            <span className="dash-nav__icon">◔</span>
            <span>Charts</span>
          </a>
          <a className="dash-nav__item" href="#tables">
            <span className="dash-nav__icon">▥</span>
            <span>Tables</span>
          </a>
        </nav>
      </aside>

      <div className="dash-main">
        <header className="dash-topbar">
          <label className="dash-search" htmlFor="dash-search-input">
            <span className="dash-search__icon">⌕</span>
            <input
              id="dash-search-input"
              className="dash-search__input"
              type="search"
              placeholder="Search for..."
            />
          </label>

          <div className="dash-topbar__actions">
            <button className="dash-action" type="button" aria-label="Alerts">
              <span className="dash-action__icon">🔔</span>
              <span className="dash-badge">3</span>
            </button>
            <button className="dash-action" type="button" aria-label="Messages">
              <span className="dash-action__icon">✉</span>
              <span className="dash-badge">7</span>
            </button>
            <span className="dash-divider" aria-hidden="true" />
            <div className="dash-user">
              <div className="dash-user__text">
                <span className="dash-user__name">Douglas McGee</span>
                <span className="dash-user__role">Administrator</span>
              </div>
              <div className="dash-user__avatar">DM</div>
            </div>
          </div>
        </header>

        <main className="dash-content">
          <section className="dash-metrics">
            {metricCards.map((card) => (
              <article key={card.label} className={`dash-card dash-card--metric ${card.accent}`}>
                <div className="dash-card__body">
                  <div>
                    <p className="dash-card__eyebrow">{card.label}</p>
                    <h2 className="dash-card__value">{card.value}</h2>
                    {card.progress ? (
                      <div className="dash-progress">
                        <div className="dash-progress__bar">
                          <span className={`dash-progress__fill is-w${card.progress}`} />
                        </div>
                        <span className="dash-progress__label">{card.progress}%</span>
                      </div>
                    ) : null}
                  </div>
                  <div className="dash-card__symbol" aria-hidden="true">
                    {card.icon}
                  </div>
                </div>
              </article>
            ))}
          </section>

          <section className="dash-charts-grid">
            <article className="dash-card dash-card--chart">
              <div className="dash-card__header">
                <h3>Earnings Overview</h3>
                <button className="dash-menu" type="button" aria-label="Overview menu">⋯</button>
              </div>
              <div className="dash-chart-area" aria-label="Earnings overview chart">
                {/* ====== BACKEND INTEGRATION: Fetch/Map dynamic dashboard metrics here ====== */}
                <svg viewBox="0 0 860 320" role="img" aria-label="Area chart placeholder" className="dash-chart-svg">
                  <defs>
                    <linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#4E73DF" stopOpacity="0.34" />
                      <stop offset="100%" stopColor="#4E73DF" stopOpacity="0.02" />
                    </linearGradient>
                  </defs>
                  <g className="dash-chart-grid">
                    <line x1="0" y1="40" x2="860" y2="40" />
                    <line x1="0" y1="100" x2="860" y2="100" />
                    <line x1="0" y1="160" x2="860" y2="160" />
                    <line x1="0" y1="220" x2="860" y2="220" />
                    <line x1="0" y1="280" x2="860" y2="280" />
                  </g>
                  <path
                    d="M0 250 C80 220, 120 130, 200 145 C280 160, 320 85, 390 110 C470 140, 510 65, 600 92 C690 118, 725 48, 790 70 C830 85, 845 92, 860 88 L860 320 L0 320 Z"
                    fill="url(#areaFill)"
                  />
                  <path
                    d="M0 250 C80 220, 120 130, 200 145 C280 160, 320 85, 390 110 C470 140, 510 65, 600 92 C690 118, 725 48, 790 70 C830 85, 845 92, 860 88"
                    fill="none"
                    stroke="#4E73DF"
                    strokeWidth="6"
                    strokeLinecap="round"
                  />
                </svg>
              </div>
            </article>

            <article className="dash-card dash-card--donut">
              <div className="dash-card__header">
                <h3>Revenue Sources</h3>
              </div>
              <div className="dash-donut">
                {/* ====== BACKEND INTEGRATION: Fetch/Map dynamic dashboard metrics here ====== */}
                <svg viewBox="0 0 320 240" role="img" aria-label="Revenue donut chart placeholder" className="dash-donut__svg">
                  <circle cx="160" cy="105" r="68" fill="none" stroke="#f1f3f9" strokeWidth="26" />
                  <circle cx="160" cy="105" r="68" fill="none" stroke="#4E73DF" strokeWidth="26" strokeDasharray="160 268" transform="rotate(-90 160 105)" />
                  <circle cx="160" cy="105" r="68" fill="none" stroke="#1cc88a" strokeWidth="26" strokeDasharray="90 338" strokeDashoffset="-160" transform="rotate(-90 160 105)" />
                  <circle cx="160" cy="105" r="68" fill="none" stroke="#f6c23e" strokeWidth="26" strokeDasharray="55 373" strokeDashoffset="-250" transform="rotate(-90 160 105)" />
                  <circle cx="160" cy="105" r="34" fill="#FFFFFF" />
                </svg>
                <div className="dash-legend">
                  <span><i className="is-blue" /> Direct</span>
                  <span><i className="is-green" /> Social</span>
                  <span><i className="is-yellow" /> Referral</span>
                </div>
              </div>
            </article>
          </section>

          <section className="dash-secondary-grid">
            <article className="dash-card dash-card--projects">
              <div className="dash-card__header">
                <h3>Projects Tracker</h3>
              </div>
              <div className="dash-projects">
                {projectRows.map((project) => (
                  <div key={project.name} className="dash-project">
                    <div className="dash-project__meta">
                      <span>{project.name}</span>
                      <span>{project.value === 100 ? 'Complete' : `${project.value}%`}</span>
                    </div>
                    <div className="dash-progress dash-progress--stacked">
                      <div className="dash-progress__bar">
                        <span className={`dash-progress__fill ${project.tone} is-w${project.value}`} />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </article>

            <div className="dash-stack">
              <article className="dash-card dash-card--illustration">
                <div className="dash-card__header">
                  <h3>Illustrations</h3>
                </div>
                <div className="dash-illustration">
                  <svg viewBox="0 0 240 140" role="img" aria-label="Illustration placeholder" className="dash-illustration__svg">
                    <rect x="22" y="28" width="196" height="86" rx="14" fill="#f8f9fa" stroke="#dfe3eb" />
                    <path d="M48 88 L92 56 L128 82 L166 48 L196 72" fill="none" stroke="#4E73DF" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />
                    <circle cx="92" cy="56" r="6" fill="#1cc88a" />
                    <circle cx="128" cy="82" r="6" fill="#f6c23e" />
                    <circle cx="166" cy="48" r="6" fill="#e74a3b" />
                  </svg>
                  <p>A clean vector placeholder for supporting artwork, onboarding visuals, or future data storytelling content.</p>
                </div>
              </article>

              <article className="dash-card dash-card--approach">
                <div className="dash-card__header">
                  <h3>Development Approach</h3>
                </div>
                <div className="dash-approach">
                  <p>
                    Structured around modular cards, fixed content regions, and responsive utility spacing so backend-fed metrics can slot into the existing dashboard shell without layout churn.
                  </p>
                  <p>
                    The visual language keeps strong borders, generous white surfaces, and calm slate backgrounds to stay aligned with the classic modern admin dashboard pattern.
                  </p>
                </div>
              </article>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}
