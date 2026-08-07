// Zlices/scheduledZlice.js
import { apiClient } from "@shared/api/client";

export const createScheduledZlice = (set, get) => ({
  // ==========================================
  // 1. BUSINESS CONTENT DATA PLACEHOLDERS
  // ==========================================
  calendarDescText: "Worker Central Time Allocation Block Calendar.",
  jobsRegistryStatus: "Confirmed Client Operations Counter",
  clientQueryStatus: "Unread Dispatches Pending Response",
  routeMatrixStatus: "Geospatial Routing Parameters Validated",

  assignedJobs: [],
  activeAssignedJob: null,

  // ==========================================
  // 2. DYNAMIC LAYOUT POSITIONS (4-Slot Map)
  // ==========================================
  scheduledSlots: {
    main: "ScheduledCalendar",
    sidebar: "ScheduledJobCard",
    bottomLeft: "ClientQueries",
    bottomRight: "ScheduledMap",
  },

  // ==========================================
  // 3. UNIVERSAL SWAPPING ACTION
  // ==========================================
  swapScheduledSlots: (clickedSlotName) =>
    set((state) => {
      if (clickedSlotName === "main") return {}; // Ignore if already main

      const outgoingMain = state.scheduledSlots.main;
      const incomingTarget = state.scheduledSlots[clickedSlotName];

      return {
        scheduledSlots: {
          ...state.scheduledSlots,
          main: incomingTarget,
          [clickedSlotName]: outgoingMain,
        },
      };
    }),

  setScheduledSlots: (slots) => set({ scheduledSlots: slots }),

  setActiveAssignedJob: (job) => set({ activeAssignedJob: job }),

  fetchAssignedJobs: async () => {
    try {
      const data = await apiClient.get("/jobs/assigned");
      if (data.status === "success") {
        const jobs = data.jobs || [];
        set({ assignedJobs: jobs });
        if (jobs.length > 0 && !get().activeAssignedJob) {
          set({ activeAssignedJob: jobs[0] });
        }
      }
    } catch (error) {
      console.error("❌ Failed to fetch assigned jobs:", error);
    }
  },
});
