export const createBookingsZlice = (set, get) => ({
  jobDescriptionDraft: "I want to install a smart home manager like alexa....",
  jobTitleDraft: "SMartHoME SeTUP",
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
    const { jobTitleDraft, jobDescriptionDraft, jobProfessional, cust_id } =
      get();

    set({ isSubmitting: true });

    try {
      const response = await fetch("http://127.0.0.1:8000/jobs/post-job", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title: jobTitleDraft,
          description: jobDescriptionDraft,
          cust_id: parseInt(cust_id),
          professional: jobProfessional,
        }),
      });

      if (!response.ok) {
        throw new Error(`Server responded with status: ${response.status}`);
      }
      const data = await response.json();

      if (data.status === "success") {
        console.log("🚀 Job saved successfully to DB:", data.job);
      }
    } catch {}
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
});
