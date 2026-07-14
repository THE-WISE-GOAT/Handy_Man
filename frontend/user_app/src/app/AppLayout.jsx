import React from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@shared/context/AuthContext";
import { apiClient } from "@shared/api/client";
import {
  FixFastNavbar,
  FixFastProfile,
} from "@shared/components/dashboard-stage/DashboardStage";
import {
  CUSTOMER_NAV_ITEMS,
  WORKER_NAV_ITEMS,
  ADMIN_NAV_ITEMS,
  getDefaultCustomerPath,
  getDefaultWorkerPath,
  getDefaultAdminPath,
} from "@shared/config/viewRoutes";
import "./app-layout.css";

export default function AppLayout({ role = "customer" }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout, canAccessWorker, canAccessAdmin, refreshUser } = useAuth();

  const navItems =
    role === "worker"
      ? WORKER_NAV_ITEMS
      : role === "admin"
        ? ADMIN_NAV_ITEMS
        : CUSTOMER_NAV_ITEMS;
  const activePanel =
    navItems.find((item) =>
      location.pathname.startsWith(item.matchPrefix || item.path),
    )?.id || navItems[0]?.id;

  const handleJoinWorker = async () => {
    try {
      await apiClient.post("/users/become-worker");
      await refreshUser();
      navigate(getDefaultWorkerPath());
    } catch (error) {
      console.error("Failed to join as worker:", error);
    }
  };

  const profileActions = [];

  if (canAccessAdmin) {
    // Admin users can reach every workspace — show the relevant switches per view.
    if (role === "admin") {
      profileActions.push(
        {
          label: "Switch to Customer Dashboard",
          onClick: () => navigate(getDefaultCustomerPath("bookings")),
        },
        {
          label: "Switch to Worker Dashboard",
          onClick: () => navigate(getDefaultWorkerPath()),
        },
      );
    } else if (role === "customer") {
      profileActions.push(
        {
          label: "Switch to Worker Dashboard",
          onClick: () => navigate(getDefaultWorkerPath()),
        },
        {
          label: "Switch to Admin Dashboard",
          onClick: () => navigate(getDefaultAdminPath()),
        },
      );
    } else if (role === "worker") {
      profileActions.push(
        {
          label: "Switch to Customer Dashboard",
          onClick: () => navigate(getDefaultCustomerPath("bookings")),
        },
        {
          label: "Switch to Admin Dashboard",
          onClick: () => navigate(getDefaultAdminPath()),
        },
      );
    }
  } else {
    // Non-admin users keep the original customer/worker switching behavior.
    if (role === "customer" && !canAccessWorker) {
      profileActions.push({
        label: "Join us as Worker",
        onClick: handleJoinWorker,
      });
    }
    if (role === "customer" && canAccessWorker) {
      profileActions.push({
        label: "Switch to Worker Dashboard",
        onClick: () => navigate(getDefaultWorkerPath()),
      });
    }
    if (role === "worker") {
      profileActions.push({
        label: "Switch to customer",
        onClick: () => navigate(getDefaultCustomerPath("bookings")),
      });
    }
  }

  profileActions.push({
    label: "Log out",
    onClick: async () => {
      await logout();
      navigate("/login", { replace: true });
    },
  });

  return (
    <div className="fixfast-page">
      <FixFastNavbar
        brandTitle="Handy Man"
        brandEyebrow={
          role === "worker"
            ? "Unified Worker Workspace"
            : role === "admin"
              ? "Unified Admin Workspace"
              : "Unified Customer Workspace"
        }
        navItems={navItems}
        activePanel={activePanel}
        onSelectPanel={(itemId) => {
          const nextItem = navItems.find((item) => item.id === itemId);
          if (nextItem) {
            navigate(nextItem.path);
          }
        }}
        profileSlot={
          <FixFastProfile
            label={
              user?.firstName ||
              user?.username ||
              (role === "worker"
                ? "Worker"
                : role === "admin"
                  ? "Admin"
                  : "Customer")
            }
            sublabel={
              user?.email ||
              (role === "worker"
                ? "Worker session"
                : role === "admin"
                  ? "Admin session"
                  : "Customer session")
            }
            actions={profileActions}
          />
        }
      />

      <main className="fixfast-shell app-layout-shell">
        <Outlet />
      </main>
    </div>
  );
}