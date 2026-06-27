// Zlices/meZlice.js

export const createMeZlice = (set) => ({
  // ==========================================
  // 1. BUSINESS CONTENT DATA PLACEHOLDERS
  // ==========================================
  interviewStatusText: "Onboarding Compliance Interview Status Run.",
  profileCredentialsText: "Credentials Secure Node Verified",
  envConfigParametersText: "Runtime Parameters Variable Panel",
  scrapedTagsMatchText: "AI Scraped Match Matrices Verified",

  // ==========================================
  // 2. DYNAMIC LAYOUT POSITIONS (4-Slot Map)
  // ==========================================
  meSlots: {
    main: "MeInterview",
    sidebar: "MeProfile",
    bottomLeft: "MeConfiguration",
    bottomRight: "MeCollectedTags"
  },

  // ==========================================
  // 3. UNIVERSAL SWAPPING ACTION
  // ==========================================
  swapMeSlots: (clickedSlotName) => set((state) => {
    if (clickedSlotName === "main") return {}; // Ignore if already main

    const outgoingMain = state.meSlots.main;
    const incomingTarget = state.meSlots[clickedSlotName];

    return {
      meSlots: {
        ...state.meSlots,
        main: incomingTarget,
        [clickedSlotName]: outgoingMain
      }
    };
  })
});