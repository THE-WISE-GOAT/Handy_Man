import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCustomerDashboardData } from './useCustomerDashboardData';
import { apiClient } from '@shared/api/client';
import { useAuth } from '@shared/context/AuthContext';
import './dash2board.css';

// 1. IMPORT LEAFLET
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

// 2. VITE-COMPATIBLE ICON IMPORTS
import iconRetinaUrl from "leaflet/dist/images/marker-icon-2x.png";
import iconUrl from "leaflet/dist/images/marker-icon.png";
import shadowUrl from "leaflet/dist/images/marker-shadow.png";

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
  className: "custom-worker-icon",
  html: `<div style="color: #1F1F1F; display: flex; justify-content: center; align-items: center; filter: drop-shadow(0px 2px 2px rgba(0,0,0,0.5));">${personSvg}</div>`,
  iconSize: [30, 30],
  iconAnchor: [15, 15],
  popupAnchor: [0, -15],
});

const blinkingWorkerIcon = L.divIcon({
  className: "custom-worker-icon blinking-red-icon",
  html: `<div style="display: flex; justify-content: center; align-items: center;">${personSvg}</div>`,
  iconSize: [30, 30],
  iconAnchor: [15, 15],
  popupAnchor: [0, -15],
});

const goldenWorkerIcon = L.divIcon({
  className: "custom-worker-icon golden-worker-icon",
  html: `<div style="color: #FF6B1A; display: flex; justify-content: center; align-items: center; filter: drop-shadow(0px 2px 2px rgba(0,0,0,0.5));">${personSvg}</div>`,
  iconSize: [30, 30],
  iconAnchor: [15, 15],
  popupAnchor: [0, -15],
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

// Unified Card Component for all Side Slots
const Card = ({ slug, title, position, onSelect, children }) => {
  const isMain = position === "main";

  return (
    <div
      className={`dashboard-card slot-rhs slot-side ${
        !isMain ? "clickable" : ""
      }`}
      onClick={!isMain ? () => onSelect(slug) : undefined}
    >
      <div className="card-header">••• {title}</div>
      <div
        style={{
          flex: 1,
          minHeight: 0,
          display: "flex",
          flexDirection: "column",
        }}
      >
        {children}
      </div>
    </div>
  );
};

export default function Dash2Board({ viewSlug }) {
  const navigate = useNavigate();
  const workerCardRefs = React.useRef({});
  const chatEndRef = React.useRef(null);
  const messagesEndRef = React.useRef(null);
  const [chatInput, setChatInput] = React.useState("");

  const getCurrentUserId = () => {
    try {
      const token =
        localStorage.getItem("handy_man_access_token") ||
        localStorage.getItem("token") ||
        localStorage.getItem("access_token");
      if (!token) return null;
      const base64Url = token.split('.')[1];
      if (!base64Url) return null;
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split('')
          .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      );
      const parsed = JSON.parse(jsonPayload);
      return parsed.user_id ?? parsed.id ?? parsed.sub ?? null;
    } catch (err) {
      console.error("Failed to parse auth token", err);
      return null;
    }
  };
  const rawUserId = getCurrentUserId();
  const { user } = useAuth();
  const authUserId = user?.id ?? user?.user_id ?? rawUserId;

  const getOtherWorkerColor = (identifier) => {
    const safeIdentifier = String(identifier || 'Unknown');
    const lightColors = [
      { background: "#BFDBFE", color: "#1E3A8A" },
      { background: "#BBF7D0", color: "#14532D" },
      { background: "#E9D5FF", color: "#581C87" },
      { background: "#FBCFE8", color: "#831843" },
      { background: "#99F6E4", color: "#134E4A" },
      { background: "#FEF08A", color: "#713F12" },
    ];

    let hash = 0;
    for (let i = 0; i < safeIdentifier.length; i++) {
      hash = safeIdentifier.charCodeAt(i) + ((hash << 5) - hash);
    }
    const index = Math.abs(hash) % lightColors.length;
    return lightColors[index];
  };

  // ── Full-width view toggle for ActiveBiddingsEngine ──
  const [viewAllBids, setViewAllBids] = useState(false);
  const [bookMultiple, setBookMultiple] = useState(false);
  const [selectedBidIds, setSelectedBidIds] = useState([]);

  // ── Centered modal state ──
  const [showBookingModal, setShowBookingModal] = useState(false);
  const [showRatingsModal, setShowRatingsModal] = useState(false);
  const [selectedWorkersForReview, setSelectedWorkersForReview] = useState([]);

  const {
    postingsSlots,
    swapPostingsSlots,
    biddingsStream,
    pendingJobs,
    selectedJob,
    setSelectedJob,
    fetchPendingJobs,
    chatMessages,
    connectCustomerChat,
    sendHumanMessage,
    appendMessage,
    disconnectCustomerChat,
    matchedWorkersMap,
    workerLocations,
    toggleWorkerInterest,
    selectedWorkerId,
    setSelectedWorkerId,
    fetchChatHistory,
  } = useCustomerDashboardData();

  useEffect(() => {
    useCustomerDashboardData.getState().fetchPendingJobs();
  }, []);

  useEffect(() => {
    const handleFocus = () => { useCustomerDashboardData.getState().fetchPendingJobs(); };
    window.addEventListener('focus', handleFocus);
    return () => window.removeEventListener('focus', handleFocus);
  }, []);

  useEffect(() => {
    if (selectedWorkerId && workerCardRefs.current[selectedWorkerId]) {
      workerCardRefs.current[selectedWorkerId].scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    }
  }, [selectedWorkerId]);

  useEffect(() => {
    const timer = setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, 100);
    return () => clearTimeout(timer);
  }, [chatMessages, viewAllBids]);

  useEffect(() => {
    if (selectedJob && selectedJob.booking_chat_id) {
      useCustomerDashboardData.getState().connectCustomerChat(selectedJob.booking_chat_id);
      useCustomerDashboardData.getState().fetchChatHistory(selectedJob.booking_chat_id);
    }
  }, [selectedJob]);

  useEffect(() => {
    if (selectedJob && selectedJob.id) {
      useCustomerDashboardData.getState().fetchJobBids(selectedJob.id);
    } else {
      useCustomerDashboardData.getState().fetchPendingJobs();
    }
  }, [selectedJob]);

  useEffect(() => {
    if (!viewSlug) return;
    if (postingsSlots.main !== viewSlug) {
      const targetSlot = Object.keys(postingsSlots).find((key) => postingsSlots[key] === viewSlug);
      if (targetSlot) swapPostingsSlots(targetSlot);
    }
  }, [viewSlug, postingsSlots, swapPostingsSlots]);

  useEffect(() => {
    return () => useCustomerDashboardData.getState().disconnectCustomerChat();
  }, []);

    useEffect(() => {

      const bookingChatId = selectedJob?.booking_chat_id;
      if (bookingChatId) {
        useCustomerDashboardData.getState().connectCustomerChat(bookingChatId);
        useCustomerDashboardData.getState().fetchChatHistory(bookingChatId);
      }
    }, [selectedJob?.booking_chat_id]);

// 1. Fetch historical bids on mount and when selectedJob changes
useEffect(() => {
  const selectedJobId = selectedJob?.id;
  if (selectedJobId) {
    useCustomerDashboardData.getState().fetchJobBids(selectedJobId);
  } else {
    useCustomerDashboardData.getState().fetchPendingJobs();
  }
}, [selectedJob?.id]);

// 2. Handle view slug slot swapping
useEffect(() => {
  if (!viewSlug) return;
  if (postingsSlots.main !== viewSlug) {
    const targetSlot = Object.keys(postingsSlots).find((key) => postingsSlots[key] === viewSlug);
    if (targetSlot) swapPostingsSlots(targetSlot);
  }
}, [viewSlug, swapPostingsSlots]);

// 3. Disconnect chat on component unmount
useEffect(() => {
  return () => useCustomerDashboardData.getState().disconnectCustomerChat();
}, []);

// 4. Poll chat history when a valid booking chat ID exists
useEffect(() => {
  const chatId = selectedJob?.booking_chat_id;
  if (!chatId) return;

  const intervalId = setInterval(() => {
    useCustomerDashboardData.getState().fetchChatHistory(chatId);
  }, 3000);

  return () => clearInterval(intervalId);
}, [selectedJob?.booking_chat_id]);



  const handleModuleSelect = (targetSlug) => {
    navigate(`/customer/postings/${targetSlug}`);
  };

  const renderBiddingsEngine = (position) => {
    const handleSendChat = async (e) => {
      e.preventDefault();
      if (!chatInput.trim() || !selectedJob) return;
      const bookingChatId = selectedJob.booking_chat_id;
      if (!bookingChatId) return;
      try {
        await sendHumanMessage(bookingChatId, "customer", chatInput.trim());
        setChatInput("");
      } catch (err) {
        console.error("Failed to send message:", err);
      }
    };

    const renderChatView = () => (
      <div style={{ width: "100%", height: "100%", display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-start", flexShrink: 0, marginBottom: "8px" }}>
          <button
            onClick={() => { setViewAllBids(true); setBookMultiple(false); setSelectedBidIds([]); }}
            style={{
              padding: "4px 14px", background: "#FF6B1A", color: "#0D0D0D",
              border: "none", borderRadius: "20px", fontWeight: 600,
              fontSize: "13px", cursor: "pointer"
            }}
          >
            View All bids
          </button>
        </div>

        <div className="chat-box" style={{ flex: 1, minHeight: 0 }}>
          {Array.isArray(chatMessages) && chatMessages
            .filter((msg) => msg && typeof msg === 'object' && (msg.sender_role === "customer" || msg.sender_role === "worker" || msg.sender_role === "system" || msg.sender_role === "client"))
            .map((msg, idx) => {
              const isSelf = Boolean(
                authUserId &&
                msg.sender_id != null &&
                 String(msg.sender_id).trim() === String(authUserId).trim()
              );
              const isClient = msg.sender_role === "customer" || msg.sender_role === "client";
              const displayName = isSelf ? "You" : (msg.sender_name || "User");

              if (msg.sender_role === "system") {
                return (
                  <div key={msg.id || `chat-msg-${idx}`} style={{ display: "flex", width: "100%", justifyContent: "center", marginBottom: "16px" }}>
                    <div style={{
                      maxWidth: "80%", padding: "4px 16px", fontSize: "0.85rem",
                      fontWeight: 600, color: "#FF6B1A", background: "rgba(255,107,26,0.1)",
                      borderRadius: "9999px", textAlign: "center"
                    }}>
                      {msg.text || ''}
                    </div>
                  </div>
                );
              }

              if (isSelf) {
                return (
                  <div key={msg.id || `chat-msg-${idx}`} style={{ display: "flex", width: "100%", justifyContent: "flex-end", marginBottom: "16px" }}>
                    <div style={{
                      maxWidth: "70%", padding: "8px 16px", color: "var(--k-ink)",
                      background: "#FF6B1A", borderRadius: "28px 4px 28px 28px",
                      fontWeight: "normal", fontStyle: "normal"
                    }}>
                      <strong>{displayName}:</strong> {msg.text || ''}
                    </div>
                  </div>
                );
              }

              if (isClient) {
                return (
                  <div key={msg.id || `chat-msg-${idx}`} style={{ display: "flex", width: "100%", justifyContent: "flex-start", marginBottom: "16px" }}>
                    <div style={{
                      maxWidth: "70%", padding: "8px 16px", color: "var(--k-ink)",
                      background: "var(--k-raise)", borderRadius: "4px 28px 28px 28px",
                      border: "1px solid var(--k-line)", fontWeight: "bold", fontStyle: "italic"
                    }}>
                      <strong>{displayName}:</strong> {msg.text || ''}
                    </div>
                  </div>
                );
              }

              const workerColor = getOtherWorkerColor(msg.sender_name || msg.sender_role);
              return (
                <div key={msg.id || `chat-msg-${idx}`} style={{ display: "flex", width: "100%", justifyContent: "flex-start", marginBottom: "16px" }}>
                  <div style={{
                    maxWidth: "70%", padding: "8px 16px",
                    background: workerColor.background, color: workerColor.color,
                    borderRadius: "4px 28px 28px 28px", border: "1px solid var(--k-line)",
                    fontWeight: "normal", fontStyle: "normal"
                  }}>
                    <strong>{displayName}:</strong> {msg.text || ''}
                  </div>
                </div>
              );
            })}
          <div ref={messagesEndRef} />
        </div>

        <form onSubmit={handleSendChat} style={{ display: 'flex', gap: '6px', paddingTop: '8px', borderTop: '1px solid var(--k-line)', flexShrink: 0 }}>
          <input
            type="text"
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            placeholder="Type a message..."
            disabled={!selectedJob}
            style={{
              flex: 1, padding: '6px 10px', borderRadius: '6px',
              border: '1px solid var(--k-border-strong)',
              background: 'var(--k-field)', color: 'var(--k-ink)',
              font: 'inherit', outline: 'none', fontSize: '13px'
            }}
          />
          <button
            type="submit"
            disabled={!chatInput.trim() || !selectedJob}
            style={{
              padding: '6px 14px', background: '#FF6B1A', color: '#0D0D0D',
              border: 'none', borderRadius: '6px', fontWeight: 700,
              cursor: 'pointer', fontSize: '13px'
            }}
          >
            Send
          </button>
        </form>
      </div>
    );

    const renderBidsView = () => {
      const checkboxStyle = { width: "16px", height: "16px", accentColor: "#FF6B1A", cursor: "pointer" };

      return (
        <div style={{ width: "100%", height: "100%", display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <div style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            flexShrink: 0, marginBottom: "12px"
          }}>
            <button
              onClick={handleViewChat}
              style={{
                padding: "4px 14px", background: "#FF6B1A", color: "#0D0D0D",
                border: "none", borderRadius: "20px", fontWeight: 600,
                fontSize: "13px", cursor: "pointer"
              }}
            >
              View Chat
            </button>
            <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px" }}>
              <input
                type="checkbox"
                checked={bookMultiple}
                onChange={(e) => { setBookMultiple(e.target.checked); setSelectedBidIds([]); }}
                style={checkboxStyle}
              />
              Book Multiple Workers
            </label>
          </div>

          <div style={{ flex: 1, overflowY: "auto", minHeight: 0, padding: "8px 0" }}>
            {bidsForSelectedJob.length === 0 ? (
              <p style={{ color: "var(--k-ink-3)", fontSize: "13px", padding: "16px" }}>No bids received yet.</p>
            ) : (
              bidsForSelectedJob.map((bid) => {
                const isSelected = selectedBidIds.includes(bid.id);
                const workerId = bid.worker_chat_id || bid.worker_id;
                const workerName = bid.worker_name || bid.provider || `Worker ${workerId}`;
                const bidAmount = bid.bid_amount || bid.offer || bid.amount || 0;
                return (
                  <div
                    key={bid.id}
                    style={{
                      display: "flex", alignItems: "center", justifyContent: "space-between",
                      padding: "10px 12px", borderRadius: "8px",
                      border: isSelected ? "1px solid #FF6B1A" : "1px solid var(--k-line)",
                      background: isSelected ? "var(--k-wash)" : "var(--k-raise)",
                      marginBottom: "8px"
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                      {bookMultiple && (
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => handleToggleBidSelection(bid.id)}
                          style={checkboxStyle}
                        />
                      )}
                      <div style={{
                        width: "32px", height: "32px", borderRadius: "50%",
                        background: "rgba(255, 107, 26, 0.2)", display: "flex",
                        alignItems: "center", justifyContent: "center", overflow: "hidden"
                      }}>
                        <span style={{ color: "#FF6B1A", fontWeight: 700, fontSize: "12px" }}>
                          {workerName ? workerName.charAt(0).toUpperCase() : 'W'}
                        </span>
                      </div>
                      <span style={{ fontSize: "13px", fontWeight: 500, color: "var(--k-ink)" }}>
                        {workerName}
                      </span>
                    </div>

                    <div style={{ display: "flex", gap: "16px", fontSize: "12px" }}>
                      <span style={{ color: "#FF6B1A", textDecoration: "underline", cursor: "not-allowed" }}>
                        Ratings &amp; Reviews
                      </span>
                      <a
                        href="http://localhost:5173/customer/postings/GeospatialLiveMap"
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ color: "#FF6B1A", textDecoration: "underline", cursor: "pointer" }}
                      >
                        View on Maps
                      </a>
                    </div>

                    <span style={{ fontSize: "13px", fontWeight: 600, color: "#FF6B1A", margin: "0 16px" }}>
                      Rs {bidAmount}
                    </span>

                    {!bookMultiple && (
                      <button
                        onClick={() => handleBookClick(bid)}
                        style={{
                          padding: "6px 12px", background: "#FF6B1A", color: "#0D0D0D",
                          border: "none", borderRadius: "6px", fontWeight: 700,
                          cursor: "pointer", fontSize: "12px"
                        }}
                      >
                        book &gt;
                      </button>
                    )}
                  </div>
                );
              })
            )}
          </div>

          {bookMultiple && (
            <div style={{
              padding: "12px 16px", display: "flex", alignItems: "center",
              justifyContent: "space-between",
              borderTop: "1px solid var(--k-line)", flexShrink: 0
            }}>
              <span style={{ fontSize: "13px", fontWeight: 500, color: "var(--k-ink)" }}>
                {selectedBidIds.length} selected
              </span>
              <button
                onClick={handleMultiBook}
                disabled={selectedBidIds.length === 0}
                style={{
                  padding: "8px 16px", background: "#FF6B1A", color: "#0D0D0D",
                  border: "none", borderRadius: "6px", fontWeight: 700, cursor: "pointer"
                }}
              >
                book &gt;
              </button>
            </div>
          )}
        </div>
      );
    };

    if (position === "main") {
      return (
        <div className="dashboard-card slot-main">
          <div className="card-header">
            ••• COMPETITIVE MARKETPLACE METRICS
          </div>

          <div className="main-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            {viewAllBids ? renderBidsView() : renderChatView()}
          </div>
        </div>
      );
    }

    return (
      <Card slug="ActiveBiddingsEngine" title="COMPETITIVE MARKETPLACE METRICS" position={position} onSelect={handleModuleSelect}>
        <div className="preview-panel">
          <span className="badge badge-highlight">CHAT ROOM AND BIDS</span>
          <p className="card-summary">Target: {selectedJob?.title || "N/A"}</p>
          <p className="card-summary">Pending Offers Count: {biddingsStream.length}</p>
        </div>
      </Card>
    );
  };

  const renderLiveMap = (position) => {
    const centerPoint =
      selectedJob && selectedJob.latitude && selectedJob.longitude
        ? [parseFloat(selectedJob.latitude), parseFloat(selectedJob.longitude)]
        : [27.7172, 85.324];

    const currentWorkers =
      selectedJob && matchedWorkersMap[selectedJob.id]
        ? matchedWorkersMap[selectedJob.id]
        : [];

    return (
      <Card
        slug="GeospatialLiveMap"
        title="GEOSPATIAL LIVE MAP"
        position={position}
        onSelect={handleModuleSelect}
      >
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
          <div
            className="main-panel"
            style={{
              height: "100%",
              display: "flex",
              flexDirection: "column",
              minHeight: 0,
            }}
          >
            <h2 style={{ flexShrink: 0 }}>GEOSPATIAL ENGINE FULL DISPLAY</h2>
            <div
              style={{
                flex: 1,
                minHeight: 0,
                borderRadius: "12px",
                overflow: "hidden",
                marginTop: "10px",
              }}
            >
              <MapContainer
                center={centerPoint}
                zoom={13}
                style={{ height: "100%", width: "100%" }}
              >
                <TileLayer
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                />
                <MapUpdater center={centerPoint} />

                {selectedJob && selectedJob.latitude && (
                  <Marker position={centerPoint}>
                    <Popup>
                      <strong>{selectedJob.title}</strong>
                      <br />
                      Job Location
                    </Popup>
                  </Marker>
                )}

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
                      eventHandlers={{
                        click: () => setSelectedWorkerId(worker.worker_chat_id),
                      }}
                    >
                      <Popup>
                        <div style={{ textAlign: "center" }}>
                          <strong>{worker.username}</strong>
                          <br />
                          {isTopThree
                            ? `🏆 Rank #${rank} Match`
                            : `Rank #${rank}`}
                          <br />
                          Match Score: {worker.match_score}%<br />
                          <button
                            onClick={() =>
                              toggleWorkerInterest(worker.worker_chat_id)
                            }
                            style={{
                              marginTop: "8px",
                              padding: "4px 8px",
                              backgroundColor: "#FF6B1A",
                              color: "#0D0D0D",
                              border: "none",
                              borderRadius: "4px",
                              cursor: "pointer",
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
            <span className="badge badge-highlight">
              VIEW MAP
            </span>
            <p className="card-summary">
              Lat: {selectedJob?.latitude || "N/A"} | Lng:{" "}
              {selectedJob?.longitude || "N/A"}
            </p>
            <p className="card-summary">
              Workers Rendered: {currentWorkers.length}
            </p>
          </div>
        )}
      </Card>
    );
  };

  const renderReviewLogs = (position) => {
    const currentWorkers =
      selectedJob && matchedWorkersMap[selectedJob.id]
        ? matchedWorkersMap[selectedJob.id]
        : [];

    return (
      <Card
        slug="RatingsReviewLogs"
        title="MATCHED PROFESSIONALS LOGS"
        position={position}
        onSelect={handleModuleSelect}
      >
        {position === "main" ? (
          <div
            className="main-panel"
            style={{
              height: "100%",
              display: "flex",
              flexDirection: "column",
              minHeight: 0,
            }}
          >
            <h2 style={{ flexShrink: 0 }}>QUALIFIED WORKER NETWORK</h2>

            <h3
              style={{
                color: "var(--text-primary)",
                flexShrink: 0,
                display: "flex",
                alignItems: "center",
                gap: "10px",
              }}
            >
              <span>
                Matched Profiles For:{" "}
                {selectedJob ? selectedJob.title : "No Job Selected"}
              </span>

              {selectedJob?.matchCategory && (
                <span
                  style={{
                    fontSize: "0.65em",
                    backgroundColor: "var(--k-wash)",
                    color: selectedJob.matchedByCategory
                      ? "var(--k-orange-ink)"
                      : "var(--k-ink-3)",
                    padding: "4px 8px",
                    borderRadius: "4px",
                    border: `1px solid ${selectedJob.matchedByCategory ? "rgba(255, 107, 26, 0.5)" : "var(--k-border-strong)"}`,
                  }}
                >
                  {selectedJob.matchedByCategory
                    ? `Category Match: ${selectedJob.matchCategory}`
                    : `Semantic Radius Fallback`}
                </span>
              )}
            </h3>

            <div
              style={{
                flex: 1,
                overflowY: "scroll",
                maxHeight: "23vw",
                minHeight: 0,
                marginTop: "15px",
                paddingRight: "10px",
                display: "flex",
                flexDirection: "column",
                gap: "12px",
              }}
            >
              {currentWorkers.length === 0 ? (
                <p style={{ opacity: 0.7 }}>
                  No professionals matched yet or scanning network...
                </p>
              ) : (
                currentWorkers.map((worker, index) => {
                  const isSelected =
                    selectedWorkerId &&
                    worker.worker_chat_id === selectedWorkerId;
                  const rank = index + 1;
                  return (
                    <div
                      key={worker.worker_chat_id}
                      ref={(el) =>
                        (workerCardRefs.current[worker.worker_chat_id] = el)
                      }
                      style={{
                        border: isSelected
                          ? "2px solid #FF6B1A"
                          : "1px solid var(--k-line)",
                        borderRadius: "8px",
                        padding: "15px",
                        backgroundColor: isSelected
                          ? "var(--k-wash)"
                          : "var(--k-raise)",
                        boxShadow: isSelected
                          ? "0 0 0 4px rgba(255, 107, 26, 0.12)"
                          : "0 2px 8px rgba(0, 0, 0, 0.3)",
                        transform: isSelected ? "scale(1.02)" : "none",
                        transition: "all 0.2s ease-in-out",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          marginBottom: "8px",
                          alignItems: "center",
                        }}
                      >
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "8px",
                          }}
                        >
                          <strong
                            style={{ fontSize: "1.1em", color: "var(--k-ink)" }}
                          >
                            {worker.username}
                          </strong>
                          {isSelected && (
                            <span
                              style={{
                                backgroundColor: "#FF6B1A",
                                color: "#0D0D0D",
                                padding: "2px 8px",
                                borderRadius: "4px",
                                fontWeight: 700,
                                fontSize: "0.75em",
                              }}
                            >
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
                        <span
                          style={{
                            fontSize: "0.85em",
                            color: "var(--k-ink-3)",
                            border: "1px solid var(--k-border-strong)",
                            padding: "2px 6px",
                            borderRadius: "4px",
                          }}
                        >
                          ID: {worker.worker_chat_id}
                        </span>
                      </div>

                      <p
                        style={{
                          margin: "0 0 10px 0",
                          fontSize: "0.9em",
                          color: "var(--k-ink-3)",
                          fontStyle: "italic",
                          lineHeight: "1.4",
                        }}
                      >
                        "{worker.job_description}"
                      </p>

                      <div
                        style={{
                          display: "flex",
                          justifyContent: "flex-start",
                          alignItems: "center",
                          fontSize: "0.85em",
                        }}
                      >
                        <span
                          style={{
                            backgroundColor: "var(--k-wash)",
                            color: "var(--k-orange-ink)",
                            padding: "4px 8px",
                            borderRadius: "4px",
                            fontWeight: 700,
                          }}
                        >
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
            <span className="badge badge-highlight">
              RATINGS AND REVIEW
            </span>
            <p className="card-summary">
              Scanning: {selectedJob?.title || "N/A"}
            </p>
            <p className="card-summary">
              Available Matches: {currentWorkers.length}
            </p>
          </div>
        )}
      </Card>
    );
  };

  const renderPostsDashboard = (position) => (
    <Card
      slug="ActivePostsDashboard"
      title="ACTIVE POSTS DASHBOARD"
      position={position}
      onSelect={handleModuleSelect}
    >
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
        <div
          className="main-panel"
          style={{
            height: "100%",
            display: "flex",
            flexDirection: "column",
            minHeight: 0,
          }}
        >
          <h2 style={{ flexShrink: 0 }}>ACTIVE POSTS PIPELINE NETWORK</h2>

          <div
            className="jobs-selector-list"
            style={{
              flex: 1,
              overflowY: "scroll",
              maxHeight: "23vw",
              minHeight: 0,
              marginTop: "20px",
              paddingRight: "10px",
              display: "flex",
              flexDirection: "column",
              gap: "12px",
            }}
          >
            {pendingJobs.length === 0 ? (
              <p>No pending jobs found.</p>
            ) : (
              pendingJobs.map((job) => {
                const isActive = selectedJob && selectedJob.id === job.id;
                return (
                  <div
                    key={job.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedJob(job);
                    }}
                    style={{
                      border: isActive
                        ? "2px solid #FF6B1A"
                        : "1px solid var(--k-border-strong)",
                      padding: "15px",
                      cursor: "pointer",
                      backgroundColor: isActive
                        ? "var(--k-wash)"
                        : "transparent",
                      color: "inherit",
                      borderRadius: "5px",
                      transition: "all 0.2s ease-in-out",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        gap: "20px",
                        marginBottom: "8px",
                        fontSize: "0.85em",
                        fontWeight: 600,
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "6px",
                          color: "var(--k-ink-3)",
                        }}
                      >
                        <svg
                          width="14"
                          height="14"
                          viewBox="0 0 24 24"
                          fill="currentColor"
                        >
                          <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
                        </svg>
                        <span>
                          {job.matchedCount || 0} matched professionals
                        </span>
                      </div>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "6px",
                          color: "var(--k-alert-ink)",
                        }}
                      >
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
          <span className="badge badge-highlight">
            ACTIVE POSTS
          </span>
          <p className="card-summary">
            Selected: {selectedJob?.title || "None"}
          </p>
          <p className="card-summary">
            Total Pending: {pendingJobs.length}
          </p>
        </div>
      )}
    </Card>
  );

  const resolveModuleBySlot = (slotKey) => {
    switch (postingsSlots[slotKey]) {
      case "ActiveBiddingsEngine":
        return renderBiddingsEngine(slotKey);
      case "GeospatialLiveMap":
        return renderLiveMap(slotKey);
      case "ActivePostsDashboard":
        return renderPostsDashboard(slotKey);
      case "RatingsReviewLogs":
        return renderReviewLogs(slotKey);
      default:
        return null;
    }
  };

  const bidsForSelectedJob = biddingsStream || [];
  const selectedBidItems = bidsForSelectedJob.filter((bid) =>
    selectedBidIds.includes(bid.id)
  );
  const totalCharge = selectedBidItems.reduce(
    (sum, bid) => sum + (bid.bid_amount || bid.offer || bid.amount || 0), 0
  );

  const handleViewChat = () => {
    setViewAllBids(false);
  };

  const handleToggleBidSelection = (bidId) => {
    setSelectedBidIds((prev) =>
      prev.includes(bidId)
        ? prev.filter((id) => id !== bidId)
        : [...prev, bidId]
    );
  };

  const handleBookClick = (bid) => {
    setSelectedBidIds([bid.id]);
    setShowBookingModal(true);
    setViewAllBids(false);
  };

  const handleMultiBook = () => {
    if (selectedBidIds.length > 0) {
      setShowBookingModal(true);
      setViewAllBids(false);
    }
  };

  const handleProceedToPayment = async () => {
    setShowBookingModal(false);
    try {
      const data = await apiClient.post(`/jobs/${selectedJob.id}/book`, {
        selected_bid_ids: selectedBidIds,
      });

      if (data.status === "success") {
        useCustomerDashboardData.getState().updateJobMetrics(selectedJob.id, {
          worker_id: data.worker_id,
          status: data.job_status || "assigned",
        });
        useCustomerDashboardData.getState().fetchJobBids(selectedJob.id);
      }
    } catch (error) {
      console.error("Failed to book worker(s):", error);
    }
  };

  const renderBookingModal = () => {
    if (!showBookingModal) return null;
    const modalStyle = {
      position: "fixed", inset: 0, backgroundColor: "rgba(0,0,0,0.6)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 99999, padding: "16px"
    };
    const contentStyle = {
      position: "relative", width: "100%", maxWidth: "640px", background: "var(--k-raise)",
      color: "var(--k-ink)", border: "1px solid var(--k-line)", borderRadius: "16px",
      boxShadow: "0 20px 60px rgba(0,0,0,0.5)", maxHeight: "90vh", overflowY: "auto", padding: "24px"
    };
    const closeBtnStyle = {
      position: "absolute", top: "12px", right: "16px", background: "none", border: "none",
      color: "var(--k-ink-3)", fontSize: "24px", cursor: "pointer", lineHeight: 1
    };
    const handleBackdropClick = (e) => { if (e.target === e.currentTarget) setShowBookingModal(false); };

    return (
      <div style={modalStyle} onClick={handleBackdropClick}>
        <div style={contentStyle}>
          <button onClick={() => setShowBookingModal(false)} style={closeBtnStyle}>×</button>

          <h3 style={{ margin: "0 0 8px", fontSize: "12px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "1px", color: "var(--k-orange-ink)" }}>
            Job Title:
          </h3>
          <p style={{ margin: "4px 0 12px", fontSize: "20px", fontWeight: 700 }}>
            {selectedJob?.title || "Untitled Job"}
          </p>

          <h4 style={{ margin: "16px 0 8px", fontSize: "12px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "1px", color: "var(--k-orange-ink)" }}>
            Job Description:
          </h4>
          <p style={{ margin: "4px 0 20px", fontSize: "13px", color: "var(--k-ink-3)", lineHeight: "1.5" }}>
            {selectedJob?.description || selectedJob?.job_description || "No description available."}
          </p>

          <h4 style={{ margin: "0 0 12px", fontSize: "11px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "1px", color: "var(--k-ink-3)" }}>
            Selected Workers &amp; Bids:
          </h4>
          <div style={{ marginBottom: "20px" }}>
            {selectedBidItems.length === 0 ? (
              <p style={{ fontSize: "13px", color: "var(--k-ink-3)" }}>No workers selected.</p>
            ) : (
              selectedBidItems.map((item, idx) => {
                const workerName = item.worker_name || item.provider || `Worker ${item.worker_chat_id}`;
                const bidAmount = item.bid_amount || item.offer || item.amount || 0;
                return (
                  <div key={item.id || idx} style={{
                    display: "flex", alignItems: "center", justifyContent: "space-between",
                    padding: "10px 12px", border: "1px solid var(--k-line)", borderRadius: "8px", marginBottom: "8px"
                  }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                      <div style={{
                        width: "28px", height: "28px", borderRadius: "50%",
                        background: "rgba(255, 107, 26, 0.2)", display: "flex",
                        alignItems: "center", justifyContent: "center", overflow: "hidden"
                      }}>
                        <span style={{ color: "#FF6B1A", fontWeight: 700, fontSize: "11px" }}>
                          {(workerName || "W").slice(0, 1).toUpperCase()}
                        </span>
                      </div>
                      <span style={{ fontSize: "13px", fontWeight: 500, color: "var(--k-ink)" }}>
                        {workerName}
                      </span>
                    </div>
                    <span style={{ fontSize: "13px", fontWeight: 600, color: "#FF6B1A" }}>
                      Rs {bidAmount}
                    </span>
                  </div>
                );
              })
            )}
          </div>

          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "20px" }}>
            <span style={{ fontSize: "13px", color: "var(--k-ink-3)" }}>Total Charge:</span>
            <span style={{ fontSize: "24px", fontWeight: 700, color: "#FF6B1A" }}>
              Rs {totalCharge}
            </span>
          </div>

          <button
            onClick={handleProceedToPayment}
            style={{
              width: "100%", padding: "12px", background: "#FF6B1A", color: "#0D0D0D",
              border: "none", borderRadius: "12px", fontWeight: 700, fontSize: "16px", cursor: "pointer"
            }}
          >
            Proceed to Payment Opt
          </button>
        </div>
      </div>
    );
  };

  const renderRatingsModal = () => {
    if (!showRatingsModal) return null;
    const modalStyle = {
      position: "fixed", inset: 0, backgroundColor: "rgba(0,0,0,0.6)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 99999, padding: "16px"
    };
    const contentStyle = {
      position: "relative", width: "100%", maxWidth: "640px", background: "var(--k-raise)",
      color: "var(--k-ink)", border: "1px solid var(--k-line)", borderRadius: "16px",
      boxShadow: "0 20px 60px rgba(0,0,0,0.5)", maxHeight: "90vh", overflowY: "auto", padding: "24px"
    };
    const closeBtnStyle = {
      position: "absolute", top: "12px", right: "16px", background: "none", border: "none",
      color: "var(--k-ink-3)", fontSize: "24px", cursor: "pointer", lineHeight: 1
    };
    const handleBackdropClick = (e) => { if (e.target === e.currentTarget) setShowRatingsModal(false); };

    return (
      <div style={modalStyle} onClick={handleBackdropClick}>
        <div style={contentStyle}>
          <button onClick={() => setShowRatingsModal(false)} style={closeBtnStyle}>×</button>

          <h3 style={{ margin: "0 0 16px", fontSize: "16px", fontWeight: 600 }}>Ratings &amp; Reviews</h3>

          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {selectedWorkersForReview.length === 0 ? (
              <>
                <p style={{ color: "var(--k-ink-3)", fontSize: "13px" }}>No worker profiles to review.</p>
                <button
                  onClick={() => setShowRatingsModal(false)}
                  style={{
                    padding: "8px 16px", background: "#FF6B1A", color: "#0D0D0D",
                    border: "none", borderRadius: "20px", fontWeight: 600, fontSize: "13px", cursor: "pointer"
                  }}
                >
                  Close
                </button>
              </>
            ) : (
              selectedWorkersForReview.map((worker) => {
                const isSelected = worker._highlighted;
                return (
                  <div key={worker.worker_chat_id || worker.id} style={{
                    padding: "12px", borderRadius: "10px", cursor: "pointer",
                    border: isSelected ? "1px solid #FF6B1A" : "1px solid var(--k-line)",
                    background: isSelected ? "var(--k-wash)" : "var(--ind-surface)"
                  }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px" }}>
                      <div style={{
                        width: "36px", height: "36px", borderRadius: "50%",
                        background: "rgba(255, 107, 26, 0.2)", display: "flex",
                        alignItems: "center", justifyContent: "center", overflow: "hidden"
                      }}>
                        <span style={{ color: "#FF6B1A", fontWeight: 700, fontSize: "14px" }}>
                          {(worker.username || worker.worker_name || "W").slice(0, 1).toUpperCase()}
                        </span>
                      </div>
                      <div>
                        <strong style={{ display: "block", color: "var(--k-ink)" }}>
                          {worker.username || worker.worker_name || `Worker ${worker.worker_chat_id}`}
                        </strong>
                        <span style={{ fontSize: "11px", color: "var(--k-ink-3)" }}>
                          ★ {worker.rating || "—"}/5
                        </span>
                      </div>
                    </div>
                    <p style={{ margin: "0 0 8px", fontSize: "12px", color: "var(--k-ink-3)", lineHeight: "1.4", fontStyle: "italic" }}>
                      {worker.review_snippet || "No review yet."}
                    </p>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <>
      <style>{`
        .dashboard-grid-4pane {
          display: grid !important;
          grid-template-columns: 1fr 380px !important;
          grid-template-rows: repeat(3, 1fr) !important;
          gap: 16px !important;
          min-height: 0 !important;
          width: 100% !important;
          box-sizing: border-box !important;
        }

        .grid-main {
          grid-column: 1 !important;
          grid-row: 1 / span 3 !important;
          display: flex !important;
          flex-direction: column !important;
          min-height: 0 !important;
          height: 100% !important;
        }

        /* Identical styling across all 3 side slot containers */
        .grid-sidebar,
        .grid-bottom-left,
        .grid-bottom-right {
          grid-column: 2 !important;
          display: flex !important;
          flex-direction: column !important;
          min-height: 0 !important;
          height: 100% !important;
          width: 100% !important;
        }

        .grid-sidebar { grid-row: 1 !important; }
        .grid-bottom-left { grid-row: 2 !important; }
        .grid-bottom-right { grid-row: 3 !important; }

        /* Unified Card properties for all side slots */
        .dashboard-card.slot-rhs {
          display: flex !important;
          flex-direction: column !important;
          height: 100% !important;
          width: 100% !important;
          min-height: 0 !important;
          box-sizing: border-box !important;
          border-radius: 12px !important;
          background: var(--k-raise, #121212) !important;
          border: 1px solid var(--k-line, rgba(255, 255, 255, 0.1)) !important;
          padding: 14px !important;
          transition: all 0.2s ease-in-out !important;
        }

        .dashboard-card.clickable {
          cursor: pointer !important;
        }

        .dashboard-card.clickable:hover {
          transform: translateY(-2px) !important;
          box-shadow: 0 6px 16px rgba(0, 0, 0, 0.4) !important;
          border-color: rgba(255, 107, 26, 0.4) !important;
        }

        .preview-panel {
          display: flex !important;
          flex-direction: column !important;
          gap: 8px !important;
          padding: 4px 0 !important;
          height: 100% !important;
          justify-content: center !important;
        }
      `}</style>

      <div className="dashboard-grid-4pane">
        {/* Left Column: Full Height */}
        <div className="grid-main">{resolveModuleBySlot("main")}</div>

        {/* Right Column: Stacked Slots 2, 3, and 4 */}
        <div className="grid-sidebar">{resolveModuleBySlot("sidebar")}</div>
        <div className="grid-bottom-left">{resolveModuleBySlot("bottomLeft")}</div>
        <div className="grid-bottom-right">{resolveModuleBySlot("bottomRight")}</div>

        {/* Centered Modals */}
        {renderBookingModal()}
        {renderRatingsModal()}
      </div>
    </>
  );
}