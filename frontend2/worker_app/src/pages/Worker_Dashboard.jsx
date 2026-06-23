import { useMemo, useState } from "react";
import { useAuth } from "@shared/context/AuthContext";
import {
  FixFastNavbar,
  FixFastProfile,
  PreviewDeck,
  TheaterStage,
} from "@shared/components/dashboard-stage/DashboardStage";
import "../worker-dashboard.css";

const WORKER_PROFILE = {
  trade: "Plumbing & Emergency Repairs",
  verificationLabel: "Verified Worker Console",
  currentShift: "On-call • Kathmandu Radius",
  switchHint: "Cross-app toggle ready",
};

const ASSIGNED_JOBS = [
  {
    id: "ws-1",
    title: "Emergency Pipe Isolation",
    customer: "Anita Shrestha",
    status: "Active",
    priority: "Critical",
    eta: "Start within 20 min",
    notes: "Kitchen line leak with rising floor water.",
  },
  {
    id: "ws-2",
    title: "Water Heater Valve Replacement",
    customer: "Suman KC",
    status: "Scheduled",
    priority: "Medium",
    eta: "Today • 10:00 AM",
    notes: "Carry replacement valve and pressure tape.",
  },
  {
    id: "ws-3",
    title: "Drainage Re-route Review",
    customer: "Mina Rai",
    status: "Unresolved",
    priority: "Follow-up",
    eta: "Needs customer callback",
    notes: "Estimate pending after inspection photos.",
  },
];

const JOBS_AROUND = [
  {
    id: "ja-1",
    title: "Fuse Box Inspection",
    client: "Prakash Lama",
    distance: "0.9 km",
    payout: "रू 1,800",
    urgency: "High",
    lat: "27.7191",
    lng: "85.3285",
  },
  {
    id: "ja-2",
    title: "Solar Inverter Reset",
    client: "Rita Karki",
    distance: "1.6 km",
    payout: "रू 2,500",
    urgency: "Medium",
    lat: "27.7138",
    lng: "85.3224",
  },
  {
    id: "ja-3",
    title: "Ceiling Leak Diagnosis",
    client: "Bikash Thapa",
    distance: "2.1 km",
    payout: "रू 2,200",
    urgency: "Critical",
    lat: "27.7115",
    lng: "85.3341",
  },
  {
    id: "ja-4",
    title: "Washing Machine Drain Repair",
    client: "Puja Maharjan",
    distance: "3.4 km",
    payout: "रू 1,400",
    urgency: "Normal",
    lat: "27.7059",
    lng: "85.3177",
  },
];

const MY_BIDS = [
  {
    id: "bid-1",
    job: "Ceiling Leak Diagnosis",
    quote: "रू 2,300",
    status: "Under Review",
    timeline: "Submitted 12 min ago",
  },
  {
    id: "bid-2",
    job: "Solar Inverter Reset",
    quote: "रू 2,500",
    status: "Shortlisted",
    timeline: "Submitted today, 8:40 AM",
  },
  {
    id: "bid-3",
    job: "Smart Lock Rewire",
    quote: "रू 1,950",
    status: "Rejected",
    timeline: "Closed yesterday",
  },
];

const CALENDAR_ITEMS = [
  {
    day: "Mon",
    date: "24",
    title: "Pipe Isolation",
    time: "08:30 - 10:00",
    detail: "Anita Shrestha • Urgent onsite",
  },
  {
    day: "Tue",
    date: "25",
    title: "Valve Replacement",
    time: "10:00 - 11:30",
    detail: "Suman KC • Confirmed booking",
  },
  {
    day: "Wed",
    date: "26",
    title: "Drain Review",
    time: "02:00 - 03:15",
    detail: "Mina Rai • Estimate follow-up",
  },
  {
    day: "Thu",
    date: "27",
    title: "Open Buffer",
    time: "04:00 - 06:00",
    detail: "Reserved for nearby dispatch pickups",
  },
];

const STATS = {
  completedJobs: 42,
  rating: "4.9 / 5.0",
  completionRate: "96%",
  repeatClients: 18,
  reviews: [
    {
      id: "rv-1",
      author: "A. Shrestha",
      score: "★★★★★",
      text: "Fast arrival, clear explanation, and the leak was contained cleanly.",
    },
    {
      id: "rv-2",
      author: "S. KC",
      score: "★★★★☆",
      text: "Very professional and punctual. Shared preventive maintenance tips too.",
    },
  ],
};

