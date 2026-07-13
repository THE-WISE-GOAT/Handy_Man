import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useCustomerDashboardData } from "./useCustomerDashboardData";
import "./dash1board.css";

export default function Dash1Board({ viewSlug }) {
  const navigate = useNavigate();
  const [chatInput, setChatInput] = useState("");

  // Bring in the items from Zustand
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
    fetchedJobs,
    fetchCustomerJobs,
    userCont,
    userAddr,
    userName,
    setUserName,
    setUserAddr,
    setUserCont,
    jobProfessional,
    cust_id,
    setProfessional,
    setId,
    createJob,
    startNewSession,
    sendCustomerMessage,
    turns_remaining,
    is_complete,
    ai_response,
    current_tags,
    categories

  } = useCustomerDashboardData();

  // References live inside the component instance scope
  const scrollRef = useRef(null);
  const isDown = useRef(false);
  const startX = useRef(0);
  const scrollLeftState = useRef(0);

  // Testing Mock Data
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


  
// Trigger HTTP Fetch once when the page loads safely
  useEffect(() => {
    fetchCustomerJobs();
  }, [fetchCustomerJobs]);

  // ── ADD THIS NEW HOOK DIRECTLY HERE ──
  useEffect(() => {
    startNewSession();
  }, [startNewSession]);

  // Route state synchronization layer
  useEffect(() => {
    if (!viewSlug) return;
    if (slots.main !== viewSlug) {
      const targetSlot = Object.keys(slots).find(
        (key) => slots[key] === viewSlug,
      );
      if (targetSlot) swapSlots(targetSlot);
    }
  }, [viewSlug, slots, swapSlots]);

  // Isolated Scroll Wheel Capture Mechanism
  useEffect(() => {
    const scrollContainer = scrollRef.current;
    if (!scrollContainer) return;

    const handleWheel = (e) => {
      e.preventDefault();
      e.stopPropagation();
      scrollContainer.scrollLeft += e.deltaY;
    };

    scrollContainer.addEventListener("wheel", handleWheel, { passive: false });

    return () => {
      scrollContainer.removeEventListener("wheel", handleWheel);
    };
  }, [slots.main]);

  const handleModuleSelect = (targetSlug) => {
    navigate(`/customer/bookings/${targetSlug}`);
  };

  // ====================================================
  // SUB-MODULE RENDERS
  // ====================================================

  const renderAiChat = (slotKey) => {
    if (slotKey === "main") {
      // ── UPDATED SUBMISSION INTERCEPTOR ──
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
          <h2>AI CHAT TERMINAL</h2>
          <div className="chat-box">
            {chatMessages.map((m) => (
              <p key={m.id}>
                <strong>{m.sender.toUpperCase()}:</strong> {m.text}
              </p>
            ))}
          </div>
          <form onSubmit={handleSend} className="chat-form">
            {/* ── UPDATED INPUT HOOKS WITH CONDITIONAL DISABLED CONTROLS ── */}
            <input
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder={is_complete ? "Conversation finalized." : "Instruct AI..."}
              disabled={is_complete}
            />
            <button type="submit" className="chat-btn" disabled={is_complete || !chatInput.trim()}>
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
            <span className="badge badge-highlight">
              Live Dispatch — Active Session
            </span>
            <p className="card-summary">Logs Captured: {chatMessages.length}</p>
          </>
        ) : (
          <span className="badge">AI Dispatch running asleep below...</span>
        )}
      </div>
    );
  };

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
          <div
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              height: "100%",
              minWidth: 0,
            }}
          >
            <span className="card-flag" style={{ marginTop: "-14px" }}>
              EDIT OR CREATE JOB POSTING
            </span>
            <h3
              className="title"
              style={{ display: "flex", alignItems: "baseline", minWidth: 0 }}
            >
              <span >
                ·•TITLE:
              </span>
              <input 
                type="text"
                value={jobTitleDraft}
                onChange={(e) => {setJobTitle(e.target.value)}}
                spellCheck = {false}
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
                border: "2px dashed #000000",
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
          <div
            style={{
              width: "35%",
              height: "100%",
              display: "flex",
              flexDirection: "column",
              minWidth: 0,
              flexShrink: 0,
            }}
          >
            <h3 className="title" dir="rtl" style={{ marginBottom: "4px" }}>
              AttACHMENTs
            </h3>

            {/* Scrollable Track Module Wrapper */}
            <div
              style={{
                position: "relative",
                display: "flex",
                alignItems: "center",
                width: "100%",
              }}
            >
              <button
                type="button"
                onClick={() => {
                  if (scrollRef.current)
                    scrollRef.current.scrollBy({
                      left: -120,
                      behavior: "smooth",
                    });
                }}
                style={{
                  position: "absolute",
                  left: "-5px",
                  zIndex: 10,
                  background: "#000",
                  color: "#fff",
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
                  if (scrollRef.current)
                    scrollRef.current.style.cursor = "grab";
                }}
                onMouseUp={() => {
                  isDown.current = false;
                  if (scrollRef.current)
                    scrollRef.current.style.cursor = "grab";
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
                      border: "1px solid #000",
                      borderRadius: "4px",
                      background: "#f9f9f9",
                      fontSize: "11px",
                      padding: "4px",
                      boxSizing: "border-box",
                    }}
                  >
                    <span style={{ fontWeight: "bold" }}>[{file.type}]</span>
                    <span
                      style={{
                        fontSize: "9px",
                        textOverflow: "ellipsis",
                        overflow: "hidden",
                        width: "100%",
                        textAlign: "center",
                      }}
                    >
                      {file.name}
                    </span>
                  </div>
                ))}
              </div>

              <button
                type="button"
                onClick={() => {
                  if (scrollRef.current)
                    scrollRef.current.scrollBy({
                      left: 120,
                      behavior: "smooth",
                    });
                }}
                style={{
                  position: "absolute",
                  right: "-5px",
                  zIndex: 10,
                  background: "#000",
                  color: "#fff",
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

            <h3 className="title" dir="rtl" style={{ marginTop: "10px" }}>
              {" "}
              UsER INFo{" "}
            </h3>
            <div className="user-info" style={{ lineHeight: '35px' }}>
            <span
              style={{
                display: "inline-flex",
                alignItems: "baseline",
              }}
            >
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

            <span
              style={{
                display: "inline-flex",
                alignItems: "baseline",
              }}
            >
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
            <span
              style={{
                display: "inline-flex",
                alignItems: "baseline",
              }}
            >
              <span>ADDRESS: </span>
              <input
                type="text"
                value={userAddr}
                onChange={(e) => setUserAddr(e.target.value)}
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

                <span
              style={{
                display: "inline-flex",
                alignItems: "baseline",
              }}
            >
              <span>PROFESSIONAL: </span>
              <input
                type="text"
                value={jobProfessional}
                onChange={(e) => setProfessional(e.target.value)}
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

            <span
              style={{
                display: "inline-flex",
                alignItems: "baseline",
              }}
            >
              <span>ID: </span>
              <input
                type="text"
                value={cust_id}
                onChange={(e) => setId(e.target.value)}
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


            </div>

<button
  type="button"
  onClick={() => emergencyToggle()} /* Replace with your actual emergency function name */
  className="title"
  dir="rtl"
  style={{ 
    marginTop: "auto", 
    alignSelf: 'center', 
    background: 'tomato',
    borderRadius: '19px', 
    color: 'wheat', 
    width: '100%',
    /* Added to clear native button behavior */
    border: 'none',
    font: 'inherit',
    cursor: 'pointer',
    textAlign: 'center',
    height: '10%',
    fontSize: '29px'
  }}
>
  EmERGENcY ToGGLE
</button>

<button
  type="button"
  onClick={() => createJob()} /* Replace with your actual post function name */
  className="title"
  dir="rtl"
  style={{ 
    margin: "0", 
    alignSelf: 'center', 
    color: 'darkslategray', 
    background: 'palegreen', 
    marginTop: '5px', 
    borderRadius: '19px',
    /* Added to clear native button behavior */
    border: 'none',
        width: '100%',
    /* Added to clear native button behavior */
    border: 'none',
    font: 'inherit',
    cursor: 'pointer',
    textAlign: 'center',
    height: '10%',
    fontSize: '29px',
    font: 'inherit',
    cursor: 'pointer',
    textAlign: 'center'
  }}
>
  {"<-"}PosT
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
            <span className="badge">
              Sidebar: Description Live Glance — Draft Mode
            </span>
            <p className="card-summary">
               <div>{ai_response}</div>
               <div>{current_tags}</div>
               <div>{categories}</div>
            </p>
          </>
        ) : (
          <span className="badge">
            Footer: Draft character footprint: {jobDescriptionDraft.length}{" "}
            chars
          </span>
        )}
      </div>
    );
  };

  const renderActivePosts = (slotKey) => {
    if (slotKey === "main") {
      return (
        <div className="dashboard-card main-view">
          <h2>YOUR ACTIVE POSTS MAIN HUB</h2>
          <p>Full active dispatch control configuration deck view.</p>
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
            <span className="badge badge-highlight">
              Network Pipeline Active
            </span>
            <p className="card-summary">
              Live Trackable: {activePostsCount} Positions
            </p>
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
    </div>
  );
}
