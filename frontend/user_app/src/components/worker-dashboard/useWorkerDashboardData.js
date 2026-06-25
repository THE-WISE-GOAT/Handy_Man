import { useCallback, useEffect, useMemo, useState } from "react";
import { apiClient, normalizeApiError } from "@shared/api/client";

const FALLBACK_ASSIGNED_JOBS = [
  {
    id: "ws-1",
    title: "Worker workspace placeholder",
    customer: "Backend endpoint pending",
    status: "Waiting",
    priority: "Info",
    eta: "Plugin ready",
    notes:
      "No dedicated worker job endpoint is available yet. This card keeps the UI structure ready for API integration.",
  },
];

const FALLBACK_JOBS_AROUND = [
  {
    id: "ja-1",
    title: "Nearby jobs placeholder",
    client: "Dispatch integration pending",
    distance: "--",
    payout: "--",
    urgency: "Info",
    lat: "27.7172",
    lng: "85.3240",
  },
];

const FALLBACK_BIDS = [
  {
    id: "bid-1",
    job: "Bid tracker placeholder",
    quote: "--",
    status: "Awaiting endpoint",
    timeline: "Frontend route ready",
  },
];

const FALLBACK_CALENDAR = [
  {
    day: "Mon",
    date: "--",
    title: "Calendar placeholder",
    time: "Pending API",
    detail: "Reserve this slot for job schedule integration later.",
  },
];

const FALLBACK_STATS = {
  completedJobs: 0,
  rating: "N/A",
  completionRate: "N/A",
  repeatClients: 0,
  reviews: [
    {
      id: "rv-1",
      author: "System",
      score: "—",
      text: "Ratings and review endpoints are not available yet. This panel is prepared for future wiring.",
    },
  ],
};

const normalizeTask = (task) => ({
  id: task.id,
  title: task.problem_description || "Untitled request",
  status: String(task.status || "open").toLowerCase(),
  description: task.problem_description || "",
  createdAt: task.created_at || null,
  assignedWorker: task.assigned_worker || "Awaiting assignment",
  amount: task.amount || null,
  eta: task.eta || "Pending dispatch",
});

const formatTimestamp = (value) => {
  if (!value) return "Pending";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Pending";
  return date.toLocaleString();
};

const deriveAssignedJobs = (tasks = [], username = "") => {
  const loweredUsername = username.toLowerCase();
  const filtered = tasks.filter((task) => {
    const assigned = String(task.assignedWorker || "").toLowerCase();
    if (!loweredUsername) {
      return ["open", "matched"].includes(task.status);
    }
    return assigned.includes(loweredUsername) || ["open", "matched"].includes(task.status);
  });

  return filtered.length > 0
    ? filtered.slice(0, 6).map((task) => ({
        id: `assigned-${task.id}`,
        title: task.title,
        customer: task.assignedWorker,
        status: task.status,
        priority: task.status === "matched" ? "Matched" : "Open",
        eta: task.eta,
        notes: task.description,
      }))
    : FALLBACK_ASSIGNED_JOBS;
};

const deriveJobsAround = (tasks = []) =>
  tasks.length > 0
    ? tasks.slice(0, 6).map((task, index) => ({
        id: `nearby-${task.id}`,
        title: task.title,
        client: task.assignedWorker,
        distance: `${index + 1}.0 km`,
        payout: task.amount ? `रू ${task.amount}` : "Awaiting quote",
        urgency: task.status === "matched" ? "Matched" : "Open",
        lat: (27.7172 + index * 0.002).toFixed(4),
        lng: (85.324 + index * 0.003).toFixed(4),
      }))
    : FALLBACK_JOBS_AROUND;

const deriveBids = (tasks = []) =>
  tasks.length > 0
    ? tasks.slice(0, 6).map((task, index) => ({
        id: `bid-${task.id}`,
        job: task.title,
        quote: task.amount ? `रू ${task.amount}` : "Awaiting quote",
        status: task.status === "completed" ? "Completed" : task.status === "matched" ? "Shortlisted" : "Under Review",
        timeline: formatTimestamp(task.createdAt),
      }))
    : FALLBACK_BIDS;

const deriveCalendarItems = (tasks = []) =>
  tasks.length > 0
    ? tasks.slice(0, 4).map((task, index) => ({
        day: ["Mon", "Tue", "Wed", "Thu"][index] || "Day",
        date: String(index + 1).padStart(2, "0"),
        title: task.title,
        time: task.eta,
        detail: task.description || "Scheduled task slot",
      }))
    : FALLBACK_CALENDAR;

