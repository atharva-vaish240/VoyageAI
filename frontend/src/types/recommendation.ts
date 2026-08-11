export interface RecommendationItem {
  category: string;
  destination: string;
  tagline: string;
  reason: string;
  highlights: string[];
}

export interface RecommendationsResponse {
  seasonal_pick: RecommendationItem;
  hidden_gem: RecommendationItem;
  experience_pick: RecommendationItem;
}
