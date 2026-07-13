import React from "react";
import "./AdminUsersBoard.css";

export default function AdminApplicationsBoard({ viewSlug }) {
  return (
    <div className="admin-board">
      <div className="admin-board__head">
        <span className="card-flag">WORKER ONBOARDING PIPELINE</span>
        <h1>WORKER APPLICATIONS</h1>
        <p className="admin-board__sub">
          Incoming worker interview sessions and verification requests.
        </p>
      </div>
      <section className="admin-section">
        <div className="admin-section__head">
          <h2>Worker Applications</h2>
        </div>
        <p className="admin-section__empty">
          Worker application management is not wired up yet — this tab is a
          placeholder.
        </p>
      </section>
    </div>
  );
}
