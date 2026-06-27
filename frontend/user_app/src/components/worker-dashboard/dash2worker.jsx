// components/worker-dashboard/dash2worker.jsx
import React from 'react';
import { useWorkerDashboardData } from './useWorkerDashboardData';
import './dash2worker.css';

export default function Dash2Worker() {
  const {
    scheduledSlots,
    swapScheduledSlots,
    calendarDescText,
    jobsRegistryStatus,
    clientQueryStatus,
    routeMatrixStatus
  } = useWorkerDashboardData();

  // ====================================================
  // SUB-MODULE 1: SYSTEM PLANNER CALENDAR
  // ====================================================
  const renderCalendar = (position) => {
    if (position === "main") {
      return (
        <div className="worker-section-card view-main">
          <div className="worker-card-header">SCHEDULE PLATFORM PLANNERS</div>
          <h2>System Planner Calendar</h2>
          <p className="worker-panel-desc">{calendarDescText}</p>
        </div>
      );
    }

    return (
      <div className={`worker-section-card view-${position} worker-clickable-node`} onClick={() => swapScheduledSlots(position)}>
        <div className="worker-card-header">SCHEDULE PLATFORM PLANNERS</div>
        <div className="worker-sleeping-box">
          <span className="worker-pill-outline">Calendar Open</span>
        </div>
      </div>
    );
  };

  // ====================================================
  // SUB-MODULE 2: SCHEDULED JOBS REGISTRY
  // ====================================================
  const renderJobRegistry = (position) => {
    if (position === "main") {
      return (
        <div className="worker-section-card view-main">
          <div className="worker-card-header">UPCOMING DEPLOYMENT NODES</div>
          <h2>Scheduled Jobs Registry</h2>
        </div>
      );
    }

    return (
      <div className={`worker-section-card view-${position} worker-clickable-node`} onClick={() => swapScheduledSlots(position)}>
        <div className="worker-card-header">UPCOMING DEPLOYMENT NODES</div>
        <div className="worker-sleeping-box">
          <span className="worker-pill-outline">{jobsRegistryStatus}</span>
        </div>
      </div>
    );
  };

  // ====================================================
  // SUB-MODULE 3: CLIENT COMMUNICATIONS TERMINAL
  // ====================================================
  const renderClientQueries = (position) => {
    if (position === "main") {
      return (
        <div className="worker-section-card view-main">
          <div className="worker-card-header">ACTIVE MESSAGING CORRIDOR</div>
          <h2>Client Communications Terminal</h2>
        </div>
      );
    }

    return (
      <div className={`worker-section-card view-${position} worker-clickable-node`} onClick={() => swapScheduledSlots(position)}>
        <div className="worker-card-header">ACTIVE MESSAGING CORRIDOR</div>
        <div className="worker-sleeping-box">
          <span className="worker-pill-outline">{clientQueryStatus}</span>
        </div>
      </div>
    );
  };

  // ====================================================
  // SUB-MODULE 4: ROUTE MATRIX OVERVIEW
  // ====================================================
  const renderRouteMatrix = (position) => {
    if (position === "main") {
      return (
        <div className="worker-section-card view-main">
          <div className="worker-card-header">APPOINTMENT LOCATION INDEX</div>
          <h2>Route Matrix Overview</h2>
        </div>
      );
    }

    return (
      <div className={`worker-section-card view-${position} worker-clickable-node`} onClick={() => swapScheduledSlots(position)}>
        <div className="worker-card-header">APPOINTMENT LOCATION INDEX</div>
        <div className="worker-sleeping-box">
          <span className="worker-pill-outline">{routeMatrixStatus}</span>
        </div>
      </div>
    );
  };

  // ====================================================
  // TRANSLATION DISPATCHER
  // ====================================================
  const resolveModuleBySlot = (slotKey) => {
    const moduleName = scheduledSlots[slotKey];
    switch (moduleName) {
      case "ScheduledCalendar": return renderCalendar(slotKey);
      case "ScheduledJobCard":  return renderJobRegistry(slotKey);
      case "ClientQueries":     return renderClientQueries(slotKey);
      case "ScheduledMap":      return renderRouteMatrix(slotKey);
      default:                  return null;
    }
  };

  // ====================================================
  // 4-PANEL LAYOUT ARCHITECTURE CANVAS GRID
  // ====================================================
  return (
    <div className="worker-scheduled-canvas-grid">
      <div className="grid-area-main">{resolveModuleBySlot("main")}</div>
      <div className="grid-area-sidebar">{resolveModuleBySlot("sidebar")}</div>
      <div className="grid-area-bottom-left">{resolveModuleBySlot("bottomLeft")}</div>
      <div className="grid-area-bottom-right">{resolveModuleBySlot("bottomRight")}</div>
    </div>
  );
}