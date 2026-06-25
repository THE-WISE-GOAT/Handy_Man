import React from "react";
import { Navigate, useParams } from "react-router-dom";
import { getDefaultCustomerPath } from "@shared/config/viewRoutes";

export default function CustomerSectionRedirect() {
  const { section } = useParams();
  return <Navigate to={getDefaultCustomerPath(section)} replace />;
}
