// components/worker-dashboard/dash4worker.jsx
import React from 'react';
import { useWorkerDashboardData } from './useWorkerDashboardData';
import './dash4worker.css';

export default function Dash4Worker() {
  const { micsSlots, swapMicsSlots, micsEmptyLabel } = useWorkerDashboardData();

  // ====================================================
  // SUB-MODULE 1: EMPTY VIEW MICS PORTAL
  // ====================================================
  const renderMicsEmpty = (position) => {
    if (position === "main") {
      return (
        <div className="worker-section-card view-main unified-center-content">
          <div className="worker-card-header">EMPTY WORKING STATE</div>
          <h2>Mics Portal</h2>
          <div className="mics-massive-fallback-text">{micsEmptyLabel}</div>
        </div>
      );
    }

    return (
      <div className={`worker-section-card view-${position} worker-clickable-node`} onClick={() => swapMicsSlots(position)}>
        <div className="worker-card-header">EMPTY WORKING STATE</div>
        <div className="worker-sleeping-box">
          <span className="worker-pill-outline">Mics Dashboard</span>
        </div>
      </div>
    );
  };

  // ====================================================
  // TRANSLATION DISPATCHER
  // ====================================================
  const resolveModuleBySlot = (slotKey) => {
    const moduleName = micsSlots[slotKey];
    switch (moduleName) {
      case "MicsEmpty": return renderMicsEmpty(slotKey);
      default:          return null;
    }
  };

  // ====================================================
  // PHYSICAL CANVAS STRUCTURE LAYER
  // ====================================================
  return (
    <div className="worker-mics-canvas-grid">
      <div className="grid-area-main">{resolveModuleBySlot("main")}</div>
      {/* Future secondary modules will add their specific slot wrapper regions below cleanly */}
    </div>
  );
}