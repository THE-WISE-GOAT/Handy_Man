import React, { useEffect, useState } from "react";
import { Navigate, useParams } from "react-router-dom";
import { getDefaultWorkerPath, getWorkerViewBySlug } from "@shared/config/viewRoutes";
import { apiClient } from "@shared/api/client";

import Dash1Worker from "../../components/worker-dashboard/dash1worker";
import Dash2Worker from "../../components/worker-dashboard/dash2worker";
import Dash3Worker from "../../components/worker-dashboard/dash3worker";
import Dash4Worker from "../../components/worker-dashboard/dash4worker";

export default function WorkerViewRoute() {
  const { section, viewSlug } = useParams();
  const activeView = getWorkerViewBySlug(viewSlug || "");
  const [isApplicant, setIsApplicant] = useState(true);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    let settled = false;
    const timeout = setTimeout(() => {
      if (active && !settled) {
        setLoading(false);
        setIsApplicant(false);
      }
    }, 15000);
    const checkApplicantStatus = async () => {
      try {
        const data = await apiClient.get("/worker-onboarding/my-status");
        settled = true;
        if (active) {
          const isVerified =
            data.is_complete === true ||
            (typeof data.stage === "string" &&
              data.stage.toLowerCase() === "approved");
          setIsApplicant(!isVerified);
        }
      } catch (error) {
        settled = true;
        if (active) {
          console.error("[WorkerViewRoute] Applicant status check failed:", error);
          // Keep isApplicant = true on error (fail closed)
          setIsApplicant(true);
        }
      } finally {
        settled = true;
        if (active) {
          clearTimeout(timeout);
          setLoading(false);
        }
      }
    };
    checkApplicantStatus();
    return () => { active = false; clearTimeout(timeout); };
  }, []);

  if (loading) {
    return <div className="admin-status">Loading…</div>;
  }

  if (isApplicant && section?.toLowerCase() !== "me") {
    return <Navigate to={`/worker/me/MeInterview`} replace />;
  }

  if (!activeView || activeView.section !== section?.toLowerCase()) {
    return <Navigate to={getDefaultWorkerPath()} replace />;
  }

  switch (section?.toLowerCase()) {
    case "workspace": return <Dash1Worker viewSlug={viewSlug} />;
    case "scheduled": return <Dash2Worker viewSlug={viewSlug} />;
    case "me":        return <Dash3Worker viewSlug={viewSlug} />;
    case "mics":      return <Dash4Worker viewSlug={viewSlug} />;
    default:          return <Dash1Worker viewSlug={viewSlug} />;
  }
}
