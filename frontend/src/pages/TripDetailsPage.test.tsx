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
    getItinerary: vi.fn(),
    updateItinerary: vi.fn(),
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

describe("TripDetailsPage User-Editable Itinerary", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    vi.mocked(getCalendarStatus).mockResolvedValue({ connected: true });
  });

  afterEach(() => {
    cleanup();
  });

  const baseTripWithItinerary: TripDetailResponse = {
    id: 900,
    user_id: 1,
    title: "Kyoto Autumn Getaway",
    destination: "Kyoto, Japan",
    start_date: "2026-10-15",
    end_date: "2026-10-18",
    status: "PLANNED",
    num_travellers: 2,
    budget: "$2,000",
    created_at: "2026-08-11T12:00:00Z",
    updated_at: "2026-08-11T12:00:00Z",
    itinerary: {
      trip_summary: "Experiencing autumn leaves in ancient Kyoto.",
      days: [
        {
          date: "2026-10-15",
          activities: [
            {
              title: "Fushimi Inari Shrine",
              description: "Walk through thousands of vermilion torii gates.",
              approximate_time: "08:30 AM",
              location: "Fushimi Ward, Kyoto",
            },
          ],
        },
      ],
    },
  };

  it("renders 'Edit Itinerary' button when an itinerary is present", async () => {
    vi.mocked(tripsApi.getTrip).mockResolvedValue({ data: baseTripWithItinerary } as never);

    render(
      <MemoryRouter initialEntries={["/app/trips/900"]}>
        <Routes>
          <Route path="/app/trips/:tripId" element={<TripDetailsPage />} />
        </Routes>
      </MemoryRouter>
    );

    const editBtn = await screen.findByTestId("edit-itinerary-btn");
    expect(editBtn).toBeDefined();
    expect(editBtn.textContent).toContain("Edit Itinerary");
  });

  it("enters edit mode when 'Edit Itinerary' is clicked and renders form controls", async () => {
    vi.mocked(tripsApi.getTrip).mockResolvedValue({ data: baseTripWithItinerary } as never);

    render(
      <MemoryRouter initialEntries={["/app/trips/900"]}>
        <Routes>
          <Route path="/app/trips/:tripId" element={<TripDetailsPage />} />
        </Routes>
      </MemoryRouter>
    );

    const editBtn = await screen.findByTestId("edit-itinerary-btn");
    fireEvent.click(editBtn);

    expect(screen.getByTestId("edit-mode-badge")).toBeDefined();
    expect(screen.getByTestId("save-itinerary-btn")).toBeDefined();
    expect(screen.getByTestId("cancel-edit-itinerary-btn")).toBeDefined();
    expect(screen.getByTestId("edit-trip-summary")).toBeDefined();
    expect(screen.getByTestId("edit-day-date-0")).toBeDefined();
    expect(screen.getByTestId("edit-act-title-0-0")).toBeDefined();
    expect(screen.getByTestId("edit-act-desc-0-0")).toBeDefined();
    expect(screen.getByTestId("edit-act-time-0-0")).toBeDefined();
    expect(screen.getByTestId("edit-act-location-0-0")).toBeDefined();
  });

  it("allows editing summary, title, description, time, location and saves successfully", async () => {
    vi.mocked(tripsApi.getTrip).mockResolvedValue({ data: baseTripWithItinerary } as never);

    const updatedItineraryResponse = {
      trip_summary: "Updated Autumn in Kyoto Summary",
      days: [
        {
          date: "2026-10-15",
          activities: [
            {
              title: "Early Morning Torii Walk",
              description: "Hike up the mountain peak.",
              approximate_time: "07:00 AM",
              location: "Mount Inari",
            },
          ],
        },
      ],
    };
    vi.mocked(tripsApi.updateItinerary).mockResolvedValue({ data: updatedItineraryResponse } as never);

    render(
      <MemoryRouter initialEntries={["/app/trips/900"]}>
        <Routes>
          <Route path="/app/trips/:tripId" element={<TripDetailsPage />} />
        </Routes>
      </MemoryRouter>
    );

    const editBtn = await screen.findByTestId("edit-itinerary-btn");
    fireEvent.click(editBtn);

    // Edit summary
    const summaryInput = screen.getByTestId("edit-trip-summary");
    fireEvent.change(summaryInput, { target: { value: "Updated Autumn in Kyoto Summary" } });

    // Edit activity fields
    const titleInput = screen.getByTestId("edit-act-title-0-0");
    fireEvent.change(titleInput, { target: { value: "Early Morning Torii Walk" } });

    const descInput = screen.getByTestId("edit-act-desc-0-0");
    fireEvent.change(descInput, { target: { value: "Hike up the mountain peak." } });

    const timeInput = screen.getByTestId("edit-act-time-0-0");
    fireEvent.change(timeInput, { target: { value: "07:00 AM" } });

    const locInput = screen.getByTestId("edit-act-location-0-0");
    fireEvent.change(locInput, { target: { value: "Mount Inari" } });

    // Save
    const saveBtn = screen.getByTestId("save-itinerary-btn");
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(tripsApi.updateItinerary).toHaveBeenCalledWith(900, {
        trip_summary: "Updated Autumn in Kyoto Summary",
        days: [
          {
            date: "2026-10-15",
            activities: [
              {
                title: "Early Morning Torii Walk",
                description: "Hike up the mountain peak.",
                approximate_time: "07:00 AM",
                location: "Mount Inari",
              },
            ],
          },
        ],
      });
    });

    const successBanner = await screen.findByTestId("itinerary-save-success");
    expect(successBanner.textContent).toContain("Itinerary saved successfully!");
    expect(screen.queryByTestId("edit-mode-badge")).toBeNull();
  });

  it("supports adding and deleting activities and days", async () => {
    vi.mocked(tripsApi.getTrip).mockResolvedValue({ data: baseTripWithItinerary } as never);

    render(
      <MemoryRouter initialEntries={["/app/trips/900"]}>
        <Routes>
          <Route path="/app/trips/:tripId" element={<TripDetailsPage />} />
        </Routes>
      </MemoryRouter>
    );

    const editBtn = await screen.findByTestId("edit-itinerary-btn");
    fireEvent.click(editBtn);

    // Add activity to Day 1
    const addActBtn = screen.getByTestId("add-activity-btn-0");
    fireEvent.click(addActBtn);

    expect(screen.getByTestId("edit-act-card-0-1")).toBeDefined();

    // Add new Day
    const addDayBtn = screen.getByTestId("add-day-btn");
    fireEvent.click(addDayBtn);

    expect(screen.getByTestId("edit-day-card-1")).toBeDefined();

    // Delete added activity
    const deleteActBtn = screen.getByTestId("delete-act-btn-0-1");
    fireEvent.click(deleteActBtn);

    expect(screen.queryByTestId("edit-act-card-0-1")).toBeNull();

    // Delete Day 2
    const deleteDayBtn = screen.getByTestId("delete-day-btn-1");
    fireEvent.click(deleteDayBtn);

    expect(screen.queryByTestId("edit-day-card-1")).toBeNull();
  });

  it("cancel button discards unsaved changes and restores original itinerary view", async () => {
    vi.mocked(tripsApi.getTrip).mockResolvedValue({ data: baseTripWithItinerary } as never);

    render(
      <MemoryRouter initialEntries={["/app/trips/900"]}>
        <Routes>
          <Route path="/app/trips/:tripId" element={<TripDetailsPage />} />
        </Routes>
      </MemoryRouter>
    );

    const editBtn = await screen.findByTestId("edit-itinerary-btn");
    fireEvent.click(editBtn);

    // Modify summary
    const summaryInput = screen.getByTestId("edit-trip-summary");
    fireEvent.change(summaryInput, { target: { value: "Unsaved Temporary Edits" } });

    // Cancel
    const cancelBtn = screen.getByTestId("cancel-edit-itinerary-btn");
    fireEvent.click(cancelBtn);

    // Edit mode should close
    expect(screen.queryByTestId("edit-mode-badge")).toBeNull();
    expect(tripsApi.updateItinerary).not.toHaveBeenCalled();

    // Original summary should still be displayed
    expect(screen.getByText("Experiencing autumn leaves in ancient Kyoto.")).toBeDefined();
  });

  it("validates empty summary or invalid inputs before calling API", async () => {
    vi.mocked(tripsApi.getTrip).mockResolvedValue({ data: baseTripWithItinerary } as never);

    render(
      <MemoryRouter initialEntries={["/app/trips/900"]}>
        <Routes>
          <Route path="/app/trips/:tripId" element={<TripDetailsPage />} />
        </Routes>
      </MemoryRouter>
    );

    const editBtn = await screen.findByTestId("edit-itinerary-btn");
    fireEvent.click(editBtn);

    // Clear summary
    const summaryInput = screen.getByTestId("edit-trip-summary");
    fireEvent.change(summaryInput, { target: { value: "   " } });

    const saveBtn = screen.getByTestId("save-itinerary-btn");
    fireEvent.click(saveBtn);

    expect(tripsApi.updateItinerary).not.toHaveBeenCalled();
    const errorBanner = screen.getByTestId("itinerary-error-banner");
    expect(errorBanner.textContent).toContain("Trip summary cannot be empty.");
  });

  it("handles API failure when saving and displays error banner without losing edit state", async () => {
    vi.mocked(tripsApi.getTrip).mockResolvedValue({ data: baseTripWithItinerary } as never);
    vi.mocked(tripsApi.updateItinerary).mockRejectedValue({
      response: { data: { detail: "Database save failed." } },
    });

    render(
      <MemoryRouter initialEntries={["/app/trips/900"]}>
        <Routes>
          <Route path="/app/trips/:tripId" element={<TripDetailsPage />} />
        </Routes>
      </MemoryRouter>
    );

    const editBtn = await screen.findByTestId("edit-itinerary-btn");
    fireEvent.click(editBtn);

    const saveBtn = screen.getByTestId("save-itinerary-btn");
    fireEvent.click(saveBtn);

    const errorBanner = await screen.findByTestId("itinerary-error-banner");
    expect(errorBanner.textContent).toContain("Database save failed.");
    // Remains in edit mode
    expect(screen.getByTestId("edit-mode-badge")).toBeDefined();
  });
});
