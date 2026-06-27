// Zlices/moreZlice.js

export const createMoreZlice = (set, get) => ({
  // ==========================================
  // 1. BUSINESS CONTENT DATA PLACEHOLDERS
  // ==========================================
  calendarEventsCount: 3,
  profileSecurityStatus: "Profile Security Node Standby",
  archivePipelineStatus: "Archived Deployments Index Stream",
  systemPortalStatus: "System Parameters Modification Portal",

  // ==========================================
  // 2. DYNAMIC LAYOUT POSITIONS (4-Slot Map)
  // ==========================================
  // Default arrangement matching your image exactly
  miscSlots: {
    main: "SystemCalendar",
    sidebar: "AccountProfiles",
    bottomLeft: "HistoricalRecordsLogs",
    bottomRight: "SystemSettings"
  },

  // ==========================================
  // 3. UNIVERSAL SWAPPING ACTION
  // ==========================================
  swapMiscSlots: (clickedSlotName) => set((state) => {
    if (clickedSlotName === "main") return {}; // Already active, ignore

    const outgoingMainModule = state.miscSlots.main;
    const incomingTargetModule = state.miscSlots[clickedSlotName];

    return {
      miscSlots: {
        ...state.miscSlots,
        main: incomingTargetModule,
        [clickedSlotName]: outgoingMainModule
      }
    };
  })
});