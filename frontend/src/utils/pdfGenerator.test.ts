// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from "vitest";
import { sanitizeFilename, generateTripItineraryPdf } from "./pdfGenerator";
import type { TripDetailResponse } from "../types/trip";
import type { ItinerarySchema } from "../types/itinerary";

// Mock jsPDF
const mockSave = vi.fn();
const mockText = vi.fn();
const mockLine = vi.fn();
const mockRect = vi.fn();
const mockRoundedRect = vi.fn();
const mockAddPage = vi.fn();
const mockSetFont = vi.fn();
const mockSetFontSize = vi.fn();
const mockSetTextColor = vi.fn();
const mockSetFillColor = vi.fn();
const mockSetDrawColor = vi.fn();
const mockSplitTextToSize = vi.fn((text: string) => [text]);

vi.mock("jspdf", () => {
  class MockjsPDF {
    internal = {
      pageSize: {
        getWidth: () => 210,
        getHeight: () => 297,
      },
    };
    setFont = mockSetFont;
    setFontSize = mockSetFontSize;
    setTextColor = mockSetTextColor;
    setFillColor = mockSetFillColor;
    setDrawColor = mockSetDrawColor;
    text = mockText;
    line = mockLine;
    rect = mockRect;
    roundedRect = mockRoundedRect;
    addPage = mockAddPage;
    splitTextToSize = mockSplitTextToSize;
    save = mockSave;
  }
  return { jsPDF: MockjsPDF };
});

describe("PDF Generator Utility", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("sanitizeFilename", () => {
    it("sanitizes spaces and special characters", () => {
      expect(sanitizeFilename("Kashmir & Ladakh Trip!!")).toBe("Kashmir-Ladakh-Trip");
      expect(sanitizeFilename("Goa 2026/2027")).toBe("Goa-20262027");
      expect(sanitizeFilename("   Tokyo - Japan  ")).toBe("Tokyo-Japan");
    });

    it("returns default 'Trip' if string becomes empty", () => {
      expect(sanitizeFilename("!!! ### $$$")).toBe("Trip");
    });
  });

  describe("generateTripItineraryPdf", () => {
    const mockTrip: TripDetailResponse = {
      id: 1,
      user_id: 10,
      title: "Kashmir Adventure",
      destination: "Kashmir, India",
      start_date: "2026-09-01",
      end_date: "2026-09-05",
      status: "PLANNED",
      num_travellers: 2,
      budget: "$2,000",
      created_at: "2026-08-11T12:00:00Z",
      updated_at: "2026-08-11T12:00:00Z",
    };

    const mockItinerary: ItinerarySchema = {
      trip_summary: "A thrilling trip to Kashmir.",
      days: [
        {
          date: "2026-09-01",
          activities: [
            {
              title: "Arrive in Srinagar",
              description: "Check into houseboat and relax.",
              approximate_time: "Morning",
              location: "Dal Lake",
            },
          ],
        },
      ],
    };

    it("generates and saves PDF with sanitized filename", () => {
      generateTripItineraryPdf(mockTrip, mockItinerary);

      expect(mockSave).toHaveBeenCalledWith("VoyageAI-Kashmir-India-Itinerary.pdf");
      expect(mockText).toHaveBeenCalled();
    });

    it("handles missing optional trip metadata gracefully", () => {
      const minimalTrip: TripDetailResponse = {
        ...mockTrip,
        destination: null,
        num_travellers: null,
        budget: null,
      };

      generateTripItineraryPdf(minimalTrip, mockItinerary);

      expect(mockSave).toHaveBeenCalledWith("VoyageAI-Kashmir-Adventure-Itinerary.pdf");
      expect(mockText).toHaveBeenCalled();
    });
  });
});
