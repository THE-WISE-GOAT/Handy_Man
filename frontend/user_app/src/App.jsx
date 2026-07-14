import React from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import HomePage from "@shared/components/HomePage";
import LoginPage from "@shared/components/LoginPage";
import ProtectedRoute from "@shared/routes/ProtectedRoute";
import AnonymousRoute from "@shared/routes/AnonymousRoute";
import AppLayout from "./app/AppLayout";
import CustomerSectionRedirect from "./pages/customer/CustomerSectionRedirect";
import CustomerViewRoute from "./pages/customer/CustomerViewRoute";
import WorkerSectionRedirect from "./pages/worker/WorkerSectionRedirect";
import WorkerViewRoute from "./pages/worker/WorkerViewRoute";
import AdminSectionRedirect from "./pages/admin/AdminSectionRedirect";
import AdminViewRoute from "./pages/admin/AdminViewRoute";
import {
  getDefaultCustomerPath,
  getDefaultWorkerPath,
  getDefaultAdminPath,
} from "@shared/config/viewRoutes";

export default function App() {
  const navigate = useNavigate();

  const goTo = (target, options = {}) => {
    const routes = {
      login: "/login",
      signup: "/signup",
      customer_dashboard: getDefaultCustomerPath("dashboard"),
      worker_dashboard: getDefaultWorkerPath(),
      admin_dashboard: getDefaultAdminPath(),
      home: "/",
    };

    navigate(routes[target] || "/", { replace: Boolean(options.replace) });
  };

  return (
    <div className="ind-app-shell">
      <Routes>
        <Route
          path="/"
          element={
            <AnonymousRoute>
              <HomePage onNavigate={goTo} />
            </AnonymousRoute>
          }
        />

        <Route
          path="/login"
          element={
            <AnonymousRoute>
              <LoginPage initialMode="login" onNavigate={goTo} />
            </AnonymousRoute>
          }
        />

        <Route
          path="/signup"
          element={
            <AnonymousRoute>
              <LoginPage initialMode="signup" onNavigate={goTo} />
            </AnonymousRoute>
          }
        />

        <Route
          path="/customer"
          element={
            <ProtectedRoute>
              <AppLayout role="customer" />
            </ProtectedRoute>
          }
        >
          <Route
            index
            element={
              <Navigate to={getDefaultCustomerPath("dashboard")} replace />
            }
          />
          <Route path=":section" element={<CustomerSectionRedirect />} />
          <Route path=":section/:viewSlug" element={<CustomerViewRoute />} />
        </Route>

        <Route
          path="/worker"
          element={
            <ProtectedRoute requiredRole="worker">
              <AppLayout role="worker" />
            </ProtectedRoute>
          }
        >
          <Route
            index
            element={<Navigate to={getDefaultWorkerPath()} replace />}
          />
          <Route path=":section" element={<WorkerSectionRedirect />} />
          <Route path=":section/:viewSlug" element={<WorkerViewRoute />} />
        </Route>

        <Route
          path="/admin"
          element={
            <ProtectedRoute requiredRole="admin">
              <AppLayout role="admin" />
            </ProtectedRoute>
          }
        >
          <Route
            index
            element={<Navigate to={getDefaultAdminPath()} replace />}
          />
          <Route path=":section" element={<AdminSectionRedirect />} />
          <Route path=":section/:viewSlug" element={<AdminViewRoute />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}
