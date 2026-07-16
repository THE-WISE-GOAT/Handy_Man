import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCustomerDashboardData } from './useCustomerDashboardData';
import './dash2board.css';

// 1. IMPORT LEAFLET
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// 2. VITE-COMPATIBLE ICON IMPORTS
import iconRetinaUrl from 'leaflet/dist/images/marker-icon-2x.png';
import iconUrl from 'leaflet/dist/images/marker-icon.png';
import shadowUrl from 'leaflet/dist/images/marker-shadow.png';

// Fix for default Leaflet icon paths in React + Vite
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl,
  iconUrl,
  shadowUrl,
});

// Helper component to smoothly center the map when job coordinates change
const MapUpdater = ({ center }) => {
  const map = useMap();
  useEffect(() => {
    if (center && center[0] && center[1]) {
      map.setView(center, map.getZoom());
    }
  }, [center, map]);
  return null;
};

const Card = ({ slug, title, position, onSelect, children }) => {
  const isMain = position === "main";
  return (
    <div 
      className={`dashboard-card slot-${position} ${!isMain ? 'clickable' : ''}`}
      onClick={!isMain ? () => onSelect(slug) : undefined}
    >
      <div className="card-header">••• {title}</div>
      {children}
    </div>
  );
};

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
    fetchPendingJobs,
    
    // NOTE: Removed global matchedCount/interestedCount from here
    // as they are now mapped directly onto the job objects.

    // --- COMMENTED OUT MATCHING STATE & ACTIONS ---
    // matchedWorkers,
    // fetchMatchedWorkers, 
    selectedWorkerId,
    setSelectedWorkerId
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

  // ====================================================
  // SUB-MODULE RENDERS
  // ====================================================

  const renderBiddingsEngine = (position) => (
    <Card slug="ActiveBiddingsEngine" title="COMPETITIVE MARKETPLACE METRICS" position={position} onSelect={handleModuleSelect}>
      {position === "main" ? (
        <div className="main-panel">
          <h2>ACTIVE BIDDINGS ENGINE</h2>
          <h3 style={{ color: "#007bff" }}>
            Bids for job: {selectedJob ? selectedJob.title : "No Job Selected"}
          </h3>
          {selectedWorkerId && (
            <h4 style={{ color: "#ff5722", margin: "5px 0 15px 0" }}>
              Focusing Worker ID: {selectedWorkerId}
            </h4>
          )}
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
             {selectedWorkerId && <p className="card-summary" style={{color: "#ff5722"}}>Focus: Worker #{selectedWorkerId}</p>}
           </>
          ) : (
            <span className="badge">Footer Slot: Bids for {selectedJob?.title || "N/A"}</span>
          )}
        </div>
      )}
    </Card>
  );

  const renderLiveMap = (position) => {
    const centerPoint = selectedJob && selectedJob.latitude && selectedJob.longitude 
      ? [parseFloat(selectedJob.latitude), parseFloat(selectedJob.longitude)]
      : [27.7172, 85.3240];

    return (
      <Card slug="GeospatialLiveMap" title="GEOSPATIAL LIVE MAP" position={position} onSelect={handleModuleSelect}>
        {position === "main" ? (
          <div className="main-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <h2>GEOSPATIAL ENGINE FULL DISPLAY</h2>
            
            <div style={{ flex: 1, minHeight: '300px', borderRadius: '12px', overflow: 'hidden', marginTop: '10px' }}>
              <MapContainer 
                center={centerPoint} 
                zoom={13} 
                style={{ height: '100%', width: '100%' }}
              >
                <TileLayer
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                />
                
                <MapUpdater center={centerPoint} />

                {/* Job Location Marker */}
                {selectedJob && selectedJob.latitude && (
                  <Marker position={centerPoint}>
                    <Popup>
                      <strong>{selectedJob.title}</strong><br/>
                      Job Location
                    </Popup>
                  </Marker>
                )}
              </MapContainer>
            </div>
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
  };

  const renderReviewLogs = (position) => (
    <Card slug="RatingsReviewLogs" title="RATINGS & REVIEW LOGS" position={position} onSelect={handleModuleSelect}>
      {position === "main" ? (
        <div className="main-panel">
          <h2>VERIFIED FEEDBACK HISTORY LOGS</h2>
          <h3 style={{ color: "#007bff" }}>
            Reviews for job: {selectedJob ? selectedJob.title : "No Job Selected"}
          </h3>
          {selectedWorkerId && (
            <h4 style={{ color: "#ff5722", margin: "5px 0 15px 0" }}>
              Viewing records for Worker ID: {selectedWorkerId}
            </h4>
          )}
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

  const renderPostsDashboard = (position) => (
    <Card slug="ActivePostsDashboard" title="ACTIVE POSTS DASHBOARD" position={position} onSelect={handleModuleSelect}>
      
      {/* ADDED INLINE STYLE FOR BLINKING DOT */}
      <style>
        {`
          @keyframes blinkDot {
            0% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(1.2); }
            100% { opacity: 1; transform: scale(1); }
          }
          .status-indicator-dot {
            animation: blinkDot 1.5s infinite ease-in-out;
            width: 8px;
            height: 8px;
            background-color: #f44336; /* Red */
            border-radius: 50%;
            display: inline-block;
          }
        `}
      </style>

      {position === "main" ? (
        <div className="main-panel">
          <h2>ACTIVE POSTS PIPELINE NETWORK</h2>
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
                      e.stopPropagation(); 
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
                    {/* NEW: JOB-SPECIFIC WORKER & INTEREST METRICS ABOVE TITLE */}
                    <div style={{ 
                      display: 'flex', 
                      gap: '20px', 
                      marginBottom: '8px', 
                      fontSize: '0.85em', 
                      fontWeight: 'bold' 
                    }}>
                      
                      {/* Matched Professionals Indicator */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#555' }}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                          <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                        </svg>
                        {/* Pulling the count specific to this job from the mapped array */}
                        <span>{job.matchedCount || 0} matched professionals</span>
                      </div>

                      {/* Interested Workers Indicator */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#d32f2f' }}>
                        <span className="status-indicator-dot"></span>
                        {/* Pulling the count specific to this job from the mapped array */}
                        <span>{job.interestedCount || 0} interested</span>
                      </div>
                      
                    </div>

                    {/* Original Job Title & Description */}
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