import api from "./client";
import type {
  AdminTripResponse,
  AdminTripDetailResponse,
  AdminTripUpdate,
} from "../types/admin";

export const adminApi = {
  /** Fetch all trips across all users (Admin only). */
  listAllTrips: () => api.get<AdminTripResponse[]>("/admin/trips"),

  /** Fetch trip detail by ID across any user (Admin only). */
  getTrip: (tripId: number) => api.get<AdminTripDetailResponse>(`/admin/trips/${tripId}`),

  /** Update trip metadata by ID (Admin only). */
  updateTrip: (tripId: number, payload: AdminTripUpdate) =>
    api.patch<AdminTripDetailResponse>(`/admin/trips/${tripId}`, payload),

  /** Delete trip by ID across any user (Admin only). */
  deleteTrip: (tripId: number) => api.delete<void>(`/admin/trips/${tripId}`),
};
