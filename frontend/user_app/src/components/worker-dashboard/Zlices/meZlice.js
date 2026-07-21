export const createMeZlice = (set, get) => ({
  // ==========================================
  // 0. ME SLOTS (required by Dash3Worker layout)
  // ==========================================
  meSlots: {
    main: "MeInterview",
    sidebar: "MeProfile",
    bottomLeft: "MeConfiguration",
    bottomRight: "MeCollectedTags",
  },

  swapMeSlots: (clickedSlotName) =>
    set((state) => {
      if (clickedSlotName === "main") return {};
      const outgoingMainModule = state.meSlots.main;
      const incomingTargetModule = state.meSlots[clickedSlotName];
      return {
        meSlots: {
          ...state.meSlots,
          main: incomingTargetModule,
          [clickedSlotName]: outgoingMainModule,
        },
      };
    }),

  // ==========================================
  // 1. ONBOARDING STATE
  // ==========================================
  applicantStage: "pending_interview",
  isApplicantComplete: false,
  isApplicantRejected: false,
  rejectionReason: null,
  workerChatId: null,
  workerId: null,

  phoneNumber: "",
  addressText: "",
  latitude: null,
  longitude: null,

  extractedProfile: null,
  isSubmittingApplication: false,
  applicationSubmitted: false,

  // ==========================================
  // 2. CHAT STATE (reused customer pattern)
  // ==========================================
  chatMessages: [
    {
      id: "init-1",
      sender: "system",
      text: "Onboarding interview session ready.",
    },
  ],
  aiResponse: "",
  isAiGenerating: false,
  isChatComplete: false,
  isChatRejected: false,
  turnsUsed: 0,
  turnsRemaining: 5,
  scenarioQuestion: null,

  // ==========================================
  // 3. MAP STATE (reused customer pattern)
  // ==========================================
  isMapOpen: false,
  mapReady: false,
  modalSearchQuery: "",
  modalLat: 27.7172,
  modalLng: 85.3240,
  modalAddrText: "",

  // ==========================================
  // 4. EDITABLE PROFILE STATE
  // ==========================================
  editableProfile: {
    job_category: "",
    category_tag: "",
    specialities: [],
    specialized_tools_or_equipment: [],
    years_experience: 0,
    license_or_certification: "",
    job_description: "",
    emergency_available: false,
    phone_number: "",
    address_text: "",
  },
  isSavingProfile: false,
  profileSaveMessage: null,

  // ==========================================
  // 5. USER BASE INFO STATE
  // ==========================================
  userProfile: {
    firstName: "",
    lastName: "",
    email: "",
    username: "",
    id: null,
  },
  isEditingUserInfo: false,
  isSavingUserInfo: false,
  userInfoSaveMessage: null,

  // ==========================================
  // 6. ACTIONS
  // ==========================================

  setApplicantStage: (stage) => set({ applicantStage: stage }),
  setWorkerChatId: (id) => set({ workerChatId: id }),
  setWorkerId: (id) => set({ workerId: id }),
  setIsApplicantComplete: (val) => set({ isApplicantComplete: val }),
  setIsApplicantRejected: (val) => set({ isApplicantRejected: val }),
  setRejectionReason: (val) => set({ rejectionReason: val }),
  setExtractedProfile: (val) => set({ extractedProfile: val }),
  setIsSubmittingApplication: (val) => set({ isSubmittingApplication: val }),
  setApplicationSubmitted: (val) => set({ applicationSubmitted: val }),

  setPhoneNumber: (val) => set({ phoneNumber: val }),
  setAddressText: (val) => set({ addressText: val }),
  setLatitude: (val) => set({ latitude: val }),
  setLongitude: (val) => set({ longitude: val }),

  setAiResponse: (val) => set({ aiResponse: val }),
  setIsAiGenerating: (val) => set({ isAiGenerating: val }),
  setIsChatComplete: (val) => set({ isChatComplete: val }),
  setIsChatRejected: (val) => set({ isChatRejected: val }),
  setTurnsUsed: (val) => set({ turnsUsed: val }),
  setTurnsRemaining: (val) => set({ turnsRemaining: val }),
  setScenarioQuestion: (val) => set({ scenarioQuestion: val }),

  setIsMapOpen: (val) => set({ isMapOpen: val }),
  setMapReady: (val) => set({ mapReady: val }),
  setModalSearchQuery: (val) => set({ modalSearchQuery: val }),
  setModalLat: (val) => set({ modalLat: val }),
  setModalLng: (val) => set({ modalLng: val }),
  setModalAddrText: (val) => set({ modalAddrText: val }),

  setEditableProfile: (val) => set({ editableProfile: val }),
  setIsSavingProfile: (val) => set({ isSavingProfile: val }),
  setProfileSaveMessage: (val) => set({ profileSaveMessage: val }),

  setUserProfile: (val) => set({ userProfile: val }),
  setIsEditingUserInfo: (val) => set({ isEditingUserInfo: val }),
  setIsSavingUserInfo: (val) => set({ isSavingUserInfo: val }),
  setUserInfoSaveMessage: (val) => set({ userInfoSaveMessage: val }),

  addChatMessage: (text, sender = "user") =>
    set((state) => ({
      chatMessages: [
        ...state.chatMessages,
        { id: crypto.randomUUID(), sender, text },
      ],
    })),

  // Start a new worker interview session
  startWorkerInterview: async () => {
    set({ isAiGenerating: true });
    try {
      const token = localStorage.getItem("handy_man_access_token");
      const response = await fetch("http://127.0.0.1:8000/worker-interview/session", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error(`Session failed: ${response.status}`);
      }

      const data = await response.json();
      set({
        workerChatId: data.worker_chat_id,
        aiResponse: data.ai_response,
        applicantStage: data.stage,
        isChatComplete: data.is_complete,
        isChatRejected: data.is_rejected,
        turnsRemaining: data.turns_remaining || 5,
        turnsUsed: 0,
        scenarioQuestion: data.scenario_question || null,
        chatMessages: [
          {
            id: "init-1",
            sender: "system",
            text: "Onboarding interview session initiated.",
          },
          {
            id: crypto.randomUUID(),
            sender: "assistant",
            text: data.ai_response,
          },
        ],
      });
    } catch (error) {
      console.error("Failed to start worker interview:", error);
    } finally {
      set({ isAiGenerating: false });
    }
  },

  // Send a message in the worker interview
  sendWorkerMessage: async (userMessage) => {
    const { workerChatId, addChatMessage } = get();

    if (!workerChatId) {
      console.error("No active worker_chat_id. Initialize a session first.");
      return;
    }

    addChatMessage(userMessage, "user");
    set({ isAiGenerating: true });

    try {
      const token = localStorage.getItem("handy_man_access_token");
      const response = await fetch("http://127.0.0.1:8000/worker-interview/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({
          worker_chat_id: parseInt(workerChatId),
          message: userMessage,
        }),
      });

      if (!response.ok) {
        throw new Error(`Chat turn rejected: ${response.status}`);
      }

      const data = await response.json();

      set({
        aiResponse: data.ai_response,
        applicantStage: data.stage,
        isChatComplete: data.is_complete,
        isChatRejected: data.is_rejected,
        scenarioQuestion: data.scenario_question || null,
        turnsUsed: data.turns_used,
        turnsRemaining: data.turns_remaining,
      });

      set((state) => ({
        chatMessages: [
          ...state.chatMessages,
          { id: crypto.randomUUID(), sender: "assistant", text: data.ai_response },
        ],
      }));

      if (data.is_complete) {
        get().fetchWorkerSummary();
      }
    } catch (error) {
      console.error("Failed to process chat turn:", error);
    } finally {
      set({ isAiGenerating: false });
    }
  },

  // Fetch worker interview summary (profile extraction)
  fetchWorkerSummary: async () => {
    const { workerChatId } = get();
    if (!workerChatId) return;

    try {
      const token = localStorage.getItem("handy_man_access_token");
      const response = await fetch(
        `http://127.0.0.1:8000/worker-interview/${workerChatId}/summary`,
        {
          headers: {
            "Authorization": `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        set({
          extractedProfile: data.profile,
          isApplicantRejected: data.is_rejected,
          rejectionReason: data.rejection_reason,
        });

        if (data.profile) {
          set({
            editableProfile: {
              job_category: data.profile.job_category || "",
              category_tag: data.profile.category_tag || "",
              specialities: data.profile.specialities || [],
              specialized_tools_or_equipment: data.profile.specialized_tools_or_equipment || [],
              years_experience: data.profile.years_experience || 0,
              license_or_certification: data.profile.license_or_certification || "",
              job_description: data.profile.job_description || "",
              emergency_available: data.profile.emergency_available || false,
              phone_number: get().phoneNumber || "",
              address_text: get().addressText || "",
            },
          });
        }
      }
    } catch (error) {
      console.error("Failed to fetch worker summary:", error);
    }
  },

  // ====================================================
  // 🛠️ ARCHITECTURAL UPDATE: Hit the correct completion/extraction endpoint!
  // ====================================================
  submitApplication: async () => {
    const { workerChatId, phoneNumber, addressText, latitude, longitude } = get();

    if (!workerChatId) {
      console.error("No worker_chat_id found.");
      return;
    }

    set({ isSubmittingApplication: true });

    try {
      const token = localStorage.getItem("handy_man_access_token");
      
      // Hitting complete instead of raw submit ensures that the profile extractor,
      // Nvidia vector embeds, and DB properties populate correctly.
      const response = await fetch(`http://127.0.0.1:8000/worker-interview/${workerChatId}/complete`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({
          phone_number: phoneNumber || "",
          location: {
            longitude: parseFloat(longitude) || 0.0,
            latitude: parseFloat(latitude) || 0.0
          }
        }),
      });

      if (!response.ok) {
        throw new Error(`Completion / submit pipeline failed: ${response.status}`);
      }

      const data = await response.json();
      
      set({
        applicantStage: "pending_admin_review", // Pushes UI state forward
        applicationSubmitted: true,
      });

      // Refresh applicant and map statuses
      await get().loadApplicantStatus();
    } catch (error) {
      console.error("Failed to complete application process:", error);
    } finally {
      set({ isSubmittingApplication: false });
    }
  },

  // Update worker profile (PATCH)
  updateWorkerProfile: async () => {
    const { workerId, editableProfile } = get();

    if (!workerId) {
      console.error("No worker_id found.");
      return;
    }

    set({ isSavingProfile: true, profileSaveMessage: null });

    try {
      const token = localStorage.getItem("handy_man_access_token");
      const response = await fetch(
        `http://127.0.0.1:8000/worker-onboarding/my-profile`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`,
          },
          body: JSON.stringify(editableProfile),
        }
      );

      if (!response.ok) {
        throw new Error(`Update failed: ${response.status}`);
      }

      const data = await response.json();
      set({ profileSaveMessage: data.message || "Profile updated successfully." });
    } catch (error) {
      console.error("Failed to update worker profile:", error);
      set({ profileSaveMessage: "Failed to update profile." });
    } finally {
      set({ isSavingProfile: false });
    }
  },

  // Fetch current user base info
  loadUserProfile: async () => {
    try {
      const token = localStorage.getItem("handy_man_access_token");
      const response = await fetch("http://127.0.0.1:8000/users/me", {
        headers: {
          "Authorization": `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        set({
          userProfile: {
            firstName: data.firstName || data.first_name || "",
            lastName: data.lastName || data.last_name || "",
            email: data.email || "",
            username: data.username || "",
            id: data.id || null,
          },
        });
      }
    } catch (error) {
      console.error("Failed to load user profile:", error);
    }
  },

  // Update user base info (PUT /users/me)
  updateUserProfile: async () => {
    const { userProfile } = get();

    set({ isSavingUserInfo: true, userInfoSaveMessage: null });

    try {
      const token = localStorage.getItem("handy_man_access_token");
      const response = await fetch("http://127.0.0.1:8000/users/me", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify(userProfile),
      });

      if (!response.ok) {
        throw new Error(`Update failed: ${response.status}`);
      }

      const data = await response.json();
      set({
        userInfoSaveMessage: data.message || "User profile updated successfully.",
        isEditingUserInfo: false,
      });
    } catch (error) {
      console.error("Failed to update user profile:", error);
      set({ userInfoSaveMessage: "Failed to update user profile." });
    } finally {
      set({ isSavingUserInfo: false });
    }
  },

  // Fetch applicant status on load
  loadApplicantStatus: async () => {
    try {
      const token = localStorage.getItem("handy_man_access_token");
      const response = await fetch("http://127.0.0.1:8000/worker-onboarding/my-status", {
        headers: {
          "Authorization": `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        set({
          workerId: data.worker_id,
          applicantStage: data.stage,
          isApplicantComplete: data.is_complete,
          isApplicantRejected: data.is_rejected,
          rejectionReason: data.rejection_reason,
          workerChatId: data.worker_chat_id,
          phoneNumber: data.phone_number || "",
          addressText: data.address_text || "",
        });

        if (data.worker_chat_id) {
          get().fetchChatHistory(data.worker_chat_id);
        }

        // Populate the worker profile state from the persisted WorkerProfile
        // so the dashboard no longer shows empty/"None" details after the
        // application is approved. Prefer the saved WorkerProfile columns;
        // fall back to any previously extracted interview profile.
        if (
          data.job_category ||
          data.specialities?.length ||
          data.job_description
        ) {
          set({
            extractedProfile: {
              job_category: data.job_category,
              category_tag: data.category_tag,
              specialities: data.specialities || [],
              specialized_tools_or_equipment:
                data.specialized_tools_or_equipment || [],
              years_experience: data.years_experience || 0,
              license_or_certification: data.license_or_certification || "",
              job_description: data.job_description || "",
              emergency_available: data.emergency_available || false,
              has_verified_specialty: data.has_verified_specialty || false,
              scenario_passed: data.scenario_passed || false,
              scenario_score: data.scenario_score || 0,
            },
            editableProfile: {
              job_category: data.job_category || "",
              category_tag: data.category_tag || "",
              specialities: data.specialities || [],
              specialized_tools_or_equipment:
                data.specialized_tools_or_equipment || [],
              years_experience: data.years_experience || 0,
              license_or_certification: data.license_or_certification || "",
              job_description: data.job_description || "",
              emergency_available: data.emergency_available || false,
              phone_number: data.phone_number || get().phoneNumber || "",
              address_text: data.address_text || get().addressText || "",
            },
          });
        }
      }
    } catch (error) {
      console.error("Failed to load applicant status:", error);
    }
  },

  // Fetch existing chat history for a worker_chat_id
  fetchChatHistory: async (workerChatId) => {
    try {
      const token = localStorage.getItem("handy_man_access_token");
      const response = await fetch(
        `http://127.0.0.1:8000/worker-interview/${workerChatId}/history`,
        {
          headers: {
            "Authorization": `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        const visibleHistory = (data.history || [])
          .filter((m) => m && m.role && m.role !== "system")
          .map((m) => ({
            id: crypto.randomUUID(),
            sender: m.role === "user" ? "user" : "assistant",
            text: m.content ?? "",
          }));
        set({
          chatMessages: visibleHistory.length > 0
            ? [
                { id: "init-1", sender: "system", text: "Onboarding interview session restored." },
                ...visibleHistory,
              ]
            : [
                { id: "init-1", sender: "system", text: "Onboarding interview session ready." },
              ],
          applicantStage: data.stage,
          isChatComplete: data.is_complete,
          turnsUsed: data.turns_used,
          turnsRemaining: data.turns_remaining,
        });

        if (data.is_complete) {
          get().fetchWorkerSummary();
        }
      }
    } catch (error) {
      console.error("Failed to fetch chat history:", error);
    }
  },
});