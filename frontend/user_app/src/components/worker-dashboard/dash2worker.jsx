// components/worker-dashboard/dash2worker.jsx
import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useWorkerDashboardData } from "./useWorkerDashboardData";
import "./dash2worker.css";

export default function Dash2Worker({ viewSlug }) {
  const navigate = useNavigate();

  const {
    scheduledSlots,
    swapScheduledSlots,
    calendarDescText,
    jobsRegistryStatus,
    clientQueryStatus,
    routeMatrixStatus,
  } = useWorkerDashboardData();

  // Route state synchronization layer
  useEffect(() => {
    if (!viewSlug) return;

    if (scheduledSlots.main !== viewSlug) {
      const targetSlot = Object.keys(scheduledSlots).find(
        (key) => scheduledSlots[key] === viewSlug
      );

      if (targetSlot) {
        swapScheduledSlots(targetSlot);
      }
    }
  }, [viewSlug, scheduledSlots, swapScheduledSlots]);

  const handleModuleSelect = (targetSlug) => {
    navigate(`/worker/scheduled/${targetSlug}`);
  };

  // ====================================================
  // SUB-MODULE RENDERS
  // ====================================================

  const renderCalendar = (slotKey) => {
    if (slotKey === "main") {
      return (
        <div className="dashboard-card slot-main">
          <div className="card-header">
            ••• SCHEDULE PLATFORM PLANNERS
          </div>

          <div className="main-panel">
            <h2>System Planner Calendar</h2>
            <p className="panel-desc">{calendarDescText}</p>
          </div>
        </div>
      );
    }

    return (
      <div
        className={`dashboard-card slot-${slotKey} clickable`}
        onClick={() => handleModuleSelect("ScheduledCalendar")}
      >
        <div className="card-header">
          ••• SCHEDULE PLATFORM PLANNERS
        </div>

        <div className="preview-panel">
          {slotKey === "sidebar" ? (
            <>
              <span className="badge badge-highlight">
                Sidebar: Planner Context
              </span>

              <p className="card-summary">
                {calendarDescText}
              </p>
            </>
          ) : (
            <span className="badge">
              Footer ({slotKey}): Calendar Monitor Live
            </span>
          )}
        </div>
      </div>
    );
  };

  const renderJobRegistry = (slotKey) => {
    if (slotKey === "main") {
      return (
        <div className="dashboard-card slot-main">
          <div className="card-header">
            ••• UPCOMING DEPLOYMENT NODES
          </div>

          <div className="main-panel">
            <h2>Scheduled Jobs Registry</h2>
          </div>
        </div>
      );
    }

    return (
      <div
        className={`dashboard-card slot-${slotKey} clickable`}
        onClick={() => handleModuleSelect("ScheduledJobCard")}
      >
        <div className="card-header">
          ••• UPCOMING DEPLOYMENT NODES
        </div>

        <div className="preview-panel">
          {slotKey === "sidebar" ? (
            <>
              <span className="badge badge-highlight">
                Sidebar: Job Matrix
              </span>

              <p className="card-summary">
                Status: {jobsRegistryStatus}
              </p>
            </>
          ) : (
            <span className="badge">
              Footer ({slotKey}): Registry — {jobsRegistryStatus}
            </span>
          )}
        </div>
      </div>
    );
  };

  const renderClientQueries = (slotKey) => {
    if (slotKey === "main") {
      return (
        <div className="dashboard-card slot-main">
          <div className="card-header">
            ••• ACTIVE MESSAGING CORRIDOR
          </div>

          <div className="main-panel">
            <h2>Client Communications Terminal</h2>
          </div>
        </div>
      );
    }

    return (
      <div
        className={`dashboard-card slot-${slotKey} clickable`}
        onClick={() => handleModuleSelect("ClientQueries")}
      >
        <div className="card-header">
          ••• ACTIVE MESSAGING CORRIDOR
        </div>

        <div className="preview-panel">
          {slotKey === "sidebar" ? (
            <>
              <span className="badge badge-highlight">
                Sidebar: Inbox Comms
              </span>

              <p className="card-summary">
                Queue: {clientQueryStatus}
              </p>
            </>
          ) : (
            <span className="badge">
              Footer ({slotKey}): Comms Feed ({clientQueryStatus})
            </span>
          )}
        </div>
      </div>
    );
  };

  const renderRouteMatrix = (slotKey) => {
    if (slotKey === "main") {
      return (
        <div className="dashboard-card slot-main">
          <div className="card-header">
            ••• APPOINTMENT LOCATION INDEX
          </div>

          <div className="main-panel">
            <h2>Route Matrix Overview</h2>
          </div>
        </div>
      );
    }

    return (
      <div
        className={`dashboard-card slot-${slotKey} clickable`}
        onClick={() => handleModuleSelect("ScheduledMap")}
      >
        <div className="card-header">
          ••• APPOINTMENT LOCATION INDEX
        </div>

        <div className="preview-panel">
          {slotKey === "sidebar" ? (
            <>
              <span className="badge badge-highlight">
                Sidebar: Matrix Node
              </span>

              <p className="card-summary">
                Routing: {routeMatrixStatus}
              </p>
            </>
          ) : (
            <span className="badge">
              Footer ({slotKey}): Routing Stream [{routeMatrixStatus}]
            </span>
          )}
        </div>
      </div>
    );
  };

  const resolveModuleBySlot = (slotKey) => {
    switch (scheduledSlots[slotKey]) {
      case "ScheduledCalendar":
        return renderCalendar(slotKey);

      case "ScheduledJobCard":
        return renderJobRegistry(slotKey);

      case "ClientQueries":
        return renderClientQueries(slotKey);

      case "ScheduledMap":
        return renderRouteMatrix(slotKey);

      default:
        return null;
    }
  };

  return (
    <div className="dashboard-grid-4pane">
      <div className="grid-main">
        {resolveModuleBySlot("main")}
      </div>

      <div className="grid-sidebar">
        {resolveModuleBySlot("sidebar")}
      </div>

      <div className="grid-bottom-left">
        {resolveModuleBySlot("bottomLeft")}
      </div>

      <div className="grid-bottom-right">
        {resolveModuleBySlot("bottomRight")}
      </div>
    </div>
  );
}