// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from "vitest";
import api from "./client";
import { tripsApi } from "./trips";

vi.mock("./client", () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

describe("Trips API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls POST /trips to create trip", async () => {
    const payload = {
      title: "Japan Expedition",
      destination: "Kyoto",
      start_date: "2026-10-01",
      end_date: "2026-10-10",
      status: "DRAFT" as const,
    };
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { id: 42, ...payload } });

    const res = await tripsApi.createTrip(payload);

    expect(api.post).toHaveBeenCalledWith("/trips", payload);
    expect(res.data.id).toBe(42);
  });

  it("calls GET /trips with status filter", async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: [] });

    await tripsApi.listTrips("upcoming");

    expect(api.get).toHaveBeenCalledWith("/trips", { params: { status: "upcoming" } });
  });

  it("calls GET /trips/{id}", async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { id: 42 } });

    await tripsApi.getTrip(42);

    expect(api.get).toHaveBeenCalledWith("/trips/42");
  });

  it("calls PATCH /trips/{id}", async () => {
    const update = { title: "Updated Title" };
    (api.patch as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { id: 42, title: "Updated Title" } });

    await tripsApi.updateTrip(42, update);

    expect(api.patch).toHaveBeenCalledWith("/trips/42", update);
  });

  it("calls DELETE /trips/{id}", async () => {
    (api.delete as ReturnType<typeof vi.fn>).mockResolvedValue({ data: undefined });

    await tripsApi.deleteTrip(42);

    expect(api.delete).toHaveBeenCalledWith("/trips/42");
  });

  it("calls POST /trips/{id}/generate-itinerary", async () => {
    const mockItinerary = {
      trip_summary: "Great trip",
      days: [],
    };
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({ data: mockItinerary });

    const res = await tripsApi.generateItinerary(42);

    expect(api.post).toHaveBeenCalledWith("/trips/42/generate-itinerary");
    expect(res.data).toEqual(mockItinerary);
  });
});
