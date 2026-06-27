import React from "react";
import { Navigate, useParams } from "react-router-dom";
import { getCustomerViewBySlug, isCustomerViewInSection, getDefaultCustomerPath } from "@shared/config/viewRoutes";

// Direct component layout imports
import Dash1Board from "../../components/customer-dashboard/dash1board";
import Dash2Board from "../../components/customer-dashboard/dash2board";
import Dash3Board from "../../components/customer-dashboard/dash3board";

export default function CustomerViewRoute() {
  const { section, viewSlug } = useParams();
  const activeView = getCustomerViewBySlug(viewSlug || "");

  if (!activeView || !isCustomerViewInSection(activeView, section)) {
    return <Navigate to={getDefaultCustomerPath(section)} replace />;
  }

  // Render the appropriate layout panel canvas directly by section string
  switch (section?.toLowerCase()) {
    case "bookings": return <Dash1Board />;
    case "postings": return <Dash2Board />;
    case "more":     return <Dash3Board />;
    default:         return <Dash1Board />;
  }
}