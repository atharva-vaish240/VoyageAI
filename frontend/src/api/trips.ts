import api from "./client";
import type {
  TripCreate,
  TripUpdate,
  TripResponse,
  TripDetailResponse,
  TripStatusFilter,
} from "../types/trip";
import type { ItinerarySchema } from "../types/itinerary";

export const tripsApi = {
  createTrip: (data: TripCreate) =>
    api.post<TripResponse>("/trips", data),

  listTrips: (status: TripStatusFilter = "all") =>
    api.get<TripResponse[]>("/trips", { params: { status } }),

  getTrip: (tripId: number) =>
    api.get<TripDetailResponse>(`/trips/${tripId}`),

  updateTrip: (tripId: number, data: TripUpdate) =>
    api.patch<TripDetailResponse>(`/trips/${tripId}`, data),

  deleteTrip: (tripId: number) =>
    api.delete<void>(`/trips/${tripId}`),

  generateItinerary: (tripId: number) =>
    api.post<ItinerarySchema>(`/trips/${tripId}/generate-itinerary`),

  getItinerary: (tripId: number) =>
    api.get<ItinerarySchema>(`/trips/${tripId}/itinerary`),

  updateItinerary: (tripId: number, data: ItinerarySchema) =>
    api.put<ItinerarySchema>(`/trips/${tripId}/itinerary`, data),
};
