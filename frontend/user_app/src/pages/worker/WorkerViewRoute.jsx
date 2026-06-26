import React from "react";
import { Navigate, useNavigate, useParams } from "react-router-dom";
import WorkerDashboardView from "../../components/worker-dashboard/WorkerDashboardView";
import {
  buildWorkerViewPath,
  getDefaultWorkerPath,
  getWorkerViewBySlug,
} from "@shared/config/viewRoutes";

export default function WorkerViewRoute() {
  const navigate = useNavigate();
  const { section, viewSlug } = useParams();
  const activeView = getWorkerViewBySlug(viewSlug || "");

  // FIX: Validate against the actual dynamic section name from viewRoutes.js
  if (!activeView || activeView.section !== section?.toLowerCase()) {
    return <Navigate to={getDefaultWorkerPath()} replace />;
  }

  return (
    <WorkerDashboardView
      embedded
      activeView={activeView}
      onViewSelect={(nextView) => navigate(buildWorkerViewPath(nextView))}
    />
  );
}