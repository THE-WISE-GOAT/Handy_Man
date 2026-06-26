import React from "react";

export default function Dash2worker({ activeModuleId }) {
  return (
    <div className="dash2-worker-root">
      {activeModuleId === "wk-map-sched" && (
        <div className="wk-module-frame wk-sched-map">
          <p>Committed Engagements Mapping Coordinates Matrix.</p>
        </div>
      )}
      {activeModuleId === "wk-sched-job" && (
        <div className="wk-module-frame wk-sched-registry">
          <p>Scheduled Maintenance Operations Registry Card.</p>
        </div>
      )}
      {activeModuleId === "wk-queries" && (
        <div className="wk-module-frame wk-chat-terminal">
          <p>Direct Client Query Dialog Stream Terminal.</p>
        </div>
      )}
      {activeModuleId === "wk-calendar" && (
        <div className="wk-module-frame wk-calendar-grid">
          <p>Worker Central Time Allocation Block Calendar.</p>
        </div>
      )}
    </div>
  );
}