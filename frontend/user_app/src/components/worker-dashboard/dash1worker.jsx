// components/worker-dashboard/dash1worker.jsx
import React, { useState, useEffect, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useWorkerDashboardData } from "./useWorkerDashboardData";
import "./dash1worker.css";

export default function Dash1Worker({ viewSlug }) {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const {
    workspaceSlots,
    swapWorkspaceSlots,
    mapStatus,
    bidsPipelineText,
    jobSpecsText,
    activeJob,
    jobDetailModal,
    openJobDetailModal,
    closeJobDetailModal,
    isInterested,
    expressInterest,
    workerChatId,
    matchedJobs,
    fetchMatchedJobs,
    setActiveJob,
    chatMessages,
    connectWorkerChat,
    sendHumanMessage,
    appendMessage,
    disconnectWorkerChat,
    fetchChatHistory,
    loadApplicantStatus,
    userProfile,
  } = useWorkerDashboardData();

  // ── Full-width view toggle for WorkspaceJobDetails ──
  const [showBidForm, setShowBidForm] = useState(false);
  const [bidAmount, setBidAmount] = useState("");

   const handleBidPlaced = async () => {
    if (!bidAmount || !activeJob) return;
    try {
      const token = localStorage.getItem("handy_man_access_token");
      const response = await fetch(
        `http://127.0.0.1:8000/jobs/${activeJob.job_id}/bid`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            bid_amount: parseFloat(bidAmount),
            bid_message: "",
          }),
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      // ── Instantly update local chat state on success ──
      const workerName = userProfile?.username || userProfile?.firstName || "Worker";
      appendMessage("system", `${workerName} placed a bid: Rs ${bidAmount}`, "BID SYSTEM");
    } catch (error) {
      console.error("Failed to place bid:", error);
    }
    setShowBidForm(false);
    setBidAmount("");
  };

  const messagesEndRef = useRef(null);
  const [chatInput, setChatInput] = useState("");
  const [isBidMode, setIsBidMode] = useState(false);

  const submitInlineBid = async (amount) => {
    if (!activeJob) return;
    const token = localStorage.getItem("handy_man_access_token");
    const response = await fetch(
      `http://127.0.0.1:8000/jobs/${activeJob.job_id}/bid`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          bid_amount: parseFloat(amount),
          bid_message: "",
        }),
      }
    );
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    const workerName = userProfile?.firstName || userProfile?.lastName
      ? `${userProfile?.firstName || ""} ${userProfile?.lastName || ""}`.trim()
      : userProfile?.username || "Worker";
    appendMessage("system", `${workerName} placed a bid: Rs ${amount}`, "BID SYSTEM");
  };

  useEffect(() => {
    useWorkerDashboardData.getState().loadApplicantStatus();
    useWorkerDashboardData.getState().fetchMatchedJobs();
  }, []);

  useEffect(() => {
    const jobIdParam = searchParams.get("jobId");
    if (!activeJob && jobIdParam) {
      const found = matchedJobs.find((j) => String(j.job_id) === String(jobIdParam));
      if (found) {
        setActiveJob(found);
      }
    }
  }, [searchParams, matchedJobs, activeJob, setActiveJob]);

  useEffect(() => {
    return () => useWorkerDashboardData.getState().disconnectWorkerChat();
  }, []);

  useEffect(() => {
    if (activeJob && activeJob.booking_chat_id) {
      useWorkerDashboardData.getState().connectWorkerChat(activeJob.booking_chat_id);
      useWorkerDashboardData.getState().fetchChatHistory(activeJob.booking_chat_id);
    }
  }, [activeJob]);

  useEffect(() => {
    if (viewSlug) {
      useWorkerDashboardData.getState().swapWorkspaceSlots(viewSlug);
    }
  }, [viewSlug]);

  useEffect(() => {
    if (jobDetailModal) {
      useWorkerDashboardData.getState().openJobDetailModal(jobDetailModal);
    }
  }, [jobDetailModal]);

  useEffect(() => {
    const timer = setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, 100);
    return () => clearTimeout(timer);
  }, [chatMessages, showBidForm]);

  useEffect(() => {
    if (activeJob && activeJob.booking_chat_id) {
      useWorkerDashboardData.getState().connectWorkerChat(activeJob.booking_chat_id);
      useWorkerDashboardData.getState().fetchChatHistory(activeJob.booking_chat_id);
    }
  }, [activeJob]);

  useEffect(() => {
    if (!viewSlug) return;

    if (workspaceSlots.main !== viewSlug) {
      const targetSlot = Object.keys(workspaceSlots).find(
        (key) => workspaceSlots[key] === viewSlug,
      );

      if (targetSlot) {
        swapWorkspaceSlots(targetSlot);
      }
    }
  }, [viewSlug, workspaceSlots, swapWorkspaceSlots]);

  useEffect(() => {
    return () => useWorkerDashboardData.getState().disconnectWorkerChat();
  }, []);

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
                      openJobDetailModal(job);
                      setSearchParams((prev) => {
                        const next = new URLSearchParams(prev);
                        next.set("jobId", String(job.job_id));
                        return next;
                      });
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
                      <span style={{ color: 'var(--k-orange-ink)', fontWeight: 600 }}>Match: {job?.match_score != null ? `${Math.round(job.match_score)}%` : '—%'}</span>
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
      const handleSendChat = async (e) => {
        e.preventDefault();
        if (!chatInput.trim() || !activeJob) return;

        let bidAmount = null;

        if (isBidMode) {
          bidAmount = Number(chatInput);
        } else if (chatInput.startsWith("$$$")) {
          const extracted = chatInput.substring(3).replace(/[^0-9]/g, "");
          if (extracted.length > 0) {
            bidAmount = Number(extracted);
          }
        }

        if (bidAmount !== null && bidAmount > 0) {
          try {
            await submitInlineBid(bidAmount);
            setChatInput("");
            if (isBidMode) setIsBidMode(false);
          } catch (err) {
            console.error("Failed to submit inline bid:", err);
          }
          return;
        }

        const bookingChatId = activeJob.booking_chat_id;
        if (!bookingChatId) return;
        try {
          await sendHumanMessage(bookingChatId, "worker", chatInput.trim());
          appendMessage("worker", chatInput.trim());
          setChatInput("");
        } catch (err) {
          console.error("Failed to send message:", err);
        }
      };

      // ── Chat View (full-width) ──
      const renderChatView = () => (
        <div style={{ width: "100%", height: "100%", display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-start", flexShrink: 0, marginBottom: "8px" }}>
            <button
              onClick={() => setShowBidForm(true)}
              style={{
                padding: "4px 14px", background: "#FF6B1A", color: "#0D0D0D",
                border: "none", borderRadius: "20px", fontWeight: 600,
                fontSize: "13px", cursor: "pointer"
              }}
            >
              Bid
            </button>
          </div>

            <div className="chat-box" style={{ flex: 1, minHeight: 0 }}>
              {chatMessages
                .filter(
                  (msg) => msg.sender === "customer" || msg.sender === "worker" || msg.sender === "system"
                )
                .map((msg) => (
                  <div key={msg.id}>
                    {msg.sender === "system" ? (
                      <div style={{ display: "flex", width: "100%", justifyContent: "center", marginBottom: "16px" }}>
                        <div style={{
                          maxWidth: "80%", padding: "4px 16px", fontSize: "0.85rem",
                          fontWeight: 600, color: "#FF6B1A", background: "rgba(255,107,26,0.1)",
                          borderRadius: "9999px", textAlign: "center"
                        }}>
                          {msg.text}
                        </div>
                      </div>
                    ) : msg.sender === "worker" ? (
                      <div style={{ display: "flex", width: "100%", justifyContent: "flex-end", marginBottom: "16px" }}>
                        <div style={{
                          maxWidth: "70%", padding: "8px 16px", color: "var(--k-ink)",
                          background: "#FF6B1A", borderRadius: "28px 4px 28px 28px"
                        }}>
                          <strong>{msg.senderName || msg.sender.toUpperCase()}:</strong> {msg.text}
                        </div>
                      </div>
                    ) : (
                      <div style={{ display: "flex", width: "100%", justifyContent: "flex-start", marginBottom: "16px" }}>
                        <div style={{
                          maxWidth: "70%", padding: "8px 16px", color: "var(--k-ink)",
                          background: "var(--k-raise)", borderRadius: "4px 28px 28px 28px",
                          border: "1px solid var(--k-line)"
                        }}>
                          <strong>{msg.senderName || msg.sender.toUpperCase()}:</strong> {msg.text}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              <div ref={messagesEndRef} />
            </div>

          <form
            onSubmit={handleSendChat}
            style={{ display: 'flex', gap: '6px', paddingTop: '8px', borderTop: '1px solid var(--k-line)', flexShrink: 0 }}
          >
            <input
              type={isBidMode ? "number" : "text"}
              value={chatInput}
              onChange={(e) => {
                let val = e.target.value;
                if (isBidMode) {
                  val = val.replace(/[^0-9]/g, "");
                }
                setChatInput(val);
              }}
              placeholder={isBidMode ? "Enter bid amount..." : "Type a message..."}
              disabled={!activeJob}
              style={{
                flex: 1,
                padding: '6px 10px',
                borderRadius: '6px',
                border: '1px solid var(--k-border-strong)',
                background: 'var(--k-field)',
                color: 'var(--k-ink)',
                font: 'inherit',
                outline: 'none',
                fontSize: '13px'
              }}
            />
            <button
              type="submit"
              disabled={!chatInput.trim() || !activeJob}
              style={{
                padding: '6px 14px',
                background: '#FF6B1A',
                color: '#0D0D0D',
                border: 'none',
                borderRadius: '6px',
                fontWeight: 700,
                cursor: 'pointer',
                fontSize: '13px'
              }}
            >
              Send
            </button>
          </form>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '4px', fontSize: '12px', color: 'var(--k-ink-3)' }}>
            <input
              type="checkbox"
              id="bidModeToggle"
              checked={isBidMode}
              onChange={(e) => {
                setIsBidMode(e.target.checked);
                if (e.target.checked) setChatInput("");
              }}
              style={{ cursor: 'pointer', accentColor: '#FF6B1A' }}
            />
            <label htmlFor="bidModeToggle" style={{ cursor: 'pointer' }}>
              type $$$amount to set bid.
            </label>
          </div>
        </div>
      );

      // ── Bid Placement View (full-width) ──
      const renderBidView = () => (
        <div style={{ width: "100%", height: "100%", display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          {/* Back to Chat header */}
          <div style={{ flexShrink: 0, marginBottom: "16px" }}>
            <button
              onClick={() => setShowBidForm(false)}
              style={{
                padding: "4px 14px", background: "transparent", color: "var(--k-ink-3)",
                border: "1px solid var(--k-line)", borderRadius: "20px", fontWeight: 600,
                fontSize: "13px", cursor: "pointer"
              }}
            >
              Back to Chat
            </button>
          </div>

          {/* Job details */}
          <h2 style={{ flexShrink: 0, margin: "0 0 8px" }}>{activeJob?.title || "Untitled Job"}</h2>
          <p style={{ flexShrink: 0, margin: "0 0 20px", fontSize: "13px", color: "var(--k-ink-3)", lineHeight: "1.5" }}>
            {activeJob?.description || activeJob?.job_description || "No description available."}
          </p>

          {/* Bid amount input */}
          <label style={{ display: "block", fontSize: "13px", fontWeight: 500, color: "var(--k-ink-3)", marginBottom: "8px", flexShrink: 0 }}>
            Enter your bid amount
          </label>
          <input
            type="number"
            value={bidAmount}
            onChange={(e) => setBidAmount(e.target.value)}
            placeholder="Rs 0.00"
            min="0"
            step="1"
            style={{
              width: "100%", padding: "12px 16px", fontSize: "18px", fontWeight: 700,
              color: "var(--k-ink)", background: "var(--k-raise)",
              border: "2px solid #FF6B1A", borderRadius: "12px", outline: "none",
              marginBottom: "20px", flexShrink: 0
            }}
          />

          <div style={{ flex: 1 }} />

          <button
            onClick={handleBidPlaced}
            disabled={!bidAmount}
            style={{
              width: "100%", padding: "12px", background: "#FF6B1A", color: "#0D0D0D",
              border: "none", borderRadius: "12px", fontWeight: 700, fontSize: "16px", cursor: "pointer",
              flexShrink: 0
            }}
          >
            Submit Bid
          </button>
        </div>
      );

      return (
        <div className="dashboard-card slot-main">
          <div className="card-header">
            ••• DEPLOYED ASSIGNMENT SPECIFICATIONS
          </div>

          {/* Full-width container — toggles between Chat and Bid views */}
          <div className="main-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            {showBidForm ? renderBidView() : renderChatView()}
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
        return <div className="dashboard-card slot-{slotKey}"><div className="card-header">••• MODULE PLACEHOLDER</div><div className="preview-panel"><span className="badge">No module loaded for {slotKey} slot</span></div></div>;
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

      {jobDetailModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            width: "100vw",
            height: "100vh",
            backgroundColor: "rgba(0, 0, 0, 0.6)",
            zIndex: 99999,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            backdropFilter: "blur(4px)",
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget) closeJobDetailModal();
          }}
        >
          <div
            style={{
              background: "var(--k-raise)",
              border: "1px solid var(--k-line)",
              borderRadius: "16px",
              boxShadow: "0 20px 60px rgba(0, 0, 0, 0.5)",
              width: "520px",
              maxWidth: "92%",
              maxHeight: "88vh",
              overflowY: "auto",
              padding: "24px",
              display: "flex",
              flexDirection: "column",
              gap: "14px",
              color: "var(--k-ink)",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <span
                style={{
                  fontSize: "12px",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "1px",
                  color: "var(--k-orange-ink)",
                }}
              >
                Job Details
              </span>
              <button
                type="button"
                onClick={closeJobDetailModal}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "var(--k-ink-3)",
                  fontSize: "18px",
                  cursor: "pointer",
                  lineHeight: 1,
                }}
              >
                ✕
              </button>
            </div>

            <h2 style={{ margin: 0 }}>
              {jobDetailModal.title || "Untitled Job"}
            </h2>
            <p style={{ margin: 0, fontSize: "13px", color: "var(--k-ink-3)" }}>
              Job ID: {jobDetailModal.booking_chat_id || jobDetailModal.job_id || "N/A"}
            </p>
            <p
              style={{
                margin: 0,
                fontSize: "14px",
                lineHeight: "1.55",
                color: "var(--k-ink)",
                whiteSpace: "pre-wrap",
              }}
            >
              {jobDetailModal.description || "No description available."}
            </p>

            <div
              style={{
                display: "flex",
                gap: "16px",
                fontSize: "13px",
                flexWrap: "wrap",
              }}
            >
              <span style={{ color: "var(--k-orange-ink)", fontWeight: 600 }}>
                Match: {Math.round(jobDetailModal.match_score || 0)}%
              </span>
              <span>Rank: #{jobDetailModal.match_rank || "-"}</span>
              <span>Status: {jobDetailModal.status || "N/A"}</span>
              <span>
                Interested: {jobDetailModal.interested_count || 0}
              </span>
            </div>

            <button
              type="button"
              onClick={() => {
                closeJobDetailModal();
                navigate(
              `/worker/workspace/WorkspaceJobDetails?jobId=${jobDetailModal.job_id}`
            );
              }}
              style={{
                marginTop: "8px",
                padding: "10px 18px",
                background: "#FF6B1A",
                color: "#0D0D0D",
                border: "none",
                borderRadius: "8px",
                fontWeight: 700,
                cursor: "pointer",
                fontSize: "14px",
                alignSelf: "flex-start",
              }}
            >
              Join in Chat
            </button>
          </div>
        </div>
       )}
    </div>
  );
}