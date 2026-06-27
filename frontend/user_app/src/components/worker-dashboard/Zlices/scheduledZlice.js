// Zlices/scheduledZlice.js

export const createScheduledZlice = (set) => ({
  // ==========================================
  // 1. BUSINESS CONTENT DATA PLACEHOLDERS
  // ==========================================
  calendarDescText: "Worker Central Time Allocation Block Calendar.",
  jobsRegistryStatus: "Confirmed Client Operations Counter",
  clientQueryStatus: "Unread Dispatches Pending Response",
  routeMatrixStatus: "Geospatial Routing Parameters Validated",

  // ==========================================
  // 2. DYNAMIC LAYOUT POSITIONS (4-Slot Map)
  // ==========================================
  scheduledSlots: {
    main: "ScheduledCalendar",
    sidebar: "ScheduledJobCard",
    bottomLeft: "ClientQueries",
    bottomRight: "ScheduledMap"
  },

  // ==========================================
  // 3. UNIVERSAL SWAPPING ACTION
  // ==========================================
  swapScheduledSlots: (clickedSlotName) => set((state) => {
    if (clickedSlotName === "main") return {}; // Ignore if already main

    const outgoingMain = state.scheduledSlots.main;
    const incomingTarget = state.scheduledSlots[clickedSlotName];

    return {
      scheduledSlots: {
        ...state.scheduledSlots,
        main: incomingTarget,
        [clickedSlotName]: outgoingMain
      }
    };
  })
});