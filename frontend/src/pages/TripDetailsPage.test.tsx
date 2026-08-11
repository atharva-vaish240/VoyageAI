// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import TripDetailsPage from "./TripDetailsPage";
import { tripsApi } from "../api/trips";
import { generateTripItineraryPdf } from "../utils/pdfGenerator";
import type { TripDetailResponse } from "../types/trip";

vi.mock("../api/trips", () => ({
  tripsApi: {
    getTrip: vi.fn(),
    generateItinerary: vi.fn(),
    deleteTrip: vi.fn(),
  },
}));

vi.mock("../utils/pdfGenerator", () => ({
  generateTripItineraryPdf: vi.fn(),
}));

describe("TripDetailsPage PDF Export", () => {
  beforeEach(() => {
    vi.clearAllMocks();
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

  it("renders 'Export as PDF' button when itinerary exists", async () => {
    vi.mocked(tripsApi.getTrip).mockResolvedValue({ data: tripWithItinerary } as never);

    render(
      <MemoryRouter initialEntries={["/app/trips/714"]}>
        <Routes>
          <Route path="/app/trips/:tripId" element={<TripDetailsPage />} />
        </Routes>
      </MemoryRouter>
    );

    const exportBtn = await screen.findByTestId("export-pdf-btn");
    expect(exportBtn).toBeDefined();
    expect(exportBtn.textContent).toContain("Export as PDF");
  });

  it("does NOT render 'Export as PDF' button when itinerary is null", async () => {
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
    expect(screen.getByText("No Itinerary Generated Yet")).toBeDefined();
  });

  it("triggers generateTripItineraryPdf when Export button is clicked", async () => {
    vi.mocked(tripsApi.getTrip).mockResolvedValue({ data: tripWithItinerary } as never);

    render(
      <MemoryRouter initialEntries={["/app/trips/714"]}>
        <Routes>
          <Route path="/app/trips/:tripId" element={<TripDetailsPage />} />
        </Routes>
      </MemoryRouter>
    );

    const exportBtn = await screen.findByTestId("export-pdf-btn");
    fireEvent.click(exportBtn);

    expect(generateTripItineraryPdf).toHaveBeenCalledWith(tripWithItinerary, tripWithItinerary.itinerary);
  });

  it("handles PDF generation failure gracefully without crashing page", async () => {
    vi.mocked(tripsApi.getTrip).mockResolvedValue({ data: tripWithItinerary } as never);
    vi.mocked(generateTripItineraryPdf).mockImplementation(() => {
      throw new Error("PDF layout failed");
    });

    render(
      <MemoryRouter initialEntries={["/app/trips/714"]}>
        <Routes>
          <Route path="/app/trips/:tripId" element={<TripDetailsPage />} />
        </Routes>
      </MemoryRouter>
    );

    const exportBtn = await screen.findByTestId("export-pdf-btn");
    fireEvent.click(exportBtn);

    const errorBanner = await screen.findByTestId("pdf-error-banner");
    expect(errorBanner.textContent).toContain("Unable to export itinerary. Please try again.");
    expect(screen.getByText("Grand Kashmir Expedition")).toBeDefined();
  });
});
