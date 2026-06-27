// components/worker-dashboard/dash1worker.jsx
import React from 'react';
import { useWorkerDashboardData } from './useWorkerDashboardData';
import './dash1worker.css';

export default function Dash1Worker() {
  const {
    workspaceSlots,
    swapWorkspaceSlots,
    mapStatus,
    bidsPipelineText,
    jobSpecsText
  } = useWorkerDashboardData();

  // ====================================================
  // SUB-MODULE 1: JOB ROUTE MAPPING
  // ====================================================
  const renderRouteMap = (position) => {
    if (position === "main") {
      return (
        <div className="worker-section-card view-main">
          <div className="worker-card-header">REALTIME FIELD DISPATCH MAP</div>
          <h2>Job Route Mapping</h2>
          <div className="worker-map-canvas-mock">
            <span className="live-status-dot"></span>
            <span className="live-status-text">{mapStatus}</span>
          </div>
        </div>
      );
    }

    return (
      <div className={`worker-section-card view-${position} worker-clickable-node`} onClick={() => swapWorkspaceSlots(position)}>
        <div className="worker-card-header">REALTIME FIELD DISPATCH MAP</div>
        <div className="worker-sleeping-box">
          <span className="worker-pill-outline">Map Feed Active</span>
        </div>
      </div>
    );
  };

  // ====================================================
  // SUB-MODULE 2: ACTIVE BIDDINGS PORTAL
  // ====================================================
  const renderBiddingsPortal = (position) => {
    if (position === "main") {
      return (
        <div className="worker-section-card view-main">
          <div className="worker-card-header">COMPETITIVE MARKETPLACE METRICS</div>
          <h2>Active Biddings Portal</h2>
          <p className="worker-panel-desc">Manage active incoming offers and customer pricing requests.</p>
        </div>
      );
    }

    return (
      <div className={`worker-section-card view-${position} worker-clickable-node`} onClick={() => swapWorkspaceSlots(position)}>
        <div className="worker-card-header">COMPETITIVE MARKETPLACE METRICS</div>
        <div className="worker-sleeping-box">
          <span className="worker-pill-outline">{bidsPipelineText}</span>
        </div>
      </div>
    );
  };

  // ====================================================
  // SUB-MODULE 3: JOB DETAILS MONITOR
  // ====================================================
  const renderJobDetails = (position) => {
    if (position === "main") {
      return (
        <div className="worker-section-card view-main">
          <div className="worker-card-header">DEPLOYED ASSIGNMENT SPECIFICATIONS</div>
          <h2>Job Details Monitor</h2>
          <p className="worker-panel-desc">Full breakdown of client structural parameters and requirements.</p>
        </div>
      );
    }

    return (
      <div className={`worker-section-card view-${position} worker-clickable-node`} onClick={() => swapWorkspaceSlots(position)}>
        <div className="worker-card-header">DEPLOYED ASSIGNMENT SPECIFICATIONS</div>
        <div className="worker-sleeping-box">
          <span className="worker-pill-outline">{jobSpecsText}</span>
        </div>
      </div>
    );
  };

  // ====================================================
  // TRANSLATION DISPATCHER
  // ====================================================
  const resolveModuleBySlot = (slotKey) => {
    const moduleName = workspaceSlots[slotKey];
    switch (moduleName) {
      case "WorkspaceMap":        return renderRouteMap(slotKey);
      case "WorkspaceBids":       return renderBiddingsPortal(slotKey);
      case "WorkspaceJobDetails": return renderJobDetails(slotKey);
      default:                    return null;
    }
  };

  // ====================================================
  // PHYSICAL WORKER WIREFRAME GRID LAYOUT
  // ====================================================
  return (
    <div className="worker-workspace-wireframe-grid">
      <div className="worker-slot-main">{resolveModuleBySlot("main")}</div>
      <div className="worker-slot-sidebar">{resolveModuleBySlot("sidebar")}</div>
      <div className="worker-slot-bottom">{resolveModuleBySlot("bottom")}</div>
    </div>
  );
}