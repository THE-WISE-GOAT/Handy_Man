// components/customer-dashboard/dash1board.jsx
import React, { useState } from 'react';
import { useCustomerDashboardData } from './useCustomerDashboardData';
import './dash1board.css';

export default function Dash1Board() {
  // 1. Hook straight into the central Zustand Bookings state slice
  const { 
    slots, 
    swapSlots,
    jobDescriptionDraft, 
    setJobDescription, 
    chatMessages, 
    addChatMessage, 
    activePostsCount 
  } = useCustomerDashboardData();

  const [chatInput, setChatInput] = useState("");

  // ====================================================
  // LOCATION-AWARE DISPLAY MATRIX FOR EACH SUB-MODULE
  // ====================================================
  
  // A. AI Chat Sub-Module View Generator
  const renderAiChat = (locationLabel) => {
    if (locationLabel === "main") {
      const handleSend = (e) => {
        e.preventDefault();
        if (!chatInput.trim()) return;
        addChatMessage(chatInput, "user");
        setChatInput("");
      };

      return (
        <div className="section-card slot-view-main">
          <span className="subtitle-flag">INTERACTIVE DISPATCH MANAGER</span>
          <h2>AI CHAT TERMINAL</h2>
          <div className="chat-logs-display">
            {chatMessages.map(m => <p key={m.id}><strong>{m.sender.toUpperCase()}:</strong> {m.text}</p>)}
          </div>
          <form onSubmit={handleSend} className="chat-entry-form">
            <input value={chatInput} onChange={e => setChatInput(e.target.value)} placeholder="Instruct AI..." />
            <button type="submit" className="chat-send-btn">Send</button>
          </form>
        </div>
      );
    }

    if (locationLabel === "sidebar") {
      return (
        <div className="section-card slot-view-sidebar clickable-swap-node" onClick={() => swapSlots("sidebar")}>
          <div className="module-title-bar">••• AI CHAT TERMINAL</div>
          <span className="pill-badge-highlight">Live Dispatch — Active Session</span>
          <p className="micro-summary">Logs Captured: {chatMessages.length}</p>
        </div>
      );
    }

    // Default: 'bottom' layout rendering logic
    return (
      <div className="section-card slot-view-bottom clickable-swap-node" onClick={() => swapSlots("bottom")}>
        <div className="module-title-bar">••• AI CHAT TERMINAL</div>
        <span className="pill-badge">AI Dispatch running asleep below...</span>
      </div>
    );
  };

  // B. Job Description Workspace Sub-Module View Generator
  const renderJobDescription = (locationLabel) => {
    if (locationLabel === "main") {
      return (
        <div className="section-card slot-view-main">
          <span className="subtitle-flag">REVIEW AND REFINE AUTO-GENERATED DETAILS</span>
          <h2>JOB DESCRIPTION WORKSPACE</h2>
          <textarea 
            className="workspace-textarea-box"
            value={jobDescriptionDraft} 
            onChange={(e) => setJobDescription(e.target.value)} 
          />
        </div>
      );
    }

    if (locationLabel === "sidebar") {
      return (
        <div className="section-card slot-view-sidebar clickable-swap-node" onClick={() => swapSlots("sidebar")}>
          <div className="module-title-bar">••• JOB DESCRIPTION WORKSPACE</div>
          <span className="pill-badge">Description Live Glance — Draft Mode</span>
          <p className="micro-summary-text">{jobDescriptionDraft.substring(0, 35)}...</p>
        </div>
      );
    }

    // Default: 'bottom' layout rendering logic
    return (
      <div className="section-card slot-view-bottom clickable-swap-node" onClick={() => swapSlots("bottom")}>
        <div className="module-title-bar">••• JOB DESCRIPTION WORKSPACE</div>
        <span className="pill-badge">Draft character footprint: {jobDescriptionDraft.length} chars</span>
      </div>
    );
  };

  // C. Your Active Posts Sub-Module View Generator
  const renderActivePosts = (locationLabel) => {
    if (locationLabel === "main") {
      return (
        <div className="section-card slot-view-main">
          <h2>YOUR ACTIVE POSTS MAIN HUB</h2>
          <p>Full active dispatch control configuration deck view.</p>
        </div>
      );
    }

    if (locationLabel === "sidebar") {
      return (
        <div className="section-card slot-view-sidebar clickable-swap-node" onClick={() => swapSlots("sidebar")}>
          <div className="module-title-bar">••• YOUR ACTIVE POSTS</div>
          <span className="pill-badge">Active Posts — {activePostsCount} live trackable</span>
        </div> 
      );
    }

    // Default: 'bottom' layout rendering logic
    return (
      <div className="section-card slot-view-bottom clickable-swap-node" onClick={() => swapSlots("bottom")}>
        <div className="module-title-bar">••• YOUR ACTIVE POSTS</div>
        <span className="pill-badge">Active Posts — {activePostsCount} live requests trackable</span>
      </div>
    );
  };

  // ====================================================
  // ROUTING CONTENT COORDINATOR DISPATCHER
  // ====================================================
  const resolveAndRenderModule = (slotKey, moduleName) => {
    switch (moduleName) {
      case "AiChatTerminal": return renderAiChat(slotKey);
      case "JobDescriptionWorkspace": return renderJobDescription(slotKey);
      case "YourActivePosts": return renderActivePosts(slotKey);
      default: return null;
    }
  };

  // ====================================================
  // VISUAL STRUCTURAL SLOTS GENERATION (The Wireframe Structure)
  // ====================================================
  return (
    <div className="dashboard-layout-wireframe-grid">
      
      {/* SLOT 1: Top Left Workspace Frame */}
      <div className="wireframe-slot-main">
        {resolveAndRenderModule("main", slots.main)}
      </div>

      {/* SLOT 2: Bottom Row Strip Frame */}
      <div className="wireframe-slot-bottom">
        {resolveAndRenderModule("bottom", slots.bottom)}
      </div>

      {/* SLOT 3: Right Side Column Sidebar Frame */}
      <div className="wireframe-slot-sidebar">
        {resolveAndRenderModule("sidebar", slots.sidebar)}
      </div>

    </div>
  );
}