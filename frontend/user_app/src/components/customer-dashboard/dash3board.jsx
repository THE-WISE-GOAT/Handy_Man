// components/customer-dashboard/dash3board.jsx
import React from 'react';
import { useCustomerDashboardData } from './useCustomerDashboardData';
import './dash3board.css'; //

export default function Dash3Board() {
  // Pull positions and content variables directly from your Zustand store
  const {
    miscSlots,
    swapMiscSlots,
    calendarEventsCount,
    profileSecurityStatus,
    archivePipelineStatus,
    systemPortalStatus
  } = useCustomerDashboardData();

  // ====================================================
  // SUB-MODULE 1: SYSTEM CALENDAR
  // ====================================================
  const renderSystemCalendar = (position) => {
    if (position === "main") {
      return (
        <div className="section-card view-main">
          <div className="misc-card-header">••• SCHEDULE PLATFORM PLANNERS</div>
          <h2>SYSTEM CALENDAR</h2>
          <p className="description-text">Calendar Workspace Terminal Primary Schedule Router.</p>
          <div className="calendar-dummy-canvas">
            <p>Active Planned Tasks: {calendarEventsCount}</p>
          </div>
        </div>
      );
    }

    return (
      <div className={`section-card view-${position} clickable-swap-node`} onClick={() => swapMiscSlots(position)}>
        <div className="misc-card-header">••• SCHEDULE PLATFORM PLANNERS</div>
        <div className="sleeping-preview-box">
          <span className="pill-outline">Calendar Active — {calendarEventsCount} Events</span>
        </div>
      </div>
    );
  };

  // ====================================================
  // SUB-MODULE 2: ACCOUNT PROFILES
  // ====================================================
  const renderAccountProfiles = (position) => {
    if (position === "main") {
      return (
        <div className="section-card view-main">
          <div className="misc-card-header">••• ACCOUNT PROFILES</div>
          <h2>ACCOUNT PROFILE MANAGER</h2>
          <p>Configure client accounts, authentication layers, and permissions records details.</p>
        </div>
      );
    }

    return (
      <div className={`section-card view-${position} clickable-swap-node`} onClick={() => swapMiscSlots(position)}>
        <div className="misc-card-header">••• ACCOUNT PROFILES</div>
        <div className="sleeping-preview-box">
          <span className="pill-outline">{profileSecurityStatus}</span>
        </div>
      </div>
    );
  };

  // ====================================================
  // SUB-MODULE 3: HISTORICAL RECORDS LOGS
  // ====================================================
  const renderHistoricalLogs = (position) => {
    if (position === "main") {
      return (
        <div className="section-card view-main">
          <div className="misc-card-header">••• HISTORICAL RECORDS LOGS</div>
          <h2>HISTORICAL SYSTEM LOGS TERMINAL</h2>
        </div>
      );
    }

    return (
      <div className={`section-card view-${position} clickable-swap-node`} onClick={() => swapMiscSlots(position)}>
        <div className="misc-card-header">••• HISTORICAL RECORDS LOGS</div>
        <div className="sleeping-preview-box">
          <span className="pill-outline">{archivePipelineStatus}</span>
        </div>
      </div>
    );
  };

  // ====================================================
  // SUB-MODULE 4: SYSTEM SETTINGS
  // ====================================================
  const renderSystemSettings = (position) => {
    if (position === "main") {
      return (
        <div className="section-card view-main">
          <div className="misc-card-header">••• SYSTEM SETTINGS</div>
          <h2>SYSTEM PREFERENCES PORTAL</h2>
        </div>
      );
    }

    return (
      <div className={`section-card view-${position} clickable-swap-node`} onClick={() => swapMiscSlots(position)}>
        <div className="misc-card-header">••• SYSTEM SETTINGS</div>
        <div className="sleeping-preview-box">
          <span className="pill-outline">{systemPortalStatus}</span>
        </div>
      </div>
    );
  };

  // ====================================================
  // SLOTS ROUTING LOGIC
  // ====================================================
  const resolveModuleBySlot = (slotKey) => {
    const targetModuleName = miscSlots[slotKey];
    switch (targetModuleName) {
      case "SystemCalendar":        return renderSystemCalendar(slotKey);
      case "AccountProfiles":       return renderAccountProfiles(slotKey);
      case "HistoricalRecordsLogs": return renderHistoricalLogs(slotKey);
      case "SystemSettings":        return renderSystemSettings(slotKey);
      default:                      return null;
    }
  };

  // ====================================================
  // MULTI-PANE STRUCTURAL MISC GRID SYSTEM
  // ====================================================
  return (
    <div className="misc-dashboard-canvas-grid">
      <div className="grid-area-main">{resolveModuleBySlot("main")}</div>
      <div className="grid-area-sidebar">{resolveModuleBySlot("sidebar")}</div>
      <div className="grid-area-bottom-left">{resolveModuleBySlot("bottomLeft")}</div>
      <div className="grid-area-bottom-right">{resolveModuleBySlot("bottomRight")}</div>
    </div>
  );
}