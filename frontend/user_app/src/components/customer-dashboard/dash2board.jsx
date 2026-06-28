// components/customer-dashboard/dash2board.jsx
import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCustomerDashboardData } from './useCustomerDashboardData';
import './dash2board.css';

export default function Dash2Board({ viewSlug }) {
  const navigate = useNavigate();
  const {
    postingsSlots,
    swapPostingsSlots,
    biddingsStream,
    gpsCoordinates,
    pipelineStatus,
    feedbackRating
  } = useCustomerDashboardData();

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
  // SUB-MODULE RENDERS
  // ====================================================

  const renderBiddingsEngine = (position) => (
    <Card slug="ActiveBiddingsEngine" title="COMPETITIVE MARKETPLACE METRICS" position={position}>
      {position === "main" ? (
        <div className="main-panel">
          <h2>ACTIVE BIDDINGS ENGINE</h2>
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
              <p className="card-summary">Pending Offers Count: {biddingsStream.length}</p>
            </>
          ) : (
            <span className="badge">Footer Slot: {biddingsStream.length} Active Valuations</span>
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
          <p>Coordinates: {gpsCoordinates.lat}, {gpsCoordinates.lng}</p>
        </div>
      ) : (
        <div className="preview-panel">
          {position === "sidebar" ? (
            <>
              <span className="badge badge-highlight">Sidebar: GPS Map Node Tracker</span>
              <p className="card-summary">Lat: {gpsCoordinates.lat} | Lng: {gpsCoordinates.lng}</p>
            </>
          ) : (
            <span className="badge">Footer Slot: Map Tracking Active</span>
          )}
        </div>
      )}
    </Card>
  );

  const renderPostsDashboard = (position) => (
    <Card slug="ActivePostsDashboard" title="ACTIVE POSTS DASHBOARD" position={position}>
      {position === "main" ? (
        <div className="main-panel">
          <h2>ACTIVE POSTS PIPELINE NETWORK</h2>
        </div>
      ) : (
        <div className="preview-panel">
          {position === "sidebar" ? (
            <>
              <span className="badge badge-highlight">Sidebar: Pipeline Stream</span>
              <p className="card-summary">Status: {pipelineStatus}</p>
            </>
          ) : (
            <span className="badge">Footer Slot: Pipeline Backgrounded ({pipelineStatus})</span>
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
        </div>
      ) : (
        <div className="preview-panel">
          {position === "sidebar" ? (
            <>
              <span className="badge badge-highlight">Sidebar: Feedback Monitoring</span>
              <p className="card-summary">Live Score Rating: {feedbackRating}</p>
            </>
          ) : (
            <span className="badge">Footer Slot: Logs Idle — Score ({feedbackRating})</span>
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