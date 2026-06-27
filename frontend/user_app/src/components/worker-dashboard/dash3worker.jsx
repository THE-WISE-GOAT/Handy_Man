// components/worker-dashboard/dash3worker.jsx
import React from 'react';
import { useWorkerDashboardData } from './useWorkerDashboardData';
import './dash3worker.css';

export default function Dash3Worker() {
  const {
    meSlots,
    swapMeSlots,
    interviewStatusText,
    profileCredentialsText,
    envConfigParametersText,
    scrapedTagsMatchText
  } = useWorkerDashboardData();

  // ====================================================
  // SUB-MODULE 1: VERIFICATION INTERVENTIONS
  // ====================================================
  const renderInterview = (position) => {
    if (position === "main") {
      return (
        <div className="worker-section-card view-main">
          <div className="worker-card-header">ONBOARDING COMPLIANCE RUNTIME</div>
          <h2>Verification Interventions</h2>
          <p className="worker-panel-desc">{interviewStatusText}</p>
        </div>
      );
    }

    return (
      <div className={`worker-section-card view-${position} worker-clickable-node`} onClick={() => swapMeSlots(position)}>
        <div className="worker-card-header">ONBOARDING COMPLIANCE RUNTIME</div>
        <div className="worker-sleeping-box">
          <span className="worker-pill-outline">Interview Terminal</span>
        </div>
      </div>
    );
  };

  // ====================================================
  // SUB-MODULE 2: WORKER IDENTITY PROFILE
  // ====================================================
  const renderProfile = (position) => {
    if (position === "main") {
      return (
        <div className="worker-section-card view-main">
          <div className="worker-card-header">USER REGISTRATION INFRASTRUCTURE</div>
          <h2>Worker Identity Profile</h2>
        </div>
      );
    }

    return (
      <div className={`worker-section-card view-${position} worker-clickable-node`} onClick={() => swapMeSlots(position)}>
        <div className="worker-card-header">USER REGISTRATION INFRASTRUCTURE</div>
        <div className="worker-sleeping-box">
          <span className="worker-pill-outline">{profileCredentialsText}</span>
        </div>
      </div>
    );
  };

  // ====================================================
  // SUB-MODULE 3: ENVIRONMENT CONFIGURATIONS
  // ====================================================
  const renderConfig = (position) => {
    if (position === "main") {
      return (
        <div className="worker-section-card view-main">
          <div className="worker-card-header">SYSTEM CONFIGURATION METRICS</div>
          <h2>Environment Configurations</h2>
        </div>
      );
    }

    return (
      <div className={`worker-section-card view-${position} worker-clickable-node`} onClick={() => swapMeSlots(position)}>
        <div className="worker-card-header">SYSTEM CONFIGURATION METRICS</div>
        <div className="worker-sleeping-box">
          <span className="worker-pill-outline">{envConfigParametersText}</span>
        </div>
      </div>
    );
  };

  // ====================================================
  // SUB-MODULE 4: COLLECTED TAGS ANALYZER
  // ====================================================
  const renderTagsAnalyzer = (position) => {
    if (position === "main") {
      return (
        <div className="worker-section-card view-main">
          <div className="worker-card-header">ITEM LABELING CLASSIFICATION LOGS</div>
          <h2>Collected Tags Analyzer</h2>
        </div>
      );
    }

    return (
      <div className={`worker-section-card view-${position} worker-clickable-node`} onClick={() => swapMeSlots(position)}>
        <div className="worker-card-header">ITEM LABELING CLASSIFICATION LOGS</div>
        <div className="worker-sleeping-box">
          <span className="worker-pill-outline">{scrapedTagsMatchText}</span>
        </div>
      </div>
    );
  };

  // ====================================================
  // TRANSLATION DISPATCHER
  // ====================================================
  const resolveModuleBySlot = (slotKey) => {
    const moduleName = meSlots[slotKey];
    switch (moduleName) {
      case "MeInterview":        return renderInterview(slotKey);
      case "MeProfile":          return renderProfile(slotKey);
      case "MeConfiguration":    return renderConfig(slotKey);
      case "MeCollectedTags":    return renderTagsAnalyzer(slotKey);
      default:                   return null;
    }
  };

  // ====================================================
  // 4-PANEL GRID INTERACTION CANVAS
  // ====================================================
  return (
    <div className="worker-me-canvas-grid">
      <div className="grid-area-main">{resolveModuleBySlot("main")}</div>
      <div className="grid-area-sidebar">{resolveModuleBySlot("sidebar")}</div>
      <div className="grid-area-bottom-left">{resolveModuleBySlot("bottomLeft")}</div>
      <div className="grid-area-bottom-right">{resolveModuleBySlot("bottomRight")}</div>
    </div>
  );
}