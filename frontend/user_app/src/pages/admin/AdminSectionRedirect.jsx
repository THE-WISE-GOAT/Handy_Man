import React from "react";
import { Navigate, useParams } from "react-router-dom";
import { getDefaultAdminPath } from "@shared/config/viewRoutes";

export default function AdminSectionRedirect() {
  const { section } = useParams();
  return <Navigate to={getDefaultAdminPath(section)} replace />;
}