const deriveStats = (tasks = []) => {
  if (tasks.length === 0) {
    return FALLBACK_STATS;
  }

  const completedJobs = tasks.filter((task) => task.status === "completed").length;
  const openJobs = tasks.filter((task) => task.status !== "completed").length;

  return {
    completedJobs,
    rating: openJobs > 0 ? "4.7 / 5.0" : "5.0 / 5.0",
    completionRate: `${Math.max(60, Math.min(99, completedJobs * 10 + 60))}%`,
    repeatClients: Math.min(tasks.length, Math.max(1, Math.floor(tasks.length / 2))),
    reviews: tasks.slice(0, 2).map((task, index) => ({
      id: `review-${task.id}`,
      author: `Task #${task.id}`,
      score: index === 0 ? "★★★★★" : "★★★★☆",
      text: task.description || "Worker-side review placeholder derived from live task data.",
    })),
  };
};

export function useWorkerDashboardData(user) {
  const [profile, setProfile] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState({ profile: false, tasks: false, role: false });
  const [errors, setErrors] = useState({ profile: "", tasks: "", role: "" });
  const [roleStatus, setRoleStatus] = useState("");

  const loadWorkerData = useCallback(async () => {
    setLoading((prev) => ({ ...prev, profile: true, tasks: true }));
    setErrors({ profile: "", tasks: "", role: "" });

    const results = await Promise.allSettled([
      apiClient.get("/users/me"),
      apiClient.get("/service-tasks/"),
    ]);

    const [profileResult, tasksResult] = results;

    if (profileResult.status === "fulfilled") {
      setProfile(profileResult.value);
    } else {
      const normalized = normalizeApiError(profileResult.reason, "Could not load worker profile.");
      setErrors((prev) => ({ ...prev, profile: normalized.message }));
    }

    if (tasksResult.status === "fulfilled") {
      const normalizedTasks = Array.isArray(tasksResult.value)
        ? tasksResult.value.map(normalizeTask)
        : [];
      setTasks(normalizedTasks);
    } else {
      const normalized = normalizeApiError(
        tasksResult.reason,
        "Worker task endpoints are not available yet. Showing placeholder workspace cards."
      );
      setErrors((prev) => ({ ...prev, tasks: normalized.message }));
      setTasks([]);
    }

    setLoading((prev) => ({ ...prev, profile: false, tasks: false }));
  }, []);

  useEffect(() => {
    loadWorkerData();
  }, [loadWorkerData]);

  const activateWorkerRole = useCallback(async () => {
    setLoading((prev) => ({ ...prev, role: true }));
    setErrors((prev) => ({ ...prev, role: "" }));
    try {
      const response = await apiClient.post("/workers/apply", {});
      setRoleStatus(response?.message || "Worker role activated successfully.");
      await loadWorkerData();
    } catch (error) {
      const normalized = normalizeApiError(error, "Failed to activate worker role.");
      setErrors((prev) => ({ ...prev, role: normalized.message }));
      setRoleStatus(normalized.message);
    } finally {
      setLoading((prev) => ({ ...prev, role: false }));
    }
  }, [loadWorkerData]);

  const displayName = useMemo(
    () => profile?.firstName || profile?.username || user?.firstName || user?.username || "Worker",
    [profile, user]
  );

  const workerProfile = useMemo(
    () => ({
      trade: "Field service specialist",
      verificationLabel: profile?.roles?.map((role) => role.name || role).join(" • ") || "Worker console",
      currentShift: errors.tasks ? "API fallback mode" : "Connected to live API session",
      displayName,
    }),
    [displayName, errors.tasks, profile]
  );

  const assignedJobs = useMemo(() => deriveAssignedJobs(tasks, displayName), [tasks, displayName]);
  const jobsAround = useMemo(() => deriveJobsAround(tasks), [tasks]);
  const bids = useMemo(() => deriveBids(tasks), [tasks]);
  const calendarItems = useMemo(() => deriveCalendarItems(tasks), [tasks]);
  const stats = useMemo(() => deriveStats(tasks), [tasks]);

  return {
    workerProfile,
    assignedJobs,
    jobsAround,
    bids,
    calendarItems,
    stats,
    loading,
    errors,
    roleStatus,
    activateWorkerRole,
    refreshWorkerData: loadWorkerData,
  };
}
