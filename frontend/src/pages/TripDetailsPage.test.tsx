// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import TripDetailsPage from "./TripDetailsPage";
import { tripsApi } from "../api/trips";
import {
  getCalendarStatus,
  getCalendarAuthUrl,
  scheduleTripToCalendar,
} from "../api/calendar";
import type { TripDetailResponse } from "../types/trip";

vi.mock("../api/trips", () => ({
  tripsApi: {
    getTrip: vi.fn(),
    generateItinerary: vi.fn(),
    deleteTrip: vi.fn(),
  },
}));

vi.mock("../api/calendar", () => ({
  getCalendarStatus: vi.fn(),
  getCalendarAuthUrl: vi.fn(),
  scheduleTripToCalendar: vi.fn(),
}));

vi.mock("../utils/pdfGenerator", () => ({
  generateTripItineraryPdf: vi.fn(),
}));

describe("TripDetailsPage Google Calendar & PDF Export", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    vi.mocked(getCalendarStatus).mockResolvedValue({ connected: true });
  });

  afterEach(() => {
    cleanup();
  });

  const tripWithItinerary: TripDetailResponse = {
    id: 714,
    user_id: 1,
    title: "Grand Kashmir Expedition",
    destination: "Kashmir, India",
    start_date: "2026-09-01",
    end_date: "2026-09-07",
    status: "PLANNED",
    num_travellers: 3,
    budget: "$3,500",
    created_at: "2026-08-11T12:00:00Z",
    updated_at: "2026-08-11T12:00:00Z",
    itinerary: {
      trip_summary: "An awesome Kashmir tour.",
      days: [
        {
          date: "2026-09-01",
          activities: [
            {
              title: "Srinagar Arrival",
              description: "Check into houseboat.",
              approximate_time: "09:00 AM",
              location: "Dal Lake",
            },
          ],
        },
      ],
    },
  };

  const tripWithoutItinerary: TripDetailResponse = {
    ...tripWithItinerary,
    id: 715,
    title: "Unplanned Weekend Trip",
    itinerary: null,
  };

  it("renders 'Export as PDF' and 'Add to Google Calendar' buttons when itinerary exists", async () => {
    vi.mocked(tripsApi.getTrip).mockResolvedValue({ data: tripWithItinerary } as never);

    render(
      <MemoryRouter initialEntries={["/app/trips/714"]}>
        <Routes>
          <Route path="/app/trips/:tripId" element={<TripDetailsPage />} />
        </Routes>
      </MemoryRouter>
    );

    const exportBtn = await screen.findByTestId("export-pdf-btn");
    const calBtn = await screen.findByTestId("add-google-calendar-btn");

    expect(exportBtn.textContent).toContain("Export as PDF");
    expect(calBtn.textContent).toContain("Add to Google Calendar");
  });

  it("does NOT render PDF export or Google Calendar buttons when itinerary is null", async () => {
    vi.mocked(tripsApi.getTrip).mockResolvedValue({ data: tripWithoutItinerary } as never);

    render(
      <MemoryRouter initialEntries={["/app/trips/715"]}>
        <Routes>
          <Route path="/app/trips/:tripId" element={<TripDetailsPage />} />
        </Routes>
      </MemoryRouter>
    );

    await screen.findByTestId("trip-details-page");

    expect(screen.queryByTestId("export-pdf-btn")).toBeNull();
    expect(screen.queryByTestId("add-google-calendar-btn")).toBeNull();
  });

  it("connected calendar -> clicking 'Add to Google Calendar' calls scheduleTripToCalendar endpoint", async () => {
    vi.mocked(tripsApi.getTrip).mockResolvedValue({ data: tripWithItinerary } as never);
    vi.mocked(scheduleTripToCalendar).mockResolvedValue({
      total_activities: 1,
      created: 1,
      already_exists: 0,
      failed: 0,
      calendar_url: "https://calendar.google.com/calendar/u/0/r",
      failed_activities: [],
    });

    render(
      <MemoryRouter initialEntries={["/app/trips/714"]}>
        <Routes>
          <Route path="/app/trips/:tripId" element={<TripDetailsPage />} />
        </Routes>
      </MemoryRouter>
    );

    const calBtn = await screen.findByTestId("add-google-calendar-btn");
    fireEvent.click(calBtn);

    await waitFor(() => {
      expect(scheduleTripToCalendar).toHaveBeenCalledWith(714);
    });

    const banner = await screen.findByTestId("calendar-result-banner");
    expect(banner.textContent).toContain("Trip Added to Google Calendar");
    expect(banner.textContent).toContain("1 activities added to your calendar");

    const link = screen.getByTestId("open-google-calendar-link") as HTMLAnchorElement;
    expect(link.href).toBe("https://calendar.google.com/calendar/u/0/r");
  });

  it("already-synced response renders 'Trip Already Synced' banner", async () => {
    vi.mocked(tripsApi.getTrip).mockResolvedValue({ data: tripWithItinerary } as never);
    vi.mocked(scheduleTripToCalendar).mockResolvedValue({
      total_activities: 1,
      created: 0,
      already_exists: 1,
      failed: 0,
      calendar_url: "https://calendar.google.com/calendar/u/0/r",
      failed_activities: [],
    });

    render(
      <MemoryRouter initialEntries={["/app/trips/714"]}>
        <Routes>
          <Route path="/app/trips/:tripId" element={<TripDetailsPage />} />
        </Routes>
      </MemoryRouter>
    );

    const calBtn = await screen.findByTestId("add-google-calendar-btn");
    fireEvent.click(calBtn);

    const banner = await screen.findByTestId("calendar-result-banner");
    expect(banner.textContent).toContain("Trip Already Synced with Google Calendar");
    expect(banner.textContent).toContain("1 activities were already scheduled");
  });

  it("partial failure displays warning banner with failed activity details", async () => {
    vi.mocked(tripsApi.getTrip).mockResolvedValue({ data: tripWithItinerary } as never);
    vi.mocked(scheduleTripToCalendar).mockResolvedValue({
      total_activities: 2,
      created: 1,
      already_exists: 0,
      failed: 1,
      calendar_url: "https://calendar.google.com/calendar/u/0/r",
      failed_activities: [
        {
          day: "2026-09-01",
          activity_index: 1,
          title: "Failed Dinner Cruise",
          error: "Google API error (500)",
        },
      ],
    });

    render(
      <MemoryRouter initialEntries={["/app/trips/714"]}>
        <Routes>
          <Route path="/app/trips/:tripId" element={<TripDetailsPage />} />
        </Routes>
      </MemoryRouter>
    );

    const calBtn = await screen.findByTestId("add-google-calendar-btn");
    fireEvent.click(calBtn);

    const banner = await screen.findByTestId("calendar-result-banner");
    expect(banner.textContent).toContain("Trip Partially Added to Google Calendar");
    expect(banner.textContent).toContain("Failed Dinner Cruise");
  });

  it("disconnected calendar -> clicking 'Add to Google Calendar' initiates OAuth flow", async () => {
    vi.mocked(tripsApi.getTrip).mockResolvedValue({ data: tripWithItinerary } as never);
    vi.mocked(getCalendarStatus).mockResolvedValue({ connected: false });
    vi.mocked(getCalendarAuthUrl).mockResolvedValue({ auth_url: "https://accounts.google.com/o/oauth2/v2/auth?client_id=123" });

    const originalLocation = window.location;
    delete (window as unknown as Record<string, unknown>).location;
    (window as unknown as Record<string, unknown>).location = { href: "" };

    render(
      <MemoryRouter initialEntries={["/app/trips/714"]}>
        <Routes>
          <Route path="/app/trips/:tripId" element={<TripDetailsPage />} />
        </Routes>
      </MemoryRouter>
    );

    const calBtn = await screen.findByTestId("add-google-calendar-btn");
    fireEvent.click(calBtn);

    await waitFor(() => {
      expect(sessionStorage.getItem("gcal_pending_trip_id")).toBe("714");
      expect(getCalendarAuthUrl).toHaveBeenCalled();
      expect(window.location.href).toContain("accounts.google.com");
    });

    (window as unknown as Record<string, unknown>).location = originalLocation;
  });

  it("auto-schedules trip post-OAuth return when gcal_auto_schedule is set", async () => {
    sessionStorage.setItem("gcal_auto_schedule", "714");
    vi.mocked(tripsApi.getTrip).mockResolvedValue({ data: tripWithItinerary } as never);
    vi.mocked(scheduleTripToCalendar).mockResolvedValue({
      total_activities: 1,
      created: 1,
      already_exists: 0,
      failed: 0,
      calendar_url: "https://calendar.google.com/calendar/u/0/r",
      failed_activities: [],
    });

    render(
      <MemoryRouter initialEntries={["/app/trips/714"]}>
        <Routes>
          <Route path="/app/trips/:tripId" element={<TripDetailsPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(scheduleTripToCalendar).toHaveBeenCalledWith(714);
    });

    expect(sessionStorage.getItem("gcal_auto_schedule")).toBeNull();
  });
});
