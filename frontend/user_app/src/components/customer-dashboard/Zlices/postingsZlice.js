// Zlices/postingsZlice.js

export const createPostingsZlice = (set, get) => ({
  // ==========================================
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

  biddingsStream: [
    { id: "bid-1", provider: "John Doe Plumbing", offer: "$120", status: "Incoming" },
    { id: "bid-2", provider: "Elite Fixers", offer: "$145", status: "Reviewing" }
  ],
  feedbackRating: "Verified Feedback - 5.0 Star Average",
  pipelineStatus: "Post Network Pipeline Monitor Active",

  customerSocket: null,

  // ==========================================
  // 3. ACTIONS AND INTEGRATION PIPELINES
  // ==========================================
  fetchPendingJobs: async () => {
    try {
      const token = localStorage.getItem("handy_man_access_token");
      const response = await fetch("http://127.0.0.1:8000/jobs/status/pending", {
        method: "GET",
        headers: {
          "Authorization": `Bearer ${token}`
        }
      });

      if (!response.ok) throw new Error(`HTTP Error: ${response.status}`);
      
      const data = await response.json();

      if (data.status === "success") {
        const jobs = data.tasks || [];
        
        // 🛠️ ARCHITECTURAL FIX: Flatten nested backend location parameters safely
        const mappedJobs = jobs.map(job => {
          const lat = job.latitude ?? job.location?.latitude;
          const lng = job.longitude ?? job.location?.longitude;
          return {
            ...job,
            id: job.booking_chat_id,
            latitude: lat,
            longitude: lng,
            matchedCount: job.matchedCount || 0,       
            interestedCount: job.interestedCount || 0  
          };
        });

        set({ pendingJobs: mappedJobs });
        
        // 🛠️ ARCHITECTURAL FIX: Ensure active selections automatically receive fresh data values
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

  // 🛠️ ARCHITECTURAL FIX: Dual-write updates to prevent decoupled stale states on-screen
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
      const token = localStorage.getItem("handy_man_access_token");
      const response = await fetch("http://127.0.0.1:8000/workers/locations", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ worker_chat_ids: workerChatIds })
      });

      if (!response.ok) throw new Error(`HTTP Error: ${response.status}`);
      
      const data = await response.json();
      
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
      const token = localStorage.getItem("handy_man_access_token");
      const response = await fetch(`http://127.0.0.1:8000/match/${jobId}/find-help`, {
        method: "GET",
        headers: {
          "Authorization": `Bearer ${token}`
        }
      });

      if (!response.ok) {
        get().updateJobMetrics(jobId, { matchedCount: 0 });
        set((state) => ({
          matchedWorkersMap: { ...state.matchedWorkersMap, [jobId]: [] }
        }));
        return;
      }

      const data = await response.json();
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
    }
  },

  setSelectedWorkerId: (workerId) => set({ selectedWorkerId: workerId }),
  setSelectedJob: (job) => set({ selectedJob: job, selectedWorkerId: null }),

  connectCustomerDispatch: (customerId, token) => {
    const socket = new WebSocket(`ws://127.0.0.1:8000/ws/customer/${customerId}?token=${token}`);
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
});