const PANEL_META = {
  workspace: {
    icon: "🧰",
    title: "Workspace",
    subtitle: "Active and unresolved assigned jobs",
    meta: "Worker queue",
  },
  jobsAround: {
    icon: "📍",
    title: "Jobs Around",
    subtitle: "Map + nearby opportunity board",
    meta: "Local dispatch",
  },
  myBids: {
    icon: "💼",
    title: "My Bids",
    subtitle: "Submitted quote tracker",
    meta: "Bid status",
  },
  calendar: {
    icon: "🗓",
    title: "Calendar",
    subtitle: "Job dates and allocated time blocks",
    meta: "Schedule grid",
  },
  stats: {
    icon: "📊",
    title: "Stats",
    subtitle: "History, ratings, and reviews",
    meta: "Performance",
  },
};

function WorkspacePanel() {
  return (
    <div className="fixfast-grid fixfast-grid--two">
      <div className="fixfast-panel">
        <div className="fixfast-panel__topline">
          <span>Assigned jobs</span>
          <span>{ASSIGNED_JOBS.length} open items</span>
        </div>
        <div className="fixfast-list">
          {ASSIGNED_JOBS.map((job) => (
            <article key={job.id} className="fixfast-card">
              <div className="fixfast-panel__topline">
                <span>{job.title}</span>
                <span>{job.status}</span>
              </div>
              <p className="fixfast-muted">Customer: {job.customer}</p>
              <div className="fixfast-chip-row">
                <span className="fixfast-chip is-active">{job.priority}</span>
                <span className="fixfast-chip">{job.eta}</span>
              </div>
              <p className="fixfast-muted">{job.notes}</p>
            </article>
          ))}
        </div>
      </div>

      <div className="fixfast-panel">
        <div className="fixfast-panel__topline">
          <span>Workspace notes</span>
          <span>Terminal board</span>
        </div>
        <div className="worker-metric-stack">
          <div className="worker-metric-card">
            <strong>Current shift</strong>
            <span>{WORKER_PROFILE.currentShift}</span>
          </div>
          <div className="worker-metric-card">
            <strong>Pending callbacks</strong>
            <span>2 customers awaiting estimate confirmation</span>
          </div>
          <div className="worker-metric-card">
            <strong>Toolkit note</strong>
            <span>
              Carry pressure valve kit, insulated tester, and seal tape.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function JobsAroundPanel() {
  return (
    <div className="worker-map-layout">
      <div className="fixfast-panel worker-map-stage">
        <div className="fixfast-panel__topline">
          <span>Interactive map placeholder</span>
          <span>Plugin slot ready</span>
        </div>
        <div className="worker-map-surface">
          <div className="worker-map-grid" aria-hidden="true" />
          {JOBS_AROUND.map((job, index) => (
            <button
              key={job.id}
              type="button"
              className={`worker-map-flag worker-map-flag--${(index % 4) + 1}`}
            >
              <span>⚑</span>
              <small>{job.title}</small>
            </button>
          ))}
          <div className="worker-map-overlay">
            <strong>Map integration placeholder</strong>
            <p className="fixfast-muted">
              Keep this panel reserved for Leaflet/Mapbox later. Current flags
              show where available jobs will appear.
            </p>
          </div>
        </div>
      </div>

      <div className="fixfast-panel">
        <div className="fixfast-panel__topline">
          <span>Nearby jobs list</span>
          <span>{JOBS_AROUND.length} available</span>
        </div>
        <div className="fixfast-list">
          {JOBS_AROUND.map((job) => (
            <article key={job.id} className="fixfast-card">
              <div className="fixfast-panel__topline">
                <span>{job.title}</span>
                <span>{job.distance}</span>
              </div>
              <p className="fixfast-muted">Client: {job.client}</p>
              <div className="fixfast-stat-row fixfast-muted">
                <span>{job.payout}</span>
                <span>{job.urgency}</span>
              </div>
              <p className="fixfast-muted">
                Coordinates: {job.lat}, {job.lng}
              </p>
            </article>
          ))}
        </div>
      </div>
    </div>
  );
}

function BidsPanel() {
  return (
    <div className="fixfast-panel">
      <div className="fixfast-panel__topline">
        <span>Bid tracker</span>
        <span>{MY_BIDS.length} submissions</span>
      </div>
      <div className="fixfast-list">
        {MY_BIDS.map((bid) => (
          <article key={bid.id} className="fixfast-card worker-bid-card">
            <div className="fixfast-panel__topline">
              <span>{bid.job}</span>
              <span>{bid.quote}</span>
            </div>
            <div className="worker-bid-status-row">
              <span
                className={`worker-status-pill worker-status-pill--${bid.status.toLowerCase().replace(/\s+/g, "-")}`}
              >
                {bid.status}
              </span>
              <span className="fixfast-muted">{bid.timeline}</span>
            </div>
            <div className="worker-progress-track" aria-hidden="true">
              <span
                className="worker-progress-track__fill"
                style={{
                  width:
                    bid.status === "Rejected"
                      ? "100%"
                      : bid.status === "Shortlisted"
                        ? "72%"
                        : "46%",
                }}
              />
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function CalendarPanel() {
  return (
    <div className="fixfast-grid fixfast-grid--two">
      <div className="fixfast-panel">
        <div className="fixfast-panel__topline">
          <span>Weekly schedule board</span>
          <span>Allocated time slots</span>
        </div>
        <div className="worker-calendar-grid">
          {CALENDAR_ITEMS.map((item) => (
            <article
              key={`${item.day}-${item.date}`}
              className="worker-calendar-tile"
            >
              <div className="worker-calendar-tile__date">
                <span>{item.day}</span>
                <strong>{item.date}</strong>
              </div>
              <div>
                <strong>{item.title}</strong>
                <p className="fixfast-muted">{item.time}</p>
                <p className="fixfast-muted">{item.detail}</p>
              </div>
            </article>
          ))}
        </div>
      </div>

      <div className="fixfast-panel">
        <div className="fixfast-panel__topline">
          <span>Calendar plugin placeholder</span>
          <span>Ready for later</span>
        </div>
        <div className="worker-plugin-slot">
          <strong>Scheduling integration space</strong>
          <p className="fixfast-muted">
            Reserve this block for drag-and-drop calendar plugins, reminders,
            and dispatch sync widgets later.
          </p>
        </div>
      </div>
    </div>
  );
}

function StatsPanel() {
  return (
    <div className="fixfast-grid fixfast-grid--two">
      <div className="fixfast-panel">
        <div className="fixfast-panel__topline">
          <span>Performance stats</span>
          <span>History</span>
        </div>
        <div className="worker-stats-grid">
          <article className="worker-stat-tile">
            <strong>{STATS.completedJobs}</strong>
            <span>Completed jobs</span>
          </article>
          <article className="worker-stat-tile">
            <strong>{STATS.rating}</strong>
            <span>Average rating</span>
          </article>
          <article className="worker-stat-tile">
            <strong>{STATS.completionRate}</strong>
            <span>Completion rate</span>
          </article>
          <article className="worker-stat-tile">
            <strong>{STATS.repeatClients}</strong>
            <span>Repeat clients</span>
          </article>
        </div>
      </div>

      <div className="fixfast-panel">
        <div className="fixfast-panel__topline">
          <span>Ratings & reviews</span>
          <span>Recent feedback</span>
        </div>
        <div className="fixfast-list">
          {STATS.reviews.map((review) => (
            <article key={review.id} className="fixfast-card">
              <div className="fixfast-panel__topline">
                <span>{review.author}</span>
                <span>{review.score}</span>
              </div>
              <p className="fixfast-muted">{review.text}</p>
            </article>
          ))}
        </div>
      </div>
    </div>
  );
}

function WorkerWindowPreview({ title, lines = [], emphasis }) {
  return (
    <div className="fixfast-window__summary">
      <div className="fixfast-window__summary-block">
        <div className="fixfast-window__summary-title">{title}</div>
        {emphasis ? (
          <div className="fixfast-window__summary-line">
            <strong>{emphasis}</strong>
          </div>
        ) : null}
      </div>
      {lines.map((line, index) => (
        <div key={`${title}-${index}`} className="fixfast-window__summary-line">
          <span>{line.label}</span>
          <strong>{line.value}</strong>
        </div>
      ))}
    </div>
  );
}

export default function WorkerDashboard({ onNavigate }) {
  const { user, logout } = useAuth();
  const [activeWindow, setActiveWindow] = useState("workspace");
  const [transitioningTo, setTransitioningTo] = useState(null);

  const handleWindowSwap = (nextWindow) => {
    if (nextWindow === activeWindow) return;
    setTransitioningTo(nextWindow);
    window.setTimeout(() => {
      setActiveWindow(nextWindow);
      window.setTimeout(() => setTransitioningTo(null), 460);
    }, 90);
  };

  const navItems = [
    { id: "workspace", label: "Workspace" },
    { id: "jobsAround", label: "Jobs Around" },
    { id: "myBids", label: "My Bids" },
    { id: "calendar", label: "Calendar" },
    { id: "stats", label: "Stats" },
  ];

  const previewItems = useMemo(
    () => [
      {
        id: "workspace",
        label: "Workspace",
        icon: PANEL_META.workspace.icon,
        meta: PANEL_META.workspace.meta,
        windowClass: "fixfast-window--history",
        preview: (
          <WorkerWindowPreview
            title="Assigned Queue"
            emphasis={`${ASSIGNED_JOBS.length} active items`}
            lines={ASSIGNED_JOBS.slice(0, 2).map((job) => ({
              label: job.customer,
              value: job.status,
            }))}
          />
        ),
      },
      {
        id: "jobsAround",
        label: "Jobs Around",
        icon: PANEL_META.jobsAround.icon,
        meta: PANEL_META.jobsAround.meta,
        windowClass: "fixfast-window--around",
        preview: (
          <WorkerWindowPreview
            title="Local Jobs"
            emphasis={`${JOBS_AROUND.length} nearby`}
            lines={JOBS_AROUND.slice(0, 2).map((job) => ({
              label: job.title.slice(0, 18),
              value: job.distance,
            }))}
          />
        ),
      },
      {
        id: "myBids",
        label: "My Bids",
        icon: PANEL_META.myBids.icon,
        meta: PANEL_META.myBids.meta,
        windowClass: "fixfast-window--bids",
        preview: (
          <WorkerWindowPreview
            title="Bid Status"
            emphasis={`${MY_BIDS.length} sent`}
            lines={MY_BIDS.slice(0, 2).map((bid) => ({
              label: bid.status,
              value: bid.quote,
            }))}
          />
        ),
      },
      {
        id: "calendar",
        label: "Calendar",
        icon: PANEL_META.calendar.icon,
        meta: PANEL_META.calendar.meta,
        windowClass: "fixfast-window--calendar",
        preview: (
          <WorkerWindowPreview
            title="Schedule"
            emphasis={CALENDAR_ITEMS[0].time}
            lines={CALENDAR_ITEMS.slice(0, 2).map((item) => ({
              label: item.day,
              value: item.title,
            }))}
          />
        ),
      },
      {
        id: "stats",
        label: "Stats",
        icon: PANEL_META.stats.icon,
        meta: PANEL_META.stats.meta,
        windowClass: "fixfast-window--chat",
        preview: (
          <WorkerWindowPreview
            title="Performance"
            emphasis={STATS.rating}
            lines={[
              { label: "Completed", value: String(STATS.completedJobs) },
              { label: "Repeat", value: String(STATS.repeatClients) },
            ]}
          />
        ),
      },
    ],
    [],
  );

  const activeMeta = PANEL_META[activeWindow];

  const profileActions = [
    {
      label: "Switch to customer app",
      onClick: () => onNavigate?.("customer_dashboard", { replace: true }),
    },
    {
      label: "Log out",
      onClick: async () => {
        await logout();
        onNavigate?.("login", { replace: true });
      },
    },
  ];

  const stageContent = {
    workspace: <WorkspacePanel />,
    jobsAround: <JobsAroundPanel />,
    myBids: <BidsPanel />,
    calendar: <CalendarPanel />,
    stats: <StatsPanel />,
  };

  return (
    <div className="fixfast-page">
      <FixFastNavbar
        brandTitle="Handy Man"
        brandEyebrow="FixFast Worker"
        navItems={navItems}
        activePanel={activeWindow}
        onSelectPanel={handleWindowSwap}
        profileSlot={
          <FixFastProfile
            label={user?.firstName || user?.username || "Worker"}
            sublabel={WORKER_PROFILE.verificationLabel}
            actions={profileActions}
          />
        }
      />

      <main className="fixfast-shell">
        <TheaterStage
          title={activeMeta.title}
          subtitle={activeMeta.subtitle}
          activeKey={activeWindow}
          isTransitioning={Boolean(transitioningTo)}
        >
          {stageContent[activeWindow]}
        </TheaterStage>

        <PreviewDeck
          items={previewItems}
          activePanel={activeWindow}
          onSelectPanel={handleWindowSwap}
          transitioningTo={transitioningTo}
        />
      </main>
    </div>
  );
}
