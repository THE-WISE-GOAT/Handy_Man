// components/customer-dashboard/dash2board.jsx
import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCustomerDashboardData } from './useCustomerDashboardData'; // Maps to your postingsZlice
import './dash2board.css';

export default function Dash2Board({ viewSlug }) {
  const navigate = useNavigate();
  const {
    postingsSlots,
    swapPostingsSlots,
    biddingsStream,
    feedbackRating,
    pipelineStatus,
    pendingJobs,
    selectedJob,
    setSelectedJob,
    fetchPendingJobs
  } = useCustomerDashboardData();

  // ── INITIAL DATA FETCH ──
  useEffect(() => {
    fetchPendingJobs();
  }, [fetchPendingJobs]);

  // Route state synchronization layer
  useEffect(() => {
    if (!viewSlug) return;
    if (postingsSlots.main !== viewSlug) {
      const targetSlot = Object.keys(postingsSlots).find((key) => postingsSlots[key] === viewSlug);
      if (targetSlot) swapPostingsSlots(targetSlot);
    }
  }, [viewSlug, postingsSlots, swapPostingsSlots]);

  const handleModuleSelect = (targetSlug) => {
    navigate(`/customer/postings/${targetSlug}`);
  };

  // Simplified shared card container component
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
  // SUB-MODULE RENDERS (DETAIL VIEWS)
  // ====================================================

  const renderBiddingsEngine = (position) => (
    <Card slug="ActiveBiddingsEngine" title="COMPETITIVE MARKETPLACE METRICS" position={position}>
      {position === "main" ? (
        <div className="main-panel">
          <h2>ACTIVE BIDDINGS ENGINE</h2>
          {/* DYNAMIC TITLE INJECTION */}
          <h3 style={{ color: "#007bff" }}>
            Bids for job: {selectedJob ? selectedJob.title : "No Job Selected"}
          </h3>
          <p className="panel-desc">Active incoming competitive service offers and rate valuation streams.</p>
          <div className="bids-box">
            {biddingsStream.map(bid => (
              <div key={bid.id} className="bid-row">
                <span><strong>{bid.provider}</strong>: {bid.offer}</span>
                <span className="status-badge">{bid.status}</span>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="preview-panel">
          {position === "sidebar" ? (
            <>
              <span className="badge badge-highlight">Sidebar: Bids Incoming Feed Active</span>
              <p className="card-summary">Target: {selectedJob?.title || "N/A"}</p>
              <p className="card-summary">Pending Offers Count: {biddingsStream.length}</p>
            </>
          ) : (
            <span className="badge">Footer Slot: Bids for {selectedJob?.title || "N/A"}</span>
          )}
        </div>
      )}
    </Card>
  );

  const renderLiveMap = (position) => (
    <Card slug="GeospatialLiveMap" title="GEOSPATIAL LIVE MAP" position={position}>
      {position === "main" ? (
        <div className="main-panel">
          <h2>GEOSPATIAL ENGINE FULL DISPLAY</h2>
          {/* DYNAMIC COORDINATES INJECTION */}
          {selectedJob ? (
            <div className="coordinates-display">
              <p>Tracking coordinates for: <strong>{selectedJob.title}</strong></p>
              <p>Latitude: {selectedJob.latitude}</p>
              <p>Longitude: {selectedJob.longitude}</p>
            </div>
          ) : (
            <p>Awaiting job selection to display coordinates...</p>
          )}
        </div>
      ) : (
        <div className="preview-panel">
          {position === "sidebar" ? (
            <>
              <span className="badge badge-highlight">Sidebar: GPS Map Node Tracker</span>
              <p className="card-summary">
                Lat: {selectedJob?.latitude || "N/A"} | Lng: {selectedJob?.longitude || "N/A"}
              </p>
            </>
          ) : (
            <span className="badge">Footer Slot: Map Tracking Active</span>
          )}
        </div>
      )}
    </Card>
  );

  const renderReviewLogs = (position) => (
    <Card slug="RatingsReviewLogs" title="RATINGS & REVIEW LOGS" position={position}>
      {position === "main" ? (
        <div className="main-panel">
          <h2>VERIFIED FEEDBACK HISTORY LOGS</h2>
          {/* DYNAMIC TITLE INJECTION */}
          <h3 style={{ color: "#007bff" }}>
            Reviews of worker for job: {selectedJob ? selectedJob.title : "No Job Selected"}
          </h3>
        </div>
      ) : (
        <div className="preview-panel">
          {position === "sidebar" ? (
            <>
              <span className="badge badge-highlight">Sidebar: Feedback Monitoring</span>
              <p className="card-summary">Live Score Rating: {feedbackRating}</p>
              <p className="card-summary">For: {selectedJob?.title || "N/A"}</p>
            </>
          ) : (
            <span className="badge">Footer Slot: Reviews for {selectedJob?.title || "N/A"}</span>
          )}
        </div>
      )}
    </Card>
  );

  // ====================================================
  // MASTER SELECTOR VIEW
  // ====================================================

  const renderPostsDashboard = (position) => (
    <Card slug="ActivePostsDashboard" title="ACTIVE POSTS DASHBOARD" position={position}>
      {position === "main" ? (
        <div className="main-panel">
          <h2>ACTIVE POSTS PIPELINE NETWORK</h2>
          {/* MASTER SELECTOR LIST */}
          <div className="jobs-selector-list" style={{ marginTop: '20px' }}>
            {pendingJobs.length === 0 ? (
              <p>No pending jobs found.</p>
            ) : (
              pendingJobs.map(job => {
                const isActive = selectedJob && selectedJob.id === job.id;
                return (
                  <div 
                    key={job.id} 
                    onClick={(e) => {
                      e.stopPropagation(); // Prevents triggering the module swap click
                      setSelectedJob(job);
                    }}
                    style={{
                      border: isActive ? '2px solid #4CAF50' : '1px solid #555',
                      padding: '15px',
                      margin: '10px 0',
                      cursor: 'pointer',
                      backgroundColor: isActive ? '#e8f5e9' : 'transparent',
                      color: isActive ? '#000' : 'inherit',
                      borderRadius: '5px',
                      transition: 'all 0.2s ease-in-out'
                    }}
                  >
                    <strong style={{ display: 'block', fontSize: '1.2em' }}>{job.title}</strong>
                    <span style={{ fontSize: '0.9em', opacity: 0.8 }}>{job.description}</span>
                  </div>
                );
              })
            )}
          </div>
        </div>
      ) : (
        <div className="preview-panel">
          {position === "sidebar" ? (
            <>
              <span className="badge badge-highlight">Sidebar: Pipeline Stream</span>
              <p className="card-summary">Selected: {selectedJob?.title || "None"}</p>
              <p className="card-summary">Total Pending: {pendingJobs.length}</p>
            </>
          ) : (
            <span className="badge">Footer Slot: Active Job ({selectedJob?.title || "None"})</span>
          )}
        </div>
      )}
    </Card>
  );

  const resolveModuleBySlot = (slotKey) => {
    switch (postingsSlots[slotKey]) {
      case "ActiveBiddingsEngine": return renderBiddingsEngine(slotKey);
      case "GeospatialLiveMap":    return renderLiveMap(slotKey);
      case "ActivePostsDashboard": return renderPostsDashboard(slotKey);
      case "RatingsReviewLogs":    return renderReviewLogs(slotKey);
      default:                     return null;
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