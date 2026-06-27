// Zlices/bookingsZlice.js

export const createBookingsZlice = (set, get) => ({
  // ==========================================
  // 1. BUSINESS CONTENT DATA
  // ==========================================
  jobDescriptionDraft: "Job Description Workspace Primary Editor Terminal Node.",
  chatMessages: [
    { id: "init-1", sender: "system", text: "Live Dispatch - Active Session initiated." }
  ],
  activePostsCount: 0,
  isAiGenerating: false,

  // ==========================================
  // 2. DYNAMIC LAYOUT POSITIONS (The Core Map)
  // ==========================================
  // Default positions mapped cleanly out as initial keys
  slots: {
    main: "AiChatTerminal",
    sidebar: "JobDescriptionWorkspace",
    bottom: "YourActivePosts"
  },

  // ==========================================
  // 3. UNIVERSAL SWAPPING ACTIONS
  // ==========================================
  
  // The truly generic swap engine. No hardcoded module strings!
  swapSlots: (clickedSlotName) => set((state) => {
    if (clickedSlotName === "main") return {}; // Already on main screen, ignore

    const outgoingMainModule = state.slots.main;
    const incomingTargetModule = state.slots[clickedSlotName];

    return {
      slots: {
        ...state.slots,
        main: incomingTargetModule,           // Target moves to center stage
        [clickedSlotName]: outgoingMainModule // Old center module moves to sleeping slot
      }
    };
  }),

  // Standard business data updates
  setJobDescription: (text) => set({ jobDescriptionDraft: text }),
  addChatMessage: (text, sender = "user") => 
    set((state) => ({
      chatMessages: [...state.chatMessages, { id: crypto.randomUUID(), sender, text }]
    })),
  setAiGenerating: (status) => set({ isAiGenerating: status }),
  setActivePostsCount: (count) => set({ activePostsCount: count })
});