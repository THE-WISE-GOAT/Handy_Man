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
        background: "#f4f7f6",
      }}
    >
      <div style={{ fontFamily: "monospace", color: "#333" }}>
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
    canAccessWorker,
    defaultHomePath,
  } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <FullScreenLoader />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (requiredRole === "worker" && !canAccessWorker) {
    return <Navigate to={defaultHomePath} replace />;
  }

  if (requiredRole && requiredRole !== "worker" && !hasRole(requiredRole)) {
    return <Navigate to={defaultHomePath} replace />;
  }

  return children;
}
