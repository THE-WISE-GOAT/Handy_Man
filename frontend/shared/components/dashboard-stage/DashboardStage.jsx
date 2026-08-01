import React from "react";
import "./dashboard-stage.css";

export function FixFastNavbar({
  brandTitle,
  brandEyebrow,
  navItems,
  activePanel,
  onSelectPanel,
  profileSlot,
}) {
  return (
    <header className="fixfast-nav">
      <div className="fixfast-nav__brand">
        <div className="fixfast-nav__logo">K</div>
        <div>
          <div className="fixfast-nav__eyebrow">{brandEyebrow}</div>
          <div className="fixfast-nav__title">{brandTitle}</div>
        </div>
      </div>

      <nav className="fixfast-nav__menu" aria-label="Dashboard navigation">
        {navItems.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`fixfast-nav__link ${activePanel === item.id ? "is-active" : ""}`}
            onClick={() => onSelectPanel(item.id)}
          >
            {item.label}
          </button>
        ))}
      </nav>

      <div className="fixfast-nav__profile">{profileSlot}</div>
    </header>
  );
}

export function FixFastProfile({ label, sublabel, actions = [] }) {
  const [open, setOpen] = React.useState(false);
  const containerRef = React.useRef(null);

  React.useEffect(() => {
    if (!open) return undefined;

    function handlePointerDown(event) {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setOpen(false);
      }
    }

    function handleKeyDown(event) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  return (
    <div className="fixfast-profile" ref={containerRef}>
      <button
        type="button"
        className="fixfast-profile__trigger"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((prev) => !prev)}
      >
        <span className="fixfast-profile__avatar">
          {(label || "U").slice(0, 1).toUpperCase()}
        </span>
      </button>
      {open && (
        <div className="fixfast-profile__menu" role="menu">
          <div className="fixfast-profile__meta">
            <strong>{label}</strong>
            <span className="fixfast-profile__email">{sublabel}</span>
          </div>
          {actions.map((action) => (
            <button
              key={action.label}
              type="button"
              role="menuitem"
              onClick={action.onClick}
            >
              {action.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function TheaterStage({
  title,
  subtitle,
  activeKey,
  isTransitioning = false,
  children,
}) {
  return (
    <section
      className={`fixfast-stage ${isTransitioning ? "stage-transitioning" : ""}`}
      aria-label={title}
    >
      <div className="fixfast-stage__header">
        <div>
          <p className="fixfast-stage__eyebrow">{subtitle}</p>
          <h1>{title}</h1>
        </div>
        <span className="fixfast-stage__dot" aria-hidden="true" />
      </div>
      <div key={activeKey} className="fixfast-stage__content">
        {children}
      </div>
    </section>
  );
}

export function PreviewDeck({
  items,
  activePanel,
  onSelectPanel,
  transitioningTo = null,
}) {
  const deckItems = items.filter((item) => item.id !== activePanel);

  return (
    <section className="fixfast-deck" aria-label="Floating window deck">
      {deckItems.map((item) => {
        const isEntering = transitioningTo === item.id;
        const windowClass = [
          "fixfast-window",
          item.windowClass || "",
          isEntering ? "is-lifting" : "",
        ]
          .filter(Boolean)
          .join(" ");

        return (
          <button
            key={item.id}
            type="button"
            className={windowClass}
            onClick={() => onSelectPanel(item.id)}
          >
            <div className="fixfast-window__topbar">
              <span className="fixfast-window__traffic" aria-hidden="true">
                <i />
                <i />
                <i />
              </span>
              <span className="fixfast-window__title">{item.label}</span>
              <span className="fixfast-window__icon" aria-hidden="true">
                {item.icon}
              </span>
            </div>
            <div className="fixfast-window__body">
              {item.preview ? (
                item.preview
              ) : (
                <div className="fixfast-window__fallback">
                  <strong>{item.label}</strong>
                  <small>{item.meta}</small>
                </div>
              )}
            </div>
          </button>
        );
      })}
    </section>
  );
}
