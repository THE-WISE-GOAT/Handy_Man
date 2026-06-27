// import React from "react";

// export default function Dash2board({ activeModuleId }) {
//   return (
//     <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
//       {activeModuleId === "biddings" && (
//         <div>
//           <p>Active incoming competitive service offers and rate valuation streams.</p>
//         </div>
//       )}
//       {activeModuleId === "map" && (
//         <div>
//           <p>Live map layout tracking active field technician routing and dispatch updates.</p>
//         </div>
//       )}
//       {activeModuleId === "ratings-review" && (
//         <div>
//           <p>Historical customer satisfaction indices, verification loops, and ratings logs.</p>
//         </div>
//       )}
//       {activeModuleId === "active-post-v2" && (
//         <div>
//           <p>Extended logging metrics tracking jobs currently deployed out to network nodes.</p>
//         </div>
//       )}
//     </div>
//   );
// }


// components/customer-dashboard/dash2board.jsx
import React from 'react';
import { useCustomerDashboardData } from './useCustomerDashboardData';
import './dash2board.css';

export default function Dash2Board() {
  // Pulling positions and content states from our global state pool
  const {
    postingsSlots,
    swapPostingsSlots,
    biddingsStream,
    gpsCoordinates,
    pipelineStatus,
    feedbackRating
  } = useCustomerDashboardData();

  // ====================================================
  // REUSABLE WIREFRAME LAYOUT WRAPPER COMPONENT
  // ====================================================
  // Optimization: Abstracting common card wrapper logic to keep code clean and optimal
  const CardWrapper = ({ slotName, title, position, children }) => {
    const isMain = position === "main";
    return (
      <div 
        className={`postings-card slot-${position} ${!isMain ? 'clickable-swap-target' : ''}`}
        onClick={!isMain ? () => swapPostingsSlots(slotName) : undefined}
      >
        <div className="postings-card-header">••• {title}</div>
        {children}
      </div>
    );
  };

  // ====================================================
  // SUB-MODULE RENDERING CONTROLLERS
  // ====================================================

  // MODULE 1: ACTIVE BIDDINGS ENGINE
  const renderBiddingsEngine = (position) => (
    <CardWrapper slotName={position} title="COMPETITIVE MARKETPLACE METRICS" position={position}>
      {position === "main" ? (
        <div className="active-view-panel">
          <h2>ACTIVE BIDDINGS ENGINE</h2>
          <p className="description-text">Active incoming competitive service offers and rate valuation streams.</p>
          <div className="bids-list-box">
            {biddingsStream.map(bid => (
              <div key={bid.id} className="bid-row-item">
                <span><strong>{bid.provider}</strong>: {bid.offer}</span>
                <span className="badge-status">{bid.status}</span>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="sleeping-preview-box">
          <span className="pill-outline">Bids Incoming Feed Active</span>
        </div>
      )}
    </CardWrapper>
  );

  // MODULE 2: GEOSPATIAL LIVE MAP
  const renderLiveMap = (position) => (
    <CardWrapper slotName={position} title="GEOSPATIAL LIVE MAP" position={position}>
      {position === "main" ? (
        <div className="active-view-panel">
          <h2>GEOSPATIAL ENGINE FULL DISPLAY</h2>
          <p>Coordinates: {gpsCoordinates.lat}, {gpsCoordinates.lng}</p>
        </div>
      ) : (
        <div className="sleeping-preview-box">
          <span className="pill-outline">GPS Coordinates — Tracking Active Feed</span>
        </div>
      )}
    </CardWrapper>
  );

  // MODULE 3: ACTIVE POSTS DASHBOARD
  const renderPostsDashboard = (position) => (
    <CardWrapper slotName={position} title="ACTIVE POSTS DASHBOARD" position={position}>
      {position === "main" ? (
        <div className="active-view-panel">
          <h2>ACTIVE POSTS PIPELINE NETWORK</h2>
        </div>
      ) : (
        <div className="sleeping-preview-box">
          <span className="pill-outline">{pipelineStatus}</span>
        </div>
      )}
    </CardWrapper>
  );

  // MODULE 4: RATINGS & REVIEW LOGS
  const renderReviewLogs = (position) => (
    <CardWrapper slotName={position} title="RATINGS & REVIEW LOGS" position={position}>
      {position === "main" ? (
        <div className="active-view-panel">
          <h2>VERIFIED FEEDBACK HISTORY LOGS</h2>
        </div>
      ) : (
        <div className="sleeping-preview-box">
          <span className="pill-outline">{feedbackRating}</span>
        </div>
      )}
    </CardWrapper>
  );

  // ====================================================
  // ROUTING ASSIGNMENT ENGINE
  // ====================================================
  const resolveModuleBySlot = (slotKey) => {
    const targetModuleName = postingsSlots[slotKey];
    switch (targetModuleName) {
      case "ActiveBiddingsEngine": return renderBiddingsEngine(slotKey);
      case "GeospatialLiveMap":    return renderLiveMap(slotKey);
      case "ActivePostsDashboard": return renderPostsDashboard(slotKey);
      case "RatingsReviewLogs":    return renderReviewLogs(slotKey);
      default: return null;
    }
  };

  // ====================================================
  // MULTI-PANE STRUCTURAL CANVAS GRID
  // ====================================================
  return (
    <div className="postings-dashboard-canvas-grid">
      <div className="grid-area-main">{resolveModuleBySlot("main")}</div>
      <div className="grid-area-sidebar">{resolveModuleBySlot("sidebar")}</div>
      <div className="grid-area-bottom-left">{resolveModuleBySlot("bottomLeft")}</div>
      <div className="grid-area-bottom-right">{resolveModuleBySlot("bottomRight")}</div>
    </div>
  );
}