// components/customer-dashboard/dash3board.jsx
import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useCustomerDashboardData } from "./useCustomerDashboardData";
import { apiClient } from "@shared/api/client";
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
    assignedJobs,
    activeAssignedJob,
    setActiveAssignedJob,
    fetchAssignedJobs,
  } = useCustomerDashboardData();

  useEffect(() => {
    fetchAssignedJobs();
  }, [fetchAssignedJobs]);

  useEffect(() => {
    if (assignedJobs.length > 0 && !activeAssignedJob) {
      setActiveAssignedJob(assignedJobs[0]);
    }
  }, [assignedJobs, activeAssignedJob, setActiveAssignedJob]);

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

  const handleJobSelect = (job) => {
    setActiveAssignedJob(job);
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

  const renderSystemCalendar = (position) => {
    const job = activeAssignedJob || assignedJobs[0];
    if (job) {
      if (position === "main") {
        return (
          <div className="dashboard-card slot-main">
            <div className="card-header">••• ASSIGNED JOB SCHEDULE</div>
            <div className="main-panel">
              <h2>{job.title} — Timeline</h2>
              <p><strong>Status:</strong> {job.status}</p>
              <p><strong>Created:</strong> {new Date(job.created_at).toLocaleString()}</p>
              <p><strong>Updated:</strong> {new Date(job.updated_at).toLocaleString()}</p>
              <p><strong>Address:</strong> {job.address_text}</p>
            </div>
          </div>
        );
      }

      return (
        <div
          className={`dashboard-card slot-${position} clickable`}
          onClick={() => handleModuleSelect("SystemCalendar")}
        >
          <div className="card-header">••• ASSIGNED JOB SCHEDULE</div>
          <div className="preview-panel">
            {position === "sidebar" ? (
              <>
                <span className="badge badge-highlight">Sidebar: Job Timeline</span>
                <p className="card-summary">{job.title} — {job.status}</p>
              </>
            ) : (
              <span className="badge">Footer ({position}): {job.status}</span>
            )}
          </div>
        </div>
      );
    }

    return (
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
  };

  const renderAccountProfiles = (position) => {
    const job = activeAssignedJob || assignedJobs[0];
    if (job) {
      if (position === "main") {
        return (
          <div className="dashboard-card slot-main">
            <div className="card-header">••• ASSIGNED WORKER DETAILS</div>
            <div className="main-panel">
              <h2>Assigned Worker</h2>
              <p><strong>Worker ID:</strong> {job.worker_id}</p>
              <p><strong>Booking Chat:</strong> {job.booking_chat_id}</p>
              <p><strong>Contact:</strong> {job.contact_name || "N/A"}</p>
              <p><strong>Phone:</strong> {job.contact_phone || "N/A"}</p>
            </div>
          </div>
        );
      }

      return (
        <div
          className={`dashboard-card slot-${position} clickable`}
          onClick={() => handleModuleSelect("AccountProfiles")}
        >
          <div className="card-header">••• ASSIGNED WORKER DETAILS</div>
          <div className="preview-panel">
            {position === "sidebar" ? (
              <>
                <span className="badge badge-highlight">Worker Node</span>
                <p className="card-summary">Worker ID: {job.worker_id}</p>
              </>
            ) : (
              <span className="badge">Footer ({position}): Assignment Specs</span>
            )}
          </div>
        </div>
      );
    }

    return (
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
  };

  const renderHistoricalLogs = (position) => {
    const job = activeAssignedJob || assignedJobs[0];
    if (job) {
      if (position === "main") {
        return (
          <div className="dashboard-card slot-main">
            <div className="card-header">••• JOB STATUS & TIMELINE</div>
            <div className="main-panel">
              <h2>{job.title}</h2>
              <p><strong>Status:</strong> {job.status}</p>
              <p><strong>Created:</strong> {new Date(job.created_at).toLocaleString()}</p>
              <p><strong>Updated:</strong> {new Date(job.updated_at).toLocaleString()}</p>
            </div>
          </div>
        );
      }

      return (
        <div
          className={`dashboard-card slot-${position} clickable`}
          onClick={() => handleModuleSelect("HistoricalRecordsLogs")}
        >
          <div className="card-header">••• JOB STATUS & TIMELINE</div>
          <div className="preview-panel">
            {position === "sidebar" ? (
              <>
                <span className="badge badge-highlight">Job Logs</span>
                <p className="card-summary">{job.title} — {job.status}</p>
              </>
            ) : (
              <span className="badge">Footer ({position}): Logs Stream</span>
            )}
          </div>
        </div>
      );
    }

    return (
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
  };

  const renderSystemSettings = (position) => {
    const job = activeAssignedJob || assignedJobs[0];
    if (job) {
      if (position === "main") {
        return (
          <div className="dashboard-card slot-main">
            <div className="card-header">••• LIVE MAP NODE TRACKER</div>
            <div className="main-panel">
              <h2>Dispatch Status Map</h2>
              {job.latitude && job.longitude ? (
                <p>
                  <strong>Location:</strong> {Number(job.latitude).toFixed(4)}, {Number(job.longitude).toFixed(4)}
                </p>
              ) : (
                <p>No geospatial data available for this job.</p>
              )}
              <p><strong>Address:</strong> {job.address_text}</p>
            </div>
          </div>
        );
      }

      return (
        <div
          className={`dashboard-card slot-${position} clickable`}
          onClick={() => handleModuleSelect("SystemSettings")}
        >
          <div className="card-header">••• LIVE MAP NODE TRACKER</div>
          <div className="preview-panel">
            {position === "sidebar" ? (
              <>
                <span className="badge badge-highlight">Map Node</span>
                <p className="card-summary">
                  {job.latitude && job.longitude
                    ? `${Number(job.latitude).toFixed(4)}, ${Number(job.longitude).toFixed(4)}`
                    : "No location"}
                </p>
              </>
            ) : (
              <span className="badge">Footer ({position}): Dispatch Active</span>
            )}
          </div>
        </div>
      );
    }

    return (
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
  };

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
