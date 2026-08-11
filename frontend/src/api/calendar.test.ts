import { describe, it, expect, vi, beforeEach } from "vitest";
import api from "./client";
import {
  getCalendarStatus,
  getCalendarAuthUrl,
  postCalendarCallback,
  scheduleTripToCalendar,
} from "./calendar";

vi.mock("./client", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe("Calendar API Client", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("getCalendarStatus calls GET /calendar/status", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { connected: true } });

    const res = await getCalendarStatus();

    expect(api.get).toHaveBeenCalledWith("/calendar/status");
    expect(res).toEqual({ connected: true });
  });

  it("getCalendarAuthUrl calls GET /calendar/auth-url", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { auth_url: "https://accounts.google.com/o/oauth2/v2/auth" } });

    const res = await getCalendarAuthUrl();

    expect(api.get).toHaveBeenCalledWith("/calendar/auth-url");
    expect(res.auth_url).toContain("accounts.google.com");
  });

  it("postCalendarCallback calls POST /calendar/callback", async () => {
    vi.mocked(api.post).mockResolvedValue({
      data: { status: "success", message: "Google Calendar connected successfully." },
    });

    const res = await postCalendarCallback("sample_auth_code");

    expect(api.post).toHaveBeenCalledWith("/calendar/callback", { code: "sample_auth_code" });
    expect(res.status).toBe("success");
  });

  it("scheduleTripToCalendar calls POST /trips/{tripId}/calendar", async () => {
    const mockResponse = {
      total_activities: 4,
      created: 4,
      already_exists: 0,
      failed: 0,
      calendar_url: "https://calendar.google.com/calendar/u/0/r",
      failed_activities: [],
    };
    vi.mocked(api.post).mockResolvedValue({ data: mockResponse });

    const res = await scheduleTripToCalendar(42);

    expect(api.post).toHaveBeenCalledWith("/trips/42/calendar");
    expect(res.created).toBe(4);
  });
});
