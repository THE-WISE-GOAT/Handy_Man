import React from "react";

export default function Dash1worker({ activeModuleId }) {
  return (
    <div className="dash1-worker-root">
      {activeModuleId === "wk-map" && (
        <div className="wk-module-frame wk-map-canvas">
          <div className="mock-gps-feed">
            <span className="ping-beacon"></span>
            <p>REALTIME DISPATCH TRACKING MATRIX ACTIVE</p>
          </div>
        </div>
      )}
      {activeModuleId === "wk-bids" && (
        <div className="wk-module-frame wk-bids-log">
          <p>Bidding Engagements and Negotiation Pipeline Engine.</p>
        </div>
      )}
      {activeModuleId === "wk-details" && (
        <div className="wk-module-frame wk-details-inspector">
          <p>Task Specifications and Requirements Inspector.</p>
        </div>
      )}
    </div>
  );
}