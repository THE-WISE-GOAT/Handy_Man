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
          background: "#f4f7f6",
        }}
      >
        <div style={{ fontFamily: "monospace", color: "#333" }}>
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
