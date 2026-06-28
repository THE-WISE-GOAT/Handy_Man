// components/worker-dashboard/dash3worker.jsx
import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useWorkerDashboardData } from './useWorkerDashboardData';
import './dash3worker.css';

export default function Dash3Worker({ viewSlug }) {
  const navigate = useNavigate();
  const {
    meSlots,
    swapMeSlots,
    interviewStatusText,
    profileCredentialsText,
    envConfigParametersText,
    scrapedTagsMatchText
  } = useWorkerDashboardData();

  // Route state synchronization layer
  useEffect(() => {
    if (!viewSlug) return;
    if (meSlots.main !== viewSlug) {
      const targetSlot = Object.keys(meSlots).find((key) => meSlots[key] === viewSlug);
      if (targetSlot) swapMeSlots(targetSlot);
    }
  }, [viewSlug, meSlots, swapMeSlots]);

  const handleModuleSelect = (targetSlug) => {
    navigate(`/worker/me/${targetSlug}`);
  };

  // Shared reusable card frame template
  const Card = ({ slug, title, position, children }) => {
    const isMain = position === "main";
    return (
      <div 
        className={`dashboard-card slot-${position} ${!isMain ? 'clickable' : ''}`}
        onClick={!isMain ? () => handleModuleSelect(slug) : undefined}
      >
        <div className="card-header">••• {title}</div>
        {children}
      </div>
    );
  };

  // ====================================================
  // SUB-MODULE RENDERS
  // ====================================================

  const renderInterview = (position) => (
    <Card slug="MeInterview" title="ONBOARDING COMPLIANCE RUNTIME" position={position}>
      {position === "main" ? (
        <div className="main-panel">
          <h2>Verification Interventions</h2>
          <p className="panel-desc">{interviewStatusText}</p>
        </div>
      ) : (
        <div className="preview-panel">
          {position === "sidebar" ? (
            <>
              <span className="badge badge-highlight">Sidebar: Compliance Node</span>
              <p className="card-summary">{interviewStatusText}</p>
            </>
          ) : (
            <span className="badge">Footer ({position}): Terminal Onboarding Feed</span>
          )}
        </div>
      )}
    </Card>
  );

  const renderProfile = (position) => (
    <Card slug="MeProfile" title="USER REGISTRATION INFRASTRUCTURE" position={position}>
      {position === "main" ? (
        <div className="main-panel">
          <h2>Worker Identity Profile</h2>
        </div>
      ) : (
        <div className="preview-panel">
          {position === "sidebar" ? (
            <>
              <span className="badge badge-highlight">Sidebar: Identity Profile</span>
              <p className="card-summary">{profileCredentialsText}</p>
            </>
          ) : (
            <span className="badge">Footer ({position}): Profile Token [{profileCredentialsText}]</span>
          )}
        </div>
      )}
    </Card>
  );

  const renderConfig = (position) => (
    <Card slug="MeConfiguration" title="SYSTEM CONFIGURATION METRICS" position={position}>
      {position === "main" ? (
        <div className="main-panel">
          <h2>Environment Configurations</h2>
        </div>
      ) : (
        <div className="preview-panel">
          {position === "sidebar" ? (
            <>
              <span className="badge badge-highlight">Sidebar: Env Metrics</span>
              <p className="card-summary">{envConfigParametersText}</p>
            </>
          ) : (
            <span className="badge">Footer ({position}): Environment Context ({envConfigParametersText})</span>
          )}
        </div>
      )}
    </Card>
  );

  const renderTagsAnalyzer = (position) => (
    <Card slug="MeCollectedTags" title="ITEM LABELING CLASSIFICATION LOGS" position={position}>
      {position === "main" ? (
        <div className="main-panel">
          <h2>Collected Tags Analyzer</h2>
        </div>
      ) : (
        <div className="preview-panel">
          {position === "sidebar" ? (
            <>
              <span className="badge badge-highlight">Sidebar: Labels Engine</span>
              <p className="card-summary">{scrapedTagsMatchText}</p>
            </>
          ) : (
            <span className="badge">Footer ({position}): Scraped Logs Stream ({scrapedTagsMatchText})</span>
          )}
        </div>
      )}
    </Card>
  );

  const resolveModuleBySlot = (slotKey) => {
    switch (meSlots[slotKey]) {
      case "MeInterview":     return renderInterview(slotKey);
      case "MeProfile":       return renderProfile(slotKey);
      case "MeConfiguration": return renderConfig(slotKey);
      case "MeCollectedTags": return renderTagsAnalyzer(slotKey);
      default:                return null;
    }
  };

  return (
    <div className="worker-me-canvas-grid">
      <div className="grid-area-main">{resolveModuleBySlot("main")}</div>
      <div className="grid-area-sidebar">{resolveModuleBySlot("sidebar")}</div>
      <div className="grid-area-bottom-left">{resolveModuleBySlot("bottomLeft")}</div>
      <div className="grid-area-bottom-right">{resolveModuleBySlot("bottomRight")}</div>
    </div>
  );
}