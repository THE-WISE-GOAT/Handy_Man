// Zlices/postingsZlice.js

export const createPostingsZlice = (set, get) => ({
  // ==========================================
  // 1. BUSINESS CONTENT DATA PLACEHOLDERS
  // ==========================================
  biddingsStream: [
    { id: "bid-1", provider: "John Doe Plumbing", offer: "$120", status: "Incoming" }
  ],
  gpsCoordinates: { lat: 27.7172, lng: 85.3240, status: "Tracking Active Feed" },
  pipelineStatus: "Post Network Pipeline Monitor Active",
  feedbackRating: "Verified Feedback - 5.0 Star Average",

  // ==========================================
  // 2. DYNAMIC LAYOUT POSITIONS (4-Slot Map)
  // ==========================================
  // Default arrangement matching your image exactly
  postingsSlots: {
    main: "ActiveBiddingsEngine",
    sidebar: "GeospatialLiveMap",
    bottomLeft: "ActivePostsDashboard",
    bottomRight: "RatingsReviewLogs"
  },

  // ==========================================
  // 3. UNIVERSAL SWAPPING ACTION
  // ==========================================
  swapPostingsSlots: (clickedSlotName) => set((state) => {
    if (clickedSlotName === "main") return {}; // Already active, ignore

    const outgoingMainModule = state.postingsSlots.main;
    const incomingTargetModule = state.postingsSlots[clickedSlotName];

    return {
      postingsSlots: {
        ...state.postingsSlots,
        main: incomingTargetModule,           // Selected module claims main stage
        [clickedSlotName]: outgoingMainModule // Old main module drops to clicked slot
      }
    };
  })
});