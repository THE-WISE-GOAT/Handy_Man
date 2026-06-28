// components/worker-dashboard/dash2worker.jsx
import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useWorkerDashboardData } from './useWorkerDashboardData';
import './dash2worker.css';

export default function Dash2Worker({ viewSlug }) {
  const navigate = useNavigate();
  const {
    scheduledSlots,
    swapScheduledSlots,
    calendarDescText,
    jobsRegistryStatus,
    clientQueryStatus,
    routeMatrixStatus
  } = useWorkerDashboardData();

  // Route state synchronization layer
  useEffect(() => {
    if (!viewSlug) return;
    if (scheduledSlots.main !== viewSlug) {
      const targetSlot = Object.keys(scheduledSlots).find((key) => scheduledSlots[key] === viewSlug);
      if (targetSlot) swapScheduledSlots(targetSlot);
    }
  }, [viewSlug, scheduledSlots, swapScheduledSlots]);

  const handleModuleSelect = (targetSlug) => {
    navigate(`/worker/scheduled/${targetSlug}`);
  };

  // Shared generic card framework for preview vs active stages
  const Card = ({ slug, title, position, children }) => {
    const isMain = position === "main";
    return (
      <div 
        className={`dashboard-card slot-${position} ${!isMain ? 'clickable' : ''}`}
        onClick={!isMain ? () => handleModuleSelect(slug) : undefined}
      >
        <div className="card-header">••• {title}</div>
        {children}
      </div>
    );
  };

  // ====================================================
  // SUB-MODULE RENDERS
  // ====================================================

  const renderCalendar = (position) => (
    <Card slug="ScheduledCalendar" title="SCHEDULE PLATFORM PLANNERS" position={position}>
      {position === "main" ? (
        <div className="main-panel">
          <h2>System Planner Calendar</h2>
          <p className="panel-desc">{calendarDescText}</p>
        </div>
      ) : (
        <div className="preview-panel">
          {position === "sidebar" ? (
            <>
              <span className="badge badge-highlight">Sidebar: Planner Context</span>
              <p className="card-summary">{calendarDescText}</p>
            </>
          ) : (
            <span className="badge">Footer ({position}): Calendar Monitor Live</span>
          )}
        </div>
      )}
    </Card>
  );

  const renderJobRegistry = (position) => (
    <Card slug="ScheduledJobCard" title="UPCOMING DEPLOYMENT NODES" position={position}>
      {position === "main" ? (
        <div className="main-panel">
          <h2>Scheduled Jobs Registry</h2>
        </div>
      ) : (
        <div className="preview-panel">
          {position === "sidebar" ? (
            <>
              <span className="badge badge-highlight">Sidebar: Job Matrix</span>
              <p className="card-summary">Status: {jobsRegistryStatus}</p>
            </>
          ) : (
            <span className="badge">Footer ({position}): Registry — {jobsRegistryStatus}</span>
          )}
        </div>
      )}
    </Card>
  );

  const renderClientQueries = (position) => (
    <Card slug="ClientQueries" title="ACTIVE MESSAGING CORRIDOR" position={position}>
      {position === "main" ? (
        <div className="main-panel">
          <h2>Client Communications Terminal</h2>
        </div>
      ) : (
        <div className="preview-panel">
          {position === "sidebar" ? (
            <>
              <span className="badge badge-highlight">Sidebar: Inbox Comms</span>
              <p className="card-summary">Queue: {clientQueryStatus}</p>
            </>
          ) : (
            <span className="badge">Footer ({position}): Comms Feed ({clientQueryStatus})</span>
          )}
        </div>
      )}
    </Card>
  );

  const renderRouteMatrix = (position) => (
    <Card slug="ScheduledMap" title="APPOINTMENT LOCATION INDEX" position={position}>
      {position === "main" ? (
        <div className="main-panel">
          <h2>Route Matrix Overview</h2>
        </div>
      ) : (
        <div className="preview-panel">
          {position === "sidebar" ? (
            <>
              <span className="badge badge-highlight">Sidebar: Matrix Node</span>
              <p className="card-summary">Routing: {routeMatrixStatus}</p>
            </>
          ) : (
            <span className="badge">Footer ({position}): Routing Stream [{routeMatrixStatus}]</span>
          )}
        </div>
      )}
    </Card>
  );

  const resolveModuleBySlot = (slotKey) => {
    switch (scheduledSlots[slotKey]) {
      case "ScheduledCalendar": return renderCalendar(slotKey);
      case "ScheduledJobCard":  return renderJobRegistry(slotKey);
      case "ClientQueries":     return renderClientQueries(slotKey);
      case "ScheduledMap":      return renderRouteMatrix(slotKey);
      default:                  return null;
    }
  };

  return (
    <div className="dashboard-grid-4pane">
      <div className="grid-main">{resolveModuleBySlot("main")}</div>
      <div className="grid-sidebar">{resolveModuleBySlot("sidebar")}</div>
      <div className="grid-bottom-left">{resolveModuleBySlot("bottomLeft")}</div>
      <div className="grid-bottom-right">{resolveModuleBySlot("bottomRight")}</div>
    </div>
  );
}