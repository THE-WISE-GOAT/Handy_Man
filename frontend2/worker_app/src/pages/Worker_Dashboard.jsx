import React, { useEffect, useState, useCallback } from "react";
import { useAuth } from "@shared/context/AuthContext";
import { apiClient } from "@shared/api/client";
import {
  FixFastNavbar,
  FixFastProfile,
  PreviewDeck,
  TheaterStage,
} from "@shared/components/dashboard-stage/DashboardStage";

const MAP_PREVIEW_URL =
  import.meta.env.VITE_MAP_STANDALONE_URL || "http://localhost:5174";

const mockSession = {
  worker: {
    fullName: "Ram Bahadur Thapa",
    trade: "Plumbing",
    verificationLabel: "Verified Plumbing Specialist",
    walletBalance: "Rs. 14,500",
    rating: "⭐ 4.9 (42 Reviews)",
    completedShifts: "18 Jobs Completed this month",
  },
  liveDispatch: {
    customerName: "Anita Shrestha",
    distance: "1.2 km away",
    urgency: "🚨 Urgent Care",
    payoutRate: "Rs. 2,400 payout",
    projectTitle: "Emergency Pipe Repair",
    homeAddress: "Maharajgunj, Kathmandu",
    scheduledAt: "Available now",
    summary: "Burst line isolation and pressure-safe reroute",
  },
  acceptedJob: {
    projectTitle: "Emergency Pipe Repair",
    nextStep: "Navigation started and customer notified.",
  },
  upcomingSchedule: [
    {
      customerName: "Suman KC",
      homeAddress: "Boudha, Kathmandu",
      scheduledTimestamp: "Thu, 10:00 AM",
      projectDetails: "Water heater inspection and valve replacement",
    },
    {
      customerName: "Mina Rai",
      homeAddress: "Lalitpur, Jawalakhel",
      scheduledTimestamp: "Thu, 3:30 PM",
      projectDetails: "Kitchen sink fitting and leak seal",
    },
    {
      customerName: "Prakash Lama",
      homeAddress: "Chabahil, Kathmandu",
      scheduledTimestamp: "Fri, 9:15 AM",
      projectDetails: "Drain inspection and pipe rerouting",
    },
  ],
};

const PANEL_META = {
  dispatch: {
    icon: "🚨",
    title: "Live Dispatch",
    subtitle: "Urgent jobs in your radius",
    meta: "Immediate response",
  },
  schedule: {
    icon: "📅",
    title: "Schedule",
    subtitle: "Upcoming customer bookings",
    meta: "Planned jobs",
  },
  earnings: {
    icon: "💸",
    title: "Earnings",
    subtitle: "Wallet and performance metrics",
    meta: "Income snapshot",
  },
  map: {
    icon: "🗺",
    title: "Map Access",
    subtitle: "PostGIS worker map launcher",
    meta: "External tool",
  },
};

function DispatchPanel({ dispatchState, handleAcceptJob, handleDeclineJob }) {
  const isDispatchLive = dispatchState === "live";

  return (
    <div className="fixfast-panel">
      <div className="fixfast-panel__topline">
        <span>Urgent live dispatches</span>
        <span>{isDispatchLive ? "Active alert" : "Updated"}</span>
      </div>
      {isDispatchLive ? (
        <div className="fixfast-list">
          <article className="fixfast-card">
            <div className="fixfast-panel__topline">
              <span>{mockSession.liveDispatch.projectTitle}</span>
              <span>{mockSession.liveDispatch.payoutRate}</span>
            </div>
            <div className="fixfast-list fixfast-muted">
              <span>Customer: {mockSession.liveDispatch.customerName}</span>
              <span>Distance: {mockSession.liveDispatch.distance}</span>
              <span>Urgency: {mockSession.liveDispatch.urgency}</span>
              <span>Address: {mockSession.liveDispatch.homeAddress}</span>
              <span>{mockSession.liveDispatch.summary}</span>
            </div>
          </article>
          <div className="fixfast-stat-row">
            <button
              type="button"
              className="fixfast-secondary-button"
              onClick={handleDeclineJob}
            >
              Decline
            </button>
            <button
              type="button"
              className="fixfast-button"
              onClick={handleAcceptJob}
            >
              Accept & Navigate
            </button>
          </div>
        </div>
      ) : (
        <article className="fixfast-card">
          <div className="fixfast-panel__topline">
            <span>Dispatch status updated</span>
            <span>{dispatchState}</span>
          </div>
          <p className="fixfast-muted">
            {dispatchState === "accepted"
              ? `${mockSession.acceptedJob.projectTitle} accepted. ${mockSession.acceptedJob.nextStep}`
              : "No urgent live dispatch is currently active in your radius."}
          </p>
        </article>
      )}
    </div>
  );
}

