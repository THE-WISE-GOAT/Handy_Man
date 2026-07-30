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
    activeJob,
    isInterested,
    expressInterest,
    workerChatId,
    matchedJobs,
    fetchMatchedJobs,
    setActiveJob,
  } = useWorkerDashboardData();

  useEffect(() => {
    fetchMatchedJobs();
  }, [fetchMatchedJobs]);

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
                      border: '1px solid var(--k-line)',
                      borderRadius: '8px',
                      padding: '12px',
                      backgroundColor: 'var(--k-raise)',
                      cursor: 'pointer',
                    }}
                    onClick={() => {
                      setActiveJob(job);
                      swapWorkspaceSlots("bottom");
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <strong style={{ fontSize: '1em' }}>{job.title}</strong>
                      <span style={{ fontSize: '0.8em', color: 'var(--k-orange-ink)', border: '1px solid rgba(255, 107, 26, 0.4)', padding: '2px 6px', borderRadius: '4px' }}>
                        Rank #{job.match_rank}
                      </span>
                    </div>
                    <p style={{ margin: '0 0 6px 0', fontSize: '0.85em', opacity: 0.8 }}>
                      {job.description?.slice(0, 120)}{job.description?.length > 120 ? '...' : ''}
                    </p>
                    <div style={{ display: 'flex', gap: '12px', fontSize: '0.8em', marginBottom: '8px' }}>
                      <span style={{ color: 'var(--k-orange-ink)', fontWeight: 600 }}>Match: {Math.round(job.match_score)}%</span>
                      <span style={{ color: 'var(--k-ink)' }}>Interested: {job.interested_count || 0}</span>
                      <span style={{ color: 'var(--k-ink-3)' }}>Status: {job.status}</span>
                    </div>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        expressInterest(job.job_id, workerChatId);
                      }}
                      style={{
                        padding: '6px 14px',
                        backgroundColor: job.is_interested ? '#FF6B1A' : 'transparent',
                        color: job.is_interested ? '#0D0D0D' : 'var(--k-orange-ink)',
                        border: job.is_interested ? '1px solid #FF6B1A' : '1px solid rgba(255, 107, 26, 0.5)',
                        borderRadius: '6px',
                        cursor: job.is_interested ? 'default' : 'pointer',
                        fontWeight: 600,
                        fontSize: '13px'
                      }}
                      disabled={job.is_interested}
                    >
                      {job.is_interested ? 'Interested ✓' : "I'm Interested"}
                    </button>
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
                  onClick={() => expressInterest(activeJob.job_id, workerChatId)}
                  style={{
                    marginTop: '16px',
                    padding: '10px 20px',
                    backgroundColor: activeJob.is_interested ? '#FF6B1A' : 'transparent',
                    color: activeJob.is_interested ? '#0D0D0D' : 'var(--k-orange-ink)',
                    border: activeJob.is_interested ? '1px solid #FF6B1A' : '1px solid rgba(255, 107, 26, 0.5)',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    fontWeight: 600,
                    fontSize: '14px'
                  }}
                >
                  {activeJob.is_interested ? '✓ Interested' : "I'm Interested"}
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