// frontend/shared/config/viewRoutes.js

export const CUSTOMER_VIEWS = {
  // ==========================================
  // Category 1: Bookings (dash1board)
  // ==========================================
  AI_CHAT: { 
    id: "AI_CHAT", 
    slug: "AiChatTerminal", 
    label: "AI Chat Terminal", 
    section: "bookings", 
    categoryKey: "bookings" 
  },
  JOB_DESCRIPTION: { 
    id: "JOB_DESCRIPTION", 
    slug: "JobDescriptionWorkspace", 
    label: "Job Description Workspace", 
    section: "bookings", 
    categoryKey: "bookings" 
  },
  MY_POSTS: { 
    id: "MY_POSTS", 
    slug: "YourActivePosts", 
    label: "Your Active Posts", 
    section: "bookings", 
    categoryKey: "bookings" 
  },
  
  // ==========================================
  // Category 2: Postings (dash2board)
  // ==========================================
  ACTIVE_BIDDINGS: { 
    id: "ACTIVE_BIDDINGS", 
    slug: "ActiveBiddingsEngine", 
    label: "Active Biddings Engine", 
    section: "postings", 
    categoryKey: "postings" 
  },
  LIVE_MAP: { 
    id: "LIVE_MAP", 
    slug: "GeospatialLiveMap", 
    label: "Geospatial Live Map", 
    section: "postings", 
    categoryKey: "postings" 
  },
  ACTIVE_POSTS: { 
    id: "ACTIVE_POSTS", 
    slug: "ActivePostsDashboard", 
    label: "Active Posts Dashboard", 
    section: "postings", 
    categoryKey: "postings" 
  },
  RATINGS_REVIEWS: { 
    id: "RATINGS_REVIEWS", 
    slug: "RatingsReviewLogs", 
    label: "Ratings & Review Logs", 
    section: "postings", 
    categoryKey: "postings" 
  },
  
  // ==========================================
  // Category 3: More / Misc (dash3board)
  // ==========================================
  CALENDAR: { 
    id: "CALENDAR", 
    slug: "SystemCalendar", 
    label: "System Calendar", 
    section: "more", 
    categoryKey: "more" 
  },
  ACCOUNT: { 
    id: "ACCOUNT", 
    slug: "AccountProfiles", 
    label: "Account Profiles", 
    section: "more", 
    categoryKey: "more" 
  },
  HISTORY: { 
    id: "HISTORY", 
    slug: "HistoricalRecordsLogs", 
    label: "Historical Records Logs", 
    section: "more", 
    categoryKey: "more" 
  },
  SYSTEM_SETTINGS: { 
    id: "SYSTEM_SETTINGS", 
    slug: "SystemSettings", 
    label: "System Settings", 
    section: "more", 
    categoryKey: "more" 
  }
};

export const WORKER_VIEWS = {
  // ==========================================
  // Category 1: WorkSpace (dash1worker)
  // ==========================================
  MAP: { 
    id: "MAP", 
    slug: "WorkspaceMap", 
    label: "Job Route Mapping", 
    section: "workspace", 
    categoryKey: "workspace" 
  },
  BIDDINGS: { 
    id: "BIDDINGS", 
    slug: "WorkspaceBids", 
    label: "Active Biddings Portal", 
    section: "workspace", 
    categoryKey: "workspace" 
  },
  JOB_DETAILS: { 
    id: "JOB_DETAILS", 
    slug: "WorkspaceJobDetails", 
    label: "Job Details Monitor", 
    section: "workspace", 
    categoryKey: "workspace" 
  },

  // ==========================================
  // Category 2: Scheduled (dash2worker)
  // ==========================================
  CALENDAR: { 
    id: "CALENDAR", 
    slug: "ScheduledCalendar", 
    label: "System Planner Calendar", 
    section: "scheduled", 
    categoryKey: "scheduled" 
  },
  SCHED_MAP: { 
    id: "SCHED_MAP", 
    slug: "ScheduledMap", 
    label: "Route Matrix Overview", 
    section: "scheduled", 
    categoryKey: "scheduled" 
  },
  SCHED_JOB: { 
    id: "SCHED_JOB", 
    slug: "ScheduledJobCard", 
    label: "Scheduled Jobs Registry", 
    section: "scheduled", 
    categoryKey: "scheduled" 
  },
  CLIENT_QUERY: { 
    id: "CLIENT_QUERY", 
    slug: "ClientQueries", 
    label: "Client Communications Terminal", 
    section: "scheduled", 
    categoryKey: "scheduled" 
  },

  // ==========================================
  // Category 3: Me (dash3worker)
  // ==========================================
  INTERVIEW: { 
    id: "INTERVIEW", 
    slug: "MeInterview", 
    label: "Verification Interventions", 
    section: "me", 
    categoryKey: "me" 
  },
  PROFILE: { 
    id: "PROFILE", 
    slug: "MeProfile", 
    label: "Worker Identity Profile", 
    section: "me", 
    categoryKey: "me" 
  },
  CONFIG: { 
    id: "CONFIG", 
    slug: "MeConfiguration", 
    label: "Environment Configurations", 
    section: "me", 
    categoryKey: "me" 
  },
  COLLECTED_TAGS: { 
    id: "COLLECTED_TAGS", 
    slug: "MeCollectedTags", 
    label: "Collected Tags Analyzer", 
    section: "me", 
    categoryKey: "me" 
  },

  // ==========================================
  // Category 4: Mics (dash4worker)
  // ==========================================
  EMPTY_VIEW: { 
    id: "EMPTY_VIEW", 
    slug: "MicsEmpty", 
    label: "Mics Portal", 
    section: "mics", 
    categoryKey: "mics" 
  }
};

