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

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl,
  iconUrl,
  shadowUrl,
});

// --- CUSTOM SVG WORKER ICONS ---
const personSvg = `
  <svg viewBox="0 0 24 24" fill="currentColor" width="30px" height="30px">
    <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
  </svg>
`;

const staticWorkerIcon = L.divIcon({
  className: 'custom-worker-icon',
  html: `<div style="color: #1F1F1F; display: flex; justify-content: center; align-items: center; filter: drop-shadow(0px 2px 2px rgba(0,0,0,0.5));">${personSvg}</div>`,
  iconSize: [30, 30],
  iconAnchor: [15, 15],
  popupAnchor: [0, -15]
});

const blinkingWorkerIcon = L.divIcon({
  className: 'custom-worker-icon blinking-red-icon',
  html: `<div style="display: flex; justify-content: center; align-items: center;">${personSvg}</div>`,
  iconSize: [30, 30],
  iconAnchor: [15, 15],
  popupAnchor: [0, -15]
});

const goldenWorkerIcon = L.divIcon({
  className: 'custom-worker-icon golden-worker-icon',
  html: `<div style="color: #FF6B1A; display: flex; justify-content: center; align-items: center; filter: drop-shadow(0px 2px 2px rgba(0,0,0,0.5));">${personSvg}</div>`,
  iconSize: [30, 30],
  iconAnchor: [15, 15],
  popupAnchor: [0, -15]
});


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
      <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        {children}
      </div>
    </div>
  );
};

