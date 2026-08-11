import type { TripStatus } from "./trip";
import type { ItinerarySchema } from "./itinerary";
import type { RecommendationImage } from "./recommendation";

export interface AdminUserSummary {
  id: number;
  name: string;
  email: string;
}

export interface AdminTripResponse {
  id: number;
  user_id: number;
  user?: AdminUserSummary | null;
  title: string;
  destination: string | null;
  start_date: string;
  end_date: string;
  status: TripStatus;
  num_travellers?: number | null;
  budget?: string | null;
  special_requirements?: string | null;
  destination_image?: RecommendationImage | null;
  created_at: string;
  updated_at: string;
}

export interface AdminTripDetailResponse extends AdminTripResponse {
  itinerary?: ItinerarySchema | null;
}

export interface AdminTripUpdate {
  title?: string;
  destination?: string | null;
  start_date?: string;
  end_date?: string;
  status?: TripStatus;
  num_travellers?: number | null;
  budget?: string | null;
  special_requirements?: string | null;
}
