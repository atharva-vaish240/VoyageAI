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

const mockRecommendationsWithImages: RecommendationsResponse = {
  seasonal_pick: {
    category: "Seasonal Pick",
    destination: "Kashmir",
    tagline: "Scenic valley",
    reason: "Autumn colors",
    highlights: ["Dal Lake", "Gulmarg"],
    image_search_term: "Dal Lake Kashmir",
    image: {
      url: "https://images.pexels.com/photos/123/large.jpg",
      photographer: "John Doe",
      photographer_url: "https://www.pexels.com/@johndoe",
      pexels_url: "https://www.pexels.com/photo/123",
    },
  },
  hidden_gem: {
    category: "Hidden Gem",
    destination: "Tirthan Valley",
    tagline: "Quiet river",
    reason: "Offbeat alpine escape",
    highlights: ["Jibhi Waterfalls"],
    image_search_term: "Tirthan Valley river",
    image: null,
  },
  experience_pick: {
    category: "Experience Pick",
    destination: "Rishikesh",
    tagline: "Rafting & yoga",
    reason: "Adventure & spirituality",
    highlights: ["Rafting", "Beatles Ashram"],
    image_search_term: "Rishikesh Ganges river",
    image: {
      url: "https://images.pexels.com/photos/456/large.jpg",
      photographer: "Jane Smith",
      photographer_url: "https://www.pexels.com/@janesmith",
      pexels_url: "https://www.pexels.com/photo/456",
    },
  },
};

describe("Recommendations API & Session Cache with Images", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  it("calls POST /recommendations to fetch 3 picks enriched with images", async () => {
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({ data: mockRecommendationsWithImages });

    const res = await recommendationsApi.getRecommendations();

    expect(api.post).toHaveBeenCalledWith("/recommendations");
    expect(res.data.seasonal_pick.image?.url).toBe("https://images.pexels.com/photos/123/large.jpg");
    expect(res.data.hidden_gem.image).toBeNull();
  });

  it("sessionStorage cache stores and retrieves recommendation images", () => {
    const userId = 101;
    setCachedRecommendations(userId, mockRecommendationsWithImages);

    const cached = getCachedRecommendations(userId);
    expect(cached).not.toBeNull();
    expect(cached?.seasonal_pick.image?.photographer).toBe("John Doe");
    expect(cached?.hidden_gem.image).toBeNull();
  });

  it("sessionStorage cache returns null if user ID does not match (user isolation)", () => {
    const userIdA = 101;
    const userIdB = 202;
    setCachedRecommendations(userIdA, mockRecommendationsWithImages);

    const cachedForB = getCachedRecommendations(userIdB);
    expect(cachedForB).toBeNull();
  });

  it("sessionStorage cache returns null if expired", () => {
    const userId = 101;
    const pastTimestamp = Date.now() - (5 * 60 * 60 * 1000); // 5 hours ago (TTL is 4 hrs)
    sessionStorage.setItem(
      "voyageai_recommendations_cache",
      JSON.stringify({ userId, timestamp: pastTimestamp, data: mockRecommendationsWithImages })
    );

    const cached = getCachedRecommendations(userId);
    expect(cached).toBeNull();
  });

  it("clearRecommendationsCache removes cached item", () => {
    const userId = 101;
    setCachedRecommendations(userId, mockRecommendationsWithImages);
    clearRecommendationsCache();

    const cached = getCachedRecommendations(userId);
    expect(cached).toBeNull();
  });
});
