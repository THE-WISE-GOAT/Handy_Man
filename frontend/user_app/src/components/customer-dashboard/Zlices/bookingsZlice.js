export const createBookingsZlice = (set, get) => ({
  jobDescriptionDraft: "I want to install a smart home manager like alexa....",
  jobTitleDraft: "SMartHoME SeTUP",
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