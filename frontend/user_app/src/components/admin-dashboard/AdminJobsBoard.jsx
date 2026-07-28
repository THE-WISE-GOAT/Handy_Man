import React from "react";
import "./AdminUsersBoard.css";

export default function AdminJobsBoard({ viewSlug }) {
  return (
    <div className="admin-board">
      <div className="admin-board__head">
        <span className="card-flag">PLATFORM JOB REGISTRY</span>
        <h1>JOBS</h1>
        <p className="admin-board__sub">
          Posted jobs and active service tasks across the platform.
        </p>
      </div>
      <section className="admin-section">
        <div className="admin-section__head">
          <h2>Jobs</h2>
        </div>
        <p className="admin-section__empty">
          Job management is not wired up yet — this tab is a placeholder.
        </p>
      </section>
    </div>
  );
}
