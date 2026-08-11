export type FoodPreference =
  | "vegetarian"
  | "non_vegetarian"
  | "vegan"
  | "no_preference";

export type DrinkingPreference =
  | "drinker"
  | "non_drinker"
  | "no_preference";

export type TravelStyle =
  | "adventure"
  | "relaxed"
  | "cultural"
  | "luxury"
  | "budget"
  | "mixed";

export type TravelPace =
  | "relaxed"
  | "moderate"
  | "packed";

export type AccommodationPreference =
  | "hotel"
  | "hostel"
  | "resort"
  | "homestay"
  | "no_preference";

export interface PreferencesUpdate {
  food_preference?: FoodPreference;
  drinking_preference?: DrinkingPreference;
  travel_style?: TravelStyle;
  travel_pace?: TravelPace;
  accommodation_preference?: AccommodationPreference;
  interests?: string[];
  additional_preferences?: string | null;
}

export interface PreferencesResponse {
  id: number;
  user_id: number;
  food_preference: FoodPreference;
  drinking_preference: DrinkingPreference;
  travel_style: TravelStyle;
  travel_pace: TravelPace;
  accommodation_preference: AccommodationPreference;
  interests: string[];
  additional_preferences: string | null;
  created_at: string;
  updated_at: string;
}
