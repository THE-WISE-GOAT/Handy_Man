// components/customer-dashboard/dash3board.jsx
import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useCustomerDashboardData } from "./useCustomerDashboardData";
import "./dash3board.css";

export default function Dash3Board({ viewSlug }) {
  const navigate = useNavigate();
  const {
    miscSlots,
    swapMiscSlots,
    calendarEventsCount,
    profileSecurityStatus,
    archivePipelineStatus,
    systemPortalStatus,
  } = useCustomerDashboardData();

  // Route state synchronization layer
  useEffect(() => {
    if (!viewSlug) return;
    if (miscSlots.main !== viewSlug) {
      const targetSlot = Object.keys(miscSlots).find(
        (key) => miscSlots[key] === viewSlug,
      );
      if (targetSlot) swapMiscSlots(targetSlot);
    }
  }, [viewSlug, miscSlots, swapMiscSlots]);

  const handleModuleSelect = (targetSlug) => {
    navigate(`/customer/more/${targetSlug}`);
  };

  // Shared component template for preview/sleeping or active panels
  const Card = ({ slug, title, position, children }) => {
    const isMain = position === "main";
    return (
      <div
        className={`dashboard-card slot-${position} ${!isMain ? "clickable" : ""}`}
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

  const renderSystemCalendar = (position) => (
    <Card
      slug="SystemCalendar"
      title="SCHEDULE PLATFORM PLANNERS"
      position={position}
    >
      {position === "main" ? (
        <div className="main-panel">
          <h2>SYSTEM CALENDAR</h2>
          <p className="panel-desc">
            Calendar Workspace Terminal Primary Schedule Router.
          </p>
          <div className="calendar-box">
            <p>Active Planned Tasks: {calendarEventsCount}</p>
          </div>
        </div>
      ) : (
        <div className="preview-panel">
          {position === "sidebar" ? (
            <>
              <span className="badge badge-highlight">
                Sidebar: Planner Overview
              </span>
              <p className="card-summary">
                Events Loaded: {calendarEventsCount}
              </p>
            </>
          ) : (
            <span className="badge">
              Footer ({position}): {calendarEventsCount} Scheduled Tasks
            </span>
          )}
        </div>
      )}
    </Card>
  );

  const renderAccountProfiles = (position) => (
    <Card slug="AccountProfiles" title="ACCOUNT PROFILES" position={position}>
      {position === "main" ? (
        <div className="main-panel">
          <h2>ACCOUNT PROFILE MANAGER</h2>
          <p>
            Configure client accounts, authentication layers, and permissions
            records details.
          </p>
        </div>
      ) : (
        <div className="preview-panel">
          {position === "sidebar" ? (
            <>
              <span className="badge badge-highlight">
                Sidebar: Security Node
              </span>
              <p className="card-summary">Status: {profileSecurityStatus}</p>
            </>
          ) : (
            <span className="badge">
              Footer ({position}): Profile Status [{profileSecurityStatus}]
            </span>
          )}
        </div>
      )}
    </Card>
  );

  const renderHistoricalLogs = (position) => (
    <Card
      slug="HistoricalRecordsLogs"
      title="HISTORICAL RECORDS LOGS"
      position={position}
    >
      {position === "main" ? (
        <div className="main-panel">
          <h2>HISTORICAL SYSTEM LOGS TERMINAL</h2>
        </div>
      ) : (
        <div className="preview-panel">
          {position === "sidebar" ? (
            <>
              <span className="badge badge-highlight">
                Sidebar: Archive System
              </span>
              <p className="card-summary">Pipeline: {archivePipelineStatus}</p>
            </>
          ) : (
            <span className="badge">
              Footer ({position}): Logs Stream {archivePipelineStatus}
            </span>
          )}
        </div>
      )}
    </Card>
  );

  const renderSystemSettings = (position) => (
    <Card slug="SystemSettings" title="SYSTEM SETTINGS" position={position}>
      {position === "main" ? (
        <div className="main-panel">
          <h2>SYSTEM PREFERENCES PORTAL</h2>
        </div>
      ) : (
        <div className="preview-panel">
          {position === "sidebar" ? (
            <>
              <span className="badge badge-highlight">
                Sidebar: Configuration Environment
              </span>
              <p className="card-summary">Status: {systemPortalStatus}</p>
            </>
          ) : (
            <span className="badge">
              Footer ({position}): Environment Config {systemPortalStatus}
            </span>
          )}
        </div>
      )}
    </Card>
  );

  const resolveModuleBySlot = (slotKey) => {
    switch (miscSlots[slotKey]) {
      case "SystemCalendar":
        return renderSystemCalendar(slotKey);
      case "AccountProfiles":
        return renderAccountProfiles(slotKey);
      case "HistoricalRecordsLogs":
        return renderHistoricalLogs(slotKey);
      case "SystemSettings":
        return renderSystemSettings(slotKey);
      default:
        return null;
    }
  };

  return (
    <div className="dashboard-grid-4pane">
      <div className="grid-main">{resolveModuleBySlot("main")}</div>
      <div className="grid-sidebar">{resolveModuleBySlot("sidebar")}</div>
      <div className="grid-bottom-left">
        {resolveModuleBySlot("bottomLeft")}
      </div>
      <div className="grid-bottom-right">
        {resolveModuleBySlot("bottomRight")}
      </div>
    </div>
  );
}
