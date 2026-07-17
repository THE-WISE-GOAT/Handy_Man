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

  // Dictionary to store matched workers by Job ID
  matchedWorkersMap: {}, 
  
  // NEW: Dictionary to store worker map coordinates by worker_chat_id
  workerLocations: {}, 

  biddingsStream: [
    { id: "bid-1", provider: "John Doe Plumbing", offer: "$120", status: "Incoming" },
    { id: "bid-2", provider: "Elite Fixers", offer: "$145", status: "Reviewing" }
  ],
  feedbackRating: "Verified Feedback - 5.0 Star Average",
  pipelineStatus: "Post Network Pipeline Monitor Active",

  // ==========================================
  // 3. ACTIONS
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
        
        const mappedJobs = jobs.map(job => ({
            ...job,
            id: job.booking_chat_id,
            matchedCount: job.matchedCount || 0,       
            interestedCount: job.interestedCount || 0  
        }));

        set({ pendingJobs: mappedJobs });
        
        const currentSelected = get().selectedJob;
        if (mappedJobs.length > 0 && (!currentSelected || !mappedJobs.find(j => j.id === currentSelected.id))) {
          set({ selectedJob: mappedJobs[0] });
        }

        mappedJobs.forEach(job => {
          get().fetchMatchedWorkersForJob(job.id);
        });
      }
    } catch (error) {
      console.error("❌ Failed to fetch pending jobs:", error);
    }
  },

  updateJobMetrics: (jobId, metrics) => set((state) => ({
    pendingJobs: state.pendingJobs.map(job => 
      job.id === jobId 
        ? { ...job, ...metrics }
        : job
    )
  })),

  // NEW ACTION: Fetch GPS coordinates for matched professionals
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
          // Merge to preserve existing states (like 'is_interested') if they exist
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

  // NEW ACTION: A test function so you can click a button to see the blinking animation
  toggleWorkerInterest: (workerChatId) => set((state) => {
    const locInfo = state.workerLocations[workerChatId];
    if (!locInfo) return state;
    
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

      // TRIGGER LOCATION FETCH FOR MATCHED WORKERS
      const workerIds = workers.map(w => w.worker_chat_id);
      if (workerIds.length > 0) {
        get().fetchWorkerLocations(workerIds);
      }

    } catch (error) {
      console.error(`❌ Failed to fetch matched workers for Job ${jobId}:`, error);
    }
  },

  setSelectedWorkerId: (workerId) => set({ selectedWorkerId: workerId }),
  setSelectedJob: (job) => set({ selectedJob: job }),
});