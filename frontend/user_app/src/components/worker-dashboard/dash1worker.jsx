// components/worker-dashboard/dash1worker.jsx
import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useWorkerDashboardData } from './useWorkerDashboardData';
import './dash1worker.css';

export default function Dash1Worker({ viewSlug }) {
  const navigate = useNavigate();
  const {
    workspaceSlots,
    swapWorkspaceSlots,
    mapStatus,
    bidsPipelineText,
    jobSpecsText,
    connectToDispatch
  } = useWorkerDashboardData();

  // Route state synchronization layer
  useEffect(() => {
    if (!viewSlug) return;
    if (workspaceSlots.main !== viewSlug) {
      const targetSlot = Object.keys(workspaceSlots).find((key) => workspaceSlots[key] === viewSlug);
      if (targetSlot) swapWorkspaceSlots(targetSlot);
    }
  }, [viewSlug, workspaceSlots, swapWorkspaceSlots]);

  const handleModuleSelect = (targetSlug) => {
    navigate(`/worker/workspace/${targetSlug}`);
  };

  useEffect(()=>{
      connectToDispatch();
  }, [])

  // Shared card component for previewing or main states
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

  const renderRouteMap = (position) => (
    <Card slug="WorkspaceMap" title="REALTIME FIELD DISPATCH MAP" position={position}>
      {position === "main" ? (
        <div className="main-panel">
          <h2>Job Route Mapping</h2>
          <div className="map-mock">
            <span className="status-dot"></span>
            <span className="status-text">{mapStatus}</span>
          </div>
        </div>
      ) : (
        <div className="preview-panel">
          {position === "sidebar" ? (
            <>
              <span className="badge badge-highlight">Sidebar: Live Telemetry</span>
              <p className="card-summary">Status: {mapStatus}</p>
            </>
          ) : (
            <span className="badge">Bottom: Map Feed Tracking Active ({mapStatus})</span>
          )}
        </div>
      )}
    </Card>
  );

  const renderBiddingsPortal = (position) => (
    <Card slug="WorkspaceBids" title="COMPETITIVE MARKETPLACE METRICS" position={position}>
      {position === "main" ? (
        <div className="main-panel">
          <h2>Active Biddings Portal</h2>
          <p className="panel-desc">Manage active incoming offers and customer pricing requests.</p>
        </div>
      ) : (
        <div className="preview-panel">
          {position === "sidebar" ? (
            <>
              <span className="badge badge-highlight">Sidebar: Pipeline Tracker</span>
              <p className="card-summary">{bidsPipelineText}</p>
            </>
          ) : (
            <span className="badge">Bottom: Bids Pipeline Stream [{bidsPipelineText}]</span>
          )}
        </div>
      )}
    </Card>
  );

  const renderJobDetails = (position) => (
    <Card slug="WorkspaceJobDetails" title="DEPLOYED ASSIGNMENT SPECIFICATIONS" position={position}>
      {position === "main" ? (
        <div className="main-panel">
          <h2>Job Details Monitor</h2>
          <p className="panel-desc">Full breakdown of client structural parameters and requirements.</p>
        </div>
      ) : (
        <div className="preview-panel">
          {position === "sidebar" ? (
            <>
              <span className="badge badge-highlight">Sidebar: Requirements Desk</span>
              <p className="card-summary">{jobSpecsText}</p>
            </>
          ) : (
            <span className="badge">Bottom: Specs Monitor Active ({jobSpecsText})</span>
          )}
        </div>
      )}
    </Card>
  );

  const resolveModuleBySlot = (slotKey) => {
    switch (workspaceSlots[slotKey]) {
      case "WorkspaceMap":        return renderRouteMap(slotKey);
      case "WorkspaceBids":       return renderBiddingsPortal(slotKey);
      case "WorkspaceJobDetails": return renderJobDetails(slotKey);
      default:                    return null;
    }
  };

  return (
    <div className="dashboard-grid">
      <div className="grid-main">{resolveModuleBySlot("main")}</div>
      <div className="grid-bottom">{resolveModuleBySlot("bottom")}</div>
      <div className="grid-sidebar">{resolveModuleBySlot("sidebar")}</div>
    </div>
  );
}