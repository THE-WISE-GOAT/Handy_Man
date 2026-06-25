import React from "react";

export default function Dash1board({ activeModuleId }) {
  return (
    <>
      {activeModuleId === "ai-chat" && (
        <div>
          <p>AI Chat Terminal Primary Application Workflow Dashboard View.</p>
        </div>
      )}
      {activeModuleId === "job-description" && (
        <div>
          <p>Job Description Workspace Primary Editor Terminal Node.</p>
        </div>
      )}
      {activeModuleId === "my-posts" && (
        <div>
          <p>Your Active Posts Network Node Deployment Visualizer Monitor.</p>
        </div>
      )}
    </>
  );
}