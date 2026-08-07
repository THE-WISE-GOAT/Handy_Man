import React, { useEffect, useState } from "react";
import { apiClient, normalizeApiError } from "@shared/api/client";
import { API_BASE_URL } from "@shared/config/api";
import "./AdminUsersBoard.css";

export default function AdminApplicationsBoard({ viewSlug }) {
  const [applications, setApplications] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionLoading, setActionLoading] = useState(null);
  const [rejectTarget, setRejectTarget] = useState(null);
  const [rejectReason, setRejectReason] = useState("");
  const [expandedId, setExpandedId] = useState(null);
  const [expandedHistory, setExpandedHistory] = useState({});

  const loadApplications = async () => {
    setIsLoading(true);
    setError("");
    try {
      const data = await apiClient.get("/worker-onboarding/admin/applications");
      setApplications(Array.isArray(data) ? data : []);
    } catch (err) {
      const normalized = normalizeApiError(err, "Failed to load applications.");
      const backendMsg =
        err.status === 404
          ? " Worker onboarding backend not available. Restart the backend server."
          : "";
      setError(normalized.message + backendMsg);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadApplications();
  }, []);

  const handleApprove = async (skillId) => {
    setActionLoading(`approve-${skillId}`);
    try {
      await apiClient.post(
        `/worker-onboarding/admin/applications/${skillId}/approve`,
      );
      await loadApplications();
    } catch (err) {
      const normalized = normalizeApiError(
        err,
        "Failed to approve application.",
      );
      alert(normalized.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleRejectClick = (app) => {
    setRejectTarget(app);
    setRejectReason("");
  };

  const handleRejectConfirm = async () => {
    if (!rejectTarget || !rejectReason.trim()) return;
    setActionLoading(`reject-${rejectTarget.skill_id}`);
    try {
      await apiClient.post(
        `/worker-onboarding/admin/applications/${rejectTarget.skill_id}/reject`,
        { reason: rejectReason.trim() },
      );
      setRejectTarget(null);
      setRejectReason("");
      await loadApplications();
    } catch (err) {
      const normalized = normalizeApiError(
        err,
        "Failed to reject application.",
      );
      alert(normalized.message);
    } finally {
      setActionLoading(null);
    }
  };

  const toggleExpand = async (app) => {
    if (expandedId === app.id) {
      setExpandedId(null);
      return;
    }

    setExpandedId(app.id);

    if (!expandedHistory[app.id] && app.worker_chat_id) {
      try {
        const token = localStorage.getItem("handy_man_access_token");
        const response = await fetch(
          `${API_BASE_URL}/worker-interview/${app.worker_chat_id}/history`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          },
        );

        if (response.ok) {
          const data = await response.json();
          setExpandedHistory((prev) => ({
            ...prev,
            [app.id]: data.history || [],
          }));
        }
      } catch (err) {
        console.error("Failed to load chat history:", err);
      }
    }
  };

  const renderHistoryPreview = (history) => {
    if (!history || !Array.isArray(history))
      return <p className="admin-section__empty">No interview history.</p>;
    const visible = history.filter((m) => m.role && m.role !== "system");
    if (visible.length === 0)
      return <p className="admin-section__empty">No interview history.</p>;
    return (
      <div className="admin-chat-preview">
        {visible.map((msg, idx) => (
          <div
            key={idx}
            className={`admin-chat-bubble admin-chat-bubble--${msg.role}`}
          >
            <strong>{msg.role?.toUpperCase()}:</strong> {msg.content}
          </div>
        ))}
      </div>
    );
  };

  const renderProfilePreview = (app) => {
    // Prefer the AI-extracted interview profile; if it is missing, fall back
    // to the persisted WorkerProfile columns so the admin always sees the
    // details the worker submitted (category, tag, specialities, etc.).
    const profile =
      app && app.profile
        ? app.profile
        : app
          ? {
              job_category: app.job_category,
              category_tag: app.category_tag,
              is_custom_category: app.is_custom_category,
              specialities: app.specialities,
              years_experience: app.years_experience,
              license_or_certification: app.license_or_certification,
              job_description: app.job_description,
              emergency_available: app.emergency_available,
            }
          : null;

    if (!profile)
      return <p className="admin-section__empty">Profile not yet extracted.</p>;
    const entries = Object.entries(profile).filter(
      ([_, v]) => v && !Array.isArray(v),
    );
    const arrays = Object.entries(profile).filter(
      ([_, v]) => Array.isArray(v) && v.length > 0,
    );
    return (
      <div className="admin-profile-preview">
        {entries.map(([k, v]) => (
          <div key={k} className="admin-profile-row">
            <span className="admin-profile-key">{k}:</span>
            <span className="admin-profile-val">{String(v)}</span>
          </div>
        ))}
        {arrays.map(([k, v]) => (
          <div key={k} className="admin-profile-row">
            <span className="admin-profile-key">{k}:</span>
            <span className="admin-profile-val">
              {Array.isArray(v) ? v.join(", ") : String(v)}
            </span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="admin-board">
      <div className="admin-board__head">
        <span className="card-flag">WORKER ONBOARDING PIPELINE</span>
        <h1>WORKER APPLICATIONS</h1>
        <p className="admin-board__sub">
          Review and approve incoming worker applications pending admin review.
        </p>
      </div>

      {isLoading && <p className="admin-status">Loading applications…</p>}
      {error && <p className="admin-status admin-status--error">{error}</p>}

      {!isLoading && !error && (
        <section className="admin-section">
          <div className="admin-section__head">
            <h2>Pending Applications ({applications.length})</h2>
          </div>
          {applications.length === 0 ? (
            <p className="admin-section__empty">No pending applications.</p>
          ) : (
            <div className="admin-applications-list">
              {applications.map((app) => (
                <div key={app.id} className="admin-application-card">
                  <div
                    className="admin-application-header"
                    onClick={() => toggleExpand(app)}
                    style={{ cursor: "pointer" }}
                  >
                    <div className="admin-application-info">
                      <h3>
                        {app.firstName && app.lastName
                          ? `${app.firstName} ${app.lastName}`
                          : app.username}
                        <span className="admin-pill">Worker Application</span>
                      </h3>
                      <p className="admin-application-meta">
                        {app.email} • ID: {app.user_id} • App ID: {app.id}
                      </p>
                      <div className="admin-application-details">
                        <span className="admin-detail-tag">
                          Skill: {app.skill_title || "—"}
                        </span>
                        <span className="admin-detail-tag">
                          Type: {app.skill_type || "—"}
                        </span>
                        <span className="admin-detail-tag">
                          Experience: {app.years_experience} yrs
                        </span>
                        <span className="admin-detail-tag">
                          Specialities:{" "}
                          {app.specialities?.length > 0
                            ? app.specialities.join(", ")
                            : "—"}
                        </span>
                        {app.phone_number && (
                          <span className="admin-detail-tag">
                            Phone: {app.phone_number}
                          </span>
                        )}
                        {app.address_text && (
                          <span className="admin-detail-tag">
                            Address: {app.address_text}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="admin-application-actions">
                      <button
                        className="admin-btn admin-btn--approve"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleApprove(app.skill_id);
                        }}
                        disabled={actionLoading === `approve-${app.skill_id}`}
                      >
                        {actionLoading === `approve-${app.skill_id}`
                          ? "Approving..."
                          : "Approve"}
                      </button>
                      <button
                        className="admin-btn admin-btn--reject"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRejectClick(app);
                        }}
                        disabled={actionLoading === `reject-${app.skill_id}`}
                      >
                        Reject
                      </button>
                      <span className="admin-expand-hint">
                        {expandedId === app.id ? "▲ Hide" : "▼ View Details"}
                      </span>
                    </div>
                  </div>

                  {expandedId === app.id && (
                    <div className="admin-application-details-grid">
                      <div className="admin-detail-section">
                        <h4>Worker Details</h4>
                        {renderProfilePreview(app)}
                        {app.phone_number && (
                          <p>
                            <strong>Phone:</strong> {app.phone_number}
                          </p>
                        )}
                        {app.address_text && (
                          <p>
                            <strong>Address:</strong> {app.address_text}
                          </p>
                        )}
                        {app.latitude != null && app.longitude != null && (
                          <p>
                            <strong>Location:</strong>{" "}
                            {app.longitude.toFixed(4)},{" "}
                            {app.latitude.toFixed(4)}
                          </p>
                        )}
                      </div>
                      <div className="admin-detail-section">
                        <h4>AI Interview Transcript</h4>
                        {renderHistoryPreview(
                          expandedHistory[app.id] || app.history,
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* Reject Modal */}
      {rejectTarget && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            width: "100vw",
            height: "100vh",
            backgroundColor: "rgba(0, 0, 0, 0.6)",
            zIndex: 99999,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            backdropFilter: "blur(3px)",
          }}
        >
          <div
            style={{
              background: "var(--ind-surface)",
              border: "1px solid var(--ind-border)",
              borderRadius: "16px",
              boxShadow: "var(--ind-shadow-tight)",
              width: "400px",
              maxWidth: "90%",
              padding: "24px",
              display: "flex",
              flexDirection: "column",
              gap: "12px",
              fontFamily: "inherit",
            }}
          >
            <h3 style={{ margin: 0 }}>Reject Application</h3>
            <p style={{ margin: 0, fontSize: "0.85rem" }}>
              Rejecting application from{" "}
              <strong>{rejectTarget.username}</strong>. Please provide a reason:
            </p>
            <textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="Enter rejection reason..."
              rows={4}
              style={{
                width: "100%",
                border: "1px solid var(--ind-border)",
                borderRadius: "8px",
                padding: "10px",
                font: "inherit",
                fontSize: "0.85rem",
                resize: "vertical",
                background: "var(--ind-surface-alpha-40)",
                color: "var(--ind-white)",
              }}
            />
            <div style={{ display: "flex", gap: "10px" }}>
              <button
                type="button"
                onClick={() => {
                  setRejectTarget(null);
                  setRejectReason("");
                }}
                style={{
                  flex: 1,
                  padding: "10px",
                  background: "rgba(31, 31, 31, 0.4)",
                  border: "1px solid rgba(245, 245, 247, 0.14)",
                  borderRadius: "8px",
                  font: "inherit",
                  fontSize: "13px",
                  fontWeight: "bold",
                  cursor: "pointer",
                  color: "#F5F5F7",
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleRejectConfirm}
                disabled={
                  !rejectReason.trim() ||
                  actionLoading === `reject-${rejectTarget.skill_id}`
                }
                style={{
                  flex: 1,
                  padding: "10px",
                  background: "rgba(220, 53, 69, 0.15)",
                  border: "1px solid rgba(220, 53, 69, 0.3)",
                  borderRadius: "8px",
                  font: "inherit",
                  fontSize: "13px",
                  fontWeight: "bold",
                  cursor: "pointer",
                  color: "#ff6b6b",
                }}
              >
                {actionLoading === `reject-${rejectTarget.skill_id}`
                  ? "Rejecting..."
                  : "Confirm Reject"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
