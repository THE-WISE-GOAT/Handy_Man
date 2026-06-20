import React, { useEffect, useRef, useState } from "react";
import { useAuth } from "@shared/context/AuthContext";
import {
  FixFastNavbar,
  FixFastProfile,
  PreviewDeck,
  TheaterStage,
} from "@shared/components/dashboard-stage/DashboardStage";
import { NAV_ITEMS, TAG_LIBRARY, CALENDAR_STUB_MESSAGE } from "./constants";
import { formatTimestamp } from "./helpers";
import { useCustomerDashboardData } from "./useCustomerDashboardData";

const PANEL_META = {
  around: {
    icon: "📍",
    title: "Who is Around",
    subtitle: "Live worker radius",
    meta: "Nearby workforce",
  },
  booking: {
    icon: "💬",
    title: "New Booking",
    subtitle: "AI dispatch terminal",
    meta: "Chat + tags",
  },
  biddings: {
    icon: "💼",
    title: "Biddings",
    subtitle: "Task and matching activity",
    meta: "Quotes + matches",
  },
  history: {
    icon: "🧾",
    title: "History",
    subtitle: "Completed jobs and chat history",
    meta: "Past records",
  },
  calendar: {
    icon: "🗓",
    title: "Calendar",
    subtitle: "Prepared frontend stub",
    meta: "Future scheduling",
  },
};

