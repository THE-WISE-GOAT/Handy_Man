import React from "react";

export default function Dash3board({ activeModuleId }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      {activeModuleId === "calendar" && (
        <div>
          <p>Calendar Workspace Terminal Primary Schedule Router.</p>
        </div>
      )}
      {activeModuleId === "history" && (
        <div>
          <p>Historical Log Ledger Activity Monitor Node.</p>
        </div>
      )}
      {activeModuleId === "account" && (
        <div>
          <p>Account Authentication Profiles Infrastructure Panel.</p>
        </div>
      )}
      {activeModuleId === "settings" && (
        <div>
          <p>System Configuration Environment Adjustments Core.</p>
        </div>
      )}
    </div>
  );
}