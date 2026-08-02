import { apiClient } from "@shared/api/client";

export const createBookingsZlice = (set, get) => ({  userAddrText: "Bhaktapur, Nepal", 
  userLng: 85.4280, 
  userLat: 27.6710, 

  setUserAddrText: (text) => set({ userAddrText: text }),
  setUserCoordinates: (lng, lat) => set({ userLng: lng, userLat: lat }),
  setUserLocation: (address, lng, lat) => set({ 
    userAddrText: address, 
    userLng: lng, 
    userLat: lat 
  }),

  jobDescriptionDraft: "I want to install a smart home manager like alexa....",
  jobTitleDraft: "SMartHoME SeTUP",
  aiTitle: "",
  aiDescription: "",
  chatMessages: [
    {
      id: "init-1",
      sender: "system",
      text: "Live Dispatch - Active Session initiated.",
    },
  ],
  activePostsCount: 0,
  isAiGenerating: false,
  fetchedJobs: [],

  userName: "ANUP G",
  userAddr: "BHAKTAPUR",
  userCont: "+977 9814737741",

  jobProfessional: "plumber",
  cust_id: 1,
  isSubmitting: false,

  slots: {
    main: "AiChatTerminal",
    sidebar: "JobDescriptionWorkspace",
    bottom: "YourActivePosts",
  },
  fetchBookingsPendingJobs: async () => {
    try {
<<<<<<< HEAD
      const token = localStorage.getItem("handy_man_access_token");
      const response = await fetch("http://127.0.0.1:8000/jobs/status/pending", {
        method: "GET",
        headers: {
          "Authorization": `Bearer ${token}`
        }
      });
=======
      console.log("hellooooo");
      const data = await apiClient.get("/jobs/status/pending");
>>>>>>> origin/And

      if (data.status === "success") {
        set({ fetchedJobs: data.tasks });
        set({ activePostsCount: data.tasks.length });
      }
    } catch (error) {
      console.error("❌ Failed to fetch pending jobs:", error);
    }
  },

  createJob: async () => {
    const { 
      booking_chat_id, 
      jobTitleDraft, 
      jobDescriptionDraft, 
      userLng, 
      userLat,
      userName,
      userCont,
      fetchBookingsPendingJobs 
    } = get();

    if (!booking_chat_id) {
      console.error("❌ Cannot post job. No active booking_chat_id found.");
      return;
    }

    set({ isSubmitting: true });

    try {
      const data = await apiClient.post(`/dispatch/${booking_chat_id}/complete`, {
        edited_description: jobDescriptionDraft || "",
        location: {
          longitude: parseFloat(userLng) || 0.0,
          latitude: parseFloat(userLat) || 0.0
        },
        title: jobTitleDraft || "NEW JOB REQUEST",
        contact_name: userName || "",
        contact_phone: userCont || "",
        status: "pending",
        mode: "regular",
        attachments: [] 
      });

      if (data.status === "success") {
        console.log("🚀 Success! Job verified, vectorized by Nvidia, and stored securely.");
        
        const { fetchPendingJobs, fetchMatchedWorkersForJob } = get();
        if (typeof fetchPendingJobs === "function") {
          await fetchPendingJobs();
        }
        
        const allPendingJobs = get().pendingJobs || [];
        const newJob = allPendingJobs.find(j => j.booking_chat_id === booking_chat_id);
        if (newJob && newJob.id && typeof fetchMatchedWorkersForJob === "function") {
          await fetchMatchedWorkersForJob(newJob.id);
        }
      }
    } catch (error) {
      console.error("❌ Failed to finalize job posting:", error);
    } finally {
      set({ isSubmitting: false });
    }
    
    await fetchBookingsPendingJobs();
  },

  swapSlots: (clickedSlotName) =>
    set((state) => {
      if (clickedSlotName === "main") return {};
      const outgoingMainModule = state.slots.main;
      const incomingTargetModule = state.slots[clickedSlotName];
      return {
        slots: {
          ...state.slots,
          main: incomingTargetModule,
          [clickedSlotName]: outgoingMainModule,
        },
      };
    }),

  setJobDescription: (text) => set({ jobDescriptionDraft: text }),
  setJobTitle: (text) => set({ jobTitleDraft: text }),
  addChatMessage: (text, sender = "user") =>
    set((state) => ({
      chatMessages: [
        ...state.chatMessages,
        { id: crypto.randomUUID(), sender, text },
      ],
    })),
  setAiGenerating: (status) => set({ isAiGenerating: status }),
  setActivePostsCount: (count) => set({ activePostsCount: count }),
  setUserName: (text) => set({ userName: text }),
  setUserAddr: (text) => set({ userAddr: text }),
  setUserCont: (text) => set({ userCont: text }),
  setId: (int) => set({ cust_id: int }),
  setProfessional: (text) => set({ jobProfessional: text }),

  booking_chat_id: null,
  ai_response: "",
  is_complete: false,
  categories: [],
  current_tags: [],
  is_job_request: false,
  is_custom_category: false,
  turns_used: 0,
  turns_remaining: 5,

  startNewSession: async () => {
    set({ isAiGenerating: true });
    try {
      const data = await apiClient.post("/dispatch/session", {});

      set({
        booking_chat_id: data.booking_chat_id,
        ai_response: data.ai_response,
        turns_remaining: data.turns_remaining,
        is_complete: false,
        turns_used: 0,
        categories: [],
        current_tags: [],
        is_job_request: false,
        is_custom_category: false,
        chatMessages: [
          {
            id: "init-1",
            sender: "system",
            text: "Live Dispatch - Active Session initiated.",
          },
          {
            id: crypto.randomUUID(),
            sender: "assistant",
            text: data.ai_response,
          }
        ],
      });
    } catch (error) {
      console.error("❌ Failed to authenticate or establish chat session:", error);
    } finally {
      set({ isAiGenerating: false });
    }
  },

  sendCustomerMessage: async (userMessage) => {
    const { booking_chat_id, addChatMessage } = get(); 
    if (!booking_chat_id) {
      console.error("❌ No active booking_chat_id found. Initialize a session first.");
      return;
    }

    addChatMessage(userMessage, "user");

    try {
      const data = await apiClient.post("/dispatch/chat", {
        booking_chat_id: parseInt(booking_chat_id, 10),
        message: userMessage,
      });

      const primaryCategory = data.categories && data.categories.length > 0 
        ? data.categories[0].category 
        : "";

      set({
        booking_chat_id: data.booking_chat_id,
        ai_response: data.ai_response,
        is_complete: data.is_complete,
        categories: data.categories,
        current_tags: data.current_tags,
        is_job_request: data.is_job_request,
        is_custom_category: data.is_custom_category,
        turns_used: data.turns_used,
        turns_remaining: data.turns_remaining,
        ...(data.is_complete ? {
          jobDescriptionDraft: data.problem_description || "",
          jobTitleDraft: primaryCategory ? primaryCategory.toUpperCase() : "NEW JOB REQUEST"
        } : {})
      });

      set((state) => ({
        chatMessages: [
          ...state.chatMessages,
          { id: crypto.randomUUID(), sender: "assistant", text: data.ai_response }
        ]
      }));
    } catch (error) {
      console.error("❌ Failed to process chat turn over secure transport:", error);
    }
  },
});