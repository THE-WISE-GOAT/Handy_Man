import React from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@shared/context/AuthContext";
import {
  FixFastNavbar,
  FixFastProfile,
} from "@shared/components/dashboard-stage/DashboardStage";
import {
  CUSTOMER_NAV_ITEMS,
  WORKER_NAV_ITEMS,
  getDefaultCustomerPath,
  getDefaultWorkerPath,
} from "@shared/config/viewRoutes";
import "./app-layout.css";

export default function AppLayout({ role = "customer" }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout, canAccessWorker } = useAuth();

  const navItems = role === "worker" ? WORKER_NAV_ITEMS : CUSTOMER_NAV_ITEMS;
  const activePanel =
    navItems.find((item) =>
      location.pathname.startsWith(item.matchPrefix || item.path),
    )?.id || navItems[0]?.id;

  const profileActions = [
    ...(role === "customer" && canAccessWorker
      ? [
          {
            label: "Switch to worker",
            onClick: () => navigate(getDefaultWorkerPath()),
          },
        ]
      : []),
    ...(role === "worker"
      ? [
          {
            label: "Switch to customer",
            onClick: () => navigate(getDefaultCustomerPath("bookings")),
          },
        ]
      : []),
    {
      label: "Log out",
      onClick: async () => {
        await logout();
        navigate("/login", { replace: true });
      },
    },
  ];

  return (
    <div className="fixfast-page">
      <FixFastNavbar
        brandTitle="Handy Man"
        brandEyebrow={
          role === "worker"
            ? "Unified Worker Workspace"
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
              (role === "worker" ? "Worker" : "Customer")
            }
            sublabel={
              user?.email ||
              (role === "worker" ? "Worker session" : "Customer session")
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