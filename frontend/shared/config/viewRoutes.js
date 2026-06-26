export const CUSTOMER_VIEWS = {
  // Category 1: Bookings
  AI_CHAT: { id: "AI_CHAT", slug: "DispatchChatTerminal", label: "AI Chat Terminal", section: "bookings", categoryKey: "bookings", moduleId: "ai-chat", subtitle: "Interactive dispatch manager", previewText: "Live Dispatch — Active Session" },
  JOB_DESCRIPTION: { id: "JOB_DESCRIPTION", slug: "JobDescriptionWorkspace", label: "Job Description Workspace", section: "bookings", categoryKey: "bookings", moduleId: "job-description", subtitle: "Review and refine auto-generated details", previewText: "Description Live Glance — Draft Mode" },
  MY_POSTS: { id: "MY_POSTS", slug: "MyActivePosts", label: "Your Active Posts", section: "bookings", categoryKey: "bookings", moduleId: "my-posts", subtitle: "Overview of tasks deployed to network", previewText: "Active Posts — 0 live requests trackable" },
  
  // Category 2: Postings
  ACTIVE_BIDDINGS: { id: "ACTIVE_BIDDINGS", slug: "ActiveBiddingsEngine", label: "Active Biddings Engine", section: "postings", categoryKey: "postings", moduleId: "biddings", subtitle: "COMPETITIVE MARKETPLACE METRICS", previewText: "Bids Portal — Active incoming traffic" },
  LIVE_MAP: { id: "LIVE_MAP", slug: "GeospatialLiveMap", label: "Geospatial Live Map", section: "postings", categoryKey: "postings", moduleId: "map", subtitle: "REALTIME FIELD LOCATION MATRIX", previewText: "GPS Coordinates — Tracking Active Feed" },
  ACTIVE_POSTS: { id: "ACTIVE_POSTS", slug: "ActivePosts", label: "Active Posts Dashboard", section: "postings", categoryKey: "postings", moduleId: "active-post-v2", subtitle: "DEPLOYED TASKS RADAR", previewText: "Post Network Pipeline Monitor Active" },
  RATINGS_REVIEWS: { id: "RATINGS_REVIEWS", slug: "RatingsAndReviewLogs", label: "Ratings & Review Logs", section: "postings", categoryKey: "postings", moduleId: "ratings-review", subtitle: "REPUTATION QUALITY VERIFICATION", previewText: "Verified Feedback — 5.0 Star Average" },
  
  // Category 3: More
  CALENDAR: { id: "calendar", slug: "Calendar", label: "Calendar", section: "more", categoryKey: "more", moduleId: "calendar", subtitle: "Scheduled jobs marked below", previewText: "You have no active jobs scheduled" },
  ACCOUNT: { id: "account", slug: "Account", label: "account", section: "more", categoryKey: "more", moduleId: "account", subtitle: "Your Account", previewText: "" },
  HISTORY: { id: "history", slug: "History", label: "history", section: "more", categoryKey: "more", moduleId: "history", subtitle: "Histoy: ", previewText: "Your history with us: " },
  SYSTEM_SETTINGS: { id: "settings", slug: "Settings", section: "more", categoryKey: "more", moduleId: "settings", subtitle: "Configure Settings", previewText: "Configure you settings here" },
};

/* ==========================================================================
   NEW ALIGNED WORKER CONFIGURATION MATRIX
   ========================================================================== */