function SchedulePanel() {
  return (
    <div className="fixfast-panel">
      <div className="fixfast-panel__topline">
        <span>Schedule queue</span>
        <span>{mockSession.upcomingSchedule.length} jobs</span>
      </div>
      <div className="fixfast-table-wrap">
        <table className="fixfast-table">
          <thead>
            <tr>
              <th>Customer</th>
              <th>Home Address</th>
              <th>Scheduled</th>
              <th>Project Details</th>
            </tr>
          </thead>
          <tbody>
            {mockSession.upcomingSchedule.map((booking) => (
              <tr key={`${booking.customerName}-${booking.scheduledTimestamp}`}>
                <td>{booking.customerName}</td>
                <td>{booking.homeAddress}</td>
                <td>{booking.scheduledTimestamp}</td>
                <td>{booking.projectDetails}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function EarningsPanel({ isOnline, setIsOnline }) {
  return (
    <div className="fixfast-grid fixfast-grid--two">
      <article className="fixfast-card">
        <div className="fixfast-panel__topline">
          <span>Wallet balance</span>
          <span>{mockSession.worker.walletBalance}</span>
        </div>
        <p className="fixfast-muted">
          Outstanding earnings ready for withdrawal.
        </p>
        <button type="button" className="fixfast-button">
          Withdraw Funds
        </button>
      </article>

      <article className="fixfast-card">
        <div className="fixfast-panel__topline">
          <span>Job rating</span>
          <span>{mockSession.worker.rating}</span>
        </div>
        <p className="fixfast-muted">
          Live feedback rolling in from verified customers.
        </p>
      </article>

      <article className="fixfast-card">
        <div className="fixfast-panel__topline">
          <span>Completed shifts</span>
          <span>{mockSession.worker.completedShifts}</span>
        </div>
        <p className="fixfast-muted">This month’s completed task count.</p>
      </article>

      <article className="fixfast-card">
        <div className="fixfast-panel__topline">
          <span>Availability</span>
          <span>{isOnline ? "Online" : "Offline"}</span>
        </div>
        <p className="fixfast-muted">
          Toggle whether dispatch can offer you new jobs.
        </p>
        <button
          type="button"
          className="fixfast-secondary-button"
          onClick={() => setIsOnline((current) => !current)}
        >
          {isOnline ? "Go Offline" : "Go Online"}
        </button>
      </article>
    </div>
  );
}

function MapPanel() {
  return (
    <div className="fixfast-panel">
      <div className="fixfast-panel__topline">
        <span>Worker map sandbox</span>
        <span>External tool</span>
      </div>
      <div className="fixfast-map-box">
        <div>
          <strong>PostGIS worker map</strong>
          <p className="fixfast-muted">
            Launch the existing live worker map sandbox in a new tab.
          </p>
          <a
            href={MAP_PREVIEW_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="fixfast-button"
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              textDecoration: "none",
              marginTop: "1rem",
            }}
          >
            Open Live Worker Map
          </a>
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
  const { user, accessToken, logout } = useAuth();
  const [isOnline, setIsOnline] = useState(true);
  const [dispatchState, setDispatchState] = useState("live");
  const [canSwitchToClient, setCanSwitchToClient] = useState(false);
  const [activeWindow, setActiveWindow] = useState("dispatch");

  const fetchSwitchPermission = useCallback(async () => {
    if (!accessToken) return;
    try {
      const response = await apiClient.get("/workers/can-switch-to-client");
      setCanSwitchToClient(response.can_switch_to_client);
    } catch {
      setCanSwitchToClient(false);
    }
  }, [accessToken]);

  useEffect(() => {
    fetchSwitchPermission();
  }, [fetchSwitchPermission]);

  const handleAcceptJob = () => {
    setDispatchState("accepted");
  };

  const handleDeclineJob = () => {
    setDispatchState("declined");
  };

  const navItems = [
    { id: "dispatch", label: "Live Dispatch" },
    { id: "schedule", label: "Schedule" },
    { id: "earnings", label: "Earnings" },
    { id: "map", label: "Map Access" },
  ];

  const previewItems = navItems.map((item) => {
    if (item.id === "dispatch") {
      return {
        ...item,
        icon: PANEL_META[item.id].icon,
        meta: PANEL_META[item.id].meta,
        windowClass: "fixfast-window--chat",
        preview: (
          <WorkerWindowPreview
            title="Urgent Dispatch"
            emphasis={
              dispatchState === "live"
                ? mockSession.liveDispatch.projectTitle
                : `Status: ${dispatchState}`
            }
            lines={[
              {
                label: "Customer",
                value: mockSession.liveDispatch.customerName,
              },
              { label: "Payout", value: mockSession.liveDispatch.payoutRate },
            ]}
          />
        ),
      };
    }

    if (item.id === "schedule") {
      return {
        ...item,
        icon: PANEL_META[item.id].icon,
        meta: PANEL_META[item.id].meta,
        windowClass: "fixfast-window--history",
        preview: (
          <WorkerWindowPreview
            title="Next Jobs"
            emphasis={`${mockSession.upcomingSchedule.length} scheduled`}
            lines={mockSession.upcomingSchedule.slice(0, 2).map((booking) => ({
              label: booking.customerName,
              value: booking.scheduledTimestamp,
            }))}
          />
        ),
      };
    }

    if (item.id === "earnings") {
      return {
        ...item,
        icon: PANEL_META[item.id].icon,
        meta: PANEL_META[item.id].meta,
        windowClass: "fixfast-window--bids",
        preview: (
          <WorkerWindowPreview
            title="Metrics"
            emphasis={mockSession.worker.walletBalance}
            lines={[
              { label: "Rating", value: mockSession.worker.rating },
              { label: "Status", value: isOnline ? "ONLINE" : "OFFLINE" },
            ]}
          />
        ),
      };
    }

    return {
      ...item,
      icon: PANEL_META[item.id].icon,
      meta: PANEL_META[item.id].meta,
      windowClass: "fixfast-window--calendar",
      preview: (
        <WorkerWindowPreview
          title="Map Access"
          emphasis="Sandbox"
          lines={[
            { label: "Mode", value: "External" },
            { label: "Status", value: "Ready" },
          ]}
        />
      ),
    };
  });

  const activeMeta = PANEL_META[activeWindow];

  const profileActions = [
    ...(canSwitchToClient
      ? [
          {
            label: "Switch to customer app",
            onClick: () =>
              onNavigate?.("customer_dashboard", { replace: true }),
          },
        ]
      : []),
    {
      label: "Log out",
      onClick: async () => {
        await logout();
        onNavigate?.("login", { replace: true });
      },
    },
  ];

  const stageContent = {
    dispatch: (
      <DispatchPanel
        dispatchState={dispatchState}
        handleAcceptJob={handleAcceptJob}
        handleDeclineJob={handleDeclineJob}
      />
    ),
    schedule: <SchedulePanel />,
    earnings: <EarningsPanel isOnline={isOnline} setIsOnline={setIsOnline} />,
    map: <MapPanel />,
  };

  return (
    <div className="fixfast-page">
      <FixFastNavbar
        brandTitle="Handy Man"
        brandEyebrow="FixFast Worker"
        navItems={navItems}
        activePanel={activeWindow}
        onSelectPanel={setActiveWindow}
        profileSlot={
          <FixFastProfile
            label={
              user?.firstName || user?.username || mockSession.worker.fullName
            }
            sublabel={mockSession.worker.verificationLabel}
            actions={profileActions}
          />
        }
      />

      <main className="fixfast-shell">
        <TheaterStage
          title={activeMeta.title}
          subtitle={activeMeta.subtitle}
          activeKey={activeWindow}
        >
          {stageContent[activeWindow]}
        </TheaterStage>

        <PreviewDeck
          items={previewItems}
          activePanel={activeWindow}
          onSelectPanel={setActiveWindow}
        />
      </main>
    </div>
  );
}
