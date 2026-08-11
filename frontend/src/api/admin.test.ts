// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from "vitest";
import api from "./client";
import { adminApi } from "./admin";

vi.mock("./client", () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

describe("Admin API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls GET /admin/trips to list all trips", async () => {
    const mockTrips = [
      {
        id: 1,
        user_id: 10,
        user: { id: 10, name: "Alice", email: "alice@example.com" },
        title: "Alice Trip",
        start_date: "2026-09-01",
        end_date: "2026-09-05",
        status: "PLANNED" as const,
        created_at: "2026-08-11T12:00:00Z",
        updated_at: "2026-08-11T12:00:00Z",
      },
    ];
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: mockTrips });

    const res = await adminApi.listAllTrips();

    expect(api.get).toHaveBeenCalledWith("/admin/trips");
    expect(res.data).toHaveLength(1);
    expect(res.data[0].user?.email).toBe("alice@example.com");
  });

  it("calls GET /admin/trips/{id}", async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { id: 1, title: "Alice Trip" } });

    await adminApi.getTrip(1);

    expect(api.get).toHaveBeenCalledWith("/admin/trips/1");
  });

  it("calls PATCH /admin/trips/{id}", async () => {
    const update = { title: "Updated Title By Admin" };
    (api.patch as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { id: 1, title: "Updated Title By Admin" } });

    await adminApi.updateTrip(1, update);

    expect(api.patch).toHaveBeenCalledWith("/admin/trips/1", update);
  });

  it("calls DELETE /admin/trips/{id}", async () => {
    (api.delete as ReturnType<typeof vi.fn>).mockResolvedValue({ data: undefined });

    await adminApi.deleteTrip(1);

    expect(api.delete).toHaveBeenCalledWith("/admin/trips/1");
  });
});
