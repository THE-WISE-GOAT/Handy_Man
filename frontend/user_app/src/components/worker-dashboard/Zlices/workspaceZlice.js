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

  connectToDispatch: () => {
    const { workerProfession } = get();

    const socket = new WebSocket(`ws://127.0.0.1:8000/ws/${workerProfession}`);

    socket.onopen = () => {
      console.log(`Connected as ${workerProfession}`);
    };

    socket.onmessage = (event) => {
      const job = JSON.parse(event.data);

      console.log("Incoming Job:", job);
    };

    socket.onclose = () => {
      console.log("Websocket disconnected");
    };

    set({ socket });
  },


});


