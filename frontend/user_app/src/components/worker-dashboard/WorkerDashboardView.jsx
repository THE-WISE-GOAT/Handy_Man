import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Dash1worker from "./dash1worker";
import Dash2worker from "./dash2worker";
import Dash3worker from "./dash3worker";
import Dash4worker from "./dash4worker";
import { WORKER_VIEWS, buildWorkerViewPath, getWorkerViewForModule } from "@shared/config/viewRoutes";
import "./worker-dashboard.css";

const CATEGORY_LAYOUTS = {
  workspace: { modules: [{ id: "wk-map" }, { id: "wk-bids" }, { id: "wk-details" }] },
  scheduled: { modules: [{ id: "wk-sched-map" }, { id: "wk-sched-job" }, { id: "wk-queries" }, { id: "wk-calendar" }] },
  me: { modules: [{ id: "wk-interview" }, { id: "wk-profile" }, { id: "wk-config" }, { id: "wk-tags" }] },
  mics: { modules: [{ id: "wk-empty" }] }
};

export default function WorkerDashboardView({ embedded = false, activeView = WORKER_VIEWS.MAP, onViewSelect }) {
  const navigate = useNavigate();
  const currentCategory = activeView.categoryKey;

  const [moduleOrder, setModuleOrder] = useState([]);
  const [lastCategory, setLastCategory] = useState("");

  // Sync state module order when category or URL path shifts
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

    updatedOrder[0] = clickedModuleId;
    updatedOrder[clickedIndex] = currentMainStageId;
    setModuleOrder(updatedOrder);

    const nextView = getWorkerViewForModule(currentCategory, clickedModuleId);
    if (!nextView) return;
    if (onViewSelect) {
      onViewSelect(nextView);
    } else {
      navigate(buildWorkerViewPath(nextView));
    }
  };

  const getModuleData = (moduleId) => {
    const linkedView = getWorkerViewForModule(currentCategory, moduleId);
    return {
      id: moduleId,
      title: linkedView?.label || "Workspace Panel",
      subtitle: linkedView?.subtitle || "",
      previewText: linkedView?.previewText || "",
    };
  };

  // Replaces RenderSlot with the customer-styled card structure
  const RenderSleepingModule = ({ targetModuleId, gridAreaClass }) => {
    if (!targetModuleId) return <div className={`${gridAreaClass} worker-slot-empty`} />;
    const targetModule = getModuleData(targetModuleId);

    return (
      <section 
        className={`${gridAreaClass} worker-sleep-card`}
        onClick={() => handleModuleSwap(targetModule.id)}
      >
        <div className="worker-card-header">
          <span className="worker-card-subtitle">{targetModule.subtitle}</span>
          <h2 className="worker-card-title">{targetModule.title}</h2>
        </div>
        <div className="worker-card-body">
          <div className="worker-preview-pill">
            <strong>{targetModule.previewText}</strong>
          </div>
        </div>
      </section>
    );
  };

  if (moduleOrder.length === 0) return null;

  const mainStageModule = getModuleData(moduleOrder[0]);

  const content = (
    <div className={`worker-dashboard-shell wk-layout-${currentCategory}`}>
      
      {/* WORKSPACE LAYOUT DECK */}
      {currentCategory === "workspace" && (
        <>
          <section className="wk1-area-map fixfast-stage">
            <div className="worker-card-header">
              <span className="worker-card-subtitle">{mainStageModule.subtitle}</span>
              <h2 className="worker-card-title">{mainStageModule.title}</h2>
            </div>
            <div className="worker-card-body">
              <Dash1worker activeModuleId={mainStageModule.id} />
            </div>
          </section>
          
          <RenderSleepingModule targetModuleId={moduleOrder[1]} gridAreaClass="wk1-area-bids" />
          <RenderSleepingModule targetModuleId={moduleOrder[2]} gridAreaClass="wk1-area-details" />
        </>
      )}

      {/* SCHEDULED LAYOUT DECK */}
      {currentCategory === "scheduled" && (
        <>
          <section className="wk2-area-map fixfast-stage">
            <div className="worker-card-header">
              <span className="worker-card-subtitle">{mainStageModule.subtitle}</span>
              <h2 className="worker-card-title">{mainStageModule.title}</h2>
            </div>
            <div className="worker-card-body">
              <Dash2worker activeModuleId={mainStageModule.id} />
            </div>
          </section>

          <RenderSleepingModule targetModuleId={moduleOrder[1]} gridAreaClass="wk2-area-job" />
          <RenderSleepingModule targetModuleId={moduleOrder[2]} gridAreaClass="wk2-area-query" />
          <RenderSleepingModule targetModuleId={moduleOrder[3]} gridAreaClass="wk2-area-calendar" />
        </>
      )}

      {/* ME LAYOUT DECK */}
      {currentCategory === "me" && (
        <>
          <section className="wk3-area-interview fixfast-stage">
            <div className="worker-card-header">
              <span className="worker-card-subtitle">{mainStageModule.subtitle}</span>
              <h2 className="worker-card-title">{mainStageModule.title}</h2>
            </div>
            <div className="worker-card-body">
              <Dash3worker activeModuleId={mainStageModule.id} />
            </div>
          </section>

          <RenderSleepingModule targetModuleId={moduleOrder[1]} gridAreaClass="wk3-area-profile" />
          <RenderSleepingModule targetModuleId={moduleOrder[2]} gridAreaClass="wk3-area-config" />
          <RenderSleepingModule targetModuleId={moduleOrder[3]} gridAreaClass="wk3-area-tags" />
        </>
      )}

      {/* MISC LAYOUT DECK */}
      {currentCategory === "mics" && (
        <section className="wk4-area-empty fixfast-stage">
          <div className="worker-card-header">
            <span className="worker-card-subtitle">{mainStageModule.subtitle}</span>
            <h2 className="worker-card-title">{mainStageModule.title}</h2>
          </div>
          <div className="worker-card-body">
            <Dash4worker />
          </div>
        </section>
      )}

    </div>
  );

  return embedded ? content : <div className="worker-page">{content}</div>;
}