import React from "react";
import { Navigate, useParams } from "react-router-dom";
import {
  getDefaultAdminPath,
  getAdminViewBySlug,
} from "@shared/config/viewRoutes";

// Direct component layout imports
import AdminUsersBoard from "../../components/admin-dashboard/AdminUsersBoard";
import AdminJobsBoard from "../../components/admin-dashboard/AdminJobsBoard";
import AdminApplicationsBoard from "../../components/admin-dashboard/AdminApplicationsBoard";

export default function AdminViewRoute() {
  const { section, viewSlug } = useParams();
  const activeView = getAdminViewBySlug(viewSlug || "");

  if (!activeView || activeView.section !== section?.toLowerCase()) {
    return <Navigate to={getDefaultAdminPath()} replace />;
  }

  switch (section?.toLowerCase()) {
    case "users":
      return <AdminUsersBoard viewSlug={viewSlug} />;
    case "jobs":
      return <AdminJobsBoard viewSlug={viewSlug} />;
    case "applications":
      return <AdminApplicationsBoard viewSlug={viewSlug} />;
    default:
      return <AdminUsersBoard viewSlug={viewSlug} />;
  }
}
