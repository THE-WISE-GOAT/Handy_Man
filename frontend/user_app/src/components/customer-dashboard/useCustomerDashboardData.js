import {create} from "zustand";
import { createBookingsZlice } from "./Zlices/bookingsZlice";
import { createPostingsZlice } from "./Zlices/postingsZlice";
import { createMoreZlice } from "./Zlices/moreZlice";

export const useCustomerDashboardData = create((...a) => ({
    ...createBookingsZlice(...a),
    ...createMoreZlice(...a),
    ...createPostingsZlice(...a),
}) );

