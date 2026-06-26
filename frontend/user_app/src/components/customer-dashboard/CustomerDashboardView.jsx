import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Dash1board from "./dash1board"; 
import Dash2board from "./dash2board"; 
import Dash3board from "./dash3board"; 
import { CUSTOMER_VIEWS, buildCustomerViewPath, getCustomerViewForModule } from "@shared/config/viewRoutes";

import "./customer-dashboard.css"; 
import "./dash1board.css";         
import "./dash2board.css";         
import "./dash3board.css"; 

const CATEGORY_LAYOUTS = {
  bookings: { modules: [{ id: "ai-chat" }, { id: "job-description" }, { id: "my-posts" }] },
  postings: { modules: [{ id: "biddings" }, { id: "map" }, { id: "active-post-v2" }, { id: "ratings-review" }] },
  more: { modules: [{ id: "calendar" }, { id: "account" }, { id: "history" }, { id: "settings" }] }
};

export default function CustomerDashboardView({ embedded = false, activeView = CUSTOMER_VIEWS.AI_CHAT, onViewSelect }) {
  const navigate = useNavigate();
  const currentCategory = activeView.categoryKey;

  const [moduleOrder, setModuleOrder] = useState([]);
  const [lastCategory, setLastCategory] = useState("");

  // Sync state module order when category changes or external route adjustments occur
  useEffect(() => {
    const defaultIds = (CATEGORY_LAYOUTS[currentCategory]?.modules || []).map(m => m.id);
    const activeId = activeView.moduleId;

    if (currentCategory !== lastCategory) {
      let initialOrder = [...defaultIds];
      if (activeId && initialOrder.includes(activeId)) {
        const idx = initialOrder.indexOf(activeId);
        if (idx > 0) {
          initialOrder[idx] = initialOrder[0];
          initialOrder[0] = activeId;
        }
      }
      setModuleOrder(initialOrder);
      setLastCategory(currentCategory);
    } else if (activeId && moduleOrder.length > 0 && moduleOrder[0] !== activeId) {
      const idx = moduleOrder.indexOf(activeId);
      if (idx !== -1) {
        const updated = [...moduleOrder];
        updated[idx] = updated[0];
        updated[0] = activeId;
        setModuleOrder(updated);
      }
    }
  }, [currentCategory, activeView.moduleId, lastCategory, moduleOrder]);

  const handleModuleSwap = (clickedModuleId) => {
    const clickedIndex = moduleOrder.indexOf(clickedModuleId);
    if (clickedIndex === -1) return;

    const updatedOrder = [...moduleOrder];
    const currentMainStageId = updatedOrder[0];

    // Core Exchange: Swap item directly into Slot 0, sending old main stage back to its visual slot
    updatedOrder[0] = clickedModuleId;
    updatedOrder[clickedIndex] = currentMainStageId;
    setModuleOrder(updatedOrder);

    // Sync route mapping state change
    const nextView = getCustomerViewForModule(currentCategory, clickedModuleId);
    if (!nextView) return;
    if (onViewSelect) {
      onViewSelect(nextView);
    } else {
      navigate(buildCustomerViewPath(nextView));
    }
  };

  const getModuleData = (moduleId) => {
    const linkedView = getCustomerViewForModule(currentCategory, moduleId);
    return {
      id: moduleId,
      title: linkedView?.label || "Workspace Panel",
      subtitle: linkedView?.subtitle || "",
      previewText: linkedView?.previewText || "",
    };
  };

  const RenderSleepingModule = ({ targetModuleId }) => {
    if (!targetModuleId) return null;
    const targetModule = getModuleData(targetModuleId);

    return (
      <div className="fixfast-sleep-card" onClick={() => handleModuleSwap(targetModule.id)}>
        <div className="fixfast-sleep-card__topbar">
          <div className="fixfast-sleep-card__traffic"><i></i><i></i><i></i></div>
          <div className="fixfast-sleep-card__title">{targetModule.title}</div>
        </div>
        <div className="fixfast-sleep-card__body">
          <div className="fixfast-preview-content">
            <div className="fixfast-preview-pill">
              <strong>{targetModule.previewText}</strong>
            </div>
          </div>
        </div>
      </div>
    );
  };

  if (moduleOrder.length === 0) return null;

  const mainStageModule = getModuleData(moduleOrder[0]);

  const content = (
    <>
      {currentCategory === "bookings" && (
        <main className="db1-shell">
          <section className="db1-stage-zone fixfast-stage">
            <div className="fixfast-stage__header">
              <span style={{ fontSize: "0.72rem", color: "var(--fixfast-muted)", fontWeight: 800, textTransform: "uppercase" }}>
                {mainStageModule.subtitle}
              </span>
              <h1>{mainStageModule.title}</h1>
            </div>
            <div style={{ flex: 1, overflowY: "auto" }}>
              <Dash1board activeModuleId={mainStageModule.id} />
            </div>
          </section>
          <section className="db1-sidebar-zone">
            <RenderSleepingModule targetModuleId={moduleOrder[1]} />
          </section>
          <section className="db1-deck-zone">
            {moduleOrder.slice(2).map((modId) => (
              <RenderSleepingModule key={modId} targetModuleId={modId} />
            ))}
          </section>
        </main>
      )}

      {currentCategory === "postings" && (
        <main className="db2-shell">
          <section className="db2-stage-zone fixfast-stage">
            <div className="fixfast-stage__header">
              <span style={{ fontSize: "0.72rem", color: "var(--fixfast-muted)", fontWeight: 800, textTransform: "uppercase" }}>
                {mainStageModule.subtitle}
              </span>
              <h1>{mainStageModule.title}</h1>
            </div>
            <div style={{ flex: 1, overflowY: "auto" }}>
              <Dash2board activeModuleId={mainStageModule.id} />
            </div>
          </section>
          <section className="db2-sidebar-zone">
            <RenderSleepingModule targetModuleId={moduleOrder[1]} />
          </section>
          <section className="db2-deck-left-zone">
            <RenderSleepingModule targetModuleId={moduleOrder[2]} />
          </section>
          <section className="db2-deck-right-zone">
            <RenderSleepingModule targetModuleId={moduleOrder[3]} />
          </section>
        </main>
      )}

      {currentCategory === "more" && (
        <main className="db3-shell">
          <section className="db3-stage-zone fixfast-stage">
            <div className="fixfast-stage__header">
              <span style={{ fontSize: "0.72rem", color: "var(--fixfast-muted)", fontWeight: 800, textTransform: "uppercase" }}>
                {mainStageModule.subtitle}
              </span>
              <h1>{mainStageModule.title}</h1>
            </div>
            <div style={{ flex: 1, overflowY: "auto" }}>
              <Dash3board activeModuleId={mainStageModule.id} />
            </div>
          </section>
          <section className="db3-account-zone">
            <RenderSleepingModule targetModuleId={moduleOrder[1]} />
          </section>
          <section className="db3-history-zone">
            <RenderSleepingModule targetModuleId={moduleOrder[2]} />
          </section>
          <section className="db3-settings-zone">
            <RenderSleepingModule targetModuleId={moduleOrder[3]} />
          </section>
        </main>
      )}
    </>
  );

  return embedded ? content : <div className="fixfast-page">{content}</div>;
}