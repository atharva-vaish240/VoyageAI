export interface CalendarStatusResponse {
  connected: boolean;
}

export interface AuthUrlResponse {
  auth_url: string;
}

export interface CalendarCallbackRequest {
  code: string;
}

export interface CalendarCallbackResponse {
  status: string;
  message: string;
}

export interface FailedActivityDetail {
  day: string;
  activity_index: number;
  title: string;
  error: string;
}

export interface TripCalendarResponse {
  total_activities: number;
  created: number;
  already_exists: number;
  failed: number;
  calendar_url: string;
  failed_activities: FailedActivityDetail[];
}
