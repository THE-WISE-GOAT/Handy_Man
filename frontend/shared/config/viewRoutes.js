export const CUSTOMER_VIEWS = {
  ACTIVE_POSTS: {
    id: "ACTIVE_POSTS",
    slug: "ActivePosts",
    label: "Active Posts Dashboard",
    section: "dashboard",
    categoryKey: "postings",
    moduleId: "active-post-v2",
    subtitle: "DEPLOYED TASKS RADAR",
    previewText: "Post Network Pipeline Monitor Active",
  },
  RATINGS_REVIEWS: {
    id: "RATINGS_REVIEWS",
    slug: "RatingsAndReviewLogs",
    label: "Ratings & Review Logs",
    section: "dashboard",
    categoryKey: "postings",
    moduleId: "ratings-review",
    subtitle: "REPUTATION QUALITY VERIFICATION",
    previewText: "Verified Feedback — 5.0 Star Average",
  },
  ACTIVE_BIDDINGS: {
    id: "ACTIVE_BIDDINGS",
    slug: "ActiveBiddingsEngine",
    label: "Active Biddings Engine",
    section: "dashboard",
    categoryKey: "postings",
    moduleId: "biddings",
    subtitle: "COMPETITIVE MARKETPLACE METRICS",
    previewText: "Bids Portal — Active incoming traffic",
  },
  LIVE_MAP: {
    id: "LIVE_MAP",
    slug: "GeospatialLiveMap",
    label: "Geospatial Live Map",
    section: "dashboard",
    categoryKey: "postings",
    moduleId: "map",
    subtitle: "REALTIME FIELD LOCATION MATRIX",
    previewText: "GPS Coordinates — Tracking Active Feed",
  },
  JOB_DESCRIPTION: {
    id: "JOB_DESCRIPTION",
    slug: "JobDescriptionWorkspace",
    label: "Job Description Workspace",
    section: "booking",
    categoryKey: "bookings",
    moduleId: "job-description",
    subtitle: "Review and refine auto-generated details",
    previewText: "Description Live Glance — Draft Mode",
  },
  AI_CHAT: {
    id: "AI_CHAT",
    slug: "DispatchChatTerminal",
    label: "AI Chat Terminal",
    section: "chat",
    categoryKey: "bookings",
    moduleId: "ai-chat",
    subtitle: "Interactive dispatch manager",
    previewText: "Live Dispatch — Active Session",
  },
  MY_POSTS: {
    id: "MY_POSTS",
    slug: "MyActivePosts",
    label: "Your Active Posts",
    section: "booking",
    categoryKey: "bookings",
    moduleId: "my-posts",
    subtitle: "Overview of tasks deployed to network",
    previewText: "Active Posts — 0 live requests trackable",
  },
};

export const WORKER_VIEWS = {
  PERFORMANCE: {
    id: "PERFORMANCE",
    slug: "PerformanceStats",
    label: "Performance Analytics",
    windowId: "stats",
    section: "dashboard",
    subtitle: "History, ratings, and reviews",
    meta: "Performance",
  },
  AVAILABLE_JOBS: {
    id: "AVAILABLE_JOBS",
    slug: "AvailableJobs",
    label: "Available Jobs Pipeline",
    windowId: "jobs",
    section: "dashboard",
    subtitle: "Map + nearby opportunity board",
    meta: "Local dispatch",
  },
  ACTIVE_BIDS: {
    id: "ACTIVE_BIDS",
    slug: "ActiveBids",
    label: "Active Bids Tracker",
    windowId: "bids",
    section: "dashboard",
    subtitle: "Submitted quote tracker",
    meta: "Bid status",
  },
  ASSIGNED_WORKSPACE: {
    id: "ASSIGNED_WORKSPACE",
    slug: "AssignedWorkspace",
    label: "Assigned Jobs Workspace",
    windowId: "dashboard",
    section: "dashboard",
    subtitle: "Active and unresolved assigned jobs",
    meta: "Worker queue",
  },
  CALENDAR: {
    id: "CALENDAR",
    slug: "CalendarPlanner",
    label: "Calendar Planning Board",
    windowId: "calendar",
    section: "dashboard",
    subtitle: "Job dates and allocated time blocks",
    meta: "Schedule grid",
  },
};