export default function Dash2Board({ viewSlug }) {
  const navigate = useNavigate();
  const workerCardRefs = React.useRef({});
  
  const {
    postingsSlots,
    swapPostingsSlots,
    biddingsStream,
    pendingJobs,
    selectedJob,
    setSelectedJob,
    fetchPendingJobs,
    
    matchedWorkersMap,
    workerLocations,          
    toggleWorkerInterest,     

    selectedWorkerId,
    setSelectedWorkerId
  } = useCustomerDashboardData();

  useEffect(() => {
    fetchPendingJobs();
  }, [fetchPendingJobs]);

  useEffect(() => {
    const handleFocus = () => { fetchPendingJobs(); };
    window.addEventListener('focus', handleFocus);
    return () => window.removeEventListener('focus', handleFocus);
  }, [fetchPendingJobs]);

  useEffect(() => {
    if (selectedWorkerId && workerCardRefs.current[selectedWorkerId]) {
      workerCardRefs.current[selectedWorkerId].scrollIntoView({
        behavior: 'smooth',
        block: 'center'
      });
    }
  }, [selectedWorkerId]);

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

  const renderBiddingsEngine = (position) => (
    <Card slug="ActiveBiddingsEngine" title="COMPETITIVE MARKETPLACE METRICS" position={position} onSelect={handleModuleSelect}>
      {position === "main" ? (
        <div className="main-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <h2 style={{ flexShrink: 0 }}>ACTIVE BIDDINGS ENGINE</h2>
          <h3 style={{ color: "var(--k-ink-3)", flexShrink: 0 }}>
            Bids for job: {selectedJob ? selectedJob.title : "No Job Selected"}
          </h3>
          <div className="bids-box" style={{ flex: 1, overflowY: 'auto', minHeight: 0, marginTop: '10px' }}>
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

  const renderLiveMap = (position) => {
    // 🛠️ ARCHITECTURAL FIX: Consumes seamlessly flattened store coordinates safely
    const centerPoint = selectedJob && selectedJob.latitude && selectedJob.longitude 
      ? [parseFloat(selectedJob.latitude), parseFloat(selectedJob.longitude)]
      : [27.7172, 85.3240];

    const currentWorkers = selectedJob && matchedWorkersMap[selectedJob.id] 
      ? matchedWorkersMap[selectedJob.id] 
      : [];

    return (
      <Card slug="GeospatialLiveMap" title="GEOSPATIAL LIVE MAP" position={position} onSelect={handleModuleSelect}>
        <style>
          {`
            @keyframes blinkRedIcon {
              0% { color: #E5484D; transform: scale(1); filter: drop-shadow(0 0 2px rgba(229,72,77,0.6)); }
              50% { color: #FF8A8E; transform: scale(1.3); filter: drop-shadow(0 0 10px rgba(229,72,77,1)); }
              100% { color: #E5484D; transform: scale(1); filter: drop-shadow(0 0 2px rgba(229,72,77,0.6)); }
            }
            .blinking-red-icon div {
              animation: blinkRedIcon 1.2s infinite ease-in-out;
            }
            @keyframes goldGlow {
              0% { filter: drop-shadow(0 0 2px rgba(255, 107, 26, 0.6)); }
              50% { filter: drop-shadow(0 0 10px rgba(255, 107, 26, 1)); }
              100% { filter: drop-shadow(0 0 2px rgba(255, 107, 26, 0.6)); }
            }
            .golden-worker-icon div {
              animation: goldGlow 1.5s infinite ease-in-out;
            }
          `}
        </style>

        {position === "main" ? (
          <div className="main-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            <h2 style={{ flexShrink: 0 }}>GEOSPATIAL ENGINE FULL DISPLAY</h2>
            <div style={{ flex: 1, minHeight: 0, borderRadius: '12px', overflow: 'hidden', marginTop: '10px' }}>
              <MapContainer center={centerPoint} zoom={13} style={{ height: '100%', width: '100%' }}>
                <TileLayer
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                />
                <MapUpdater center={centerPoint} />
                
                {selectedJob && selectedJob.latitude && (
                  <Marker position={centerPoint}>
                    <Popup><strong>{selectedJob.title}</strong><br/>Job Location</Popup>
                  </Marker>
                )}

                {/* 2. Worker Location Markers */}
                 {currentWorkers.map((worker, index) => {
                   const locInfo = workerLocations[worker.worker_chat_id];
                   if (!locInfo || !locInfo.latitude || !locInfo.longitude) return null;
                   
                   const workerPos = [locInfo.latitude, locInfo.longitude];
                   const rank = index + 1;
                   const isTopThree = rank <= 3;
                   const isInterested = worker.is_interested || locInfo.is_interested;
                   const iconToUse = isTopThree ? goldenWorkerIcon : (isInterested ? blinkingWorkerIcon : staticWorkerIcon);

                  return (
                    <Marker 
                      key={`map-worker-${worker.worker_chat_id}`} 
                      position={workerPos} 
                      icon={iconToUse}
                      eventHandlers={{ click: () => setSelectedWorkerId(worker.worker_chat_id) }}
                    >
                      <Popup>
                        <div style={{ textAlign: 'center' }}>
                          <strong>{worker.username}</strong><br/>
                          {isTopThree ? `🏆 Rank #${rank} Match` : `Rank #${rank}`}<br/>
                          Match Score: {worker.match_score}%<br/>
                          <button 
                            onClick={() => toggleWorkerInterest(worker.worker_chat_id)}
                            style={{
                              marginTop: '8px',
                              padding: '4px 8px',
                              backgroundColor: '#FF6B1A',
                              color: '#0D0D0D',
                              border: 'none',
                              borderRadius: '4px',
                              cursor: 'pointer'
                            }}
                          >
                            Toggle Interest (Test)
                          </button>
                        </div>
                      </Popup>
                    </Marker>
                  );
                })}
              </MapContainer>
            </div>
          </div>
        ) : (
          <div className="preview-panel">
            {position === "sidebar" ? (
              <>
                <span className="badge badge-highlight">Sidebar: GPS Map Node Tracker</span>
                <p className="card-summary">Lat: {selectedJob?.latitude || "N/A"} | Lng: {selectedJob?.longitude || "N/A"}</p>
                <p className="card-summary">Workers Rendered: {currentWorkers.length}</p>
              </>
            ) : (
              <span className="badge">Footer Slot: Map Tracking Active</span>
            )}
          </div>
        )}
      </Card>
    );
  };

  const renderReviewLogs = (position) => {
    const currentWorkers = selectedJob && matchedWorkersMap[selectedJob.id] 
      ? matchedWorkersMap[selectedJob.id] 
      : [];

    return (
      <Card slug="RatingsReviewLogs" title="MATCHED PROFESSIONALS LOGS" position={position} onSelect={handleModuleSelect}>
        {position === "main" ? (
          <div className="main-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            <h2 style={{ flexShrink: 0 }}>QUALIFIED WORKER NETWORK</h2>
            
            <h3 style={{ color: "var(--text-primary)", flexShrink: 0, display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span>Matched Profiles For: {selectedJob ? selectedJob.title : "No Job Selected"}</span>
              
              {selectedJob?.matchCategory && (
                <span style={{
                  fontSize: '0.65em',
                  backgroundColor: 'var(--k-wash)',
                  color: selectedJob.matchedByCategory ? 'var(--k-orange-ink)' : 'var(--k-ink-3)',
                  padding: '4px 8px',
                  borderRadius: '4px',
                  border: `1px solid ${selectedJob.matchedByCategory ? 'rgba(255, 107, 26, 0.5)' : 'var(--k-border-strong)'}`
                }}>
                  {selectedJob.matchedByCategory 
                    ? `Category Match: ${selectedJob.matchCategory}` 
                    : `Semantic Radius Fallback`}
                </span>
              )}
            </h3>

            <div style={{ 
              flex: 1, 
              overflowY: 'scroll',
              maxHeight: '23vw',
              minHeight: 0, 
              marginTop: '15px', 
              paddingRight: '10px', 
              display: 'flex', 
              flexDirection: 'column', 
              gap: '12px' 
            }}>
              {currentWorkers.length === 0 ? (
                <p style={{ opacity: 0.7 }}>No professionals matched yet or scanning network...</p>
              ) : (
                currentWorkers.map((worker, index) => {
                  const isSelected = selectedWorkerId && worker.worker_chat_id === selectedWorkerId;
                  const rank = index + 1;
                  return (
                    <div 
                      key={worker.worker_chat_id} 
                      ref={el => workerCardRefs.current[worker.worker_chat_id] = el}
                      style={{
                        border: isSelected ? '2px solid #FF6B1A' : '1px solid var(--k-line)',
                        borderRadius: '8px',
                        padding: '15px',
                        backgroundColor: isSelected ? 'var(--k-wash)' : 'var(--k-raise)',
                        boxShadow: isSelected ? '0 0 0 4px rgba(255, 107, 26, 0.12)' : '0 2px 8px rgba(0, 0, 0, 0.3)',
                        transform: isSelected ? 'scale(1.02)' : 'none',
                        transition: 'all 0.2s ease-in-out'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', alignItems: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <strong style={{ fontSize: '1.1em', color: 'var(--k-ink)' }}>{worker.username}</strong>
                          {isSelected && (
                            <span style={{
                              backgroundColor: '#FF6B1A',
                              color: '#0D0D0D',
                              padding: '2px 8px',
                              borderRadius: '4px',
                              fontWeight: 700,
                              fontSize: '0.75em'
                            }}>
                              🏆 Rank #{rank}
                            </span>
                          )}
                          {worker.is_interested && (
                            <span style={{
                              backgroundColor: '#28a745',
                              color: '#fff',
                              padding: '2px 8px',
                              borderRadius: '4px',
                              fontWeight: 700,
                              fontSize: '0.75em'
                            }}>
                              Interested
                            </span>
                          )}
                        </div>
                        <span style={{ fontSize: '0.85em', color: 'var(--k-ink-3)', border: '1px solid var(--k-border-strong)', padding: '2px 6px', borderRadius: '4px' }}>
                          ID: {worker.worker_chat_id}
                        </span>
                      </div>

                    <p style={{ margin: '0 0 10px 0', fontSize: '0.9em', color: 'var(--k-ink-3)', fontStyle: 'italic', lineHeight: '1.4' }}>
                      "{worker.job_description}"
                    </p>

                    <div style={{ display: 'flex', justifyContent: 'flex-start', alignItems: 'center', fontSize: '0.85em' }}>
                      <span style={{
                        backgroundColor: 'var(--k-wash)',
                        color: 'var(--k-orange-ink)',
                        padding: '4px 8px',
                        borderRadius: '4px',
                        fontWeight: 700
                      }}>
                        Vector Match Score: {worker.match_score}%
                      </span>
                    </div>
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
                <span className="badge badge-highlight">Sidebar: Network Discovery</span>
                <p className="card-summary">Scanning: {selectedJob?.title || "N/A"}</p>
                <p className="card-summary">Available Matches: {currentWorkers.length}</p>
              </>
            ) : (
              <span className="badge">Footer Slot: Matches for {selectedJob?.title || "N/A"}</span>
            )}
          </div>
        )}
      </Card>
    );
  };

  const renderPostsDashboard = (position) => (
    <Card slug="ActivePostsDashboard" title="ACTIVE POSTS DASHBOARD" position={position} onSelect={handleModuleSelect}>
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
            background-color: #E5484D;
            border-radius: 50%;
            display: inline-block;
          }
          ::-webkit-scrollbar { width: 8px; }
          ::-webkit-scrollbar-track { background: transparent; }
          ::-webkit-scrollbar-thumb { background-color: var(--k-border-strong); border-radius: 4px; }
          ::-webkit-scrollbar-thumb:hover { background-color: rgba(255, 107, 26, 0.6); }
        `}
      </style>

      {position === "main" ? (
        <div className="main-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <h2 style={{ flexShrink: 0 }}>ACTIVE POSTS PIPELINE NETWORK</h2>
          
          <div className="jobs-selector-list" style={{ 
            flex: 1, 
            overflowY: 'scroll',
            maxHeight: '23vw',
            minHeight: 0,
            marginTop: '20px', 
            paddingRight: '10px', 
            display: 'flex', 
            flexDirection: 'column', 
            gap: '12px' 
          }}>
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
                      border: isActive ? '2px solid #FF6B1A' : '1px solid var(--k-border-strong)',
                      padding: '15px',
                      cursor: 'pointer',
                      backgroundColor: isActive ? 'var(--k-wash)' : 'transparent',
                      color: 'inherit',
                      borderRadius: '5px',
                      transition: 'all 0.2s ease-in-out'
                    }}
                  >
                    <div style={{ display: 'flex', gap: '20px', marginBottom: '8px', fontSize: '0.85em', fontWeight: 600 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--k-ink-3)' }}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                          <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                        </svg>
                        <span>{job.matchedCount || 0} matched professionals</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--k-alert-ink)' }}>
                        <span className="status-indicator-dot"></span>
                        <span>{job.interestedCount || 0} interested</span>
                      </div>
                    </div>

                      <strong style={{ display: 'block', fontSize: '1.2em' }}>{job.title}</strong>
                      <span style={{ fontSize: '0.9em', opacity: 0.8 }}>{job.description}</span>
                      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '10px' }}>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedJob(job);
                            navigate('/customer/postings/ActiveBiddingsEngine');
                          }}
                          style={{
                            padding: '8px 20px',
                            background: '#FF6B1A',
                            color: '#0D0D0D',
                            border: 'none',
                            borderRadius: '8px',
                            fontWeight: 700,
                            cursor: 'pointer',
                            fontSize: '14px',
                          }}
                        >
                          Chat
                        </button>
                      </div>
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