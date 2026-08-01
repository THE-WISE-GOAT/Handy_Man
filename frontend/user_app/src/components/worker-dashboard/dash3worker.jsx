import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useWorkerDashboardData } from "./useWorkerDashboardData";
import "./dash3worker.css";

export default function Dash3Worker({ viewSlug }) {
  const navigate = useNavigate();
  const [chatInput, setChatInput] = useState("");
  const [activeModule, setActiveModule] = useState("interview");

  const {
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

    // editable profile state
    editableProfile,
    isSavingProfile,
    profileSaveMessage,
    setEditableProfile,
    setIsSavingProfile,
    setProfileSaveMessage,

    // user base info state
    userProfile,
    isEditingUserInfo,
    isSavingUserInfo,
    userInfoSaveMessage,
    setUserProfile,
    setIsEditingUserInfo,
    setIsSavingUserInfo,
    setUserInfoSaveMessage,

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
    updateWorkerProfile,
    loadUserProfile,
    updateUserProfile,
    loadApplicantStatus,
    setApplicationSubmitted,
  } = useWorkerDashboardData();

  const mapContainerRef = useRef(null);
  const leafletMapRef = useRef(null);
  const leafletMarkerRef = useRef(null);

  // Load applicant status on mount
  useEffect(() => {
    loadApplicantStatus();
  }, []);

  // Load user base info on mount
  useEffect(() => {
    loadUserProfile();
  }, [loadUserProfile]);

  // Refetch status after application is submitted
  useEffect(() => {
    if (applicationSubmitted) {
      const timer = setTimeout(() => loadApplicantStatus(), 1500);
      return () => clearTimeout(timer);
    }
  }, [applicationSubmitted, loadApplicantStatus]);

  // Sync activeModule with URL slug
  useEffect(() => {
    if (!viewSlug) return;
    const slugToModule = {
      MeInterview: "interview",
      MeProfile: "profile",
      MeConfiguration: "extraction",
      MeCollectedTags: "status",
    };
    const mod = slugToModule[viewSlug];
    if (mod && mod !== activeModule) {
      setActiveModule(mod);
    }
  }, [viewSlug]);

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
  // PROFILE EDIT HANDLERS
  // ====================================================
  const handleProfileChange = (field, value) => {
    setEditableProfile((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleSaveProfile = async () => {
    await updateWorkerProfile();
  };

  // ====================================================
  // RENDER: Under Review / Rejected State
  // ====================================================
  const renderStatusView = () => {
    if ((applicationSubmitted || applicantStage === "pending_admin_review") && !isApplicantRejected) {
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
              Pending Admin Approval
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
  // RENDER: AI Chat Terminal
  // ====================================================
  const renderChatTerminal = ({ isActive }) => {
    if (!isActive) {
      return (
        <div className="dashboard-card module-preview" onClick={() => setActiveModule("interview")}>
          <div className="card-header">••• AI INTERVIEW TERMINAL</div>
          <div className="main-panel">
            <p className="panel-desc">Click to open the AI interview terminal</p>
            <span className="badge">
              {chatMessages.length > 1 ? `${chatMessages.length} messages` : "Not started"}
            </span>
          </div>
        </div>
      );
    }

    if (renderStatusView()) return renderStatusView();

    const hasActiveChat = chatMessages.length > 1 || isChatComplete || isAiGenerating;

    return (
      <div className="dashboard-card slot-main">
        <div className="card-header">••• AI INTERVIEW TERMINAL</div>
        <div className="main-panel chat-terminal-panel">
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
            <>
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
            </>
          )}
        </div>
      </div>
    );
  };

  // ====================================================
  // RENDER: Extraction & Submission Module
  // ====================================================
  const renderExtractionModule = ({ isActive }) => {
    if (!isActive) {
      return (
        <div className="dashboard-card module-preview" onClick={() => setActiveModule("extraction")}>
          <div className="card-header">••• EXTRACTION & SUBMISSION</div>
          <div className="main-panel">
            <p className="panel-desc">Click to view extraction details and submit</p>
            <span className="badge">
              {extractedProfile ? extractedProfile.job_category || "Profile ready" : "Awaiting extraction"}
            </span>
          </div>
        </div>
      );
    }

    return (
      <div className="dashboard-card slot-main">
        <div className="card-header">••• EXTRACTION & SUBMISSION</div>
        <div className="main-panel sidebar-content">
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
    );
  };

  // ====================================================
  // RENDER: Worker Profile Module
  // ====================================================
  const renderProfileModule = ({ isActive }) => {
    const displayName = [userProfile.firstName, userProfile.lastName].filter(Boolean).join(" ") || userProfile.username || "Worker";
    const locationLine = [addressText, phoneNumber].filter(Boolean).join(" | ") || "No location set";
    const primaryTag = extractedProfile?.job_category || editableProfile.job_category || "";

    if (!isActive) {
      return (
        <div className="dashboard-card module-preview" onClick={() => setActiveModule("profile")}>
          <div className="card-header">••• WORKER PROFILE</div>
          <div className="main-panel">
            <p className="panel-desc">Click to view full profile</p>
            <div className="profile-preview-tags">
              <span className="badge badge-highlight">{displayName}</span>
              <span className="badge">ID: {userProfile.id || "—"}</span>
              {primaryTag && <span className="badge">{primaryTag}</span>}
            </div>
            <p className="card-summary">{locationLine}</p>
          </div>
        </div>
      );
    }

    const renderEmpty = (label, value) => (
      <div className="profile-detail-row">
        <span className="profile-detail-label">{label}:</span>
        <span className="profile-detail-value profile-detail-value--empty">{value || "None"}</span>
      </div>
    );

    return (
      <div className="dashboard-card slot-main">
        <div className="card-header">••• WORKER PROFILE</div>
        <div className="main-panel profile-editor">
          {/* ========== BASE USER INFO (EDITABLE) ========== */}
          <div className="profile-section">
            <div className="profile-section-header">
              <h3>Personal Information</h3>
              {!isEditingUserInfo ? (
                <button
                  type="button"
                  className="icon-btn"
                  onClick={() => setIsEditingUserInfo(true)}
                  title="Edit personal information"
                >
                  ✏️
                </button>
              ) : (
                <button
                  type="button"
                  className="icon-btn icon-btn--cancel"
                  onClick={() => {
                    setIsEditingUserInfo(false);
                    setUserInfoSaveMessage(null);
                  }}
                  title="Cancel editing"
                >
                  ✕
                </button>
              )}
            </div>

            {!isEditingUserInfo ? (
              <div className="profile-read-only">
                <div className="profile-detail-row">
                  <span className="profile-detail-label">Name:</span>
                  <span className="profile-detail-value">{displayName}</span>
                </div>
                <div className="profile-detail-row">
                  <span className="profile-detail-label">User ID:</span>
                  <span className="profile-detail-value">{userProfile.id || "—"}</span>
                </div>
                <div className="profile-detail-row">
                  <span className="profile-detail-label">Email:</span>
                  <span className="profile-detail-value">{userProfile.email || "—"}</span>
                </div>
                <div className="profile-detail-row">
                  <span className="profile-detail-label">Address:</span>
                  <span className="profile-detail-value">{addressText || "—"}</span>
                </div>
                <div className="profile-detail-row">
                  <span className="profile-detail-label">Phone:</span>
                  <span className="profile-detail-value">{phoneNumber || "—"}</span>
                </div>
              </div>
            ) : (
              <div className="profile-edit-form">
                <div className="profile-field">
                  <label>First Name</label>
                  <input
                    type="text"
                    value={userProfile.firstName}
                    onChange={(e) => setUserProfile((prev) => ({ ...prev, firstName: e.target.value }))}
                  />
                </div>
                <div className="profile-field">
                  <label>Last Name</label>
                  <input
                    type="text"
                    value={userProfile.lastName}
                    onChange={(e) => setUserProfile((prev) => ({ ...prev, lastName: e.target.value }))}
                  />
                </div>
                <div className="profile-field">
                  <label>Email</label>
                  <input
                    type="email"
                    value={userProfile.email}
                    onChange={(e) => setUserProfile((prev) => ({ ...prev, email: e.target.value }))}
                  />
                </div>
                <div className="profile-field">
                  <label>Username</label>
                  <input
                    type="text"
                    value={userProfile.username}
                    onChange={(e) => setUserProfile((prev) => ({ ...prev, username: e.target.value }))}
                  />
                </div>
                <div className="profile-field">
                  <label>New Password {userProfile.password ? "(leave blank to keep current)" : ""}</label>
                  <input
                    type="password"
                    value={userProfile.password || ""}
                    onChange={(e) => setUserProfile((prev) => ({ ...prev, password: e.target.value }))}
                    placeholder="Enter new password"
                  />
                </div>

                <div className="profile-actions">
                  <button
                    type="button"
                    className="submit-app-btn"
                    onClick={updateUserProfile}
                    disabled={isSavingUserInfo}
                  >
                    {isSavingUserInfo ? "Saving..." : "Save Changes"}
                  </button>
                  {userInfoSaveMessage && (
                    <span className={`profile-save-message ${userInfoSaveMessage.includes("Failed") ? "profile-save-message--error" : "profile-save-message--success"}`}>
                      {userInfoSaveMessage}
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* ========== WORKER SPECIFIC DETAILS (READ-ONLY) ========== */}
          <div className="profile-section profile-section--worker">
            <div className="profile-section-header">
              <h3>Worker Details</h3>
              <span className="badge badge--readonly">Read-Only</span>
            </div>
            <div className="profile-read-only-grid">
              {renderEmpty("Job Category", extractedProfile?.job_category || editableProfile.job_category)}
              {renderEmpty("Category Tag", extractedProfile?.category_tag || editableProfile.category_tag)}
              {renderEmpty("Specialities", (extractedProfile?.specialities || editableProfile.specialities || [])?.length > 0 ? (extractedProfile?.specialities || editableProfile.specialities || []).join(", ") : "None")}
              {renderEmpty("Tools", (extractedProfile?.specialized_tools_or_equipment || editableProfile.specialized_tools_or_equipment || [])?.length > 0 ? (extractedProfile?.specialized_tools_or_equipment || editableProfile.specialized_tools_or_equipment || []).join(", ") : "None")}
              {renderEmpty("Years Experience", extractedProfile?.years_experience ?? editableProfile.years_experience)}
              {renderEmpty("License / Certification", extractedProfile?.license_or_certification || editableProfile.license_or_certification)}
              {renderEmpty("Job Description", extractedProfile?.job_description || editableProfile.job_description)}
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderStatusModule = ({ isActive }) => {
    if (!isActive) {
      return (
        <div className="dashboard-card module-preview" onClick={() => setActiveModule("status")}>
          <div className="card-header">••• INTERVIEW STATUS</div>
          <div className="main-panel">
            <p className="panel-desc">Click to view interview status</p>
            <span className="badge">Stage: {applicantStage}</span>
          </div>
        </div>
      );
    }

    return (
      <div className="dashboard-card slot-main">
        <div className="card-header">••• INTERVIEW STATUS</div>
        <div className="main-panel">
          <h3>Current Stage: {applicantStage}</h3>
          <div className="status-badges">
            {isApplicantComplete && <span className="badge badge-highlight">Complete</span>}
            {isApplicantRejected && <span className="badge badge--rejected">Rejected</span>}
            {!isApplicantComplete && !isApplicantRejected && (
              <span className="badge">In Progress</span>
            )}
          </div>
          {rejectionReason && (
            <div className="rejection-reason-box">
              <strong>Reason:</strong> {rejectionReason}
            </div>
          )}
        </div>
      </div>
    );
  };

  // ====================================================
  // RESOLVE MODULE BY ACTIVE STATE
  // ====================================================
  const modules = [
    { key: "interview", label: "AI Interview Terminal" },
    { key: "extraction", label: "Extraction & Submission" },
    { key: "profile", label: "Worker Profile" },
    { key: "status", label: "Interview Status" },
  ];

  const activeModuleConfig = modules.find((m) => m.key === activeModule);
  const inactiveModules = modules.filter((m) => m.key !== activeModule);

  const renderActiveModule = () => {
    switch (activeModule) {
      case "interview":
        return renderChatTerminal({ isActive: true });
      case "extraction":
        return renderExtractionModule({ isActive: true });
      case "profile":
        return renderProfileModule({ isActive: true });
      case "status":
        return renderStatusModule({ isActive: true });
      default:
        return renderChatTerminal({ isActive: true });
    }
  };

  const renderInactiveModule = (mod) => {
    switch (mod.key) {
      case "interview":
        return renderChatTerminal({ isActive: false });
      case "extraction":
        return renderExtractionModule({ isActive: false });
      case "profile":
        return renderProfileModule({ isActive: false });
      case "status":
        return renderStatusModule({ isActive: false });
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
            backgroundColor: "rgba(0, 0, 0, 0.6)", zIndex: 99999, display: "flex",
            alignItems: "center", justifyContent: "center", backdropFilter: "blur(3px)"
          }}
        >
          <div
            style={{
              background: "var(--ind-surface)", border: "1px solid var(--ind-border)", borderRadius: "16px",
              boxShadow: "var(--ind-shadow-tight)", width: "450px", maxWidth: "90%",
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
                  flex: 1, border: "1px solid var(--ind-border)", borderRadius: "6px",
                  padding: "6px 10px", outline: "none", font: "inherit", fontSize: "11px",
                  background: "var(--ind-surface-alpha-40)", color: "var(--ind-white)"
                }}
              />
              <button
                type="submit"
                style={{
                  background: "#FF6B1A", color: "#0D0D0D", border: "none",
                  borderRadius: "6px", padding: "0 12px", font: "inherit",
                  fontSize: "11px", fontWeight: 700, cursor: "pointer"
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
                  background: "var(--k-wash)", border: "1px solid rgba(255, 107, 26, 0.4)", borderRadius: "6px",
                  padding: "0 10px", cursor: "pointer", fontSize: "14px", display: "flex",
                  alignItems: "center", justifyContent: "center"
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
              width: "100%", height: "260px", border: "1px solid var(--ind-border)",
              borderRadius: "8px", background: "var(--ind-surface-alpha-40)", position: "relative",
            }}
          />

          <div style={{ fontSize: "11px", background: "var(--ind-surface-alpha-40)", padding: "8px", border: "1px dashed var(--ind-border)", borderRadius: "6px" }}>
            <strong style={{ color: "var(--text-secondary)" }}>SELECTED ADDRESS:</strong>
            <div style={{ textTransform: "uppercase", marginTop: "2px", fontWeight: "bold", wordBreak: "break-word" }}>
              {modalAddrText || "DRAG THE PIN OR CLICK ON THE MAP TO CHOOSE..."}
            </div>
          </div>

          <div style={{ display: "flex", gap: "10px", marginTop: "4px" }}>
            <button
              type="button"
              onClick={() => setIsMapOpen(false)}
                style={{
                  flex: 1, padding: "8px", background: "var(--ind-surface-alpha-40)", border: "1px solid var(--ind-border)",
                  borderRadius: "8px", font: "inherit", fontSize: "13px", fontWeight: "bold",
                  cursor: "pointer", color: "var(--text-secondary)"
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
                  flex: 1, padding: "8px", background: "#FF6B1A", border: "1px solid #FF6B1A",
                  borderRadius: "8px", font: "inherit", fontSize: "13px", fontWeight: 700,
                  cursor: "pointer", color: "#0D0D0D"
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
  return (
    <div className="worker-me-canvas-grid">
      <div className="grid-area-main">
        {renderActiveModule()}
      </div>

      <div className="grid-area-sidebar">
        {inactiveModules.map((mod) => (
          <div key={mod.key} className="module-preview-wrapper">
            {renderInactiveModule(mod)}
          </div>
        ))}
      </div>

      {renderMapModal()}
    </div>
  );
}
