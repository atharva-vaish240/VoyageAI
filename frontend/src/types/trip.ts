import type { ItinerarySchema } from "./itinerary";

export type TripStatus = "DRAFT" | "PLANNED" | "COMPLETED";

export type TripStatusFilter = "upcoming" | "past" | "all";

export interface TripCreate {
  title: string;
  destination?: string | null;
  start_date: string;
  end_date: string;
  status?: TripStatus;
  num_travellers?: number | null;
  budget?: string | null;
  special_requirements?: string | null;
}

export interface TripUpdate {
  title?: string;
  destination?: string | null;
  start_date?: string;
  end_date?: string;
  status?: TripStatus;
  num_travellers?: number | null;
  budget?: string | null;
  special_requirements?: string | null;
}

export interface TripResponse {
  id: number;
  user_id: number;
  title: string;
  destination: string | null;
  start_date: string;
  end_date: string;
  status: TripStatus;
  created_at: string;
  updated_at: string;
}

export interface TripDetailResponse extends TripResponse {
  num_travellers?: number | null;
  budget?: string | null;
  special_requirements?: string | null;
  itinerary?: ItinerarySchema | null;
}
