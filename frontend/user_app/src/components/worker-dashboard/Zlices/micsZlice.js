// Zlices/micsZlice.js

export const createMicsZlice = (set) => ({
  // ==========================================
  // 1. BUSINESS CONTENT DATA PLACEHOLDERS
  // ==========================================
  micsEmptyLabel: "EMPTY",

  // ==========================================
  // 2. DYNAMIC LAYOUT POSITIONS (Single-Slot Expandable Map)
  // ==========================================
  micsSlots: {
    main: "MicsEmpty"
  },

  // ==========================================
  // 3. UNIVERSAL SWAPPING ACTION (Prepared for future expansions)
  // ==========================================
  swapMicsSlots: (clickedSlotName) => set((state) => {
    if (clickedSlotName === "main") return {};

    const outgoingMain = state.micsSlots.main;
    const incomingTarget = state.micsSlots[clickedSlotName];

    return {
      micsSlots: {
        ...state.micsSlots,
        main: incomingTarget,
        [clickedSlotName]: outgoingMain
      }
    };
  })
});