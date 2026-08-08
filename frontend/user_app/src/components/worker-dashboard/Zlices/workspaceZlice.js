import { apiClient } from "@shared/api/client";
import { API_BASE_URL } from "@shared/config/api";

const normalizeMessage = (msg) => {
  if (!msg || typeof msg !== 'object') {
    return {
      id: `msg-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
      sender_id: null,
      sender_role: 'system',
      sender_name: 'System',
      text: '',
      timestamp: new Date().toISOString(),
    };
  }

  const rawId = msg.id ?? msg.message_id ?? msg._id;
  const safeId = rawId != null ? String(rawId) : `msg-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;

  const rawSenderId = msg.sender_id ?? msg.senderId ?? msg.user_id ?? msg.author_id;

  return {
    id: safeId,
    sender_id: rawSenderId != null ? rawSenderId : null,
    sender_role: String(msg.sender_role || msg.role || msg.sender_type || '').toLowerCase(),
    sender_name: msg.sender_name || msg.username || msg.sender || 'User',
    text: typeof msg.text === 'string' ? msg.text : (msg.message || msg.content || ''),
    timestamp: msg.timestamp || msg.created_at || new Date().toISOString(),
  };
};

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

      let targetSlot = clickedSlotName;
      if (!Object.prototype.hasOwnProperty.call(state.workspaceSlots, clickedSlotName)) {
        targetSlot = Object.keys(state.workspaceSlots).find(
          (key) => state.workspaceSlots[key] === clickedSlotName
        );
      }

      if (!targetSlot || targetSlot === "main") return {};

      const outgoingMain = state.workspaceSlots.main;
      const incomingTarget = state.workspaceSlots[targetSlot];

      return {
        workspaceSlots: {
          ...state.workspaceSlots,
          main: incomingTarget,
          [targetSlot]: outgoingMain,
        },
      };
    }),

  setActiveModule: (moduleName) => set({ activeModule: moduleName }),

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
    const wsBaseUrl = (import.meta.env?.VITE_WS_URL || API_BASE_URL).replace(/^http/, "ws");
    const socket = new WebSocket(
      `${wsBaseUrl}/ws/booking/${workerChatId}?token=${token}`
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

  appendMessage: (senderOrMsg, text, senderName, senderId) => {
    const raw = typeof senderOrMsg === "object" && senderOrMsg !== null
      ? senderOrMsg
      : { 
          sender: senderOrMsg, 
          role: senderOrMsg,
          text, 
          sender_name: senderName || (senderOrMsg === "worker" ? "You" : undefined), 
          sender_id: senderId 
        };
    const msg = normalizeMessage(raw);
    set((state) => ({
      chatMessages: [...state.chatMessages, msg]
    }));
  },

  connectWorkerChat: async (workerChatId) => {
    get().disconnectWorkerChat();
    const token = localStorage.getItem("handy_man_access_token");
    if (!token) {
      console.error("No access token found for WebSocket connection");
      return;
    }
    const wsBaseUrl = (import.meta.env?.VITE_WS_URL || API_BASE_URL).replace(/^http/, "ws");
    const socket = new WebSocket(
      `${wsBaseUrl}/ws/booking/${workerChatId}?token=${token}`
    );

    socket.onopen = () => {
      set({ isChatConnected: true, chatWorkerChatId: workerChatId });
    };

    socket.onerror = (err) =>
      console.error("❌ Worker chat WebSocket error:", err);

    socket.onclose = () =>
      set({ isChatConnected: false, chatWorkerChatId: null });

    socket.onmessage = (event) => {
      const rawData = JSON.parse(event.data);
      if (rawData.type === "HUMAN_MESSAGE") {
        const normalized = normalizeMessage(rawData.data);
        set((state) => {
          const exists = state.chatMessages.some(m => m.id === normalized.id);
          if (exists) return state;

          const filtered = state.chatMessages.filter(
            m => !String(m.id).startsWith("temp-") || m.text !== normalized.text
          );
          return { chatMessages: [...filtered, normalized] };
        });
      }
      if (rawData.type === "NEW_JOB_NOTIFICATION") {
        set({ activeJob: rawData.data });
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
    const token = localStorage.getItem("handy_man_access_token");
    let currentUserId = null;
    try {
      if (token) {
        const base64Payload = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
        const jsonPayload = decodeURIComponent(
          atob(base64Payload)
            .split("")
            .map((c) => `%${`00${c.charCodeAt(0).toString(16)}`.slice(-2)}`)
            .join("")
        );
        currentUserId = JSON.parse(jsonPayload).user_id;
      }
    } catch {
      currentUserId = null;
    }

    const optimisticMsg = normalizeMessage({
      id: `temp-${Date.now()}`,
      sender_id: currentUserId,
      sender_role: sender,
      sender_name: "You",
      text,
      timestamp: new Date().toISOString(),
    });
    get().appendMessage(optimisticMsg);

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
          if (!msg) return false;
          if (msg.role !== "system") return true;
          if (msg.role === "system" && msg.content && msg.content.length < 200) return true;
          return false;
        });
        const messages = sanitizedHistory.map((msg) => normalizeMessage(msg));
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