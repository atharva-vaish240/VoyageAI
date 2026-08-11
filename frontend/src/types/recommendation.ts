export interface RecommendationImage {
  url: string;
  photographer: string;
  photographer_url: string;
  pexels_url: string;
}

export interface RecommendationItem {
  category: string;
  destination: string;
  tagline: string;
  reason: string;
  highlights: string[];
  image_search_term?: string;
  image?: RecommendationImage | null;
}

export interface RecommendationsResponse {
  seasonal_pick: RecommendationItem;
  hidden_gem: RecommendationItem;
  experience_pick: RecommendationItem;
}
