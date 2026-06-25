import React from "react";
import { useNavigate } from "react-router-dom";
import Dash1board from "./dash1board";
import Dash2board from "./dash2board";
import Dash3board from "./dash3board";
import {
  CUSTOMER_VIEWS,
  buildCustomerViewPath,
  getCustomerViewForModule,
} from "@shared/config/viewRoutes";

import "./customer-dashboard.css";
import "./dash1board.css";
import "./dash2board.css";
import "./dash3board.css";

const CATEGORY_LAYOUTS = {
  bookings: {
    modules: [
      { id: "ai-chat", fallbackTitle: "AI Chat Terminal" },
      { id: "job-description", fallbackTitle: "Job Description Workspace" },
      { id: "my-posts", fallbackTitle: "Your Active Posts" },
    ],
  },
  postings: {
    modules: [
      { id: "biddings", fallbackTitle: "Active Biddings Engine" },
      { id: "map", fallbackTitle: "Geospatial Live Map" },
      { id: "active-post-v2", fallbackTitle: "Active Posts Dashboard" },
      { id: "ratings-review", fallbackTitle: "Ratings & Review Logs" },
    ],
  },
  misc: {
    modules: [
      { id: "calendar", fallbackTitle: "System Calendar" },
      { id: "account", fallbackTitle: "Account Profiles" },
      { id: "history", fallbackTitle: "Historical Records Logs" },
      { id: "settings", fallbackTitle: "System Settings" },
    ],
  },
};

function buildModuleOrder(categoryKey, preferredModuleId = null) {
  const modules = CATEGORY_LAYOUTS[categoryKey]?.modules || [];
  const defaultIds = modules.map((module) => module.id);

  if (!preferredModuleId || !defaultIds.includes(preferredModuleId)) {
    return defaultIds;
  }

  return [
    preferredModuleId,
    ...defaultIds.filter((moduleId) => moduleId !== preferredModuleId),
  ];
}

function getRenderableModules(categoryKey) {
  const modules = CATEGORY_LAYOUTS[categoryKey]?.modules || [];
  return modules.map((module) => {
    const linkedView = getCustomerViewForModule(categoryKey, module.id);
    return {
      ...module,
      title: linkedView?.label || module.fallbackTitle,
      subtitle: linkedView?.subtitle || "Workspace panel",
      previewText: linkedView?.previewText || module.fallbackTitle,
      linkedView,
    };
  });
}

function StageHeader({ view }) {
  return (
    <div className="fixfast-stage__header">
      <span
        style={{
          fontSize: "0.72rem",
          color: "var(--fixfast-muted)",
          fontWeight: 800,
          textTransform: "uppercase",
        }}
      >
        {view.subtitle}
      </span>
      <h1>{view.label}</h1>
    </div>
  );
}

export default function CustomerDashboardView({
  embedded = false,
  activeView = CUSTOMER_VIEWS.ACTIVE_POSTS,
  onViewSelect,
}) {
  const navigate = useNavigate();
  const currentCategory = activeView.categoryKey;
  const moduleOrder = buildModuleOrder(currentCategory, activeView.moduleId);
  const activeModulesList = getRenderableModules(currentCategory);
  const mainStageModule =
    activeModulesList.find((module) => module.id === moduleOrder[0]) ||
    activeModulesList[0];

  const handleModuleSelect = (moduleId) => {
    const nextView = getCustomerViewForModule(currentCategory, moduleId);
    if (!nextView) {
      return;
    }

    if (onViewSelect) {
      onViewSelect(nextView);
      return;
    }

    navigate(buildCustomerViewPath(nextView));
  };

  const RenderSleepingModule = ({ targetModule }) => {
    if (!targetModule) return null;

    return (
      <div
        className="fixfast-sleep-card"
        onClick={() => handleModuleSelect(targetModule.id)}
      >
        <div className="fixfast-sleep-card__topbar">
          <div className="fixfast-sleep-card__traffic">
            <i></i>
            <i></i>
            <i></i>
          </div>
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

  const content = (
    <>
      {currentCategory === "bookings" && (
        <main className="db1-shell">
          <section className="db1-stage-zone fixfast-stage">
            <StageHeader view={activeView} />
            <div style={{ flex: 1, overflowY: "auto" }}>
              <Dash1board activeModuleId={mainStageModule.id} />
            </div>
          </section>
          <section className="db1-sidebar-zone">
            <RenderSleepingModule
              targetModule={activeModulesList.find(
                (module) => module.id === moduleOrder[1],
              )}
            />
          </section>
          <section className="db1-deck-zone">
            {moduleOrder.slice(2).map((moduleId) => (
              <RenderSleepingModule
                key={moduleId}
                targetModule={activeModulesList.find(
                  (module) => module.id === moduleId,
                )}
              />
            ))}
          </section>
        </main>
      )}

      {currentCategory === "postings" && (
        <main className="db2-shell">
          <section className="db2-stage-zone fixfast-stage">
            <StageHeader view={activeView} />
            <div style={{ flex: 1, overflowY: "auto" }}>
              <Dash2board activeModuleId={mainStageModule.id} />
            </div>
          </section>
          <section className="db2-sidebar-zone">
            <RenderSleepingModule
              targetModule={activeModulesList.find(
                (module) => module.id === moduleOrder[1],
              )}
            />
          </section>
          <section className="db2-deck-left-zone">
            <RenderSleepingModule
              targetModule={activeModulesList.find(
                (module) => module.id === moduleOrder[2],
              )}
            />
          </section>
          <section className="db2-deck-right-zone">
            <RenderSleepingModule
              targetModule={activeModulesList.find(
                (module) => module.id === moduleOrder[3],
              )}
            />
          </section>
        </main>
      )}

      {currentCategory === "misc" && (
        <main className="db3-shell">
          <section className="db3-stage-zone fixfast-stage">
            <StageHeader view={activeView} />
            <div style={{ flex: 1, overflowY: "auto" }}>
              <Dash3board activeModuleId={mainStageModule.id} />
            </div>
          </section>
          <section className="db3-account-zone">
            <RenderSleepingModule
              targetModule={activeModulesList.find(
                (module) => module.id === moduleOrder[1],
              )}
            />
          </section>
          <section className="db3-history-zone">
            <RenderSleepingModule
              targetModule={activeModulesList.find(
                (module) => module.id === moduleOrder[2],
              )}
            />
          </section>
          <section className="db3-settings-zone">
            <RenderSleepingModule
              targetModule={activeModulesList.find(
                (module) => module.id === moduleOrder[3],
              )}
            />
          </section>
        </main>
      )}
    </>
  );

  if (embedded) {
    return content;
  }

  return <div className="fixfast-page">{content}</div>;
}