function AroundPanel({
  location,
  workersAround,
  loading,
  errors,
  refreshWorkers,
}) {
  return (
    <div className="fixfast-grid fixfast-grid--two">
      <div className="fixfast-panel">
        <div className="fixfast-panel__topline">
          <span>Coverage radius</span>
          <button
            type="button"
            className="fixfast-mini-button"
            onClick={refreshWorkers}
          >
            Refresh
          </button>
        </div>
        <div className="fixfast-map-box">
          <div>
            <strong>Worker coverage preview</strong>
            <p className="fixfast-muted">
              Backend source: GET /service-tasks/available-workers around{" "}
              {location.lat}, {location.lng}
            </p>
          </div>
        </div>
      </div>

      <div className="fixfast-panel">
        <div className="fixfast-panel__topline">
          <span>Nearby workers</span>
          <span>{workersAround.length} found</span>
        </div>
        {loading.workers ? (
          <p className="fixfast-empty">Loading nearby workers…</p>
        ) : null}
        {errors.workers ? (
          <p className="fixfast-error">{errors.workers}</p>
        ) : null}
        <div className="fixfast-list">
          {workersAround.map((worker, index) => (
            <article
              key={`${worker.id || "worker"}-${index}`}
              className="fixfast-card"
            >
              <div className="fixfast-panel__topline">
                <span>Worker #{worker.id || index + 1}</span>
                <span>
                  {worker.operating_radius
                    ? `${worker.operating_radius} km`
                    : "N/A"}
                </span>
              </div>
              <p className="fixfast-muted">
                {Array.isArray(worker.skills) && worker.skills.length > 0
                  ? worker.skills.join(", ")
                  : "Skills metadata unavailable"}
              </p>
              <div className="fixfast-chip-row">
                {(Array.isArray(worker.tags) ? worker.tags : []).map((tag) => (
                  <span key={tag} className="fixfast-chip">
                    {tag}
                  </span>
                ))}
              </div>
            </article>
          ))}
          {!loading.workers && !errors.workers && workersAround.length === 0 ? (
            <p className="fixfast-empty">
              No workers returned for the current query.
            </p>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function BookingPanel({
  activeTags,
  activeTask,
  workerApplicationStatus,
  applyForWorkerRole,
  chatMessages,
  chatInput,
  setChatInput,
  handleChatSubmit,
  loading,
  errors,
  chatLogRef,
}) {
  return (
    <div className="fixfast-grid fixfast-grid--booking">
      <aside className="fixfast-panel">
        <div className="fixfast-panel__topline">
          <span>Active filters / tags</span>
          <span>AI synced</span>
        </div>
        <div className="fixfast-tag-cloud">
          {TAG_LIBRARY.map((tag) => (
            <span
              key={tag}
              className={`fixfast-chip ${activeTags.includes(tag) ? "is-active" : ""}`}
            >
              {tag}
            </span>
          ))}
        </div>

        <div className="fixfast-subpanel" style={{ marginTop: "1rem" }}>
          <div className="fixfast-panel__topline">
            <span>Booking state</span>
          </div>
          <p>
            {activeTask ? activeTask.title : "No open booking detected yet."}
          </p>
          <div className="fixfast-list fixfast-muted">
            <span>Status: {activeTask?.status || "open draft"}</span>
            <span>
              Assigned: {activeTask?.assignedWorker || "Awaiting dispatch"}
            </span>
            <span>ETA: {activeTask?.eta || "Pending"}</span>
          </div>
        </div>

        <button
          type="button"
          className="fixfast-button"
          style={{ width: "100%", marginTop: "1rem" }}
          onClick={applyForWorkerRole}
        >
          Join as worker
        </button>
        {workerApplicationStatus ? (
          <p className="fixfast-muted">{workerApplicationStatus}</p>
        ) : null}
      </aside>

      <div className="fixfast-panel fixfast-chat-shell">
        <div className="fixfast-panel__topline">
          <span>AI dispatch chat terminal</span>
          <span>POST /chat/message</span>
        </div>

        <div ref={chatLogRef} className="fixfast-chat-log">
          {chatMessages.map((message) => (
            <div
              key={message.id}
              className={`fixfast-chat-row ${message.sender === "user" ? "is-user" : ""}`}
            >
              <div className="fixfast-chat-bubble">
                <p>{message.text}</p>
                <span>{message.timestamp || "Just now"}</span>
              </div>
            </div>
          ))}
        </div>

        {errors.chat ? <p className="fixfast-error">{errors.chat}</p> : null}

        <form className="fixfast-chat-form" onSubmit={handleChatSubmit}>
          <input
            className="fixfast-input"
            type="text"
            value={chatInput}
            onChange={(event) => setChatInput(event.target.value)}
            placeholder="Describe emergency or attach photo..."
            disabled={loading.chat}
          />
          <button
            type="submit"
            className="fixfast-button"
            disabled={!chatInput.trim() || loading.chat}
          >
            {loading.chat ? "Sending…" : "Send"}
          </button>
        </form>
      </div>
    </div>
  );
}

function BiddingsPanel({ biddings, loading, errors }) {
  return (
    <div className="fixfast-panel">
      <div className="fixfast-panel__topline">
        <span>Available backend data</span>
        <span>Derived from service tasks</span>
      </div>
      <p className="fixfast-muted">
        The backend currently exposes service tasks but not a dedicated customer
        bidding endpoint. This panel derives bidding-style cards from GET
        /service-tasks/ without changing backend logic.
      </p>
      {loading.tasks ? (
        <p className="fixfast-empty">Loading biddings…</p>
      ) : null}
      {errors.tasks ? <p className="fixfast-error">{errors.tasks}</p> : null}
      <div className="fixfast-list">
        {biddings.map((item) => (
          <article key={item.id} className="fixfast-card">
            <div className="fixfast-panel__topline">
              <span>{item.title}</span>
              <span>{item.status}</span>
            </div>
            <p className="fixfast-muted">Worker: {item.worker}</p>
            <div className="fixfast-stat-row fixfast-muted">
              <span>{item.amount}</span>
              <span>{item.submittedAt}</span>
            </div>
          </article>
        ))}
        {!loading.tasks && biddings.length === 0 ? (
          <p className="fixfast-empty">No bidding activity yet.</p>
        ) : null}
      </div>
    </div>
  );
}

function HistoryPanel({ history, chatMessages }) {
  return (
    <div className="fixfast-grid fixfast-grid--two">
      <div className="fixfast-panel">
        <div className="fixfast-panel__topline">
          <span>Completed jobs</span>
          <span>GET /service-tasks/</span>
        </div>
        <div className="fixfast-table-wrap">
          <table className="fixfast-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Service</th>
                <th>Worker</th>
                <th>Cost</th>
              </tr>
            </thead>
            <tbody>
              {history.map((item) => (
                <tr key={item.id}>
                  <td>{item.date}</td>
                  <td>{item.serviceType}</td>
                  <td>{item.providerName}</td>
                  <td>{item.cost}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {history.length === 0 ? (
          <p className="fixfast-empty">No completed jobs returned yet.</p>
        ) : null}
      </div>

      <div className="fixfast-panel">
        <div className="fixfast-panel__topline">
          <span>Chat history snapshot</span>
          <span>GET /chat/history</span>
        </div>
        <div className="fixfast-list">
          {chatMessages.slice(-8).map((message) => (
            <article key={message.id} className="fixfast-card">
              <div className="fixfast-panel__topline">
                <span>{message.sender === "user" ? "You" : "AI Dispatch"}</span>
                <span>{message.timestamp || formatTimestamp()}</span>
              </div>
              <p className="fixfast-muted">{message.text}</p>
            </article>
          ))}
        </div>
      </div>
    </div>
  );
}

function CalendarPanel() {
  return (
    <div className="fixfast-panel">
      <div className="fixfast-panel__topline">
        <span>Scheduling placeholder</span>
        <span>Frontend stub</span>
      </div>
      <div className="fixfast-table-wrap">
        <table className="fixfast-table">
          <thead>
            <tr>
              <th>Mon</th>
              <th>Tue</th>
              <th>Wed</th>
              <th>Thu</th>
              <th>Fri</th>
              <th>Sat</th>
              <th>Sun</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>1</td>
              <td>2</td>
              <td>3</td>
              <td>4</td>
              <td>5</td>
              <td>6</td>
              <td>7</td>
            </tr>
            <tr>
              <td>8</td>
              <td>9</td>
              <td>10</td>
              <td>11</td>
              <td>12</td>
              <td>13</td>
              <td>14</td>
            </tr>
            <tr>
              <td>15</td>
              <td>16</td>
              <td>17</td>
              <td>18</td>
              <td>19</td>
              <td>20</td>
              <td>21</td>
            </tr>
            <tr>
              <td>22</td>
              <td>23</td>
              <td>24</td>
              <td>25</td>
              <td>26</td>
              <td>27</td>
              <td>28</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p className="fixfast-muted">{CALENDAR_STUB_MESSAGE}</p>
    </div>
  );
}

function CustomerWindowPreview({ title, lines = [], emphasis }) {
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

export default function CustomerDashboardView({ onNavigate }) {
  const { user, logout } = useAuth();
  const {
    location,
    chatMessages,
    chatInput,
    setChatInput,
    sendChatMessage,
    activeTags,
    workersAround,
    activeTask,
    biddings,
    history,
    loading,
    errors,
    workerApplicationStatus,
    applyForWorkerRole,
    refreshWorkers,
  } = useCustomerDashboardData(user);

  const [activeWindow, setActiveWindow] = useState("around");
  const [transitioningTo, setTransitioningTo] = useState(null);
  const chatLogRef = useRef(null);

  useEffect(() => {
    if (chatLogRef.current) {
      chatLogRef.current.scrollTop = chatLogRef.current.scrollHeight;
    }
  }, [chatMessages, activeWindow]);

  const handleChatSubmit = async (event) => {
    event.preventDefault();
    await sendChatMessage();
  };

  const handleWindowSwap = (nextWindow) => {
    if (nextWindow === activeWindow) return;
    setTransitioningTo(nextWindow);
    window.setTimeout(() => {
      setActiveWindow(nextWindow);
      window.setTimeout(() => setTransitioningTo(null), 460);
    }, 90);
  };

  const navItems = [
    { id: "booking", label: "New Booking" },
    { id: "biddings", label: "Biddings" },
    { id: "history", label: "History" },
    { id: "around", label: "Who is Around" },
    { id: "calendar", label: "Calendar" },
  ];

  const previewItems = NAV_ITEMS.map((item) => {
    if (item.id === "around") {
      return {
        ...item,
        icon: PANEL_META[item.id].icon,
        meta: PANEL_META[item.id].meta,
        windowClass: "fixfast-window--around",
        preview: (
          <CustomerWindowPreview
            title="Workers Around"
            emphasis={`${workersAround.length} active`}
            lines={workersAround.slice(0, 2).map((worker, index) => ({
              label: `Worker ${worker.id || index + 1}`,
              value: worker.operating_radius
                ? `${worker.operating_radius} km`
                : "Radius N/A",
            }))}
          />
        ),
      };
    }

    if (item.id === "booking") {
      return {
        ...item,
        icon: PANEL_META[item.id].icon,
        meta: PANEL_META[item.id].meta,
        windowClass: "fixfast-window--chat",
        preview: (
          <CustomerWindowPreview
            title="Dispatch Chat"
            emphasis={activeTask?.title || "No active booking"}
            lines={chatMessages.slice(-2).map((message, index) => ({
              label:
                message.sender === "user"
                  ? `You ${index + 1}`
                  : `AI ${index + 1}`,
              value:
                message.text.slice(0, 36) +
                (message.text.length > 36 ? "…" : ""),
            }))}
          />
        ),
      };
    }

    if (item.id === "biddings") {
      return {
        ...item,
        icon: PANEL_META[item.id].icon,
        meta: PANEL_META[item.id].meta,
        windowClass: "fixfast-window--bids",
        preview: (
          <CustomerWindowPreview
            title="Top Quotes"
            emphasis={
              biddings.length
                ? `${biddings.length} open items`
                : "No quotes yet"
            }
            lines={biddings.slice(0, 2).map((bid) => ({
              label: bid.worker,
              value: bid.amount,
            }))}
          />
        ),
      };
    }

    if (item.id === "history") {
      return {
        ...item,
        icon: PANEL_META[item.id].icon,
        meta: PANEL_META[item.id].meta,
        windowClass: "fixfast-window--history",
        preview: (
          <CustomerWindowPreview
            title="Recent History"
            emphasis={
              history.length ? `${history.length} completed` : "No history"
            }
            lines={history.slice(0, 2).map((entry) => ({
              label: entry.serviceType.slice(0, 18),
              value: entry.cost,
            }))}
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
        <CustomerWindowPreview
          title="Calendar"
          emphasis="Schedule stub"
          lines={[
            { label: "Status", value: "Ready" },
            { label: "Backend", value: "Pending" },
          ]}
        />
      ),
    };
  });

  const profileActions = [
    {
      label: "Open worker app",
      onClick: () => onNavigate?.("worker_dashboard"),
    },
    {
      label: "Log out",
      onClick: async () => {
        await logout();
        onNavigate?.("login", { replace: true });
      },
    },
  ];

  const activeMeta = PANEL_META[activeWindow];

  const stageContent = {
    around: (
      <AroundPanel
        location={location}
        workersAround={workersAround}
        loading={loading}
        errors={errors}
        refreshWorkers={refreshWorkers}
      />
    ),
    booking: (
      <BookingPanel
        activeTags={activeTags}
        activeTask={activeTask}
        workerApplicationStatus={workerApplicationStatus}
        applyForWorkerRole={applyForWorkerRole}
        chatMessages={chatMessages}
        chatInput={chatInput}
        setChatInput={setChatInput}
        handleChatSubmit={handleChatSubmit}
        loading={loading}
        errors={errors}
        chatLogRef={chatLogRef}
      />
    ),
    biddings: (
      <BiddingsPanel biddings={biddings} loading={loading} errors={errors} />
    ),
    history: <HistoryPanel history={history} chatMessages={chatMessages} />,
    calendar: <CalendarPanel />,
  };

  return (
    <div className="fixfast-page">
      <FixFastNavbar
        brandTitle="Handy Man"
        brandEyebrow="FixFast Customer"
        navItems={navItems}
        activePanel={activeWindow}
        onSelectPanel={handleWindowSwap}
        profileSlot={
          <FixFastProfile
            label={user?.firstName || user?.username || "Customer"}
            sublabel={user?.email || "Signed-in user"}
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
