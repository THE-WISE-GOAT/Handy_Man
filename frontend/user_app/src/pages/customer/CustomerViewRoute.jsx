import React from "react";
import { Navigate, useNavigate, useParams } from "react-router-dom";
import CustomerDashboardView from "../../components/customer-dashboard/CustomerDashboardView";
import {
  buildCustomerViewPath,
  getCustomerViewBySlug,
  isCustomerViewInSection,
  getDefaultCustomerPath,
} from "@shared/config/viewRoutes";

export default function CustomerViewRoute() {
  const navigate = useNavigate();
  const { section, viewSlug } = useParams();
  const activeView = getCustomerViewBySlug(viewSlug || "");

  if (!activeView || !isCustomerViewInSection(activeView, section)) {
    return <Navigate to={getDefaultCustomerPath(section)} replace />;
  }

  return (
    <CustomerDashboardView
      embedded
      activeView={activeView}
      onViewSelect={(nextView) => navigate(buildCustomerViewPath(nextView))}
    />
  );
}
