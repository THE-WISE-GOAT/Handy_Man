import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "@shared/context/AuthContext";

export default function AnonymousRoute({ children }) {
  const { isAuthenticated, isLoading, defaultHomePath } = useAuth();

  if (isLoading) {
    return (
      <div
        className="auth-loader"
        style={{
          minHeight: "100vh",
          display: "grid",
          placeItems: "center",
        }}
      >
        <div style={{ fontFamily: "monospace", color: "var(--text-primary)" }}>
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
