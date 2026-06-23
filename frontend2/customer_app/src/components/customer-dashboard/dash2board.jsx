import React from "react";

export default function Dash2board({ activeModuleId }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      {activeModuleId === "biddings" && (
        <div>
          <p>Active incoming competitive service offers and rate valuation streams.</p>
        </div>
      )}
      {activeModuleId === "map" && (
        <div>
          <p>Live map layout tracking active field technician routing and dispatch updates.</p>
        </div>
      )}
      {activeModuleId === "ratings-review" && (
        <div>
          <p>Historical customer satisfaction indices, verification loops, and ratings logs.</p>
        </div>
      )}
      {activeModuleId === "active-post-v2" && (
        <div>
          <p>Extended logging metrics tracking jobs currently deployed out to network nodes.</p>
        </div>
      )}
    </div>
  );
}