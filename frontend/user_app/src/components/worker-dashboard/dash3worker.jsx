import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useWorkerDashboardData } from "./useWorkerDashboardData";
import "./dash3worker.css";

export default function Dash3Worker({ viewSlug }) {
  const navigate = useNavigate();
  const [chatInput, setChatInput] = useState("");

  const {
    meSlots,
    swapMeSlots,
    interviewStatusText,
    profileCredentialsText,
    envConfigParametersText,
    scrapedTagsMatchText,

    // onboarding state
    applicantStage,
    isApplicantComplete,
    isApplicantRejected,
    rejectionReason,
    workerChatId,
    workerId,
    phoneNumber,
    addressText,
    latitude,
    longitude,
    extractedProfile,
    isSubmittingApplication,
    applicationSubmitted,

    // chat state
    chatMessages,
    aiResponse,
    isAiGenerating,
    isChatComplete,
    isChatRejected,
    turnsUsed,
    turnsRemaining,
    scenarioQuestion,

    // map state
    isMapOpen,
    mapReady,
    modalSearchQuery,
    modalLat,
    modalLng,
    modalAddrText,

    // actions
    setPhoneNumber,
    setAddressText,
    setLatitude,
    setLongitude,
    addChatMessage,
    setIsAiGenerating,
    setIsChatComplete,
    setIsChatRejected,
    setTurnsUsed,
    setTurnsRemaining,
    setScenarioQuestion,
    setIsMapOpen,
    setMapReady,
    setModalSearchQuery,
    setModalLat,
    setModalLng,
    setModalAddrText,
    startWorkerInterview,
    sendWorkerMessage,
    fetchWorkerSummary,
    submitApplication,
    loadApplicantStatus,
    setApplicationSubmitted,
  } = useWorkerDashboardData();

  const mapContainerRef = useRef(null);
  const leafletMapRef = useRef(null);
  const leafletMarkerRef = useRef(null);
  const scrollRef = useRef(null);

  // Load applicant status on mount
  useEffect(() => {
    loadApplicantStatus();
  }, [loadApplicantStatus]);

  // Refetch status after application is submitted
  useEffect(() => {
    if (applicationSubmitted) {
      const timer = setTimeout(() => loadApplicantStatus(), 1500);
      return () => clearTimeout(timer);
    }
  }, [applicationSubmitted, loadApplicantStatus]);

  // Route state synchronization
  useEffect(() => {
    if (!viewSlug) return;
    const currentSlots = meSlots || {};
    if (currentSlots.main !== viewSlug) {
      const targetSlot = Object.keys(currentSlots).find(
        (key) => currentSlots[key] === viewSlug
      );
      if (targetSlot) {
        swapMeSlots(targetSlot);
      }
    }
  }, [viewSlug, meSlots, swapMeSlots]);

  // ====================================================
  // MAP ASSET LOADER (reused from customer dashboard)
  // ====================================================
  useEffect(() => {
    if (isMapOpen) {
      if (latitude && longitude) {
        setModalLat(latitude);
        setModalLng(longitude);
        setModalAddrText(addressText || "");
      } else {
        setModalLat(27.7172);
        setModalLng(85.3240);
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
  // MAP ENGINE (reused from customer dashboard)
  // ====================================================
  useEffect(() => {
    if (!mapReady || !mapContainerRef.current || !window.L) return;
    const L = window.L;

    const stylizedPinIcon = L.divIcon({
      html: `<div style="font-size: 30px; transform: translate(-3px, -24px); filter: drop-shadow(2px 3px 0px rgba(0,0,0,0.6));">📍</div>`,
      className: "cute-custom-pin",
      iconSize: [30, 30],
      iconAnchor: [15, 30]
    });

    const map = L.map(mapContainerRef.current, { zoomControl: false }).setView([modalLat, modalLng], 14);
    L.control.zoom({ position: 'bottomright' }).addTo(map);
    leafletMapRef.current = map;

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    const marker = L.marker([modalLat, modalLng], { icon: stylizedPinIcon, draggable: true }).addTo(map);
    leafletMarkerRef.current = marker;

    const runReverseGeocode = async (lat, lng) => {
      try {
        const resp = await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}`);
        if (resp.ok) {
          const data = await resp.json();
          const cleanString = data.display_name.split(",").slice(0, 3).join(",").toUpperCase();
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
    if (!modalSearchQuery.trim() || !leafletMapRef.current || !leafletMarkerRef.current) return;

    try {
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(modalSearchQuery)}&countrycodes=np&limit=1`
      );
      if (response.ok) {
        const results = await response.json();
        if (results && results.length > 0) {
          const firstResult = results[0];
          const newLat = parseFloat(firstResult.lat);
          const newLng = parseFloat(firstResult.lon);

          setModalLat(newLat);
          setModalLng(newLng);

          const title = firstResult.display_name.split(",").slice(0, 3).join(",").toUpperCase();
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
            `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${latitude}&lon=${longitude}`
          );
          if (!response.ok) throw new Error("Reverse lookup failed");
          const data = await response.json();
          const cleanString = data.display_name.split(",").slice(0, 3).join(",").toUpperCase();
          setModalAddrText(cleanString.trim());
        } catch (err) {
          setModalAddrText("CURRENT LIVE LOCATION");
        }
      },
      (error) => {
        alert("LOCATION ACQUISITION LOCK DENIED. PLEASE ALLOW LOCATION PERMISSIONS.");
      },
      { enableHighAccuracy: true, timeout: 7000 }
    );
  };

  const handleModuleSelect = (targetSlug) => {
    navigate(`/worker/me/${targetSlug}`);
  };

  // ====================================================
  // CHAT HANDLERS
  // ====================================================
  const handleSendChat = (e) => {
    e.preventDefault();
    if (!chatInput.trim() || isAiGenerating || isChatComplete) return;
    sendWorkerMessage(chatInput);
    setChatInput("");
  };

  // ====================================================
  // SUBMIT HANDLER
  // ====================================================
  const handleSubmitApplication = async () => {
    await submitApplication();
  };

  const confirmMapLocation = () => {
    setAddressText(modalAddrText || `POINT(${modalLng.toFixed(4)} ${modalLat.toFixed(4)})`);
    setLatitude(modalLat);
    setLongitude(modalLng);
    setIsMapOpen(false);
  };

  // ====================================================
  // RENDER: Under Review / Rejected State
  // ====================================================
  const renderStatusView = () => {
    if (applicationSubmitted && !isApplicantRejected) {
      return (
        <div className="dashboard-card slot-main">
          <div className="card-header">••• APPLICATION STATUS</div>
          <div className="main-panel">
            <h2>Under Review</h2>
            <p className="panel-desc">
              Your application has been submitted and is currently under admin review.
              You will be notified once a decision is made.
            </p>
            <div className="status-badge status-badge--review">
              Pending Admin Review
            </div>
          </div>
        </div>
      );
    }

    if (isApplicantRejected) {
      return (
        <div className="dashboard-card slot-main">
          <div className="card-header">••• APPLICATION STATUS</div>
          <div className="main-panel">
            <h2>Application Not Approved</h2>
            <p className="panel-desc">
              Your application was not approved at this time.
            </p>
            {rejectionReason && (
              <div className="rejection-reason-box">
                <strong>Reason:</strong> {rejectionReason}
              </div>
            )}
          </div>
        </div>
      );
    }

    return null;
  };

  // ====================================================
  // RENDER: Onboarding Interview (main slot)
  // ====================================================
  const renderOnboardingMain = () => {
    if (renderStatusView()) return renderStatusView();

    const hasActiveChat = chatMessages.length > 1 || isChatComplete || isAiGenerating;

    return (
      <div className="dashboard-card slot-main">
        <div className="card-header">••• WORKER ONBOARDING INTERVIEW</div>
        <div className="main-panel onboarding-main-panel">
          {!hasActiveChat && !applicationSubmitted ? (
            <div className="start-interview-prompt">
              <h3>Ready to begin your onboarding interview?</h3>
              <p className="panel-desc">
                The AI will ask about your skills, experience, and tools to build your worker profile.
              </p>
              <button
                type="button"
                className="submit-app-btn"
                onClick={startWorkerInterview}
                disabled={isAiGenerating}
              >
                {isAiGenerating ? "Starting..." : "Start Onboarding Interview"}
              </button>
            </div>
          ) : (
            <div className="onboarding-layout">
              {/* LEFT: AI Chat Terminal */}
              <div className="onboarding-chat-section">
                <h3>AI Interview Terminal</h3>
                {turnsRemaining !== undefined && (
                  <span className="turns-badge">TURNS LEFT: {turnsRemaining}</span>
                )}
                <div className="chat-box">
                  {chatMessages.map((m) => (
                    <p key={m.id} className={`chat-msg chat-msg--${m.sender}`}>
                      <strong>{m.sender.toUpperCase()}:</strong> {m.text}
                    </p>
                  ))}
                  {isAiGenerating && (
                    <p className="chat-msg chat-msg--assistant">
                      <strong>ASSISTANT:</strong> <em>typing...</em>
                    </p>
                  )}
                </div>
                <form onSubmit={handleSendChat} className="chat-form">
                  <input
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    placeholder={isChatComplete ? "Conversation finalized." : "Instruct AI..."}
                    disabled={isChatComplete || isAiGenerating}
                  />
                  <button
                    type="submit"
                    className="chat-btn"
                    disabled={isChatComplete || isAiGenerating || !chatInput.trim()}
                  >
                    Send
                  </button>
                </form>
              </div>

              {/* RIGHT: Live Extraction + Location + Submit */}
              <div className="onboarding-sidebar-section">
                {/* Live Extraction Module */}
                <div className="extraction-panel">
                  <h3>Live Extraction</h3>
                  {extractedProfile ? (
                    <div className="extracted-data">
                      <div className="extracted-row">
                        <span className="extracted-label">Job Category:</span>
                        <span className="extracted-value">{extractedProfile.job_category || "—"}</span>
                      </div>
                      <div className="extracted-row">
                        <span className="extracted-label">Category Tag:</span>
                        <span className="extracted-value">{extractedProfile.category_tag || "—"}</span>
                      </div>
                      <div className="extracted-row">
                        <span className="extracted-label">Specialities:</span>
                        <span className="extracted-value">
                          {extractedProfile.specialities?.length > 0
                            ? extractedProfile.specialities.join(", ")
                            : "—"}
                        </span>
                      </div>
                      <div className="extracted-row">
                        <span className="extracted-label">Years Experience:</span>
                        <span className="extracted-value">{extractedProfile.years_experience ?? "—"}</span>
                      </div>
                      <div className="extracted-row">
                        <span className="extracted-label">Tools:</span>
                        <span className="extracted-value">
                          {extractedProfile.specialized_tools_or_equipment?.length > 0
                            ? extractedProfile.specialized_tools_or_equipment.join(", ")
                            : "—"}
                        </span>
                      </div>
                      <div className="extracted-row">
                        <span className="extracted-label">License:</span>
                        <span className="extracted-value">{extractedProfile.license_or_certification || "—"}</span>
                      </div>
                    </div>
                  ) : (
                    <p className="panel-desc">
                      {isChatComplete
                        ? "Finalizing profile extraction..."
                        : "Profile data will appear here as the AI interview progresses."}
                    </p>
                  )}
                </div>

                {/* Location Module */}
                <div className="location-panel">
                  <h3>Location & Contact</h3>
                  <div className="location-form">
                    <label>
                      Phone Number
                      <input
                        type="tel"
                        value={phoneNumber}
                        onChange={(e) => setPhoneNumber(e.target.value)}
                        placeholder="+977 98XXXXXXXX"
                      />
                    </label>
                    <label>
                      Address
                      <input
                        type="text"
                        value={addressText}
                        onChange={(e) => setAddressText(e.target.value)}
                        placeholder="Click map to set address"
                        readOnly
                      />
                    </label>
                    <button
                      type="button"
                      className="map-open-btn"
                      onClick={() => setIsMapOpen(true)}
                    >
                      📍 {addressText ? "Change Location" : "Pin Your Location"}
                    </button>
                  </div>
                </div>

                {/* Submit Button */}
                {!applicationSubmitted && !isApplicantRejected && (
                  <button
                    type="button"
                    className="submit-app-btn"
                    onClick={handleSubmitApplication}
                    disabled={isSubmittingApplication || isChatComplete === false}
                  >
                    {isSubmittingApplication ? "Submitting..." : "Send Application"}
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  // ====================================================
  // RENDER: Location Module (sidebar slot)
  // ====================================================
  const renderLocationSidebar = () => (
    <div
      className={`dashboard-card asleep-view sidebar-slot clickable`}
      onClick={() => handleModuleSelect("MeInterview")}
    >
      <div className="card-header">••• LOCATION MODULE</div>
      {addressText ? (
        <>
          <span className="badge badge-highlight">Location Pinned</span>
          <p className="card-summary">{addressText}</p>
        </>
      ) : (
        <span className="badge">Click to pin your location on the map</span>
      )}
    </div>
  );

  // ====================================================
  // RENDER: Extraction Sidebar
  // ====================================================
  const renderExtractionSidebar = () => (
    <div
      className={`dashboard-card asleep-view sidebar-slot clickable`}
      onClick={() => handleModuleSelect("MeInterview")}
    >
      <div className="card-header">••• LIVE EXTRACTION</div>
      {extractedProfile ? (
        <>
          <span className="badge badge-highlight">Profile Extracted</span>
          <p className="card-summary">
            {extractedProfile.job_category} • {extractedProfile.years_experience} yrs exp
          </p>
        </>
      ) : (
        <span className="badge">AI extraction in progress...</span>
      )}
    </div>
  );

  // ====================================================
  // RESOLVE MODULE
  // ====================================================
  const resolveModuleBySlot = (slotKey) => {
    const currentSlots = meSlots || {};
    switch (currentSlots[slotKey]) {
      case "MeInterview":
        return renderOnboardingMain();
      case "MeProfile":
        return renderLocationSidebar();
      case "MeConfiguration":
        return renderExtractionSidebar();
      case "MeCollectedTags":
        return (
          <div
            className={`dashboard-card asleep-view ${slotKey}-slot clickable`}
            onClick={() => handleModuleSelect("MeCollectedTags")}
          >
            <div className="card-header">••• ITEM LABELING CLASSIFICATION LOGS</div>
            <span className="badge">Interview status: {applicantStage}</span>
          </div>
        );
      default:
        return null;
    }
  };

  // ====================================================
  // MAP MODAL (reused from customer dashboard)
  // ====================================================
  const renderMapModal = () => {
    if (!isMapOpen) return null;

    return (
      <div
        style={{
          position: "fixed", top: 0, left: 0, width: "100vw", height: "100vh",
          backgroundColor: "rgba(0, 0, 0, 0.4)", zIndex: 99999, display: "flex",
          alignItems: "center", justifyContent: "center", backdropFilter: "blur(3px)"
        }}
      >
        <div
          style={{
            background: "#ffffff", border: "3px solid #000000", borderRadius: "16px",
            boxShadow: "8px 8px 0px #000000", width: "450px", maxWidth: "90%",
            padding: "20px", display: "flex", flexDirection: "column", gap: "12px",
            fontFamily: "inherit"
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
                  flex: 1, border: "2px solid #000000", borderRadius: "6px",
                  padding: "6px 10px", outline: "none", font: "inherit", fontSize: "11px"
                }}
              />
              <button
                type="submit"
                style={{
                  background: "#000000", color: "#ffffff", border: "none",
                  borderRadius: "6px", padding: "0 12px", font: "inherit",
                  fontSize: "11px", fontWeight: "bold", cursor: "pointer"
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
                background: "#e0f2fe", border: "2px solid #000000", borderRadius: "6px",
                padding: "0 10px", cursor: "pointer", fontSize: "14px", display: "flex",
                alignItems: "center", justifyContent: "center", boxShadow: "2px 2px 0px #000000"
              }}
              onMouseDown={(e) => e.currentTarget.style.transform = "translate(1px, 1px)"}
              onMouseUp={(e) => e.currentTarget.style.transform = "none"}
            >
              📍
            </button>
          </div>

          <div
            ref={mapContainerRef}
            style={{
              width: "100%", height: "260px", border: "2px solid #000000",
              borderRadius: "8px", background: "#f0f0f0", position: "relative",
              boxShadow: "inset 2px 2px 5px rgba(0,0,0,0.1)"
            }}
          />

          <div style={{ fontSize: "11px", background: "#f9f9f9", padding: "8px", border: "1px dashed #000", borderRadius: "6px" }}>
            <strong style={{ color: "#333" }}>SELECTED ADDRESS:</strong>
            <div style={{ textTransform: "uppercase", marginTop: "2px", fontWeight: "bold", wordBreak: "break-word" }}>
              {modalAddrText || "DRAG THE PIN OR CLICK ON THE MAP TO CHOOSE..."}
            </div>
          </div>

          <div style={{ display: "flex", gap: "10px", marginTop: "4px" }}>
            <button
              type="button"
              onClick={() => setIsMapOpen(false)}
              style={{
                flex: 1, padding: "8px", background: "#f0f0f0", border: "2px solid #000",
                borderRadius: "8px", font: "inherit", fontSize: "13px", fontWeight: "bold",
                cursor: "pointer", boxShadow: "2px 2px 0px #000"
              }}
              onMouseDown={(e) => e.currentTarget.style.transform = "translate(2px, 2px)"}
              onMouseUp={(e) => e.currentTarget.style.transform = "none"}
            >
              CANCEL
            </button>

            <button
              type="button"
              onClick={confirmMapLocation}
              style={{
                flex: 1, padding: "8px", background: "palegreen", border: "2px solid #000",
                borderRadius: "8px", font: "inherit", fontSize: "13px", fontWeight: "bold",
                cursor: "pointer", boxShadow: "2px 2px 0px #000", color: "darkslategray"
              }}
              onMouseDown={(e) => e.currentTarget.style.transform = "translate(2px, 2px)"}
              onMouseUp={(e) => e.currentTarget.style.transform = "none"}
            >
              CONFIRM LOCATION
            </button>
          </div>
        </div>
      </div>
    );
  };

  // ====================================================
  // MAIN RENDER
  // ====================================================
  const mainContent = resolveModuleBySlot("main");
  const sidebarContent = resolveModuleBySlot("sidebar");
  const bottomLeftContent = resolveModuleBySlot("bottomLeft");
  const bottomRightContent = resolveModuleBySlot("bottomRight");

  return (
    <div className="worker-me-canvas-grid">
      <div className="grid-area-main">
        {mainContent || <div className="dashboard-card slot-main"><div className="main-panel"><p className="panel-desc">Loading onboarding module…</p></div></div>}
      </div>

      <div className="grid-area-sidebar">
        {sidebarContent || <div className="dashboard-card asleep-view sidebar-slot"><div className="card-header">••• SIDEBAR</div><span className="badge">Loading…</span></div>}
      </div>

      <div className="grid-area-bottom-left">
        {bottomLeftContent || <div className="dashboard-card asleep-view bottomLeft-slot"><div className="card-header">••• BOTTOM LEFT</div><span className="badge">Loading…</span></div>}
      </div>

      <div className="grid-area-bottom-right">
        {bottomRightContent || <div className="dashboard-card asleep-view bottomRight-slot"><div className="card-header">••• BOTTOM RIGHT</div><span className="badge">Loading…</span></div>}
      </div>

      {renderMapModal()}
    </div>
  );
}
