// useWorkerDashboardData.js
import { create } from "zustand";
import { createWorkspaceZlice } from "./Zlices/workspaceZlice";
import { createScheduledZlice } from "./Zlices/scheduledZlice";
import { createMeZlice } from "./Zlices/meZlice";
import { createMicsZlice } from "./Zlices/micsZlice";

export const useWorkerDashboardData = create((...a) => ({
  ...createWorkspaceZlice(...a),
  ...createScheduledZlice(...a),
  ...createMeZlice(...a),
  ...createMicsZlice(...a) 
}));