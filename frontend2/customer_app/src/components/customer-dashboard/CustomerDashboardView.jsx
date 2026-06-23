import React, { useState } from "react";
import { useAuth } from "@shared/context/AuthContext";
import { FixFastNavbar, FixFastProfile } from "@shared/components/dashboard-stage/DashboardStage";
import Dash1board from "./dash1board"; 
import Dash2board from "./dash2board"; 
import Dash3board from "./dash3board"; // Imported the new dashboard layer

import "./customer-dashboard.css"; 
import "./dash1board.css";         
import "./dash2board.css";         
import "./dash3board.css"; // Applied dimensional layout sheet

const DASHBOARD_CONFIG = {
  bookings: {
    label: "Bookings",
    modules: [
      { id: "ai-chat", title: "AI Chat Terminal", subtitle: "Interactive dispatch manager", previewText: "Live Dispatch — Active Session" },
      { id: "job-description", title: "Job Description Workspace", subtitle: "Review and refine auto-generated details", previewText: "Description Live Glance — Draft Mode" },
      { id: "my-posts", title: "Your Active Posts", subtitle: "Overview of tasks deployed to network", previewText: "Active Posts — 0 live requests trackable" },
    ],
  },
  postings: {
    label: "Postings",
    modules: [
      { id: "biddings", title: "Active Biddings Engine", subtitle: "COMPETITIVE MARKETPLACE METRICS", previewText: "Bids Portal — Active incoming traffic" },
      { id: "map", title: "Geospatial Live Map", subtitle: "REALTIME FIELD LOCATION MATRIX", previewText: "GPS Coordinates — Tracking Active Feed" },
      { id: "active-post-v2", title: "Active Posts Dashboard", subtitle: "DEPLOYED TASKS RADAR", previewText: "Post Network Pipeline Monitor Active" },
      { id: "ratings-review", title: "Ratings & Review Logs", subtitle: "REPUTATION QUALITY VERIFICATION", previewText: "Verified Feedback — 5.0 Star Average" },
    ],
  },
  misc: {
    label: "Misc",
    modules: [
      { id: "calendar", title: "System Calendar", subtitle: "SCHEDULE PLATFORM PLANNERS", previewText: "Calendar Feeds — Fully Synced Status" },
      { id: "account", title: "Account Profiles", subtitle: "USER REGISTRATION SYSTEM UTILS", previewText: "Profile Security Node Standby" },
      { id: "history", title: "Historical Records Logs", subtitle: "COMPLETED ENGINE TRANSCRIPTS", previewText: "Archived Deployments Index Stream" },
      { id: "settings", title: "System Settings", subtitle: "CONFIGURATIONS CORE ADJUSTMENTS", previewText: "System Parameters Modification Portal" },
    ],
  },
};

export default function CustomerDashboardView({ onNavigate }) {
  const { user, logout } = useAuth();
  const [currentCategory, setCurrentCategory] = useState("bookings");
  const [moduleOrder, setModuleOrder] = useState(["ai-chat", "job-description", "my-posts"]);

  const handleCategoryChange = (categoryKey) => {
    setCurrentCategory(categoryKey);
    const newModuleIds = DASHBOARD_CONFIG[categoryKey].modules.map(m => m.id);
    setModuleOrder(newModuleIds);
  };

  const handleModuleSwap = (clickedModuleId) => {
    const clickedIndex = moduleOrder.indexOf(clickedModuleId);
    if (clickedIndex === -1) return;

    const updatedOrder = [...moduleOrder];
    const currentMainStageId = updatedOrder[0];

    updatedOrder[0] = clickedModuleId;
    updatedOrder[clickedIndex] = currentMainStageId;

    setModuleOrder(updatedOrder);
  };

  const activeModulesList = DASHBOARD_CONFIG[currentCategory].modules;
  const mainStageModule = activeModulesList.find(m => m.id === moduleOrder[0]) || activeModulesList[0];

  const headerNavItems = Object.keys(DASHBOARD_CONFIG).map((key) => ({
    id: key,
    label: DASHBOARD_CONFIG[key].label,
  }));

  const RenderSleepingModule = ({ targetModule }) => {
    if (!targetModule) return null;
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

  return (
    <div className="fixfast-page">
      <FixFastNavbar
        navItems={headerNavItems}
        activePanel={currentCategory}
        onSelectPanel={handleCategoryChange}
        profileSlot={
          <FixFastProfile
            label={user?.firstName || user?.username || "Customer"}
            sublabel={user?.email || "Signed-in user"}
            actions={[{ label: "Log out", onClick: async () => { await logout(); onNavigate?.("login"); } }]}
          />
        }
      />

      {/* RENDER SYSTEM CATEGORY DECK SWITCHES */}
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
            <RenderSleepingModule targetModule={activeModulesList.find(m => m.id === moduleOrder[1])} />
          </section>
          <section className="db1-deck-zone">
            {moduleOrder.slice(2).map((modId) => (
              <RenderSleepingModule key={modId} targetModule={activeModulesList.find(m => m.id === modId)} />
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
            <RenderSleepingModule targetModule={activeModulesList.find(m => m.id === moduleOrder[1])} />
          </section>
          <section className="db2-deck-left-zone">
            <RenderSleepingModule targetModule={activeModulesList.find(m => m.id === moduleOrder[2])} />
          </section>
          <section className="db2-deck-right-zone">
            <RenderSleepingModule targetModule={activeModulesList.find(m => m.id === moduleOrder[3])} />
          </section>
        </main>
      )}

      {currentCategory === "misc" && (
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
            <RenderSleepingModule targetModule={activeModulesList.find(m => m.id === moduleOrder[1])} />
          </section>
          <section className="db3-history-zone">
            <RenderSleepingModule targetModule={activeModulesList.find(m => m.id === moduleOrder[2])} />
          </section>
          <section className="db3-settings-zone">
            <RenderSleepingModule targetModule={activeModulesList.find(m => m.id === moduleOrder[3])} />
          </section>
        </main>
      )}
    </div>
  );
}