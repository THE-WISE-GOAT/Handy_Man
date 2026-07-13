export const createBookingsZlice = (set, get) => ({
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

  fetchCustomerJobs: async () => {
    try {
      const response = await fetch("http://127.0.0.1:8000/jobs/my-tasks");

      if (!response.ok) {
        throw new Error(`HTTP Error Status: ${response.status}`);
      }

      const data = await response.json();

      if (data.status === "success") {
        set({ fetchedJobs: data.tasks });
        set({ activePostsCount: data.tasks.length });
      }
    } catch (error) {
      console.error("❌ Frontend fetch failure:", error);
    }
  },

 createJob: async () => {
    const { booking_chat_id, jobTitleDraft, jobDescriptionDraft } = get();

    if (!booking_chat_id) {
      console.error("❌ Cannot post job. No active booking_chat_id found.");
      return;
    }

    set({ isSubmitting: true });

    try {
      const token = localStorage.getItem("handy_man_access_token");

      // ── Hitting the updated data integration pipeline route ──
      const response = await fetch(`http://127.0.0.1:8000/dispatch/${booking_chat_id}/complete`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          // Fixed fallback implementation: if text inputs are deleted entirely, submit safe clean parameters to backend 
          edited_description: jobDescriptionDraft || ""
        }),
      });

      if (!response.ok) {
        throw new Error(`Posting pipeline rejected by server: ${response.status}`);
      }
      
      const data = await response.json();
      if (data.status === "success") {
        console.log("🚀 Success! Job verified, vectorized by Nvidia, and stored securely.");
        
        // Optional: Reset drafts or trigger UI success view changes here
      }
    } catch (error) {
      console.error("❌ Failed to finalize job posting:", error);
    } finally {
      set({ isSubmitting: false });
    }
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

  
// ── Step 1: Initialize the Session (Protected by get_current_user) ──
  startNewSession: async () => {
    set({ isAiGenerating: true });

    try {
      // Pull the JWT keycard out of localStorage
      const token = localStorage.getItem("handy_man_access_token"); 

      const response = await fetch("http://127.0.0.1:8000/dispatch/session", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          // The security guard (OAuth2PasswordBearer) reads this header line
          "Authorization": `Bearer ${token}` 
        },
      });

      if (!response.ok) {
        throw new Error(`Session authorization failed: ${response.status}`);
      }

      const data = await response.json();

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

  // ── Step 2: Send Message Turn (Protected by get_current_user) ──
  sendCustomerMessage: async (userMessage) => {
    const { booking_chat_id, addChatMessage, swapSlots } = get(); 
    
    if (!booking_chat_id) {
      console.error("❌ No active booking_chat_id found. Initialize a session first.");
      return;
    }

    // Instantly reflect user message on UI terminal screen
    addChatMessage(userMessage, "user");

    try {
      // Pull the same JWT keycard out of localStorage
      const token = localStorage.getItem("handy_man_access_token");

      const response = await fetch("http://127.0.0.1:8000/dispatch/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          // Validates against _get_own_session to ensure they own this chat ID
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          booking_chat_id: parseInt(booking_chat_id),
          message: userMessage,
        }),
      });

      if (!response.ok) {
        throw new Error(`Chat turn rejected by server: ${response.status}`);
      }

      const data = await response.json(); 

      // Determine the primary category title generated by AI (if any exist)
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

        // ── POPULATE THE DRAFTS AUTOMATICALLY IF COMPLETE ──
        ...(data.is_complete ? {
          jobDescriptionDraft: data.problem_description || "",
          jobTitleDraft: primaryCategory ? primaryCategory.toUpperCase() : "NEW JOB REQUEST"
        } : {})
      });

      // Show AI reply bubble on UI screen
      set((state) => ({
        chatMessages: [
          ...state.chatMessages,
          { id: crypto.randomUUID(), sender: "assistant", text: data.ai_response }
        ]
      }));

      // ── AUTO SWAP WINDOWS IF COMPLETED ──
      // This will seamlessly slide the editable workspace right in front of the customer when chat finishes
      if (data.is_complete && get().slots.main !== "JobDescriptionWorkspace") {
        swapSlots("sidebar");
      }

    } catch (error) {
      console.error("❌ Failed to process chat turn over secure transport:", error);
    }
  },
});