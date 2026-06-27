import React from "react";
import { Navigate, useParams } from "react-router-dom";
import { getDefaultWorkerPath, getWorkerViewBySlug } from "@shared/config/viewRoutes";

// Direct component layout imports
import Dash1Worker from "../../components/worker-dashboard/dash1worker";
import Dash2Worker from "../../components/worker-dashboard/dash2worker";
import Dash3Worker from "../../components/worker-dashboard/dash3worker";
import Dash4Worker from "../../components/worker-dashboard/dash4worker";

export default function WorkerViewRoute() {
  const { section, viewSlug } = useParams();
  const activeView = getWorkerViewBySlug(viewSlug || "");

  // Validate that the view exists and matches the current path category section
  if (!activeView || activeView.section !== section?.toLowerCase()) {
    return <Navigate to={getDefaultWorkerPath()} replace />;
  }

  // Render the appropriate layout panel canvas directly by section string
  switch (section?.toLowerCase()) {
    case "workspace": return <Dash1Worker />;
    case "scheduled": return <Dash2Worker />;
    case "me":        return <Dash3Worker />;
    case "mics":      return <Dash4Worker />;
    default:          return <Dash1Worker />;
  }
}