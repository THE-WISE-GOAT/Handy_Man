// components/customer-dashboard/dash1board.jsx
import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useCustomerDashboardData } from "./useCustomerDashboardData";
import "./dash1board.css";

export default function Dash1Board({ viewSlug }) {
  const navigate = useNavigate();
  const [chatInput, setChatInput] = useState("");

  const {
    slots,
    swapSlots,
    jobDescriptionDraft,
    setJobDescription,
    chatMessages,
    addChatMessage,
    activePostsCount,
  } = useCustomerDashboardData();

  // Route state synchronization layer
  useEffect(() => {
    if (!viewSlug) return;
    if (slots.main !== viewSlug) {
      const targetSlot = Object.keys(slots).find((key) => slots[key] === viewSlug);
      if (targetSlot) swapSlots(targetSlot);
    }
  }, [viewSlug, slots, swapSlots]);

  const handleModuleSelect = (targetSlug) => {
    navigate(`/customer/bookings/${targetSlug}`);
  };

  // ====================================================
  // SUB-MODULE RENDERS
  // ====================================================

  const renderAiChat = (slotKey) => {
    if (slotKey === "main") {
      const handleSend = (e) => {
        e.preventDefault();
        if (!chatInput.trim()) return;
        addChatMessage(chatInput, "user");
        setChatInput("");
      };

      return (
        <div className="dashboard-card main-view">
          <span className="card-flag">INTERACTIVE DISPATCH MANAGER</span>
          <h2>AI CHAT TERMINAL</h2>
          <div className="chat-box">
            {chatMessages.map((m) => (
              <p key={m.id}>
                <strong>{m.sender.toUpperCase()}:</strong> {m.text}
              </p>
            ))}
          </div>
          <form onSubmit={handleSend} className="chat-form">
            <input
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Instruct AI..."
            />
            <button type="submit" className="chat-btn">Send</button>
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

  const renderJobDescription = (slotKey) => {
    if (slotKey === "main") {
      return (
        <div className="dashboard-card main-view">
          <span className="card-flag">Main: REVIEW AND REFINE AUTO-GENERATED DETAILS</span>
          <h2>JOB DESCRIPTION WORKSPACE</h2>
          <textarea
            className="workspace-textarea"
            value={jobDescriptionDraft}
            onChange={(e) => setJobDescription(e.target.value)}
          />
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
            <p className="card-summary">{jobDescriptionDraft.substring(0, 35)}...</p>
          </>
        ) : (
          <span className="badge">Footer: Draft character footprint: {jobDescriptionDraft.length} chars</span>
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
            <span className="badge badge-highlight">Network Pipeline Active</span>
            <p className="card-summary">Live Trackable: {activePostsCount} Positions</p>
          </>
        ) : (
          <span className="badge">Posts Monitor sleeping below — {activePostsCount} items queued</span>
        )}
      </div>
    );
  };

  const resolveAndRenderModule = (slotKey) => {
    const moduleName = slots[slotKey];
    switch (moduleName) {
      case "AiChatTerminal":           return renderAiChat(slotKey);
      case "JobDescriptionWorkspace": return renderJobDescription(slotKey);
      case "YourActivePosts":          return renderActivePosts(slotKey);
      default:                         return null;
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