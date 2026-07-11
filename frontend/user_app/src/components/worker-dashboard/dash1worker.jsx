// components/worker-dashboard/dash1worker.jsx
import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useWorkerDashboardData } from "./useWorkerDashboardData";
import "./dash1worker.css";

export default function Dash1Worker({ viewSlug }) {
  const navigate = useNavigate();

  const {
    workspaceSlots,
    swapWorkspaceSlots,
    mapStatus,
    bidsPipelineText,
    jobSpecsText,
    connectToDispatch,
  } = useWorkerDashboardData();

  // Route state synchronization layer
  useEffect(() => {
    if (!viewSlug) return;

    if (workspaceSlots.main !== viewSlug) {
      const targetSlot = Object.keys(workspaceSlots).find(
        (key) => workspaceSlots[key] === viewSlug
      );

      if (targetSlot) {
        swapWorkspaceSlots(targetSlot);
      }
    }
  }, [viewSlug, workspaceSlots, swapWorkspaceSlots]);

  const handleModuleSelect = (targetSlug) => {
    navigate(`/worker/workspace/${targetSlug}`);
  };

  useEffect(() => {
    connectToDispatch();
  }, [connectToDispatch]);

  // ====================================================
  // SUB-MODULE RENDERS
  // ====================================================

  const renderRouteMap = (slotKey) => {
    if (slotKey === "main") {
      return (
        <div className="dashboard-card slot-main">
          <div className="card-header">
            ••• REALTIME FIELD DISPATCH MAP
          </div>

          <div className="main-panel">
            <h2>Job Route Mapping</h2>

            <div className="map-mock">
              <span className="status-dot"></span>
              <span className="status-text">{mapStatus}</span>
            </div>
          </div>
        </div>
      );
    }

    return (
      <div
        className={`dashboard-card slot-${slotKey} clickable`}
        onClick={() => handleModuleSelect("WorkspaceMap")}
      >
        <div className="card-header">
          ••• REALTIME FIELD DISPATCH MAP
        </div>

        <div className="preview-panel">
          {slotKey === "sidebar" ? (
            <>
              <span className="badge badge-highlight">
                Sidebar: Live Telemetry
              </span>

              <p className="card-summary">
                Status: {mapStatus}
              </p>
            </>
          ) : (
            <span className="badge">
              Bottom: Map Feed Tracking Active ({mapStatus})
            </span>
          )}
        </div>
      </div>
    );
  };

  const renderBiddingsPortal = (slotKey) => {
    if (slotKey === "main") {
      return (
        <div className="dashboard-card slot-main">
          <div className="card-header">
            ••• COMPETITIVE MARKETPLACE METRICS
          </div>

          <div className="main-panel">
            <h2>Active Biddings Portal</h2>

            <p className="panel-desc">
              Manage active incoming offers and customer pricing requests.
            </p>
          </div>
        </div>
      );
    }

    return (
      <div
        className={`dashboard-card slot-${slotKey} clickable`}
        onClick={() => handleModuleSelect("WorkspaceBids")}
      >
        <div className="card-header">
          ••• COMPETITIVE MARKETPLACE METRICS
        </div>

        <div className="preview-panel">
          {slotKey === "sidebar" ? (
            <>
              <span className="badge badge-highlight">
                Sidebar: Pipeline Tracker
              </span>

              <p className="card-summary">
                {bidsPipelineText}
              </p>
            </>
          ) : (
            <span className="badge">
              Bottom: Bids Pipeline Stream [{bidsPipelineText}]
            </span>
          )}
        </div>
      </div>
    );
  };

  const renderJobDetails = (slotKey) => {
    if (slotKey === "main") {
      return (
        <div className="dashboard-card slot-main">
          <div className="card-header">
            ••• DEPLOYED ASSIGNMENT SPECIFICATIONS
          </div>

          <div className="main-panel">
            <h2>Job Details Monitor</h2>

            <p className="panel-desc">
              Full breakdown of client structural parameters and requirements.
            </p>
          </div>
        </div>
      );
    }

    return (
      <div
        className={`dashboard-card slot-${slotKey} clickable`}
        onClick={() => handleModuleSelect("WorkspaceJobDetails")}
      >
        <div className="card-header">
          ••• DEPLOYED ASSIGNMENT SPECIFICATIONS
        </div>

        <div className="preview-panel">
          {slotKey === "sidebar" ? (
            <>
              <span className="badge badge-highlight">
                Sidebar: Requirements Desk
              </span>

              <p className="card-summary">
                {jobSpecsText}
              </p>
            </>
          ) : (
            <span className="badge">
              Bottom: Specs Monitor Active ({jobSpecsText})
            </span>
          )}
        </div>
      </div>
    );
  };

  const resolveModuleBySlot = (slotKey) => {
    switch (workspaceSlots[slotKey]) {
      case "WorkspaceMap":
        return renderRouteMap(slotKey);

      case "WorkspaceBids":
        return renderBiddingsPortal(slotKey);

      case "WorkspaceJobDetails":
        return renderJobDetails(slotKey);

      default:
        return null;
    }
  };

  return (
    <div className="dashboard-grid">
      <div className="grid-main">
        {resolveModuleBySlot("main")}
      </div>

      <div className="grid-bottom">
        {resolveModuleBySlot("bottom")}
      </div>

      <div className="grid-sidebar">
        {resolveModuleBySlot("sidebar")}
      </div>
    </div>
  );
}