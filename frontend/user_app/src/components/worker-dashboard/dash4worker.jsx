// components/worker-dashboard/dash4worker.jsx
import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useWorkerDashboardData } from "./useWorkerDashboardData";
import "./dash4worker.css";

export default function Dash4Worker({ viewSlug }) {
  const navigate = useNavigate();

  const { micsSlots, swapMicsSlots, micsEmptyLabel } = useWorkerDashboardData();

  // Route state synchronization layer
  useEffect(() => {
    if (!viewSlug) return;

    if (micsSlots.main !== viewSlug) {
      const targetSlot = Object.keys(micsSlots).find(
        (key) => micsSlots[key] === viewSlug,
      );

      if (targetSlot) {
        swapMicsSlots(targetSlot);
      }
    }
  }, [viewSlug, micsSlots, swapMicsSlots]);

  const handleModuleSelect = (targetSlug) => {
    navigate(`/worker/mics/${targetSlug}`);
  };

  // ====================================================
  // SUB-MODULE RENDERS
  // ====================================================

  const renderMicsEmpty = (slotKey) => {
    if (slotKey === "main") {
      return (
        <div className="dashboard-card slot-main center-content">
          <div className="card-header">••• EMPTY WORKING STATE</div>

          <div className="main-panel">
            <h2>Mics Portal</h2>

            <div className="fallback-text-large">{micsEmptyLabel}</div>
          </div>
        </div>
      );
    }

    return (
      <div
        className={`dashboard-card slot-${slotKey} clickable`}
        onClick={() => handleModuleSelect("MicsEmpty")}
      >
        <div className="card-header">••• EMPTY WORKING STATE</div>

        <div className="preview-panel">
          {slotKey === "sidebar" ? (
            <>
              <span className="badge badge-highlight">
                Sidebar: Mics Dashboard
              </span>

              <p className="card-summary">{micsEmptyLabel}</p>
            </>
          ) : (
            <span className="badge">
              Footer ({slotKey}): Mics Blueprint Empty
            </span>
          )}
        </div>
      </div>
    );
  };

  const resolveModuleBySlot = (slotKey) => {
    switch (micsSlots[slotKey]) {
      case "MicsEmpty":
        return renderMicsEmpty(slotKey);

      default:
        return null;
    }
  };

  return (
    <div className="worker-mics-canvas-grid">
      <div className="grid-area-main">{resolveModuleBySlot("main")}</div>

      <div className="grid-area-sidebar">{resolveModuleBySlot("sidebar")}</div>

      <div className="grid-area-bottom-left">
        {resolveModuleBySlot("bottomLeft")}
      </div>

      <div className="grid-area-bottom-right">
        {resolveModuleBySlot("bottomRight")}
      </div>
    </div>
  );
}
