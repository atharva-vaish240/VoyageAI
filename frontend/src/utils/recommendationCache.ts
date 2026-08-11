import type { RecommendationsResponse } from "../types/recommendation";

const CACHE_KEY = "voyageai_recommendations_cache";
const CACHE_TTL_MS = 4 * 60 * 60 * 1000; // 4 hours

interface CachedData {
  userId: number;
  timestamp: number;
  data: RecommendationsResponse;
}

export function getCachedRecommendations(userId: number): RecommendationsResponse | null {
  try {
    const raw = sessionStorage.getItem(CACHE_KEY);
    if (!raw) return null;

    const cached: CachedData = JSON.parse(raw);
    if (cached.userId !== userId) return null;

    if (Date.now() - cached.timestamp > CACHE_TTL_MS) {
      sessionStorage.removeItem(CACHE_KEY);
      return null;
    }

    return cached.data;
  } catch {
    return null;
  }
}

export function setCachedRecommendations(userId: number, data: RecommendationsResponse): void {
  try {
    const payload: CachedData = {
      userId,
      timestamp: Date.now(),
      data,
    };
    sessionStorage.setItem(CACHE_KEY, JSON.stringify(payload));
  } catch {
    // SessionStorage may fail or be restricted
  }
}

export function clearRecommendationsCache(): void {
  try {
    sessionStorage.removeItem(CACHE_KEY);
  } catch {
    // Ignore
  }
}
