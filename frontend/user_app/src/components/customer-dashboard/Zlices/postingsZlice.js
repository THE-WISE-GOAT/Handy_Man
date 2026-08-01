import { apiClient } from "@shared/api/client";

export const createPostingsZlice = (set, get) => ({  // ==========================================
  // 1. DYNAMIC LAYOUT POSITIONS (4-Slot Map)
  // ==========================================
  postingsSlots: {
    main: "ActiveBiddingsEngine",
    sidebar: "GeospatialLiveMap",
    bottomLeft: "ActivePostsDashboard",
    bottomRight: "RatingsReviewLogs"
  },

  swapPostingsSlots: (clickedSlotName) => set((state) => {
    if (clickedSlotName === "main") return {}; 
    const outgoingMainModule = state.postingsSlots.main;
    const incomingTargetModule = state.postingsSlots[clickedSlotName];
    return {
      postingsSlots: {
        ...state.postingsSlots,
        main: incomingTargetModule,           
        [clickedSlotName]: outgoingMainModule 
      }
    };
  }),

  // ==========================================
  // 2. BUSINESS CONTENT DATA & SELECTOR STATE
  // ==========================================
  pendingJobs: [],
  selectedJob: null,
  selectedWorkerId: null,
  matchedWorkersMap: {}, 
  workerLocations: {}, 

  biddingsStream: [], 
  feedbackRating: "Verified Feedback - 5.0 Star Average",
  pipelineStatus: "Post Network Pipeline Monitor Active",

  customerSocket: null,
  chatSocket: null,
  chatMessages: [],
  chatBookingChatId: null,
  isChatConnected: false,

  // ==========================================
  // 3. ACTIONS AND INTEGRATION PIPELINES
  // ==========================================
  fetchPendingJobs: async () => {
    try {
      const data = await apiClient.get("/jobs/status/pending");

      if (data.status === "success") {
        const jobs = data.tasks || [];
        
        const mappedJobs = jobs.map(job => {
          const lat = job.latitude ?? job.location?.latitude;
          const lng = job.longitude ?? job.location?.longitude;
          return {
            ...job,
            id: job.booking_chat_id,
            latitude: lat,
            longitude: lng,
            matchedCount: job.matched_count || 0,
            interestedCount: job.interested_count || 0
          };
        });

        set({ pendingJobs: mappedJobs });
        
        const currentSelected = get().selectedJob;
        if (mappedJobs.length > 0) {
          const matchingActiveJob = currentSelected 
            ? mappedJobs.find(j => j.id === currentSelected.id) 
            : null;
          set({ selectedJob: matchingActiveJob || mappedJobs[0] });
        }

        mappedJobs.forEach(job => {
          get().fetchMatchedWorkersForJob(job.id);
        });
      }
    } catch (error) {
      console.error("❌ Failed to fetch pending jobs:", error);
    }
  },

  fetchJobBids: async (jobId) => {
    if (!jobId) return;
    try {
      const data = await apiClient.get(`/workers/jobs/${jobId}/bids`);
      
      if (data.status === "success") {
        set({ biddingsStream: data.bids || [] });
      }
    } catch (error) {
      console.error(`❌ Failed to fetch bids for Job ${jobId}:`, error);
    }
  },

  updateJobMetrics: (jobId, metrics) => set((state) => {
    const updatedJobs = state.pendingJobs.map(job => 
      job.id === jobId ? { ...job, ...metrics } : job
    );
    
    const currentSelected = state.selectedJob;
    const updatedSelected = currentSelected && currentSelected.id === jobId
      ? { ...currentSelected, ...metrics }
      : currentSelected;

    return {
      pendingJobs: updatedJobs,
      selectedJob: updatedSelected
    };
  }),

  fetchWorkerLocations: async (workerChatIds) => {
    if (!workerChatIds || workerChatIds.length === 0) return;

    try {
      const data = await apiClient.post("/workers/locations", { worker_chat_ids: workerChatIds });
      
      if (data.status === "success") {
        const locationsMap = { ...get().workerLocations };
        data.locations.forEach(loc => {
          locationsMap[loc.worker_chat_id] = {
            ...locationsMap[loc.worker_chat_id],
            ...loc
          };
        });
        set({ workerLocations: locationsMap });
      }
    } catch (error) {
      console.error("❌ Failed to fetch worker locations:", error);
    }
  },

  toggleWorkerInterest: (workerChatId) => set((state) => {
    const locInfo = state.workerLocations[workerChatId];
    if (!locInfo) return {};
    
    return {
      workerLocations: {
        ...state.workerLocations,
        [workerChatId]: {
          ...locInfo,
          is_interested: !locInfo.is_interested
        }
      }
    };
  }),

  fetchMatchedWorkersForJob: async (jobId) => {
    if (!jobId) return;

    try {
      const data = await apiClient.get(`/dispatch/match/${jobId}/find-help`);
      const workers = data.workers || [];

      get().updateJobMetrics(jobId, { 
        matchedCount: workers.length,
        matchCategory: data.category,
        matchedByCategory: data.matched_by_category
      });

      set((state) => ({
        matchedWorkersMap: { 
          ...state.matchedWorkersMap, 
          [jobId]: workers 
        }
      }));

      const workerIds = workers.map(w => w.worker_chat_id);
      if (workerIds.length > 0) {
        get().fetchWorkerLocations(workerIds);
      }

    } catch (error) {
      console.error(`❌ Failed to fetch matched workers for Job ${jobId}:`, error);
      get().updateJobMetrics(jobId, { matchedCount: 0 });
      set((state) => ({
        matchedWorkersMap: { ...state.matchedWorkersMap, [jobId]: [] }
      }));
    }
  },

  setSelectedWorkerId: (workerId) => set({ selectedWorkerId: workerId }),
  
  setSelectedJob: (job) => {
    set({ selectedJob: job, selectedWorkerId: null });
    if (job && job.id) {
      get().fetchJobBids(job.id); 
    }
  },

  disconnectCustomerDispatch: () => {
    const { customerSocket } = get();
    if (customerSocket) {
      customerSocket.close();
      set({ customerSocket: null });
    }
  },

  connectCustomerDispatch: (bookingChatId, token) => {
    get().disconnectCustomerDispatch();

    const wsBaseUrl = import.meta.env?.VITE_WS_URL || "ws://127.0.0.1:8000";
    const socket = new WebSocket(`${wsBaseUrl}/ws/booking/${bookingChatId}?token=${token}`);
    
    socket.onopen = () => console.log("🟢 Live Dispatch WebSocket Connected");
    socket.onerror = (err) => console.error("❌ Live Dispatch WebSocket Error:", err);
    socket.onclose = () => console.log("🔴 Live Dispatch WebSocket Disconnected");

    socket.onmessage = (event) => {
      const message = JSON.parse(event.data);

      if (message.type === "WORKER_INTEREST_UPDATE") {
        const { job_id, worker_chat_id, interested } = message.data;
        set((state) => ({
          pendingJobs: state.pendingJobs.map(job =>
            job.id === job_id
              ? { ...job, interestedCount: (job.interestedCount || 0) + (interested ? 1 : -1) }
              : job
          ),
          workerLocations: {
            ...state.workerLocations,
            [worker_chat_id]: {
              ...state.workerLocations[worker_chat_id],
              is_interested: interested
            }
          }
        }));
      }

      if (message.type === "NEW_BID") {
        const { job_id, bid } = message.data;
        set((state) => ({
          biddingsStream: [...state.biddingsStream, { ...bid, id: crypto.randomUUID(), status: "Incoming" }]
        }));
      }
    };

    set({ customerSocket: socket });
  },

  appendMessage: (sender, text) =>
    set((state) => ({
      chatMessages: [
        ...state.chatMessages,
        { id: crypto.randomUUID(), sender, text }
      ]
    })),

  connectCustomerChat: async (bookingChatId) => {
    get().disconnectCustomerChat();
    const token = localStorage.getItem("handy_man_access_token");
    const wsBaseUrl = import.meta.env?.VITE_WS_URL || "ws://127.0.0.1:8000";
    const socket = new WebSocket(
      `${wsBaseUrl}/ws/booking/${bookingChatId}?token=${token}`
    );

    socket.onopen = () => {
      set({ isChatConnected: true, chatBookingChatId: bookingChatId });
    };

    socket.onerror = (err) =>
      console.error("❌ Customer chat WebSocket error:", err);

    socket.onclose = () =>
      set({ isChatConnected: false, chatBookingChatId: null });

    socket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === "HUMAN_MESSAGE") {
        const { sender, message: msgContent } = message.data;
        set((state) => ({
          chatMessages: [
            ...state.chatMessages,
            { id: crypto.randomUUID(), sender, text: msgContent }
          ]
        }));
      }
    };

    set({ chatSocket: socket });
  },

  disconnectCustomerChat: () => {
    const { chatSocket } = get();
    if (chatSocket) {
      chatSocket.close();
      set({ chatSocket: null, isChatConnected: false, chatBookingChatId: null, chatMessages: [] });
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
        const messages = history
          .filter((msg) => msg.role !== "system")
          .map((msg) => ({
            id: crypto.randomUUID(),
            sender: msg.role === "user" ? "customer" : "worker",
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