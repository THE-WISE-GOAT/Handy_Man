// Zlices/workspaceZlice.js

export const createWorkspaceZlice = (set) => ({
  // ==========================================
  // 1. BUSINESS CONTENT DATA PLACEHOLDERS
  // ==========================================
  mapStatus: "REALTIME DISPATCH TRACKING MATRIX ACTIVE",
  bidsPipelineText: "Live Quote Pipeline Tracking",
  jobSpecsText: "Scope and Requirements Pipeline Overview",

  // ==========================================
  // 2. DYNAMIC LAYOUT POSITIONS (3-Slot Map)
  // ==========================================
  workspaceSlots: {
    main: "WorkspaceMap",
    sidebar: "WorkspaceBids",
    bottom: "WorkspaceJobDetails"
  },

  // ==========================================
  // 3. UNIVERSAL SWAPPING ACTION
  // ==========================================
  swapWorkspaceSlots: (clickedSlotName) => set((state) => {
    if (clickedSlotName === "main") return {}; // Ignore if already main

    const outgoingMain = state.workspaceSlots.main;
    const incomingTarget = state.workspaceSlots[clickedSlotName];

    return {
      workspaceSlots: {
        ...state.workspaceSlots,
        main: incomingTarget,
        [clickedSlotName]: outgoingMain
      }
    };
  })
});