export const CUSTOMER_SECTIONS = {
  Bookings: { id: "bookings", label: "Bookings", defaultViewId: "AI_CHAT" },
  Postings: { id: "postings", label: "Postings", defaultViewId: "ACTIVE_BIDDINGS" },
  More: { id: "more", label: "More", defaultViewId: "CALENDAR" },
};

export const WORKER_SECTIONS = {
  WorkSpace: { id: "workspace", label: "WorkSpace", defaultViewId: "MAP" },
  Scheduled: { id: "scheduled", label: "Scheduled", defaultViewId: "CALENDAR" },
  Me: { id: "me", label: "Me", defaultViewId: "INTERVIEW" },
  Mics: { id: "mics", label: "Mics", defaultViewId: "EMPTY_VIEW" }
};

export const CUSTOMER_VIEW_LIST = Object.values(CUSTOMER_VIEWS);
export const WORKER_VIEW_LIST = Object.values(WORKER_VIEWS);

export const CUSTOMER_VIEW_BY_SLUG = Object.fromEntries(CUSTOMER_VIEW_LIST.map((v) => [v.slug, v]));
export const WORKER_VIEW_BY_SLUG = Object.fromEntries(WORKER_VIEW_LIST.map((v) => [v.slug, v]));

export const CUSTOMER_NAV_ITEMS = Object.values(CUSTOMER_SECTIONS).map((section) => ({
  id: section.id,
  label: section.label,
  path: `/customer/${section.id}/${CUSTOMER_VIEWS[section.defaultViewId].slug}`,
  matchPrefix: `/customer/${section.id}/`,
}));

export const WORKER_NAV_ITEMS = Object.values(WORKER_SECTIONS).map((section) => ({
  id: section.id,
  label: section.label,
  path: `/worker/${section.id}/${WORKER_VIEWS[section.defaultViewId].slug}`,
  matchPrefix: `/worker/${section.id}/`,
}));

export const DEFAULT_CUSTOMER_VIEW = CUSTOMER_VIEWS[CUSTOMER_SECTIONS.Bookings.defaultViewId];
export const DEFAULT_WORKER_VIEW = WORKER_VIEWS[WORKER_SECTIONS.WorkSpace.defaultViewId];

export function buildCustomerViewPath(view) { return `/customer/${view.section}/${view.slug}`; }
export function buildWorkerViewPath(view) { return `/worker/${view.section}/${view.slug}`; }

export function getDefaultCustomerPath(sectionKey = "bookings") {
  const normalizedKey = String(sectionKey).toLowerCase();
  const matchedSection = Object.values(CUSTOMER_SECTIONS).find((s) => s.id === normalizedKey) || CUSTOMER_SECTIONS.Bookings;
  return buildCustomerViewPath(CUSTOMER_VIEWS[matchedSection.defaultViewId]);
}

export function getDefaultWorkerPath(sectionKey = "workspace") {
  const normalizedKey = String(sectionKey).toLowerCase();
  const matchedSection = Object.values(WORKER_SECTIONS).find((s) => s.id === normalizedKey) || WORKER_SECTIONS.WorkSpace;
  return buildWorkerViewPath(WORKER_VIEWS[matchedSection.defaultViewId]);
}

export function getCustomerViewBySlug(slug) { return CUSTOMER_VIEW_BY_SLUG[slug] || null; }
export function getWorkerViewBySlug(slug) { return WORKER_VIEW_BY_SLUG[slug] || null; }

// Fixed to map via slug now that internal structural moduleIds are pruned
export const WORKER_VIEW_BY_SLUG_MAP = Object.fromEntries(
  WORKER_VIEW_LIST.map((view) => [
    `${view.categoryKey}:${view.slug}`,
    view,
  ]),
);

export function getWorkerViewForModule(categoryKey, slug) {
  return WORKER_VIEW_BY_SLUG_MAP[`${categoryKey}:${slug}`] || null;
}

export function isCustomerViewInSection(view, sectionKey) {
  return Boolean(view) && view.section === sectionKey;
}