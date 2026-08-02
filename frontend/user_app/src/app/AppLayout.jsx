import React, { useEffect, useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@shared/context/AuthContext";
import { apiClient, normalizeApiError } from "@shared/api/client";
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
import { useTheme } from "../hooks/useTheme";
import "./app-layout.css";

export default function AppLayout({ role = "customer" }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout, canAccessWorker, canAccessAdmin, refreshUser } = useAuth();
  const { theme, toggleTheme } = useTheme();

  const [isWorkerApplicant, setIsWorkerApplicant] = useState(false);
  const [checkingApplicant, setCheckingApplicant] = useState(false);
  const [joinError, setJoinError] = useState("");
  const [isJoining, setIsJoining] = useState(false);

  useEffect(() => {
    if (role !== "worker") {
      setIsWorkerApplicant(false);
      return;
    }
    let active = true;

    let storedToken;
    try {
      storedToken = localStorage.getItem("handy_man_access_token");
    } catch {
      storedToken = null;
    }
    if (!storedToken) {
      setIsWorkerApplicant(false);
      setCheckingApplicant(false);
      return;
    }

    setCheckingApplicant(true);
    // Default to restricted (applicant mode) until the backend confirms otherwise.
    // This is a fail-closed approach: if the endpoint is missing or errors,
    // the worker stays in restricted mode rather than gaining full access.
    setIsWorkerApplicant(true);

    let settled = false;
    const timeout = setTimeout(() => {
      if (active && !settled) {
        setCheckingApplicant(false);
        setIsWorkerApplicant(false);
      }
    }, 15000);

    apiClient
      .get("/worker-onboarding/my-status")
      .then((data) => {
        settled = true;
        if (active) {
          const isVerified =
            data.is_complete === true ||
            typeof data.stage === "string" && data.stage.toLowerCase() === "approved";
          setIsWorkerApplicant(!isVerified);
        }
      })
      .catch((error) => {
        settled = true;
        if (active) {
          console.error("[AppLayout] Applicant status check failed:", error);
          if (error.status === 404) {
            setJoinError(
              "Worker onboarding backend is not available. Please restart the backend server."
            );
          }
          // Keep isWorkerApplicant = true on error (fail closed)
        }
      })
      .finally(() => {
        settled = true;
        if (active) {
          clearTimeout(timeout);
          setCheckingApplicant(false);
        }
      });
    return () => { active = false; clearTimeout(timeout); };
  }, []);

  const filteredWorkerNavItems = isWorkerApplicant
    ? WORKER_NAV_ITEMS.filter((item) => item.id === "me" || item.id === "Me")
    : WORKER_NAV_ITEMS;

  const navItems =
    role === "worker"
      ? filteredWorkerNavItems
      : role === "admin"
        ? ADMIN_NAV_ITEMS
        : CUSTOMER_NAV_ITEMS;

  const activePanel =
    navItems.find((item) =>
      location.pathname.startsWith(item.matchPrefix || item.path),
    )?.id || navItems[0]?.id;

  const handleJoinWorker = async () => {
    console.log("[Join as Worker] button clicked");
    setIsJoining(true);
    setJoinError("");
    try {
      console.log("[Join as Worker] calling /worker-onboarding/initialize");
      await apiClient.post("/worker-onboarding/initialize");
      console.log("[Join as Worker] initialize succeeded");
      await refreshUser();
      console.log("[Join as Worker] refreshUser succeeded, navigating to worker dashboard");
      navigate(getDefaultWorkerPath());
    } catch (error) {
      console.log("[Join as Worker] primary endpoint failed:", error);
      const normalized = normalizeApiError(error, "Failed to join as worker.");
      setJoinError(normalized.message);
      alert(
        "Failed to join as worker.\n\n" +
        "Error: " + normalized.message + "\n\n" +
        "Please ensure the backend is running and restarted after the latest code changes."
      );
    } finally {
      setIsJoining(false);
    }
  };

  const profileActions = [];

  if (canAccessAdmin) {
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
    label: theme === "dark" ? "☀️ Light Mode" : "🌙 Dark Mode",
    onClick: toggleTheme,
  });

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
        brandTitle="Kamigo"
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
        {joinError && (
          <div style={{
            position: "fixed", top: "1rem", right: "1rem", zIndex: 99999,
            background: "var(--k-alert-wash)", border: "1px solid rgba(229, 72, 77, 0.45)", borderRadius: "8px",
            padding: "0.8rem 1rem", maxWidth: "400px", font: "inherit", fontSize: "0.85rem", color: "var(--k-alert-ink)"
          }}>
            <strong>Error:</strong> {joinError}
            <button
              type="button"
              onClick={() => setJoinError("")}
              style={{ marginLeft: "0.8rem", border: "none", background: "transparent", cursor: "pointer", fontWeight: 700, color: "var(--k-alert-ink)" }}
            >
              ✕
            </button>
          </div>
        )}
        {checkingApplicant && role === "worker" ? (
          <p className="admin-status">Loading workspace…</p>
        ) : (
          <Outlet />
        )}
      </main>
    </div>
  );
}