export const CUSTOMER_SECTIONS = {
  dashboard: {
    id: "dashboard",
    label: "Dashboard",
    defaultViewId: "ACTIVE_POSTS",
  },
  booking: {
    id: "booking",
    label: "Booking",
    defaultViewId: "JOB_DESCRIPTION",
  },
  chat: {
    id: "chat",
    label: "Chat",
    defaultViewId: "AI_CHAT",
  },
};

export const CUSTOMER_VIEW_LIST = Object.values(CUSTOMER_VIEWS);
export const WORKER_VIEW_LIST = Object.values(WORKER_VIEWS);

export const CUSTOMER_VIEW_BY_SLUG = Object.fromEntries(
  CUSTOMER_VIEW_LIST.map((view) => [view.slug, view]),
);

export const WORKER_VIEW_BY_SLUG = Object.fromEntries(
  WORKER_VIEW_LIST.map((view) => [view.slug, view]),
);

export const CUSTOMER_VIEW_BY_MODULE = Object.fromEntries(
  CUSTOMER_VIEW_LIST.map((view) => [
    `${view.categoryKey}:${view.moduleId}`,
    view,
  ]),
);

export const WORKER_VIEW_BY_WINDOW = Object.fromEntries(
  WORKER_VIEW_LIST.map((view) => [view.windowId, view]),
);

export const CUSTOMER_NAV_ITEMS = Object.values(CUSTOMER_SECTIONS).map(
  (section) => ({
    id: section.id,
    label: section.label,
    path: `/customer/${section.id}/${CUSTOMER_VIEWS[section.defaultViewId].slug}`,
    matchPrefix: `/customer/${section.id}/`,
  }),
);

export const WORKER_NAV_ITEMS = WORKER_VIEW_LIST.map((view) => ({
  id: view.id,
  label: view.label,
  path: `/worker/${view.section}/${view.slug}`,
  matchPrefix: `/worker/${view.section}/${view.slug}`,
}));

export const DEFAULT_CUSTOMER_VIEW =
  CUSTOMER_VIEWS[CUSTOMER_SECTIONS.dashboard.defaultViewId];
export const DEFAULT_WORKER_VIEW = WORKER_VIEWS.PERFORMANCE;

export function buildCustomerViewPath(view) {
  return `/customer/${view.section}/${view.slug}`;
}

export function buildWorkerViewPath(view) {
  return `/worker/${view.section}/${view.slug}`;
}

export function getDefaultCustomerPath(sectionKey = "dashboard") {
  const section = CUSTOMER_SECTIONS[sectionKey] || CUSTOMER_SECTIONS.dashboard;
  return buildCustomerViewPath(CUSTOMER_VIEWS[section.defaultViewId]);
}

export function getDefaultWorkerPath() {
  return buildWorkerViewPath(DEFAULT_WORKER_VIEW);
}

export function getCustomerViewBySlug(slug) {
  return CUSTOMER_VIEW_BY_SLUG[slug] || null;
}

export function getWorkerViewBySlug(slug) {
  return WORKER_VIEW_BY_SLUG[slug] || null;
}

export function getCustomerViewForModule(categoryKey, moduleId) {
  return CUSTOMER_VIEW_BY_MODULE[`${categoryKey}:${moduleId}`] || null;
}

export function getWorkerViewForWindow(windowId) {
  return WORKER_VIEW_BY_WINDOW[windowId] || null;
}

export function isCustomerViewInSection(view, sectionKey) {
  return Boolean(view) && view.section === sectionKey;
}
