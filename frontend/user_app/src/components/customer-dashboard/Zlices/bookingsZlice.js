export const createBookingsZlice = (set, get) => ({
  jobDescriptionDraft: "Job Description Workspace Primary Editor Terminal Node.",
  chatMessages: [
    { id: "init-1", sender: "system", text: "Live Dispatch - Active Session initiated." }
  ],
  activePostsCount: 0,
  isAiGenerating: false,
  fetchedJobs: [],

  slots: {
    main: "AiChatTerminal",
    sidebar: "JobDescriptionWorkspace",
    bottom: "YourActivePosts"
  },

  // Keep it purely as an action function
  fetchCustomerJobs: async () => {
    try {
      const response = await fetch("http://localhost:8000/jobs/my-tasks");
      const data = await response.json();
      if (data.status === "success") {
        set({ fetchedJobs: data.tasks });
        set({ activePostsCount: data.tasks.length });
        if (data.tasks.length > 0) {
          set({ jobDescriptionDraft: data.tasks[0].problem_description });
        }
      }
    } catch (error) {
      console.error("Fetch Error:", error);
    }
  },

  swapSlots: (clickedSlotName) => set((state) => {
    if (clickedSlotName === "main") return {};
    const outgoingMainModule = state.slots.main;
    const incomingTargetModule = state.slots[clickedSlotName];
    return {
      slots: {
        ...state.slots,
        main: incomingTargetModule,
        [clickedSlotName]: outgoingMainModule
      }
    };
  }),

  setJobDescription: (text) => set({ jobDescriptionDraft: text }),
  addChatMessage: (text, sender = "user") => 
    set((state) => ({
      chatMessages: [...state.chatMessages, { id: crypto.randomUUID(), sender, text }]
    })),
  setAiGenerating: (status) => set({ isAiGenerating: status }),
  setActivePostsCount: (count) => set({ activePostsCount: count })
});