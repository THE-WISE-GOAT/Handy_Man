// components/worker-dashboard/dash3worker.jsx
import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useWorkerDashboardData } from "./useWorkerDashboardData";
import "./dash3worker.css";

export default function Dash3Worker({ viewSlug }) {
  const navigate = useNavigate();

  const {
    meSlots,
    swapMeSlots,
    interviewStatusText,
    profileCredentialsText,
    envConfigParametersText,
    scrapedTagsMatchText,
  } = useWorkerDashboardData();

  // Route state synchronization layer
  useEffect(() => {
    if (!viewSlug) return;

    if (meSlots.main !== viewSlug) {
      const targetSlot = Object.keys(meSlots).find(
        (key) => meSlots[key] === viewSlug
      );

      if (targetSlot) {
        swapMeSlots(targetSlot);
      }
    }
  }, [viewSlug, meSlots, swapMeSlots]);

  const handleModuleSelect = (targetSlug) => {
    navigate(`/worker/me/${targetSlug}`);
  };

  // ====================================================
  // SUB-MODULE RENDERS
  // ====================================================

  const renderInterview = (slotKey) => {
    if (slotKey === "main") {
      return (
        <div className="dashboard-card slot-main">
          <div className="card-header">
            ••• ONBOARDING COMPLIANCE RUNTIME
          </div>

          <div className="main-panel">
            <h2>Verification Interventions</h2>
            <p className="panel-desc">{interviewStatusText}</p>
          </div>
        </div>
      );
    }

    return (
      <div
        className={`dashboard-card slot-${slotKey} clickable`}
        onClick={() => handleModuleSelect("MeInterview")}
      >
        <div className="card-header">
          ••• ONBOARDING COMPLIANCE RUNTIME
        </div>

        <div className="preview-panel">
          {slotKey === "sidebar" ? (
            <>
              <span className="badge badge-highlight">
                Sidebar: Compliance Node
              </span>

              <p className="card-summary">
                {interviewStatusText}
              </p>
            </>
          ) : (
            <span className="badge">
              Footer ({slotKey}): Terminal Onboarding Feed
            </span>
          )}
        </div>
      </div>
    );
  };

  const renderProfile = (slotKey) => {
    if (slotKey === "main") {
      return (
        <div className="dashboard-card slot-main">
          <div className="card-header">
            ••• USER REGISTRATION INFRASTRUCTURE
          </div>

          <div className="main-panel">
            <h2>Worker Identity Profile</h2>
          </div>
        </div>
      );
    }

    return (
      <div
        className={`dashboard-card slot-${slotKey} clickable`}
        onClick={() => handleModuleSelect("MeProfile")}
      >
        <div className="card-header">
          ••• USER REGISTRATION INFRASTRUCTURE
        </div>

        <div className="preview-panel">
          {slotKey === "sidebar" ? (
            <>
              <span className="badge badge-highlight">
                Sidebar: Identity Profile
              </span>

              <p className="card-summary">
                {profileCredentialsText}
              </p>
            </>
          ) : (
            <span className="badge">
              Footer ({slotKey}): Profile Token [{profileCredentialsText}]
            </span>
          )}
        </div>
      </div>
    );
  };

  const renderConfig = (slotKey) => {
    if (slotKey === "main") {
      return (
        <div className="dashboard-card slot-main">
          <div className="card-header">
            ••• SYSTEM CONFIGURATION METRICS
          </div>

          <div className="main-panel">
            <h2>Environment Configurations</h2>
          </div>
        </div>
      );
    }

    return (
      <div
        className={`dashboard-card slot-${slotKey} clickable`}
        onClick={() => handleModuleSelect("MeConfiguration")}
      >
        <div className="card-header">
          ••• SYSTEM CONFIGURATION METRICS
        </div>

        <div className="preview-panel">
          {slotKey === "sidebar" ? (
            <>
              <span className="badge badge-highlight">
                Sidebar: Env Metrics
              </span>

              <p className="card-summary">
                {envConfigParametersText}
              </p>
            </>
          ) : (
            <span className="badge">
              Footer ({slotKey}): Environment Context ({envConfigParametersText})
            </span>
          )}
        </div>
      </div>
    );
  };

  const renderTagsAnalyzer = (slotKey) => {
    if (slotKey === "main") {
      return (
        <div className="dashboard-card slot-main">
          <div className="card-header">
            ••• ITEM LABELING CLASSIFICATION LOGS
          </div>

          <div className="main-panel">
            <h2>Collected Tags Analyzer</h2>
          </div>
        </div>
      );
    }

    return (
      <div
        className={`dashboard-card slot-${slotKey} clickable`}
        onClick={() => handleModuleSelect("MeCollectedTags")}
      >
        <div className="card-header">
          ••• ITEM LABELING CLASSIFICATION LOGS
        </div>

        <div className="preview-panel">
          {slotKey === "sidebar" ? (
            <>
              <span className="badge badge-highlight">
                Sidebar: Labels Engine
              </span>

              <p className="card-summary">
                {scrapedTagsMatchText}
              </p>
            </>
          ) : (
            <span className="badge">
              Footer ({slotKey}): Scraped Logs Stream ({scrapedTagsMatchText})
            </span>
          )}
        </div>
      </div>
    );
  };

  const resolveModuleBySlot = (slotKey) => {
    switch (meSlots[slotKey]) {
      case "MeInterview":
        return renderInterview(slotKey);

      case "MeProfile":
        return renderProfile(slotKey);

      case "MeConfiguration":
        return renderConfig(slotKey);

      case "MeCollectedTags":
        return renderTagsAnalyzer(slotKey);

      default:
        return null;
    }
  };

  return (
    <div className="worker-me-canvas-grid">
      <div className="grid-area-main">
        {resolveModuleBySlot("main")}
      </div>

      <div className="grid-area-sidebar">
        {resolveModuleBySlot("sidebar")}
      </div>

      <div className="grid-area-bottom-left">
        {resolveModuleBySlot("bottomLeft")}
      </div>

      <div className="grid-area-bottom-right">
        {resolveModuleBySlot("bottomRight")}
      </div>
    </div>
  );
}