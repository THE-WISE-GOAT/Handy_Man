import React from "react";
import { Navigate } from "react-router-dom";
import { getDefaultWorkerPath } from "@shared/config/viewRoutes";

export default function WorkerSectionRedirect() {
  return <Navigate to={getDefaultWorkerPath()} replace />;
}
