// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from "vitest";
import api from "./client";
import { preferencesApi } from "./preferences";

vi.mock("./client", () => ({
  default: {
    get: vi.fn(),
    put: vi.fn(),
  },
}));

describe("Preferences API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls GET /preferences", async () => {
    const mockData = {
      id: 1,
      user_id: 10,
      food_preference: "vegetarian",
      drinking_preference: "non_drinker",
      travel_style: "cultural",
      travel_pace: "moderate",
      accommodation_preference: "hotel",
      interests: ["museums", "history"],
      additional_preferences: "Quiet room",
      created_at: "2026-08-11T00:00:00Z",
      updated_at: "2026-08-11T00:00:00Z",
    };
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: mockData });

    const res = await preferencesApi.getPreferences();

    expect(api.get).toHaveBeenCalledWith("/preferences");
    expect(res.data).toEqual(mockData);
  });

  it("calls PUT /preferences with payload", async () => {
    const payload = {
      food_preference: "vegan" as const,
      drinking_preference: "no_preference" as const,
      travel_style: "adventure" as const,
      travel_pace: "packed" as const,
      accommodation_preference: "hostel" as const,
      interests: ["hiking"],
      additional_preferences: null,
    };
    (api.put as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { ...payload, id: 1, user_id: 10 } });

    const res = await preferencesApi.updatePreferences(payload);

    expect(api.put).toHaveBeenCalledWith("/preferences", payload);
    expect(res.data.food_preference).toBe("vegan");
  });
});
