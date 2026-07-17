import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@shared/context/AuthContext";

function FullScreenLoader() {
  return (
    <div
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        background: "#0D0D0D",
      }}
    >
      <div style={{ fontFamily: "monospace", color: "#F5F5F7" }}>
        Checking session...
      </div>
    </div>
  );
}

export default function ProtectedRoute({ children, requiredRole = null }) {
  const {
    isAuthenticated,
    isLoading,
    hasRole,
    defaultHomePath,
  } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <FullScreenLoader />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (requiredRole && !hasRole(requiredRole)) {
    return <Navigate to={defaultHomePath} replace />;
  }

  return children;
}
