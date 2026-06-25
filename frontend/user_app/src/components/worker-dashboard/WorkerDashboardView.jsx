import React, { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  PreviewDeck,
  TheaterStage,
} from "@shared/components/dashboard-stage/DashboardStage";
import {
  WORKER_VIEWS,
  WORKER_VIEW_LIST,
  buildWorkerViewPath,
  getWorkerViewForWindow,
} from "@shared/config/viewRoutes";
import { useWorkerDashboardData } from "./useWorkerDashboardData";
import "./worker-dashboard.css";

const WINDOW_ICONS = {
  dashboard: "🧰",
  jobs: "📍",
  bids: "💼",
  calendar: "🗓",
  stats: "📊",
};

function WorkspacePanel({
  assignedJobs,
  workerProfile,
  roleStatus,
  errors,
  loading,
  activateWorkerRole,
}) {
  return (
    <div className="fixfast-grid fixfast-grid--two">
      <div className="fixfast-panel">
        <div className="fixfast-panel__topline">
          <span>Assigned jobs</span>
          <span>{assignedJobs.length} open items</span>
        </div>
        {errors.tasks ? <p className="worker-notice">{errors.tasks}</p> : null}
        <div className="fixfast-list">
          {assignedJobs.map((job) => (
            <article key={job.id} className="fixfast-card">
              <div className="fixfast-panel__topline">
                <span>{job.title}</span>
                <span>{job.status}</span>
              </div>
              <p className="fixfast-muted">Source: {job.customer}</p>
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
          <span>Worker profile</span>
          <span>{workerProfile.trade}</span>
        </div>
        {errors.profile ? (
          <p className="worker-notice">{errors.profile}</p>
        ) : null}
        <div className="worker-metric-stack">
          <div className="worker-metric-card">
            <strong>Verification</strong>
            <span>{workerProfile.verificationLabel}</span>
          </div>
          <div className="worker-metric-card">
            <strong>Current shift</strong>
            <span>{workerProfile.currentShift}</span>
          </div>
          <div className="worker-metric-card">
            <strong>Role activation</strong>
            <span>
              {roleStatus ||
                "Use this action if the current account still needs worker capability."}
            </span>
          </div>
        </div>
        <button
          type="button"
          className="fixfast-button"
          style={{ width: "100%", marginTop: "1rem" }}
          onClick={activateWorkerRole}
          disabled={loading.role}
        >
          {loading.role ? "Activating…" : "Activate Worker Role"}
        </button>
      </div>
    </div>
  );
}

function JobsAroundPanel({ jobsAround, errors }) {
  return (
    <div className="worker-map-layout">
      <div className="fixfast-panel worker-map-stage">
        <div className="fixfast-panel__topline">
          <span>Interactive map placeholder</span>
          <span>Plugin slot ready</span>
        </div>
        <div className="worker-map-surface">
          <div className="worker-map-grid" aria-hidden="true" />
          {jobsAround.map((job, index) => (
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
              This panel is intentionally reserved for a real mapping plugin
              later. It currently mirrors the nearby job list with generated
              markers.
            </p>
          </div>
        </div>
      </div>

      <div className="fixfast-panel">
        <div className="fixfast-panel__topline">
          <span>Nearby jobs list</span>
          <span>{jobsAround.length} available</span>
        </div>
        {errors.tasks ? <p className="worker-notice">{errors.tasks}</p> : null}
        <div className="fixfast-list">
          {jobsAround.map((job) => (
            <article key={job.id} className="fixfast-card">
              <div className="fixfast-panel__topline">
                <span>{job.title}</span>
                <span>{job.distance}</span>
              </div>
              <p className="fixfast-muted">Source: {job.client}</p>
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

function BidsPanel({ bids }) {
  return (
    <div className="fixfast-panel">
      <div className="fixfast-panel__topline">
        <span>Bid tracker</span>
        <span>{bids.length} submissions</span>
      </div>
      <div className="fixfast-list">
        {bids.map((bid) => (
          <article key={bid.id} className="fixfast-card worker-bid-card">
            <div className="fixfast-panel__topline">
              <span>{bid.job}</span>
              <span>{bid.quote}</span>
            </div>
            <div className="worker-bid-status-row">
              <span
                className={`worker-status-pill worker-status-pill--${bid.status
                  .toLowerCase()
                  .replace(/\s+/g, "-")}`}
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
                        : bid.status === "Completed"
                          ? "100%"
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

function CalendarPanel({ calendarItems }) {
  return (
    <div className="fixfast-grid fixfast-grid--two">
      <div className="fixfast-panel">
        <div className="fixfast-panel__topline">
          <span>Weekly schedule board</span>
          <span>Allocated time slots</span>
        </div>
        <div className="worker-calendar-grid">
          {calendarItems.map((item) => (
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
            Reserve this block for drag-and-drop scheduling tools, reminders,
            and worker dispatch plugins later.
          </p>
        </div>
      </div>
    </div>
  );
}

function StatsPanel({ stats }) {
  return (
    <div className="fixfast-grid fixfast-grid--two">
      <div className="fixfast-panel">
        <div className="fixfast-panel__topline">
          <span>Performance stats</span>
          <span>History</span>
        </div>
        <div className="worker-stats-grid">
          <article className="worker-stat-tile">
            <strong>{stats.completedJobs}</strong>
            <span>Completed jobs</span>
          </article>
          <article className="worker-stat-tile">
            <strong>{stats.rating}</strong>
            <span>Average rating</span>
          </article>
          <article className="worker-stat-tile">
            <strong>{stats.completionRate}</strong>
            <span>Completion rate</span>
          </article>
          <article className="worker-stat-tile">
            <strong>{stats.repeatClients}</strong>
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
          {stats.reviews.map((review) => (
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

export default function WorkerDashboardView({
  embedded = false,
  activeView = WORKER_VIEWS.PERFORMANCE,
  onViewSelect,
}) {
  const navigate = useNavigate();
  const {
    workerProfile,
    assignedJobs,
    jobsAround,
    bids,
    calendarItems,
    stats,
    loading,
    errors,
    roleStatus,
    activateWorkerRole,
  } = useWorkerDashboardData();

  const previewItems = useMemo(
    () =>
      WORKER_VIEW_LIST.map((view) => ({
        id: view.id,
        label: view.label,
        icon: WINDOW_ICONS[view.windowId] || "🧩",
        meta: view.meta,
        windowClass: `fixfast-window--${view.windowId}`,
        preview:
          view.windowId === "dashboard" ? (
            <WorkerWindowPreview
              title="Assigned Queue"
              emphasis={`${assignedJobs.length} active items`}
              lines={assignedJobs.slice(0, 2).map((job) => ({
                label: job.customer,
                value: job.status,
              }))}
            />
          ) : view.windowId === "jobs" ? (
            <WorkerWindowPreview
              title="Local Jobs"
              emphasis={`${jobsAround.length} nearby`}
              lines={jobsAround.slice(0, 2).map((job) => ({
                label: job.title.slice(0, 18),
                value: job.distance,
              }))}
            />
          ) : view.windowId === "bids" ? (
            <WorkerWindowPreview
              title="Bid Status"
              emphasis={`${bids.length} tracked`}
              lines={bids.slice(0, 2).map((bid) => ({
                label: bid.status,
                value: bid.quote,
              }))}
            />
          ) : view.windowId === "calendar" ? (
            <WorkerWindowPreview
              title="Schedule"
              emphasis={calendarItems[0]?.time || "Pending API"}
              lines={calendarItems.slice(0, 2).map((item) => ({
                label: item.day,
                value: item.title,
              }))}
            />
          ) : (
            <WorkerWindowPreview
              title="Performance"
              emphasis={stats.rating}
              lines={[
                { label: "Completed", value: String(stats.completedJobs) },
                { label: "Repeat", value: String(stats.repeatClients) },
              ]}
            />
          ),
      })),
    [assignedJobs, bids, calendarItems, jobsAround, stats],
  );

  const stageContent = {
    dashboard: (
      <WorkspacePanel
        assignedJobs={assignedJobs}
        workerProfile={workerProfile}
        roleStatus={roleStatus}
        errors={errors}
        loading={loading}
        activateWorkerRole={activateWorkerRole}
      />
    ),
    jobs: <JobsAroundPanel jobsAround={jobsAround} errors={errors} />,
    bids: <BidsPanel bids={bids} />,
    calendar: <CalendarPanel calendarItems={calendarItems} />,
    stats: <StatsPanel stats={stats} />,
  };

  const handleWindowSelect = (viewId) => {
    const nextView =
      WORKER_VIEW_LIST.find((view) => view.id === viewId) ||
      getWorkerViewForWindow(viewId);

    if (!nextView) {
      return;
    }

    if (onViewSelect) {
      onViewSelect(nextView);
      return;
    }

    navigate(buildWorkerViewPath(nextView));
  };

  const content = (
    <>
      <TheaterStage
        title={activeView.label}
        subtitle={activeView.subtitle}
        activeKey={activeView.id}
        isTransitioning={false}
      >
        {stageContent[activeView.windowId]}
      </TheaterStage>

      <PreviewDeck
        items={previewItems}
        activePanel={activeView.id}
        onSelectPanel={handleWindowSelect}
        transitioningTo={null}
      />
    </>
  );

  if (embedded) {
    return content;
  }

  return (
    <div className="fixfast-page">
      <main className="fixfast-shell">{content}</main>
    </div>
  );
}
