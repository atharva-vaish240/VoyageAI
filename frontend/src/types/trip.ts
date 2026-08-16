import type { ItinerarySchema } from "./itinerary";
import type { RecommendationImage } from "./recommendation";

export type TripStatus = "DRAFT" | "PLANNED" | "COMPLETED";

export type TripStatusFilter = "upcoming" | "past" | "all";

export interface TripMemberResponse {
  id: number;
  trip_id: number;
  user_id: number;
  email: string;
  name: string;
  role: "OWNER" | "MEMBER" | string;
  created_at: string;
}

export interface AddTripMemberRequest {
  email: string;
}

export interface TripCreate {
  title: string;
  destination?: string | null;
  start_date: string;
  end_date: string;
  status?: TripStatus;
  num_travellers?: number | null;
  budget?: string | null;
  special_requirements?: string | null;
  destination_image?: RecommendationImage | null;
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
  destination_image?: RecommendationImage | null;
}

export interface TripResponse {
  id: number;
  user_id: number;
  title: string;
  destination: string | null;
  start_date: string;
  end_date: string;
  status: TripStatus;
  destination_image?: RecommendationImage | null;
  created_at: string;
  updated_at: string;
  role?: "OWNER" | "MEMBER" | string;
  is_owner?: boolean;
}

export interface TripDetailResponse extends TripResponse {
  num_travellers?: number | null;
  budget?: string | null;
  special_requirements?: string | null;
  itinerary?: ItinerarySchema | null;
  members?: TripMemberResponse[];
}
