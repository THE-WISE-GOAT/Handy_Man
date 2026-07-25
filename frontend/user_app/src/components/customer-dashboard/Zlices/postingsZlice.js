// Zlices/postingsZlice.js

import { apiClient, normalizeApiError } from "@shared/api/client";

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
      const data = await apiClient.get("/jobs/status/pending");

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
      console.error("❌ Failed to fetch pending jobs:", normalizeApiError(error));
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
      const data = await apiClient.post("/workers/locations", {
        worker_chat_ids: workerChatIds
      });
      
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
      console.error("❌ Failed to fetch worker locations:", normalizeApiError(error));
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
      const data = await apiClient.get(`/match/${jobId}/find-help`);
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
      get().updateJobMetrics(jobId, { matchedCount: 0 });
      set((state) => ({
        matchedWorkersMap: { ...state.matchedWorkersMap, [jobId]: [] }
      }));
      console.error(`❌ Failed to fetch matched workers for Job ${jobId}:`, normalizeApiError(error));
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
