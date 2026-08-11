export type TripStatus = "DRAFT" | "PLANNED" | "COMPLETED";

export type TripStatusFilter = "upcoming" | "past" | "all";

export interface TripCreate {
  title: string;
  destination?: string | null;
  start_date: string;
  end_date: string;
  status?: TripStatus;
}

export interface TripUpdate {
  title?: string;
  destination?: string | null;
  start_date?: string;
  end_date?: string;
  status?: TripStatus;
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
