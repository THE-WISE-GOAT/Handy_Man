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
  matchedJobs: [], // Jobs matched to this worker via semantic matching

  setActiveJob: (job) => set({ activeJob: job }),

  fetchMatchedJobs: async () => {
    try {
      const token = localStorage.getItem("handy_man_access_token");
      const response = await fetch("http://127.0.0.1:8000/worker/matched-jobs", {
        method: "GET",
        headers: {
          "Authorization": `Bearer ${token}`
        }
      });

      if (!response.ok) {
        console.error("Failed to fetch matched jobs:", response.status);
        return;
      }

      const data = await response.json();
      set({ matchedJobs: data || [] });
    } catch (error) {
      console.error("❌ Failed to fetch matched jobs:", error);
    }
  },

  connectToDispatch: (workerChatId, token) => {
    const socket = new WebSocket(`ws://127.0.0.1:8000/ws/worker/${workerChatId}?token=${token}`);

    socket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.event === "new_job_match") {
        set((state) => {
          const exists = state.matchedJobs.some(
            (job) => job.booking_chat_id === message.booking_chat_id
          );
          if (exists) return {};
          return {
            matchedJobs: [
              {
                job_id: 0,
                title: message.title || "New Job Match",
                description: message.description || "",
                budget: null,
                location: null,
                match_score: 0,
                created_at: new Date().toISOString(),
                status: "matched",
                booking_chat_id: message.booking_chat_id,
              },
              ...state.matchedJobs,
            ],
          };
        });
      }
    };

    socket.onclose = () => {
      set({ socket: null });
    };

    socket.onerror = (err) => {
      console.error("WebSocket error:", err);
    };

    set({ socket });
  },

  disconnectFromDispatch: () => {
    const { socket } = get();
    if (socket) {
      socket.close();
      set({ socket: null });
    }
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


