// components/worker-dashboard/dash2worker.jsx
import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useWorkerDashboardData } from "./useWorkerDashboardData";
import { apiClient } from "@shared/api/client";
import "./dash2worker.css";

export default function Dash2Worker({ viewSlug }) {
  const navigate = useNavigate();

  const {
    scheduledSlots,
    swapScheduledSlots,
    calendarDescText,
    jobsRegistryStatus,
    clientQueryStatus,
    routeMatrixStatus,
    assignedJobs,
    activeAssignedJob,
    setActiveAssignedJob,
    fetchAssignedJobs,
  } = useWorkerDashboardData();

  useEffect(() => {
    fetchAssignedJobs();
  }, [fetchAssignedJobs]);

  useEffect(() => {
    if (!viewSlug) return;

    if (scheduledSlots.main !== viewSlug) {
      const targetSlot = Object.keys(scheduledSlots).find(
        (key) => scheduledSlots[key] === viewSlug,
      );

      if (targetSlot) {
        swapScheduledSlots(targetSlot);
      }
    }
  }, [viewSlug, scheduledSlots, swapScheduledSlots]);

  useEffect(() => {
    if (assignedJobs.length > 0 && !activeAssignedJob) {
      setActiveAssignedJob(assignedJobs[0]);
    }
  }, [assignedJobs, activeAssignedJob, setActiveAssignedJob]);

  const handleModuleSelect = (targetSlug) => {
    navigate(`/worker/scheduled/${targetSlug}`);
  };

  const handleJobSelect = (job) => {
    setActiveAssignedJob(job);
  };

  // ====================================================
  // SUB-MODULE RENDERS
  // ====================================================

  const job = activeAssignedJob || assignedJobs[0];

  const renderCalendar = (slotKey) => {
    if (slotKey === "main") {
      return (
        <div className="dashboard-card slot-main">
          <div className="card-header">••• ASSIGNED JOB SCHEDULE</div>

          <div className="main-panel">
            {job ? (
              <>
                <h2>{job.title} — Timeline</h2>
                <p><strong>Status:</strong> {job.status}</p>
                <p><strong>Created:</strong> {new Date(job.created_at).toLocaleString()}</p>
                <p><strong>Updated:</strong> {new Date(job.updated_at).toLocaleString()}</p>
                <p><strong>Address:</strong> {job.address_text}</p>
              </>
            ) : (
              <>
                <h2>System Planner Calendar</h2>
                <p className="panel-desc">{calendarDescText}</p>
              </>
            )}
          </div>
        </div>
      );
    }

    return (
      <div
        className={`dashboard-card slot-${slotKey} clickable`}
        onClick={() => handleModuleSelect("ScheduledCalendar")}
      >
        <div className="card-header">••• ASSIGNED JOB SCHEDULE</div>

        <div className="preview-panel">
          {slotKey === "sidebar" ? (
            <>
              <span className="badge badge-highlight">
                Sidebar: Job Timeline
              </span>

              <p className="card-summary">
                {job ? `${job.title} — ${job.status}` : calendarDescText}
              </p>
            </>
          ) : (
            <span className="badge">
              Footer ({slotKey}): {job ? job.status : "Calendar Monitor Live"}
            </span>
          )}
        </div>
      </div>
    );
  };

  const renderJobRegistry = (slotKey) => {
    if (slotKey === "main") {
      return (
        <div className="dashboard-card slot-main">
          <div className="card-header">••• ASSIGNED JOB DETAILS</div>

          <div className="main-panel">
            {job ? (
              <>
                <h2>{job.title}</h2>
                <p><strong>Status:</strong> {job.status}</p>
                <p><strong>Description:</strong> {job.description}</p>
                <p><strong>Contact:</strong> {job.contact_name || "N/A"}</p>
                <p><strong>Phone:</strong> {job.contact_phone || "N/A"}</p>
                <p><strong>Address:</strong> {job.address_text || "N/A"}</p>
                {job.booking_chat_id && (
                  <p><strong>Booking Chat:</strong> {job.booking_chat_id}</p>
                )}
              </>
            ) : (
              <>
                <h2>Scheduled Jobs Registry</h2>
              </>
            )}
          </div>
        </div>
      );
    }

    return (
      <div
        className={`dashboard-card slot-${slotKey} clickable`}
        onClick={() => handleModuleSelect("ScheduledJobCard")}
      >
        <div className="card-header">••• ASSIGNED JOB DETAILS</div>

        <div className="preview-panel">
          {slotKey === "sidebar" ? (
            <>
              <span className="badge badge-highlight">Sidebar: Job Matrix</span>

              <p className="card-summary">
                {job ? `${job.title} — ${job.status}` : jobsRegistryStatus}
              </p>
            </>
          ) : (
            <span className="badge">
              Footer ({slotKey}): {job ? job.status : `Registry — ${jobsRegistryStatus}`}
            </span>
          )}
        </div>
      </div>
    );
  };

  const renderClientQueries = (slotKey) => {
    if (slotKey === "main") {
      return (
        <div className="dashboard-card slot-main">
          <div className="card-header">••• ACTIVE BOOKING CHAT</div>

          <div className="main-panel">
            {job?.booking_chat_id ? (
              <>
                <h2>Booking Chat: {job.booking_chat_id}</h2>
                <p>Real-time communication with customer for assigned job <strong>{job.title}</strong>.</p>
                <p><strong>Customer:</strong> {job.contact_name || "N/A"}</p>
              </>
            ) : (
              <>
                <h2>Client Communications Terminal</h2>
                <p>No active booking chat for this job.</p>
              </>
            )}
          </div>
        </div>
      );
    }

    return (
      <div
        className={`dashboard-card slot-${slotKey} clickable`}
        onClick={() => handleModuleSelect("ClientQueries")}
      >
        <div className="card-header">••• ACTIVE BOOKING CHAT</div>

        <div className="preview-panel">
          {slotKey === "sidebar" ? (
            <>
              <span className="badge badge-highlight">
                Sidebar: Inbox Comms
              </span>

              <p className="card-summary">
                {job?.booking_chat_id
                  ? `Chat ${job.booking_chat_id} — ${job.title}`
                  : `Queue: ${clientQueryStatus}`}
              </p>
            </>
          ) : (
            <span className="badge">
              Footer ({slotKey}): {job?.booking_chat_id ? "Comms Active" : `Comms Feed (${clientQueryStatus})`}
            </span>
          )}
        </div>
      </div>
    );
  };

  const renderRouteMatrix = (slotKey) => {
    if (slotKey === "main") {
      return (
        <div className="dashboard-card slot-main">
          <div className="card-header">••• APPOINTMENT LOCATION INDEX</div>

          <div className="main-panel">
            {job ? (
              <>
                <h2>Job Location — {job.title}</h2>
                {job.latitude && job.longitude ? (
                  <p>
                    <strong>Coordinates:</strong> {Number(job.latitude).toFixed(6)}, {Number(job.longitude).toFixed(6)}
                  </p>
                ) : (
                  <p>No geospatial data available for this job.</p>
                )}
                <p><strong>Address:</strong> {job.address_text}</p>
              </>
            ) : (
              <>
                <h2>Route Matrix Overview</h2>
              </>
            )}
          </div>
        </div>
      );
    }

    return (
      <div
        className={`dashboard-card slot-${slotKey} clickable`}
        onClick={() => handleModuleSelect("ScheduledMap")}
      >
        <div className="card-header">••• APPOINTMENT LOCATION INDEX</div>

        <div className="preview-panel">
          {slotKey === "sidebar" ? (
            <>
              <span className="badge badge-highlight">
                Sidebar: Matrix Node
              </span>

              <p className="card-summary">
                {job && job.latitude && job.longitude
                  ? `${Number(job.latitude).toFixed(4)}, ${Number(job.longitude).toFixed(4)}`
                  : `Routing: ${routeMatrixStatus}`}
              </p>
            </>
          ) : (
            <span className="badge">
              Footer ({slotKey}): {job ? "Dispatch Active" : `Routing Stream [${routeMatrixStatus}]`}
            </span>
          )}
        </div>
      </div>
    );
  };

  const resolveModuleBySlot = (slotKey) => {
    switch (scheduledSlots[slotKey]) {
      case "ScheduledCalendar":
        return renderCalendar(slotKey);

      case "ScheduledJobCard":
        return renderJobRegistry(slotKey);

      case "ClientQueries":
        return renderClientQueries(slotKey);

      case "ScheduledMap":
        return renderRouteMatrix(slotKey);

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
