import { useState, useEffect, type FormEvent } from "react";
import { preferencesApi } from "../api/preferences";
import type {
  PreferencesResponse,
  PreferencesUpdate,
  FoodPreference,
  DrinkingPreference,
  TravelStyle,
  TravelPace,
  AccommodationPreference,
} from "../types/preferences";
import "./PreferencesPage.css";

const FOOD_OPTIONS: { label: string; value: FoodPreference }[] = [
  { label: "No Preference", value: "no_preference" },
  { label: "Vegetarian", value: "vegetarian" },
  { label: "Non-Vegetarian", value: "non_vegetarian" },
  { label: "Vegan", value: "vegan" },
];

const DRINKING_OPTIONS: { label: string; value: DrinkingPreference }[] = [
  { label: "No Preference", value: "no_preference" },
  { label: "Drinker", value: "drinker" },
  { label: "Non-Drinker", value: "non_drinker" },
];

const STYLE_OPTIONS: { label: string; value: TravelStyle }[] = [
  { label: "Mixed", value: "mixed" },
  { label: "Adventure", value: "adventure" },
  { label: "Relaxed", value: "relaxed" },
  { label: "Cultural", value: "cultural" },
  { label: "Luxury", value: "luxury" },
  { label: "Budget", value: "budget" },
];

const PACE_OPTIONS: { label: string; value: TravelPace }[] = [
  { label: "Relaxed", value: "relaxed" },
  { label: "Moderate", value: "moderate" },
  { label: "Packed", value: "packed" },
];

const ACCOMMODATION_OPTIONS: { label: string; value: AccommodationPreference }[] = [
  { label: "No Preference", value: "no_preference" },
  { label: "Hotel", value: "hotel" },
  { label: "Hostel", value: "hostel" },
  { label: "Resort", value: "resort" },
  { label: "Homestay", value: "homestay" },
];

