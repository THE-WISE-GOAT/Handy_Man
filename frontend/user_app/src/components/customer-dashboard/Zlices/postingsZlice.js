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
  selectedJob: null, // This acts as the global selector for all modules
  

  matchedWorkers: [],
  selectedWorkerId: null,



  // Dummy data for structure (will be augmented by selectedJob title in UI)
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
        // Map booking_chat_id to id for seamless UI integration
        const mappedJobs = jobs.map(job => ({
            ...job,
            id: job.booking_chat_id 
        }));

        set({ pendingJobs: mappedJobs });
        
        // MASTER-DETAIL LOGIC: Set latest job as default selector if none is chosen
        const currentSelected = get().selectedJob;
        if (mappedJobs.length > 0 && (!currentSelected || !mappedJobs.find(j => j.id === currentSelected.id))) {
          set({ selectedJob: mappedJobs[0] });
        }
      }
    } catch (error) {
      console.error("❌ Failed to fetch pending jobs:", error);
    }
  },

fetchMatchedWorkers: async (category) => {
    if (!category) return;
    try {
      const response = await fetch(`http://127.0.0.1:8000/jobs/workers/match?category=${encodeURIComponent(category)}`);
      const data = await response.json();
      if (data.status === "success") {
        set({ matchedWorkers: data.workers });
      }
    } catch (error) {
      console.error("❌ Failed to fetch matched workers:", error);
    }
  },

  setSelectedWorkerId: (workerId) => set({ selectedWorkerId: workerId }),
  setSelectedJob: (job) => set({ selectedJob: job }),
});