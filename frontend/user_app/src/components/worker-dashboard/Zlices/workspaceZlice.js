import { apiClient } from "@shared/api/client";
import { API_BASE_URL, WS_BASE_URL } from "@shared/config/api";

export const createWorkspaceZlice = (set, get) => ({
  mapStatus: "REALTIME DISPATCH TRACKING MATRIX ACTIVE",
  bidsPipelineText: "Live Quote Pipeline Tracking",
  jobSpecsText: "Scope and Requirements Pipeline Overview",

  workspaceSlots: {
    main: "WorkspaceMap",
    sidebar: "WorkspaceBids",
    bottom: "WorkspaceJobDetails",
  },

  swapWorkspaceSlots: (clickedSlotName) =>
    set((state) => {
      if (clickedSlotName === "main") return {};

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
  chatSocket: null,
  activeJob: null,
  jobDetailModal: null,
  isInterested: false,
  matchedJobs: [],
  chatMessages: [],
  chatWorkerChatId: null,
  isChatConnected: false,

  setActiveJob: (job) => set({ activeJob: job }),
  openJobDetailModal: (job) =>
    set({ jobDetailModal: job, activeJob: job }),
  closeJobDetailModal: () => set({ jobDetailModal: null }),

  fetchMatchedJobs: async () => {
    try {
      const token = localStorage.getItem("handy_man_access_token");
      const response = await fetch(`${API_BASE_URL}/jobs/for-worker`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        console.error("Failed to fetch matched jobs:", response.status);
        return;
      }

      const data = await response.json();
      if (data.status === "success") {
        set({ matchedJobs: data.jobs || [] });
      }
    } catch (error) {
      console.error("❌ Failed to fetch matched jobs:", error);
    }
  },

  connectToDispatch: (workerChatId, token) => {
    const socket = new WebSocket(
      `${WS_BASE_URL}/ws/${workerChatId}?token=${token}`
    );

    socket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === "NEW_JOB_NOTIFICATION") {
        set({ activeJob: message.data });
      }
    };

    set({ socket });
  },

  expressInterest: async (jobId, workerChatId) => {
    const newInterestState = true;

    const payload = {
      type: "TOGGLE_INTEREST",
      data: { job_id: jobId, worker_chat_id: workerChatId, interested: newInterestState },
    };

    set((state) => ({
      matchedJobs: state.matchedJobs.map((job) => {
        if (job.job_id !== jobId) return job;
        return {
          ...job,
          is_interested: newInterestState,
          interested_count: (job.interested_count || 0) + 1,
        };
      }),
      isInterested: newInterestState,
    }));

    const socket = get().socket;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(payload));
    } else {
      try {
        const token = localStorage.getItem("handy_man_access_token");
        const res = await fetch(`${API_BASE_URL}/jobs/${jobId}/interest`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ worker_chat_id: workerChatId, interested: newInterestState }),
        });
        if (!res.ok) {
          set((state) => ({
            matchedJobs: state.matchedJobs.map((job) => {
              if (job.job_id !== jobId) return job;
              return {
                ...job,
                is_interested: !newInterestState,
                interested_count: Math.max((job.interested_count || 0) - 1, 0),
              };
            }),
            isInterested: !newInterestState,
          }));
        } else {
          const data = await res.json();
          if (data.interested_count !== undefined) {
            set((state) => ({
              matchedJobs: state.matchedJobs.map((job) =>
                job.job_id === jobId ? { ...job, interested_count: data.interested_count } : job
              ),
            }));
          }
        }
       } catch (error) {
         set((state) => ({
           matchedJobs: state.matchedJobs.map((job) => {
             if (job.job_id !== jobId) return job;
             return {
               ...job,
               is_interested: !newInterestState,
               interested_count: Math.max((job.interested_count || 0) - 1, 0),
             };
           }),
           isInterested: !newInterestState,
         }));
         console.error("❌ Failed to express interest:", error);
       }
    }
  },

  appendMessage: (sender, text, senderName = "You") =>
    set((state) => ({
      chatMessages: [
        ...state.chatMessages,
        { id: crypto.randomUUID(), sender, senderName, text }
      ]
    })),

  connectWorkerChat: async (workerChatId) => {
    get().disconnectWorkerChat();
    const token = localStorage.getItem("handy_man_access_token");
    if (!token) {
      console.error("No access token found for WebSocket connection");
      return;
    }
    const socket = new WebSocket(
      `${WS_BASE_URL}/ws/worker/${workerChatId}?token=${token}`
    );

    socket.onopen = () => {
      set({ isChatConnected: true, chatWorkerChatId: workerChatId });
    };

    socket.onerror = (err) =>
      console.error("❌ Worker chat WebSocket error:", err);

    socket.onclose = () =>
      set({ isChatConnected: false, chatWorkerChatId: null });

    socket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === "HUMAN_MESSAGE") {
        const { sender, sender_name, message: msgContent } = message.data;
        set((state) => ({
          chatMessages: [
            ...state.chatMessages,
            { id: crypto.randomUUID(), sender, senderName: sender_name, text: msgContent }
          ]
        }));
      }
      if (message.type === "NEW_JOB_NOTIFICATION") {
        set({ activeJob: message.data });
      }
    };

    set({ chatSocket: socket });
  },

  disconnectWorkerChat: () => {
    const { chatSocket } = get();
    if (chatSocket) {
      chatSocket.close();
      set({
        chatSocket: null,
        isChatConnected: false,
        chatWorkerChatId: null,
        chatMessages: [],
      });
    }
  },

  sendHumanMessage: async (bookingChatId, sender, text) => {
    try {
      const data = await apiClient.post(
        `/dispatch/chat/${bookingChatId}/message`,
        { sender, message: text }
      );
      return data;
    } catch (error) {
      console.error("❌ Failed to send human message:", error);
      throw error;
    }
  },

  fetchChatHistory: async (bookingChatId) => {
      try {
        const data = await apiClient.get(`/dispatch/${bookingChatId}/history`);
        const history = data.history || [];
        const sanitizedHistory = history.filter((msg) => {
          if (msg.role !== "system") return true;
          if (msg.role === "system" && msg.content && msg.content.length < 200) return true;
          return false;
        });
        const messages = sanitizedHistory
          .map((msg) => ({
            id: crypto.randomUUID(),
            sender: msg.role,
            senderName: msg.sender_name || (msg.role === "customer" ? "Customer" : msg.role === "worker" ? "Worker" : "BID SYSTEM"),
            text: msg.content,
          }));
        set({ chatMessages: messages });
      } catch (error) {
        if (error.status === 500) {
          console.error("❌ Chat history fetch failed (server error), skipping retry:", error.message);
        } else {
          console.error("❌ Failed to fetch chat history:", error);
        }
      }
    },
});
