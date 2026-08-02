import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useCustomerDashboardData } from "./useCustomerDashboardData";
import "./dash1board.css";

export default function Dash1Board({ viewSlug }) {
  const navigate = useNavigate();
  const [chatInput, setChatInput] = useState("");
<<<<<<< HEAD

  // 🗺️ MAP STATES
=======
>>>>>>> origin/And
  const [isMapOpen, setIsMapOpen] = useState(false);
  const [mapReady, setMapReady] = useState(false);
  const [modalSearchQuery, setModalSearchQuery] = useState("");
  const [modalLat, setModalLat] = useState(27.7172); // Default to Kathmandu
  const [modalLng, setModalLng] = useState(85.324);
  const [modalAddrText, setModalAddrText] = useState("");
  const mapContainerRef = useRef(null);
  const leafletMapRef = useRef(null);
  const leafletMarkerRef = useRef(null);

  // Bring in items from Zustand store
  const {
    slots,
    swapSlots,
    jobDescriptionDraft,
    jobTitleDraft,
    setJobTitle,
    setJobDescription,
    chatMessages,
    addChatMessage,
    activePostsCount,
    userCont,
    fetchBookingsPendingJobs,
    // Spatial state parameters from Zustand configuration
    userAddrText,
    userLng,
    userLat,
    setUserAddrText,
    setUserCoordinates,
    fetchedJobs,
    userName,
    setUserName,
    setUserCont,
    jobProfessional,
    cust_id,
    setProfessional,
    setId,
    createJob,
    startNewSession,
    sendCustomerMessage,
    turns_remaining,
<<<<<<< HEAD
    ai_response,
    current_tags,
    categories,
    is_complete,
    createJobDirect,
    isSubmitting,
=======
    is_complete,
    current_tags,
    categories,
>>>>>>> origin/And
  } = useCustomerDashboardData();

  const scrollRef = useRef(null);
  const isDown = useRef(false);
  const startX = useRef(0);
  const scrollLeftState = useRef(0);

  const attachments = [
    { id: 1, name: "Plan.pdf", type: "PDF" },
    { id: 2, name: "Invoice.jpg", type: "IMG" },
    { id: 3, name: "Wiring.png", type: "IMG" },
    { id: 4, name: "Specs.txt", type: "DOC" },
    { id: 5, name: "Setup.log", type: "LOG" },
    { id: 6, name: "Plan.pdf", type: "PDF" },
    { id: 7, name: "Invoice.jpg", type: "IMG" },
    { id: 8, name: "Wiring.png", type: "IMG" },
    { id: 9, name: "Specs.txt", type: "DOC" },
    { id: 10, name: "Setup.log", type: "LOG" },
  ];

  useEffect(() => {
    useCustomerDashboardData.getState().startNewSession();
  }, []);

  useEffect(() => {
    if (!viewSlug) return;
    if (slots.main !== viewSlug) {
      const targetSlot = Object.keys(slots).find(
        (key) => slots[key] === viewSlug,
      );
      if (targetSlot) swapSlots(targetSlot);
    }
  }, [viewSlug, slots, swapSlots]);

  useEffect(() => {
    fetchBookingsPendingJobs();
  }, [fetchBookingsPendingJobs]);

  useEffect(() => {
    const scrollContainer = scrollRef.current;
    if (!scrollContainer) return;

    const handleWheel = (e) => {
      e.preventDefault();
      e.stopPropagation();
      scrollContainer.scrollLeft += e.deltaY;
    };

    scrollContainer.addEventListener("wheel", handleWheel, { passive: false });
    return () => scrollContainer.removeEventListener("wheel", handleWheel);
  }, [slots.main]);

const [hasNavigatedForCompletion, setHasNavigatedForCompletion] = useState(false);

  useEffect(() => {
    if (is_complete && !hasNavigatedForCompletion) {
      setHasNavigatedForCompletion(true);
      navigate("/customer/bookings/JobDescriptionWorkspace");
    } else if (!is_complete && hasNavigatedForCompletion) {
      // Reset the flag when a new chat session starts and is_complete goes back to false
      setHasNavigatedForCompletion(false);
    }
  }, [is_complete, hasNavigatedForCompletion, navigate]);

  // ====================================================
  // 🗺️ OPENSTREETMAP ASYNC ASSET LOADER
  // ====================================================
  useEffect(() => {
    if (isMapOpen) {
      if (userLat && userLng) {
        setModalLat(userLat);
        setModalLng(userLng);
        setModalAddrText(userAddrText || "");
      } else {
        setModalLat(27.7172);
        setModalLng(85.324);
        setModalAddrText("");
      }

      if (!document.getElementById("leaflet-cdn-css")) {
        const link = document.createElement("link");
        link.id = "leaflet-cdn-css";
        link.rel = "stylesheet";
        link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
        document.head.appendChild(link);
      }

      if (!window.L) {
        const script = document.createElement("script");
        script.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
        script.onload = () => setMapReady(true);
        document.body.appendChild(script);
      } else {
        setMapReady(true);
      }
    } else {
      setMapReady(false);
      leafletMapRef.current = null;
      leafletMarkerRef.current = null;
    }
  }, [isMapOpen]);

  // ====================================================
  // 🗺️ MAP ENGINE INITIALIZATION AND CONTROLS
  // ====================================================
  useEffect(() => {
    if (!mapReady || !mapContainerRef.current || !window.L) return;
    const L = window.L;

    const stylizedPinIcon = L.divIcon({
      html: `<div style="font-size: 30px; transform: translate(-3px, -24px); filter: drop-shadow(2px 3px 0px rgba(0,0,0,0.6));">📍</div>`,
      className: "cute-custom-pin",
      iconSize: [30, 30],
      iconAnchor: [15, 30],
    });

    const map = L.map(mapContainerRef.current, { zoomControl: false }).setView(
      [modalLat, modalLng],
      14,
    );
    L.control.zoom({ position: "bottomright" }).addTo(map);
    leafletMapRef.current = map;

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);

    const marker = L.marker([modalLat, modalLng], {
      icon: stylizedPinIcon,
      draggable: true,
    }).addTo(map);
    leafletMarkerRef.current = marker;

    const runReverseGeocode = async (lat, lng) => {
      try {
        const resp = await fetch(
          `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}`,
        );
        if (resp.ok) {
          const data = await resp.json();
          const cleanString = data.display_name
            .split(",")
            .slice(0, 3)
            .join(",")
            .toUpperCase();
          setModalAddrText(cleanString.trim());
        }
      } catch (err) {
        console.warn("Reverse lookup throttled:", err);
      }
    };

    if (!modalAddrText) {
      runReverseGeocode(modalLat, modalLng);
    }

    marker.on("dragend", () => {
      const point = marker.getLatLng();
      setModalLat(point.lat);
      setModalLng(point.lng);
      runReverseGeocode(point.lat, point.lng);
    });

    map.on("click", (e) => {
      marker.setLatLng(e.latlng);
      setModalLat(e.latlng.lat);
      setModalLng(e.latlng.lng);
      runReverseGeocode(e.latlng.lat, e.latlng.lng);
    });

    return () => {
      map.remove();
    };
  }, [mapReady]);

  const executeModalAddressSearch = async (e) => {
    e.preventDefault();
    if (
      !modalSearchQuery.trim() ||
      !leafletMapRef.current ||
      !leafletMarkerRef.current
    )
      return;

    try {
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(modalSearchQuery)}&countrycodes=np&limit=1`,
      );
      if (response.ok) {
        const results = await response.json();
        if (results && results.length > 0) {
          const firstResult = results[0];
          const newLat = parseFloat(firstResult.lat);
          const newLng = parseFloat(firstResult.lon);

          setModalLat(newLat);
          setModalLng(newLng);

          const title = firstResult.display_name
            .split(",")
            .slice(0, 3)
            .join(",")
            .toUpperCase();
          setModalAddrText(title.trim());

          leafletMapRef.current.setView([newLat, newLng], 15);
          leafletMarkerRef.current.setLatLng([newLat, newLng]);
        } else {
          alert("NO DETECTED LOCATIONS FOUND MATCHING CONSTRAINTS WITHIN NEPAL.");
        }
      }
    } catch (err) {
      console.error("Search pipeline execution exception error:", err);
    }
  };

  const handleModalLiveTracking = () => {
    if (!navigator.geolocation) {
      alert("GEOLOCATION SELECTION SYSTEM IS NOT SUPPORTED BY THIS CLIENT BROWSER.");
      return;
    }

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords;
        setModalLat(latitude);
        setModalLng(longitude);

        if (leafletMapRef.current && leafletMarkerRef.current) {
          leafletMapRef.current.setView([latitude, longitude], 15);
          leafletMarkerRef.current.setLatLng([latitude, longitude]);
        }

        try {
          const response = await fetch(
            `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${latitude}&lon=${longitude}`,
          );
          if (!response.ok) throw new Error("Reverse lookup failed");
          const data = await response.json();
          const cleanString = data.display_name
            .split(",")
            .slice(0, 3)
            .join(",")
            .toUpperCase();
          setModalAddrText(cleanString.trim());
        } catch (err) {
          setModalAddrText("CURRENT LIVE LOCATION");
        }
      },
      (error) => {
        alert("LOCATION ACQUISITION LOCK DENIED. PLEASE ALLOW LOCATION PERMISSIONS.");
      },
      { enableHighAccuracy: true, timeout: 7000 },
    );
  };

  const handleModuleSelect = (targetSlug) => {
    navigate(`/customer/bookings/${targetSlug}`);
  };

  // Safe wrapper execution to refresh list instantly upon new creations
  const handleCreateJobFinalize = async () => {
    await createJob();
    fetchBookingsPendingJobs();
  };

  // ====================================================
  // SUB-MODULE RENDERS
  // ====================================================

  const renderAiChat = (slotKey) => {
    if (slotKey === "main") {
      const handleSend = (e) => {
        e.preventDefault();
        if (!chatInput.trim() || is_complete) return;
        sendCustomerMessage(chatInput);
        setChatInput("");
      };

      return (
        <div className="dashboard-card main-view">
          <span className="card-flag">
            INTERACTIVE DISPATCH MANAGER
            {turns_remaining !== undefined && ` — TURNS LEFT: ${turns_remaining}`}
          </span>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
            <h2 style={{ margin: 0 }}>AI CHAT TERMINAL</h2>
<<<<<<< HEAD
            <button
              type="button"
              onClick={() => {
                navigate("/customer/bookings/JobDescriptionWorkspace");
              }}
              style={{
=======
             <button
               type="button"
               onClick={() => navigate('/customer/bookings/JobDescriptionWorkspace')}
               style={{
>>>>>>> origin/And
                background: "#FF6B1A",
                color: "#0D0D0D",
                border: "none",
                borderRadius: "8px",
                padding: "8px 14px",
                fontWeight: 700,
                cursor: "pointer",
                fontSize: "12px",
                transition: "transform 120ms ease, opacity 120ms ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.opacity = 0.85;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.opacity = 1;
              }}
              onMouseDown={(e) => {
                e.currentTarget.style.transform = "scale(0.95)";
              }}
              onMouseUp={(e) => {
                e.currentTarget.style.transform = "scale(1)";
              }}
            >
              + Create Job Manually
            </button>
          </div>
          <div className="chat-box">
            {chatMessages.map((m) => (
              <p key={m.id} className={`chat-msg chat-msg--${m.sender}`}>
                <strong>{m.sender.toUpperCase()}:</strong> {m.text}
              </p>
            ))}
          </div>
          <form onSubmit={handleSend} className="chat-form">
            <input
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder={is_complete ? "Conversation finalized." : "Instruct AI..."}
              disabled={is_complete}
            />
            <button
              type="submit"
              className="chat-btn"
              disabled={is_complete || !chatInput.trim()}
            >
              Send
            </button>
          </form>
        </div>
      );
    }

    return (
      <div
        className={`dashboard-card asleep-view ${slotKey}-slot clickable`}
        onClick={() => handleModuleSelect("AiChatTerminal")}
      >
        <div className="card-header">••• AI CHAT TERMINAL</div>
        {slotKey === "sidebar" ? (
          <>
            <span className="badge badge-highlight">Live Dispatch — Active Session</span>
            <p className="card-summary">Logs Captured: {chatMessages.length}</p>
          </>
        ) : (
          <span className="badge">AI Dispatch running asleep below...</span>
        )}
      </div>
    );
  };

<<<<<<< HEAD
 

=======
>>>>>>> origin/And
  const renderJobDescription = (slotKey) => {
    if (slotKey === "main") {
      return (
        <div
          className="dashboard-card main-view"
          style={{
            display: "flex",
            flexDirection: "row",
            gap: "16px",
            width: "100%",
            boxSizing: "border-box",
            minWidth: 0,
          }}
        >
          {/* ⬅️ LEFT SIDE COLUMN */}
          <div style={{ flex: 1, display: "flex", flexDirection: "column", height: "100%", minWidth: 0 }}>
            <span className="card-flag" style={{ marginTop: "-14px" }}>EDIT OR CREATE JOB POSTING</span>
            <h3 className="title" style={{ display: "flex", alignItems: "baseline", minWidth: 0 }}>
              <span>·•TITLE:</span>
              <input
                type="text"
                value={jobTitleDraft}
                onChange={(e) => setJobTitle(e.target.value)}
                spellCheck={false}
                style={{
                  outline: "none",
                  border: "none",
                  background: "transparent",
                  font: "inherit",
                  color: "inherit",
                  padding: 0,
                  margin: 0,
                  width: "100%",
                }}
              />
              <span style={{ whiteSpace: "nowrap", flexShrink: 0 }}>•·</span>
            </h3>

            <h3 className="title">DEsCRIPTION:</h3>
            <textarea
              className="workspace-textarea"
              value={jobDescriptionDraft}
              onChange={(e) => setJobDescription(e.target.value)}
              style={{
                border: "2px dashed var(--ind-border-strong)",
                borderRadius: "4px",
                padding: "10px",
                outline: "none",
                flex: 1,
                width: "100%",
                boxSizing: "border-box",
              }}
            />
          </div>

          {/* ➡️ RIGHT SIDE COLUMN */}
          <div style={{ width: "35%", height: "100%", display: "flex", flexDirection: "column", minWidth: 0, flexShrink: 0 }}>
            <h3 className="title" dir="rtl" style={{ marginBottom: "4px" }}>AttACHMENTs</h3>

            <div style={{ position: "relative", display: "flex", alignItems: "center", width: "100%" }}>
              <button
                type="button"
                onClick={() => {
                  if (scrollRef.current) scrollRef.current.scrollBy({ left: -120, behavior: "smooth" });
                }}
                style={{
                  position: "absolute",
                  left: "-5px",
                  zIndex: 10,
                  background: "#FF6B1A",
                  color: "#0D0D0D",
                  border: "none",
                  borderRadius: "50%",
                  width: "22px",
                  height: "22px",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontWeight: "bold",
                  fontSize: "12px",
                }}
              >
                ‹
              </button>

              <div
                ref={scrollRef}
                style={{
                  display: "flex",
                  flexDirection: "row",
                  gap: "8px",
                  overflowX: "auto",
                  overflowY: "hidden",
                  scrollbarWidth: "none",
                  WebkitOverflowScrolling: "touch",
                  width: "100%",
                  padding: "6px 15px",
                  cursor: "grab",
                  userSelect: "none",
                  whiteSpace: "nowrap",
                }}
                onMouseDown={(e) => {
                  isDown.current = true;
                  if (scrollRef.current) {
                    scrollRef.current.style.cursor = "grabbing";
                    startX.current = e.pageX - scrollRef.current.offsetLeft;
                    scrollLeftState.current = scrollRef.current.scrollLeft;
                  }
                }}
                onMouseLeave={() => {
                  isDown.current = false;
                  if (scrollRef.current) scrollRef.current.style.cursor = "grab";
                }}
                onMouseUp={() => {
                  isDown.current = false;
                  if (scrollRef.current) scrollRef.current.style.cursor = "grab";
                }}
                onMouseMove={(e) => {
                  if (!isDown.current || !scrollRef.current) return;
                  e.preventDefault();
                  const x = e.pageX - scrollRef.current.offsetLeft;
                  const walk = (x - startX.current) * 1.5;
                  scrollRef.current.scrollLeft = scrollLeftState.current - walk;
                }}
              >
                {attachments.map((file) => (
                  <div
                    key={file.id}
                    style={{
                      display: "inline-flex",
                      flexDirection: "column",
                      alignItems: "center",
                      justifyContent: "center",
                      minWidth: "65px",
                      maxWidth: "65px",
                      height: "65px",
                      border: "1px solid var(--k-border-strong)",
                      borderRadius: "8px",
                      background: "var(--k-raise)",
                      color: "var(--k-ink)",
                      fontSize: "11px",
                      padding: "4px",
                      boxSizing: "border-box",
                    }}
                  >
                    <span style={{ fontWeight: 700, color: "var(--k-orange-ink)" }}>[{file.type}]</span>
                    <span style={{ fontSize: "9px", textOverflow: "ellipsis", overflow: "hidden", width: "100%", textAlign: "center" }}>
                      {file.name}
                    </span>
                  </div>
                ))}
              </div>

              <button
                type="button"
                onClick={() => {
                  if (scrollRef.current) scrollRef.current.scrollBy({ left: 120, behavior: "smooth" });
                }}
                style={{
                  position: "absolute",
                  right: "-5px",
                  zIndex: 10,
                  background: "#FF6B1A",
                  color: "#0D0D0D",
                  border: "none",
                  borderRadius: "50%",
                  width: "22px",
                  height: "22px",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontWeight: "bold",
                  fontSize: "12px",
                }}
              >
                ›
              </button>
            </div>

            <h3 className="title" dir="rtl" style={{ marginTop: "10px" }}> UsER INFo </h3>
            <div className="user-info" style={{ lineHeight: "35px" }}>
              <span style={{ display: "inline-flex", alignItems: "baseline" }}>
                <span>NAME:</span>
                <input
                  type="text"
                  value={userName}
                  onChange={(e) => setUserName(e.target.value)}
                  spellCheck={false}
                  style={{
                    outline: "none",
                    border: "none",
                    background: "transparent",
                    font: "inherit",
                    color: "inherit",
                    padding: 0,
                    margin: 0,
                    width: "auto",
                    minWidth: "50px",
                    maxWidth: "100%",
                  }}
                />
              </span>

              <span style={{ display: "inline-flex", alignItems: "baseline" }}>
                <span>CONTACT:</span>
                <input
                  type="text"
                  value={userCont}
                  onChange={(e) => setUserCont(e.target.value)}
                  spellCheck={false}
                  style={{
                    outline: "none",
                    border: "none",
                    background: "transparent",
                    font: "inherit",
                    color: "inherit",
                    padding: 0,
                    margin: 0,
                    width: "auto",
                    minWidth: "50px",
                    maxWidth: "100%",
                  }}
                />
              </span>

              <div
                onClick={() => setIsMapOpen(true)}
                style={{
                  display: "inline-flex",
                  alignItems: "baseline",
                  cursor: "pointer",
                  width: "100%",
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.opacity = 0.75)}
                onMouseLeave={(e) => (e.currentTarget.style.opacity = 1)}
              >
                <span style={{ flexShrink: 0 }}>ADDRESS:</span>
                <span
                  style={{
                    paddingLeft: "4px",
                    textTransform: "uppercase",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    color: "var(--k-orange-ink)",
                    textDecoration: "underline",
                    fontWeight: 700,
                  }}
                  title={userAddrText || "CLICK TO SET LOCATION"}
                >
                  {userAddrText || "SET LOCATION 🗺️"}
                </span>
              </div>
            </div>

            <button
              type="button"
              onClick={() => console.log("🚨 Emergency toggle triggered")}
              className="title"
              dir="rtl"
              name="emergency"
            >
              EmERGENcY ToGGLE
            </button>

            <button
              type="button"
              onClick={handleCreateJobFinalize}
              className="title"
              dir="rtl"
              name="post"
              style={{
                background: "#FF6B1A",
                color: "#0D0D0D",
                border: "none",
                borderRadius: "8px",
                padding: "10px 18px",
                fontWeight: "bold",
                cursor: "pointer",
                fontSize: "13px",
                transition: "transform 120ms ease, opacity 120ms ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.opacity = 0.85;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.opacity = 1;
              }}
              onMouseDown={(e) => {
                e.currentTarget.style.transform = "scale(0.95)";
              }}
              onMouseUp={(e) => {
                e.currentTarget.style.transform = "scale(1)";
              }}
            >
              {"<-"} Post Job
            </button>
          </div>
        </div>
      );
    }

    return (
      <div
        className={`dashboard-card asleep-view ${slotKey}-slot clickable`}
        onClick={() => handleModuleSelect("JobDescriptionWorkspace")}
      >
        <div className="card-header">••• JOB DESCRIPTION WORKSPACE</div>
        {slotKey === "sidebar" ? (
          <>
            <span className="badge">Sidebar: Description Live Glance — Draft Mode</span>
          </>
        ) : (
          <span className="badge">
            Footer: Draft character footprint: {jobDescriptionDraft.length} chars
          </span>
        )}
      </div>
    );
  };

  const renderActivePosts = (slotKey) => {
    if (slotKey === "main") {
      return (
        <div className="dashboard-card main-view" style={{ overflow: "scroll", maxHeight:"33vw" }}>
          <span className="card-flag">REAL-TIME DISPATCH PIPELINE</span>
          <h2>ACTIVE PENDING POSTS</h2>
          <button 
            onClick={fetchBookingsPendingJobs}
            style={{
              background: "transparent",
              color: "var(--k-orange-ink)",
              border: "1px solid rgba(255, 107, 26, 0.5)",
              borderRadius: "12px",
              padding: "8px 16px",
              fontWeight: 600,
              cursor: "pointer",
              marginBottom: "16px",
              width: "fit-content"
            }}
          >
            🔄 REFRESH LIVE PIPELINE
          </button>
          
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {fetchedJobs.length === 0 ? (
              <p style={{ fontFamily: "Courier New", color: "var(--k-ink-3)", fontSize: "0.9rem" }}>
                No active pending jobs found in your database instance.
              </p>
            ) : (
              fetchedJobs.map((job) => (
                <div 
                  key={job.id} 
                  style={{
                    border: "1px solid var(--k-line)",
                    borderRadius: "16px",
                    padding: "16px",
                    background: "var(--k-raise)",
                    color: "var(--k-ink)",
                    boxShadow: "0 2px 10px rgba(0, 0, 0, 0.35)"
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                    <span style={{ fontFamily: "Courier New", fontWeight: "bold", fontSize: "1.1rem" }}>
                      {job.title ? job.title.toUpperCase() : "NEW JOB REQUEST"}
                    </span>
                    <span className="badge badge-highlight" style={{ textTransform: "uppercase", fontSize: "0.75rem", padding: "4px 8px" }}>
                      ⚙️ {job.status || "PENDING"}
                    </span>
                  </div>
                  <p style={{ margin: "4px 0", fontSize: "0.9rem", color: "var(--k-ink-3)", lineHeight: "1.4" }}>
                    {job.description}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      );
    }

    return (
      <div
        className={`dashboard-card asleep-view ${slotKey}-slot clickable`}
        onClick={() => handleModuleSelect("YourActivePosts")}
      >
        <div className="card-header">••• YOUR ACTIVE POSTS</div>
        {slotKey === "sidebar" ? (
          <>
            <span className="badge badge-highlight">Network Pipeline Active</span>
            <p className="card-summary">Live Trackable: {activePostsCount} Positions</p>
          </>
        ) : (
          <span className="badge">
            Posts Monitor sleeping below — {activePostsCount} items queued
          </span>
        )}
      </div>
    );
  };

  const resolveAndRenderModule = (slotKey) => {
    const moduleName = slots[slotKey];
    switch (moduleName) {
      case "AiChatTerminal":
        return renderAiChat(slotKey);
      case "JobDescriptionWorkspace":
        return renderJobDescription(slotKey);
      case "YourActivePosts":
        return renderActivePosts(slotKey);
      default:
        return null;
    }
  };

  return (
    <div className="dashboard-grid">
      <div className="grid-main">{resolveAndRenderModule("main")}</div>
      <div className="grid-bottom">{resolveAndRenderModule("bottom")}</div>
      <div className="grid-sidebar">{resolveAndRenderModule("sidebar")}</div>

      {/* 🎯 NEO-BRUTALIST CUTE MAP PICKER POPUP MODAL */}
      {isMapOpen && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            width: "100vw",
            height: "100vh",
            backgroundColor: "rgba(0, 0, 0, 0.4)",
            zIndex: 99999,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            backdropFilter: "blur(3px)",
          }}
        >
          <div
            style={{
              background: "var(--ind-surface)",
              border: "1px solid var(--ind-border)",
              borderRadius: "16px",
              boxShadow: "var(--ind-shadow-tight)",
              width: "450px",
              maxWidth: "90%",
              padding: "20px",
              display: "flex",
              flexDirection: "column",
              gap: "12px",
              fontFamily: "inherit",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", width: "100%" }}>
              <span style={{ fontWeight: "bold", fontSize: "14px", textTransform: "uppercase", letterSpacing: "1px" }}>
                🗺️ CHOOSE DELIVERY PIN (NEPAL)
              </span>
            </div>

            <div style={{ display: "flex", gap: "6px", width: "100%" }}>
              <form onSubmit={executeModalAddressSearch} style={{ display: "flex", gap: "6px", flex: 1 }}>
                <input
                  type="text"
                  placeholder="SEARCH LALITPUR, THAMEL, ETC..."
                  value={modalSearchQuery}
                  onChange={(e) => setModalSearchQuery(e.target.value)}
                  style={{
                    flex: 1,
                    border: "1px solid var(--ind-border)",
                    borderRadius: "6px",
                    padding: "6px 10px",
                    outline: "none",
                    font: "inherit",
                    fontSize: "11px",
                    background: "var(--ind-surface-alpha-40)",
                    color: "var(--ind-white)"
                  }}
                />
                <button
                  type="submit"
                  style={{
                    background: "#FF6B1A",
                    color: "#0D0D0D",
                    border: "none",
                    borderRadius: "6px",
                    padding: "0 12px",
                    font: "inherit",
                    fontSize: "11px",
                    fontWeight: "bold",
                    cursor: "pointer"
                  }}
                >
                  FIND
                </button>
              </form>

              <button
                type="button"
                onClick={handleModalLiveTracking}
                title="Snap to My Current Position"
                style={{
                  background: "rgba(255, 107, 26, 0.12)",
                  border: "1px solid rgba(255, 107, 26, 0.4)",
                  borderRadius: "6px",
                  padding: "0 10px",
                  cursor: "pointer",
                  fontSize: "14px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                📍
              </button>
            </div>

            <div
              ref={mapContainerRef}
              style={{
                width: "100%",
                height: "260px",
                border: "1px solid var(--ind-border)",
                borderRadius: "8px",
                background: "var(--ind-surface-alpha-40)",
                position: "relative",
              }}
            />

            {/* Resolved Preview Description Output Text Block */}
            <div
              style={{
                fontSize: "11px",
                background: "var(--ind-surface-alpha-40)",
                padding: "8px",
                border: "1px dashed var(--ind-border)",
                borderRadius: "6px",
              }}
            >
              <strong style={{ color: "var(--text-secondary)" }}>SELECTED ADDRESS:</strong>
              <div
                style={{
                  textTransform: "uppercase",
                  marginTop: "2px",
                  fontWeight: "bold",
                  wordBreak: "break-word",
                }}
              >
                {modalAddrText ||
                  "DRAG THE PIN OR CLICK ON THE MAP TO CHOOSE..."}
              </div>
            </div>

            <div style={{ display: "flex", gap: "10px", marginTop: "4px" }}>
              <button
                type="button"
                onClick={() => setIsMapOpen(false)}
                style={{
                  flex: 1,
                  padding: "8px",
                  background: "var(--ind-surface-alpha-40)",
                  border: "1px solid var(--ind-border)",
                  borderRadius: "8px",
                  font: "inherit",
                  fontSize: "13px",
                  fontWeight: "bold",
                  cursor: "pointer",
                  color: "var(--text-secondary)"
                }}
              >
                CANCEL
              </button>

              <button
                type="button"
                onClick={() => {
                  setUserAddrText(modalAddrText || `POINT(${modalLng.toFixed(4)} ${modalLat.toFixed(4)})`);
                  setUserCoordinates(modalLng, modalLat);
                  setIsMapOpen(false);
                }}
                style={{
                  flex: 1,
                  padding: "8px",
                  background: "#FF6B1A",
                  border: "1px solid #FF6B1A",
                  borderRadius: "8px",
                  font: "inherit",
                  fontSize: "13px",
                  fontWeight: 700,
                  cursor: "pointer",
                  color: "#0D0D0D",
                }}
              >
                CONFIRM LOCATION
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}