export const WORKER_VIEWS = {
  // Category 1: WorkSpace
  MAP: { id: "WK_MAP", slug: "WorkspaceMap", label: "Job Route Mapping", section: "workspace", categoryKey: "workspace", moduleId: "wk-map", subtitle: "REALTIME FIELD DISPATCH MAP", previewText: "Active Tracking Feed Proximity Node" },
  BIDDINGS: { id: "WK_BIDDINGS", slug: "WorkspaceBids", label: "Active Biddings Portal", section: "workspace", categoryKey: "workspace", moduleId: "wk-bids", subtitle: "COMPETITIVE MARKETPLACE METRICS", previewText: "Live Quote Pipeline Tracking" },
  JOB_DETAILS: { id: "WK_JOB_DETAILS", slug: "WorkspaceJobDetails", label: "Job Details Monitor", section: "workspace", categoryKey: "workspace", moduleId: "wk-details", subtitle: "DEPLOYED ASSIGNMENT SPECIFICATIONS", previewText: "Scope and Requirements Pipeline Overview" },

  // Category 2: Scheduled
  CALENDAR: { id: "WK_CALENDAR", slug: "ScheduledCalendar", label: "System Planner Calendar", section: "scheduled", categoryKey: "scheduled", moduleId: "wk-calendar", subtitle: "SCHEDULE PLATFORM PLANNERS", previewText: "Calendar Feeds Synchronized" },
  SCHED_MAP: { id: "WK_SCHED_MAP", slug: "ScheduledMap", label: "Route Matrix Overview", section: "scheduled", categoryKey: "scheduled", moduleId: "wk-sched-map", subtitle: "APPOINTMENT LOCATION INDEX", previewText: "Geospatial Routing Parameters Validated" },
  SCHED_JOB: { id: "WK_SCHED_JOB", slug: "ScheduledJobCard", label: "Scheduled Jobs Registry", section: "scheduled", categoryKey: "scheduled", moduleId: "wk-sched-job", subtitle: "UPCOMING DEPLOYMENT NODES", previewText: "Confirmed Client Operations Counter" },
  CLIENT_QUERY: { id: "WK_CLIENT_QUERY", slug: "ClientQueries", label: "Client Communications Terminal", section: "scheduled", categoryKey: "scheduled", moduleId: "wk-queries", subtitle: "ACTIVE MESSAGING CORRIDOR", previewText: "Unread Dispatches Pending Response" },

  // Category 3: Me
  INTERVIEW: { id: "WK_INTERVIEW", slug: "MeInterview", label: "Verification Interventions", section: "me", categoryKey: "me", moduleId: "wk-interview", subtitle: "ONBOARDING COMPLIANCE RUNTIME", previewText: "Vetting Streams Active Standby" },
  PROFILE: { id: "WK_PROFILE", slug: "MeProfile", label: "Worker Identity Profile", section: "me", categoryKey: "me", moduleId: "wk-profile", subtitle: "USER REGISTRATION INFRASTRUCTURE", previewText: "Credentials Secure Node Verified" },
  CONFIG: { id: "WK_CONFIG", slug: "MeConfiguration", label: "Environment Configurations", section: "me", categoryKey: "me", moduleId: "wk-config", subtitle: "SYSTEM CONFIGURATION METRICS", previewText: "Runtime Parameters Variable Panel" },
  COLLECTED_TAGS: { id: "WK_COLLECTED_TAGS", slug: "MeCollectedTags", label: "Collected Tags Analyzer", section: "me", categoryKey: "me", moduleId: "wk-tags", subtitle: "ITEM LABELING CLASSIFICATION LOGS", previewText: "AI Scraped Match Matrices Verified" },

  // Category 4: Mics
  EMPTY_VIEW: { id: "WK_EMPTY", slug: "MicsEmpty", label: "Mics Portal", section: "mics", categoryKey: "mics", moduleId: "wk-empty", subtitle: "EMPTY WORKING STATE", previewText: "No metrics active in this segment" }
};

export const CUSTOMER_SECTIONS = {
  Bookings: { id: "bookings", label: "Bookings", defaultViewId: "AI_CHAT" },
  Postings: { id: "postings", label: "Postings", defaultViewId: "ACTIVE_BIDDINGS" },
  More: { id: "more", label: "More", defaultViewId: "CALENDAR" },
};

export const WORKER_SECTIONS = {
  WorkSpace: { id: "workspace", label: "WorkSpace", defaultViewId: "MAP" },
  Scheduled: { id: "scheduled", label: "Scheduled", defaultViewId: "CALENDAR" },
  Me: { id: "me", label: "Me", defaultViewId: "INTERVIEW" }, // Fixed: Points to Interview, not Calendar
  Mics: { id: "mics", label: "Mics", defaultViewId: "EMPTY_VIEW" } // Added Mics section
};

export const CUSTOMER_VIEW_LIST = Object.values(CUSTOMER_VIEWS);
export const WORKER_VIEW_LIST = Object.values(WORKER_VIEWS);

export const CUSTOMER_VIEW_BY_SLUG = Object.fromEntries(CUSTOMER_VIEW_LIST.map((v) => [v.slug, v]));
export const WORKER_VIEW_BY_SLUG = Object.fromEntries(WORKER_VIEW_LIST.map((v) => [v.slug, v]));

export const CUSTOMER_VIEW_BY_MODULE = Object.fromEntries(CUSTOMER_VIEW_LIST.map((v) => [`${v.categoryKey}:${v.moduleId}`, v]));
export const WORKER_VIEW_BY_MODULE = Object.fromEntries(WORKER_VIEW_LIST.map((v) => [`${v.categoryKey}:${v.moduleId}`, v]));

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

export function getCustomerViewForModule(categoryKey, moduleId) { return CUSTOMER_VIEW_BY_MODULE[`${categoryKey}:${moduleId}`] || null; }
export function getWorkerViewForModule(categoryKey, moduleId) { return WORKER_VIEW_BY_MODULE[`${categoryKey}:${moduleId}`] || null; }

export function isCustomerViewInSection(view, sectionKey) {
  return Boolean(view) && view.section === sectionKey;
}