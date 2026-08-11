import api from "./client";
import type { RecommendationsResponse } from "../types/recommendation";

export const recommendationsApi = {
  getRecommendations: () =>
    api.post<RecommendationsResponse>("/recommendations"),
};
