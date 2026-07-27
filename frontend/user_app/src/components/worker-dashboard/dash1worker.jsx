// components/worker-dashboard/dash1worker.jsx
import React, { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useWorkerDashboardData } from "./useWorkerDashboardData";
import "./dash1worker.css";

export default function Dash1Worker({ viewSlug }) {
  const navigate = useNavigate();
  const wsConnected = useRef(false);

  const {
    workspaceSlots,
    swapWorkspaceSlots,
    mapStatus,
    bidsPipelineText,
    jobSpecsText,
    activeJob,
    isInterested,
    expressInterest,
    workerChatId,
    matchedJobs,
    fetchMatchedJobs,
    setActiveJob,
    connectToDispatch,
    disconnectFromDispatch,
  } = useWorkerDashboardData();

  useEffect(() => {
    fetchMatchedJobs();
  }, [fetchMatchedJobs]);

  useEffect(() => {
    if (workerChatId && !wsConnected.current) {
      const token = localStorage.getItem("handy_man_access_token");
      if (token) {
        connectToDispatch(workerChatId, token);
        wsConnected.current = true;
      }
    }

    return () => {
      if (wsConnected.current) {
        disconnectFromDispatch();
        wsConnected.current = false;
      }
    };
  }, [workerChatId, connectToDispatch, disconnectFromDispatch]);

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

          <div className="main-panel" style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
            <h2>Active Biddings Portal</h2>

            <p className="panel-desc">
              Manage active incoming offers and customer pricing requests.
            </p>

            {matchedJobs.length === 0 ? (
              <p style={{ opacity: 0.7, marginTop: '12px' }}>No matched jobs yet. New opportunities will appear here.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '12px' }}>
                {matchedJobs.map((job) => (
                  <div
                    key={job.job_id}
                    style={{
                      border: '1px solid #555',
                      borderRadius: '8px',
                      padding: '12px',
                      backgroundColor: '#1a1a1a',
                      cursor: 'pointer',
                    }}
                    onClick={() => {
                      setActiveJob(job);
                      swapWorkspaceSlots("bottom");
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <strong style={{ fontSize: '1em' }}>{job.title}</strong>
                      <span style={{ fontSize: '0.8em', color: '#4db8ff', border: '1px solid #555', padding: '2px 6px', borderRadius: '4px' }}>
                        Rank #{job.match_rank}
                      </span>
                    </div>
                    <p style={{ margin: '0 0 6px 0', fontSize: '0.85em', opacity: 0.8 }}>
                      {job.description?.slice(0, 120)}{job.description?.length > 120 ? '...' : ''}
                    </p>
                    <div style={{ display: 'flex', gap: '12px', fontSize: '0.8em' }}>
                      <span style={{ color: '#4CAF50' }}>Match: {Math.round(job.match_score)}%</span>
                      <span style={{ color: '#ff9800' }}>Interested: {job.interested_count || 0}</span>
                      <span style={{ color: '#aaa' }}>Status: {job.status}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
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
            {activeJob ? (
              <>
                <h2>{activeJob.title || "Untitled Job"}</h2>
                <p><strong>Job ID:</strong> {activeJob.booking_chat_id || activeJob.id || "N/A"}</p>
                <p className="panel-desc">{activeJob.description || activeJob.job_description || "No description available."}</p>
                <button
                  type="button"
                  onClick={() => expressInterest(activeJob.booking_chat_id || activeJob.id, workerChatId)}
                  style={{
                    marginTop: '16px',
                    padding: '10px 20px',
                    backgroundColor: isInterested ? '#4CAF50' : '#2196F3',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    fontWeight: 'bold',
                    fontSize: '14px'
                  }}
                >
                  {isInterested ? '✓ Interested' : "I'm Interested"}
                </button>
              </>
            ) : (
              <>
                <h2>Job Details Monitor</h2>

                <p className="panel-desc">
                  Full breakdown of client structural parameters and requirements.
                </p>
              </>
            )}
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