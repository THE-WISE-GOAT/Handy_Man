// Zlices/moreZlice.js
import { apiClient } from "@shared/api/client";

export const createMoreZlice = (set, get) => ({
  // ==========================================
  // 1. BUSINESS CONTENT DATA PLACEHOLDERS
  // ==========================================
  calendarEventsCount: 3,
  profileSecurityStatus: "Profile Security Node Standby",
  archivePipelineStatus: "Archived Deployments Index Stream",
  systemPortalStatus: "System Parameters Modification Portal",

  assignedJobs: [],
  activeAssignedJob: null,

  // ==========================================
  // 2. DYNAMIC LAYOUT POSITIONS (4-Slot Map)
  // ==========================================
  miscSlots: {
    main: "SystemCalendar",
    sidebar: "AccountProfiles",
    bottomLeft: "HistoricalRecordsLogs",
    bottomRight: "SystemSettings",
  },

  // ==========================================
  // 3. UNIVERSAL SWAPPING ACTION
  // ==========================================
  swapMiscSlots: (clickedSlotName) =>
    set((state) => {
      if (clickedSlotName === "main") return {}; // Already active, ignore

      const outgoingMainModule = state.miscSlots.main;
      const incomingTargetModule = state.miscSlots[clickedSlotName];

      return {
        miscSlots: {
          ...state.miscSlots,
          main: incomingTargetModule,
          [clickedSlotName]: outgoingMainModule,
        },
      };
    }),

  setMiscSlots: (slots) => set({ miscSlots: slots }),

  setActiveAssignedJob: (job) => set({ activeAssignedJob: job }),

  fetchAssignedJobs: async () => {
    try {
      const data = await apiClient.get("/jobs/status/assigned");
      if (data.status === "success") {
        const jobs = data.tasks || [];
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
