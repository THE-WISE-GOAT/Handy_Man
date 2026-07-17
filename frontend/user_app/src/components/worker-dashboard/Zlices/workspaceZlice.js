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
  isInterested: false,

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
  
  expressInterest: async (jobId, workerChatId) => {
    const newInterestState = !get().isInterested;
    set({ isInterested: newInterestState });

    const payload = {
      type: "TOGGLE_INTEREST",
      data: { job_id: jobId, worker_chat_id: workerChatId, interested: newInterestState }
    };

    const socket = get().socket;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(payload));
    } else {
      try {
        const token = localStorage.getItem("handy_man_access_token");
        await fetch(`http://127.0.0.1:8000/jobs/${jobId}/interest`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({ worker_chat_id: workerChatId, interested: newInterestState })
        });
      } catch (error) {
        console.error("❌ Failed to express interest:", error);
      }
    }
  },
  

});


