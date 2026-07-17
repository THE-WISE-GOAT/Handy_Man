import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "@shared/context/AuthContext";

export default function AnonymousRoute({ children }) {
  const { isAuthenticated, isLoading, defaultHomePath } = useAuth();

  if (isLoading) {
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

  if (isAuthenticated) {
    return <Navigate to={defaultHomePath} replace />;
  }

  return children;
}
