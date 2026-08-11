import api from "./client";
import type {
  CalendarStatusResponse,
  AuthUrlResponse,
  CalendarCallbackResponse,
  TripCalendarResponse,
} from "../types/calendar";

export async function getCalendarStatus(): Promise<CalendarStatusResponse> {
  const { data } = await api.get<CalendarStatusResponse>("/calendar/status");
  return data;
}

export async function getCalendarAuthUrl(): Promise<AuthUrlResponse> {
  const { data } = await api.get<AuthUrlResponse>("/calendar/auth-url");
  return data;
}

export async function postCalendarCallback(code: string): Promise<CalendarCallbackResponse> {
  const { data } = await api.post<CalendarCallbackResponse>("/calendar/callback", { code });
  return data;
}

export async function scheduleTripToCalendar(tripId: number): Promise<TripCalendarResponse> {
  const { data } = await api.post<TripCalendarResponse>(`/trips/${tripId}/calendar`);
  return data;
}
