import React, { useState } from "react";

const MAP_PREVIEW_URL = import.meta.env.VITE_MAP_STANDALONE_URL || "";

const serviceCards = [
  {
    tag: "Mechanical Core",
    title: "Mechanical & Plumbing",
    description:
      "Leaking taps, pipeline repair, structural maintenance and practical household fixes with disciplined field execution.",
    meta: "Built for repeatable repair work",
  },
  {
    tag: "Safety Scan",
    title: "Electrical & Infrastructure Audits",
    description:
      "Safety inspection, circuit wiring, EV charging setups and preventative checks for homes under active use.",
    meta: "Inspection-first service flow",
  },
  {
    tag: "Connected Living",
    title: "Smart Home & IoT Deployment",
    description:
      "CCTV installation, home networking, router configuration and low-friction smart-device deployment.",
    meta: "Network-ready service packaging",
  },
  {
    tag: "Emergency Dispatch",
    title: "Urgent Care Dispatch",
    description:
      "Fast-response repair routing with a two-hour emergency repair window for critical home issues.",
    meta: "Priority allocation queue",
  },
];

export default function HomePage({ onNavigate }) {
  const [serviceQuery, setServiceQuery] = useState("");

  const handleSearchSubmit = (event) => {
    event.preventDefault();

    /* ====== BACKEND INTEGRATION PLACEHOLDER: Insert API endpoint/Search payload here ======
       - POST or GET the service query to your matching endpoint.
       - Attach location, urgency, category filters, and session metadata here.
       - Populate a results view or transition into a search results page.
    ====== */

    console.log("Dispatch search requested:", { serviceQuery });
  };

  const navigateToAuth = () => {
    onNavigate?.("login");
  };

  return (
    <div className="ind-page">
      <header className="ind-topbar">
        <div className="ind-container ind-topbar__inner">
          <a
            className="ind-brand"
            href="#home"
            onClick={(event) => event.preventDefault()}
          >
            <span className="ind-brand__mark">HM</span>
            <span className="ind-brand__copy">
              <span className="ind-brand__eyebrow">On-Demand Local Works</span>
              <span className="ind-brand__name">Handy Man Dispatch</span>
            </span>
          </a>

          <div className="ind-topbar__actions">
            <a className="ind-nav-link" href="#services">
              Services
            </a>
            <a className="ind-nav-link" href="#trust">
              Trust
            </a>
            {MAP_PREVIEW_URL ? (
              <a
                className="ind-nav-link"
                href={MAP_PREVIEW_URL}
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Open live worker map sandbox in a new tab"
              >
                🗺️ Live Worker Map
              </a>
            ) : null}
            <button
              className="ind-cta-button"
              type="button"
              onClick={navigateToAuth}
            >
              Login / Signup
            </button>
          </div>
        </div>
      </header>

      <section className="ind-hero">
        <div className="ind-container hero-grid">
          <div className="hero-copy">
            <span className="ind-kicker">
              <span className="ind-kicker__dot" />
              Engineered dispatch for home services
            </span>

            <h1 className="ind-hero__title">
              Engineered Home <span>Maintenance</span> On Demand
            </h1>

            <p className="ind-hero__lede">
              A structured local services platform for repairs, installations,
              and urgent field support. Search by need, route to the right
              trade, and move from request to resolution without friction.
            </p>

            <div className="hero-stats" aria-label="Platform highlights">
              <div className="hero-stat">
                <strong className="hero-stat__value">24/7</strong>
                <span className="hero-stat__label">Dispatch availability</span>
              </div>
              <div className="hero-stat">
                <strong className="hero-stat__value">Field</strong>
                <span className="hero-stat__label">
                  Verified technician pool
                </span>
              </div>
              <div className="hero-stat">
                <strong className="hero-stat__value">Grid</strong>
                <span className="hero-stat__label">
                  Structured service routing
                </span>
              </div>
            </div>

            {MAP_PREVIEW_URL ? (
              <div style={{ marginTop: "1.25rem" }}>
                <a
                  className="ind-primary-button"
                  href={MAP_PREVIEW_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label="Open live worker map sandbox in a new tab"
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    textDecoration: "none",
                  }}
                >
                  🗺️ Live Worker Map (PostGIS Sandbox)
                </a>
              </div>
            ) : null}
          </div>

          <aside className="hero-panel">
            <h2 className="ind-panel-title">Service Search Console</h2>
            <form className="hero-search" onSubmit={handleSearchSubmit}>
              <label className="hero-search__field" htmlFor="service-search">
                <span className="hero-search__label">
                  What service do you require?
                </span>
                <input
                  id="service-search"
                  className="hero-search__input"
                  type="text"
                  value={serviceQuery}
                  onChange={(event) => setServiceQuery(event.target.value)}
                  placeholder="e.g., Electrician, Plumbing, Smart Home..."
                />
              </label>

              <div className="hero-search__actions">
                <button className="ind-primary-button" type="submit">
                  Find Technicians
                </button>
                <span className="hero-search__hint">
                  Fast matching for household repair and install requests.
                </span>
              </div>
            </form>

            <div className="ind-mini-panel">
              <h3 className="ind-panel-title">Operational Notes</h3>
              <div className="ind-mini-grid">
                <div className="ind-mini-chip">
                  <span>Verified field network</span>
                  <span className="ind-mini-chip__tag">Live</span>
                </div>
                <div className="ind-mini-chip">
                  <span>Transparent estimate flow</span>
                  <span className="ind-mini-chip__tag">Quote</span>
                </div>
                <div className="ind-mini-chip">
                  <span>Urgent repair routing</span>
                  <span className="ind-mini-chip__tag">Fast</span>
                </div>
                <div className="ind-mini-chip">
                  <span>Warranty-backed jobs</span>
                  <span className="ind-mini-chip__tag">Safe</span>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </section>

      <section className="ind-grid-section" id="services">
        <div className="ind-container">
          <div className="ind-grid-header">
            <h2>Core Verticals & Features</h2>
            <p>
              A four-box service matrix designed for quick scanning, clear job
              scope definition, and efficient response routing.
            </p>
          </div>

          <div className="hero-card-grid">
            {serviceCards.map((card) => (
              <article className="ind-card" key={card.title}>
                <span className="ind-card__tag">{card.tag}</span>
                <h3>{card.title}</h3>
                <p>{card.description}</p>
                <div className="ind-card__meta">{card.meta}</div>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="ind-grid-section" id="trust">
        <div className="ind-container">
          <div className="ind-trust-banner">
            <div className="ind-trust-item">
              <strong>Verified Nepalese Technicians</strong>
              <span>
                Local, accountable, and trade-focused dispatch network.
              </span>
            </div>
            <div className="ind-trust-item">
              <strong>30-Day Work Warranty</strong>
              <span>
                Clear post-job coverage for eligible service categories.
              </span>
            </div>
            <div className="ind-trust-item">
              <strong>Upfront Transparent Pricing</strong>
              <span>
                Cost framing before work begins, no hidden structural surprises.
              </span>
            </div>
          </div>
        </div>
      </section>

      <footer className="ind-footer">
        <div className="ind-container ind-footer__bar">
          <span className="ind-footer__meta">Handy Man Dispatch</span>
          <span>
            Industrial technical layout built for local home service operations.
          </span>
        </div>
      </footer>
    </div>
  );
}