export default function PreferencesPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const [foodPreference, setFoodPreference] = useState<FoodPreference>("no_preference");
  const [drinkingPreference, setDrinkingPreference] = useState<DrinkingPreference>("no_preference");
  const [travelStyle, setTravelStyle] = useState<TravelStyle>("mixed");
  const [travelPace, setTravelPace] = useState<TravelPace>("moderate");
  const [accommodationPreference, setAccommodationPreference] = useState<AccommodationPreference>("no_preference");

  const [interests, setInterests] = useState<string[]>([]);
  const [interestInput, setInterestInput] = useState("");
  const [additionalPreferences, setAdditionalPreferences] = useState("");

  useEffect(() => {
    let isMounted = true;
    const fetchPrefs = async () => {
      try {
        setLoading(true);
        setError(null);
        const { data } = await preferencesApi.getPreferences();
        if (isMounted && data) {
          setFoodPreference(data.food_preference || "no_preference");
          setDrinkingPreference(data.drinking_preference || "no_preference");
          setTravelStyle(data.travel_style || "mixed");
          setTravelPace(data.travel_pace || "moderate");
          setAccommodationPreference(data.accommodation_preference || "no_preference");
          setInterests(data.interests || []);
          setAdditionalPreferences(data.additional_preferences || "");
        }
      } catch (err: unknown) {
        if (isMounted) {
          const message = err instanceof Error ? err.message : "Failed to load travel preferences.";
          setError(message);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchPrefs();

    return () => {
      isMounted = false;
    };
  }, []);

  const handleAddInterest = () => {
    const trimmed = interestInput.trim();
    if (trimmed && !interests.includes(trimmed)) {
      setInterests([...interests, trimmed]);
      setInterestInput("");
    }
  };

  const handleRemoveInterest = (target: string) => {
    setInterests(interests.filter((i) => i !== target));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccessMsg(null);

    const payload: PreferencesUpdate = {
      food_preference: foodPreference,
      drinking_preference: drinkingPreference,
      travel_style: travelStyle,
      travel_pace: travelPace,
      accommodation_preference: accommodationPreference,
      interests,
      additional_preferences: additionalPreferences.trim() || null,
    };

    try {
      const { data }: { data: PreferencesResponse } = await preferencesApi.updatePreferences(payload);
      setFoodPreference(data.food_preference);
      setDrinkingPreference(data.drinking_preference);
      setTravelStyle(data.travel_style);
      setTravelPace(data.travel_pace);
      setAccommodationPreference(data.accommodation_preference);
      setInterests(data.interests);
      setAdditionalPreferences(data.additional_preferences || "");

      setSuccessMsg("Travel preferences saved successfully!");
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const msg = axiosErr?.response?.data?.detail || "Failed to save preferences. Please try again.";
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="preferences-page-wrapper">
        <div className="pref-loading">
          <div className="spinner" />
          <p>Loading your travel preferences...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="preferences-page-wrapper">
      {/* Fixed Scenic Background Layer */}
      <div className="pref-scenic-bg-layer" aria-hidden="true">
        <img
          src="/voyageai-prefernces-background.png"
          alt=""
          className="pref-scenic-img"
        />
        <div className="pref-scenic-fade-overlay" />
      </div>

      <div className="preferences-container">
        {/* Left Hero Section */}
        <div className="pref-left-hero">
          <h1>Travel Preferences</h1>
          <p>
            Customize your travel style so VoyageAI can tailor personalized itineraries for you.
          </p>
        </div>

        {/* Right Form Card */}
        <div className="pref-right-card-wrapper">
          {error && (
            <div className="pref-alert pref-alert-error" role="alert">
              {error}
            </div>
          )}
          {successMsg && (
            <div className="pref-alert pref-alert-success" role="status">
              {successMsg}
            </div>
          )}

          <form className="pref-right-card" onSubmit={handleSubmit}>
            {/* Food Preference */}
            <div className="pref-field-group">
              <label htmlFor="food-pref" className="pref-field-label">
                Food Preference
              </label>
              <select
                id="food-pref"
                className="pref-field-select"
                value={foodPreference}
                onChange={(e) => setFoodPreference(e.target.value as FoodPreference)}
              >
                {FOOD_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Drinking Preference */}
            <div className="pref-field-group">
              <label htmlFor="drinking-pref" className="pref-field-label">
                Drinking Preference
              </label>
              <select
                id="drinking-pref"
                className="pref-field-select"
                value={drinkingPreference}
                onChange={(e) => setDrinkingPreference(e.target.value as DrinkingPreference)}
              >
                {DRINKING_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Travel Style */}
            <div className="pref-field-group">
              <label htmlFor="travel-style" className="pref-field-label">
                Travel Style
              </label>
              <select
                id="travel-style"
                className="pref-field-select"
                value={travelStyle}
                onChange={(e) => setTravelStyle(e.target.value as TravelStyle)}
              >
                {STYLE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Travel Pace */}
            <div className="pref-field-group">
              <label htmlFor="travel-pace" className="pref-field-label">
                Travel Pace
              </label>
              <select
                id="travel-pace"
                className="pref-field-select"
                value={travelPace}
                onChange={(e) => setTravelPace(e.target.value as TravelPace)}
              >
                {PACE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Accommodation Preference */}
            <div className="pref-field-group">
              <label htmlFor="accommodation-pref" className="pref-field-label">
                Accommodation Preference
              </label>
              <select
                id="accommodation-pref"
                className="pref-field-select"
                value={accommodationPreference}
                onChange={(e) =>
                  setAccommodationPreference(e.target.value as AccommodationPreference)
                }
              >
                {ACCOMMODATION_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Interests & Activities */}
            <div className="pref-field-group">
              <label htmlFor="interests-input" className="pref-field-label">
                Interests & Activities
              </label>
              <div className="pref-field-hint">Add hobbies, sights, or activities you enjoy</div>
              <div className="interests-pill-box">
                {interests.map((tag) => (
                  <span key={tag} className="interest-tag-pill">
                    {tag}
                    <button
                      type="button"
                      className="tag-remove-btn"
                      onClick={() => handleRemoveInterest(tag)}
                      aria-label={`Remove ${tag}`}
                    >
                      ×
                    </button>
                  </span>
                ))}
                <input
                  id="interests-input"
                  type="text"
                  className="interests-inline-input"
                  placeholder="Type and press Add"
                  value={interestInput}
                  onChange={(e) => setInterestInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleAddInterest();
                    }
                  }}
                />
              </div>
            </div>

            {/* Additional Notes */}
            <div className="pref-field-group">
              <label htmlFor="additional-pref" className="pref-field-label">
                Additional Notes / Requests
              </label>
              <textarea
                id="additional-pref"
                className="pref-field-textarea"
                rows={2}
                placeholder="Any allergies, mobility requirements, or specific travel notes..."
                value={additionalPreferences}
                onChange={(e) => setAdditionalPreferences(e.target.value)}
              />
            </div>

            {/* Submit Button */}
            <button type="submit" className="pref-save-btn" disabled={saving}>
              <span>💾</span>
              <span>{saving ? "Saving Preferences..." : "Save Preferences"}</span>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
