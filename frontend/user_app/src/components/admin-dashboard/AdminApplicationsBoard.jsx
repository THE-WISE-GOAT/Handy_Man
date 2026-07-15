import React, { useEffect, useState, useMemo } from "react";
import { API_BASE_URL } from "@shared/config/api";
import { apiClient, normalizeApiError } from "@shared/api/client";
import "./AdminUsersBoard.css";

const REJECT_MODAL_ID = "reject-modal";

export default function AdminApplicationsBoard({ viewSlug }) {
  const [applications, setApplications] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionLoading, setActionLoading] = useState(null);
  const [rejectTarget, setRejectTarget] = useState(null);
  const [rejectReason, setRejectReason] = useState("");
  const [expandedId, setExpandedId] = useState(null);

  const loadApplications = async () => {
    console.log("[AdminApplicationsBoard] Loading applications...");
    setIsLoading(true);
    setError("");
    try {
      console.log("[AdminApplicationsBoard] Making API request to /worker-onboarding/admin/applications");
      const data = await apiClient.get("/worker-onboarding/admin/applications");
      console.log("[AdminApplicationsBoard] API response:", data);
      setApplications(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("[AdminApplicationsBoard] API request failed:", err);
      const normalized = normalizeApiError(err, "Failed to load applications.");
      let backendMsg = "";
      if (err.status === 404) {
        backendMsg = " Worker onboarding backend not available. Restart the backend server.";
      } else if (err.status === 401) {
        backendMsg = " Authentication required. Please log in as admin.";
      } else if (err.status === 403) {
        backendMsg = " Admin access required.";
      } else if (err.status === 0 || err.message?.includes("Network error")) {
        backendMsg = " Cannot reach the backend. Ensure it is running at http://localhost:8000.";
      }
      setError(normalized.message + backendMsg);
      console.error("[AdminApplicationsBoard] Load failed:", {
        status: err.status,
        message: err.message,
        url: err.url,
        apiBaseUrl: API_BASE_URL,
        errors: err.errors,
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadApplications();
  }, []);

  const handleApprove = async (workerId) => {
    setActionLoading(`approve-${workerId}`);
    try {
      await apiClient.post(`/worker-onboarding/admin/applications/${workerId}/approve`);
      await loadApplications();
    } catch (err) {
      const normalized = normalizeApiError(err, "Failed to approve application.");
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
    setActionLoading(`reject-${rejectTarget.id}`);
    try {
      await apiClient.post(
        `/worker-onboarding/admin/applications/${rejectTarget.id}/reject`,
        { reason: rejectReason.trim() }
      );
      setRejectTarget(null);
      setRejectReason("");
      await loadApplications();
    } catch (err) {
      const normalized = normalizeApiError(err, "Failed to reject application.");
      alert(normalized.message);
    } finally {
      setActionLoading(null);
    }
  };

  const renderHistoryPreview = (history) => {
    if (!history || !Array.isArray(history)) return <p className="admin-section__empty">No interview history.</p>;
    const visible = history.filter((m) => m.role && m.role !== "system");
    if (visible.length === 0) return <p className="admin-section__empty">No interview history.</p>;
    return (
      <div className="admin-chat-preview">
        {visible.slice(-6).map((msg, idx) => (
          <div key={idx} className={`admin-chat-bubble admin-chat-bubble--${msg.role}`}>
            <strong>{msg.role.toUpperCase()}:</strong> {msg.content}
          </div>
        ))}
      </div>
    );
  };

  const renderProfilePreview = (profile) => {
    if (!profile) return <p className="admin-section__empty">Profile not yet extracted.</p>;
    const entries = Object.entries(profile).filter(([_, v]) => v && !Array.isArray(v));
    const arrays = Object.entries(profile).filter(([_, v]) => Array.isArray(v) && v.length > 0);
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
            <span className="admin-profile-val">{Array.isArray(v) ? v.join(", ") : String(v)}</span>
          </div>
        ))}
      </div>
    );
  };

  const toggleExpand = (id) => {
    setExpandedId(expandedId === id ? null : id);
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
                  <div className="admin-application-header">
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
                        <span className="admin-detail-tag">Category: {app.job_category || "—"}</span>
                        <span className="admin-detail-tag">Tag: {app.category_tag || "—"}</span>
                        <span className="admin-detail-tag">Experience: {app.years_experience} yrs</span>
                        <span className="admin-detail-tag">Specialities: {app.specialities?.length > 0 ? app.specialities.join(", ") : "—"}</span>
                        {app.phone_number && (
                          <span className="admin-detail-tag">Phone: {app.phone_number}</span>
                        )}
                        {app.address_text && (
                          <span className="admin-detail-tag">Address: {app.address_text}</span>
                        )}
                      </div>
                    </div>
                    <div className="admin-application-actions">
                      <button
                        className="admin-btn admin-btn--approve"
                        onClick={() => handleApprove(app.id)}
                        disabled={actionLoading === `approve-${app.id}`}
                      >
                        {actionLoading === `approve-${app.id}` ? "Approving..." : "Approve"}
                      </button>
                      <button
                        className="admin-btn admin-btn--reject"
                        onClick={() => handleRejectClick(app)}
                        disabled={actionLoading === `reject-${app.id}`}
                      >
                        Reject
                      </button>
                      <button
                        className="admin-btn admin-btn--expand"
                        onClick={() => toggleExpand(app.id)}
                      >
                        {expandedId === app.id ? "Hide Details" : "View Details"}
                      </button>
                    </div>
                  </div>

                  {expandedId === app.id && (
                    <div className="admin-application-details-grid">
                      <div className="admin-detail-section">
                        <h4>AI Interview Transcript</h4>
                        {renderHistoryPreview(app.history)}
                      </div>
                      <div className="admin-detail-section">
                        <h4>Extracted Profile</h4>
                        {renderProfilePreview(app.profile)}
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
            position: "fixed", top: 0, left: 0, width: "100vw", height: "100vh",
            backgroundColor: "rgba(0, 0, 0, 0.5)", zIndex: 99999, display: "flex",
            alignItems: "center", justifyContent: "center", backdropFilter: "blur(3px)"
          }}
        >
          <div
            style={{
              background: "#ffffff", border: "3px solid #000000", borderRadius: "16px",
              boxShadow: "8px 8px 0px #000000", width: "400px", maxWidth: "90%",
              padding: "24px", display: "flex", flexDirection: "column", gap: "12px",
              fontFamily: "inherit"
            }}
          >
            <h3 style={{ margin: 0 }}>Reject Application</h3>
            <p style={{ margin: 0, fontSize: "0.85rem" }}>
              Rejecting application from <strong>{rejectTarget.username}</strong>.
              Please provide a reason:
            </p>
            <textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="Enter rejection reason..."
              rows={4}
              style={{
                width: "100%", border: "2px solid #000", borderRadius: "8px",
                padding: "10px", font: "inherit", fontSize: "0.85rem", resize: "vertical"
              }}
            />
            <div style={{ display: "flex", gap: "10px" }}>
              <button
                type="button"
                onClick={() => { setRejectTarget(null); setRejectReason(""); }}
                style={{
                  flex: 1, padding: "10px", background: "#f0f0f0", border: "2px solid #000",
                  borderRadius: "8px", font: "inherit", fontSize: "13px", fontWeight: "bold",
                  cursor: "pointer"
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleRejectConfirm}
                disabled={!rejectReason.trim() || actionLoading === `reject-${rejectTarget.id}`}
                style={{
                  flex: 1, padding: "10px", background: "#ffcccc", border: "2px solid #000",
                  borderRadius: "8px", font: "inherit", fontSize: "13px", fontWeight: "bold",
                  cursor: "pointer"
                }}
              >
                {actionLoading === `reject-${rejectTarget.id}` ? "Rejecting..." : "Confirm Reject"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
