// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from "vitest";
import api from "./client";
import { recommendationsApi } from "./recommendations";
import {
  getCachedRecommendations,
  setCachedRecommendations,
  clearRecommendationsCache,
} from "../utils/recommendationCache";
import type { RecommendationsResponse } from "../types/recommendation";

vi.mock("./client", () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

const mockRecommendations: RecommendationsResponse = {
  seasonal_pick: {
    category: "Seasonal Pick",
    destination: "Kashmir",
    tagline: "Scenic valley",
    reason: "Autumn colors",
    highlights: ["Dal Lake", "Gulmarg"],
  },
  hidden_gem: {
    category: "Hidden Gem",
    destination: "Tirthan Valley",
    tagline: "Quiet river",
    reason: "Offbeat alpine escape",
    highlights: ["Jibhi Waterfalls"],
  },
  experience_pick: {
    category: "Experience Pick",
    destination: "Rishikesh",
    tagline: "Rafting & yoga",
    reason: "Adventure & spirituality",
    highlights: ["Rafting", "Beatles Ashram"],
  },
};

describe("Recommendations API & Session Cache", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  it("calls POST /recommendations to fetch 3 picks", async () => {
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({ data: mockRecommendations });

    const res = await recommendationsApi.getRecommendations();

    expect(api.post).toHaveBeenCalledWith("/recommendations");
    expect(res.data.seasonal_pick.destination).toBe("Kashmir");
  });

  it("sessionStorage cache stores and retrieves data for current user", () => {
    const userId = 101;
    setCachedRecommendations(userId, mockRecommendations);

    const cached = getCachedRecommendations(userId);
    expect(cached).not.toBeNull();
    expect(cached?.seasonal_pick.destination).toBe("Kashmir");
  });

  it("sessionStorage cache returns null if user ID does not match (user isolation)", () => {
    const userIdA = 101;
    const userIdB = 202;
    setCachedRecommendations(userIdA, mockRecommendations);

    const cachedForB = getCachedRecommendations(userIdB);
    expect(cachedForB).toBeNull();
  });

  it("sessionStorage cache returns null if expired", () => {
    const userId = 101;
    const pastTimestamp = Date.now() - (5 * 60 * 60 * 1000); // 5 hours ago (TTL is 4 hrs)
    sessionStorage.setItem(
      "voyageai_recommendations_cache",
      JSON.stringify({ userId, timestamp: pastTimestamp, data: mockRecommendations })
    );

    const cached = getCachedRecommendations(userId);
    expect(cached).toBeNull();
  });

  it("clearRecommendationsCache removes cached item", () => {
    const userId = 101;
    setCachedRecommendations(userId, mockRecommendations);
    clearRecommendationsCache();

    const cached = getCachedRecommendations(userId);
    expect(cached).toBeNull();
  });
});
