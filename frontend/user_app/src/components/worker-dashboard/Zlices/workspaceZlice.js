// Zlices/workspaceZlice.js

export const createWorkspaceZlice = (set, get) => ({
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
    bottom: "WorkspaceJobDetails",
  },

  // ==========================================
  // 3. UNIVERSAL SWAPPING ACTION
  // ==========================================
  swapWorkspaceSlots: (clickedSlotName) =>
    set((state) => {
      if (clickedSlotName === "main") return {}; // Ignore if already main

      const outgoingMain = state.workspaceSlots.main;
      const incomingTarget = state.workspaceSlots[clickedSlotName];

      return {
        workspaceSlots: {
          ...state.workspaceSlots,
          main: incomingTarget,
          [clickedSlotName]: outgoingMain,
        },
      };
    }),

  workerProfession: "plumber",
  socket: null,
activeJob: null, // New state for the incoming job

  connectToDispatch: (workerChatId, token) => {
    // Connect using the token as a query param
    const socket = new WebSocket(`ws://127.0.0.1:8000/ws/${workerChatId}?token=${token}`);

    socket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === "NEW_JOB_NOTIFICATION") {
        // This will update the state, which your React component will see
        set({ activeJob: message.data });
      }
    };
    
    set({ socket });
  },
  

});


