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
      <div className="page-container preferences-page">
        <div className="pref-loading">
          <div className="spinner" />
          <p>Loading your travel preferences...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container preferences-page">
      <div className="pref-header">
        <h1>Travel Preferences</h1>
        <p>Customize your travel style so VoyageAI can tailor personalized itineraries for you.</p>
      </div>

      {error && <div className="pref-alert pref-alert-error" role="alert">{error}</div>}
      {successMsg && <div className="pref-alert pref-alert-success" role="status">{successMsg}</div>}

      <form className="pref-form" onSubmit={handleSubmit}>
        {/* Food Preference */}
        <div className="pref-group">
          <label htmlFor="food-pref" className="pref-label">Food Preference</label>
          <select
            id="food-pref"
            className="pref-select"
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
        <div className="pref-group">
          <label htmlFor="drinking-pref" className="pref-label">Drinking Preference</label>
          <select
            id="drinking-pref"
            className="pref-select"
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
        <div className="pref-group">
          <label htmlFor="travel-style" className="pref-label">Travel Style</label>
          <select
            id="travel-style"
            className="pref-select"
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
        <div className="pref-group">
          <label htmlFor="travel-pace" className="pref-label">Travel Pace</label>
          <select
            id="travel-pace"
            className="pref-select"
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
        <div className="pref-group">
          <label htmlFor="accommodation-pref" className="pref-label">Accommodation Preference</label>
          <select
            id="accommodation-pref"
            className="pref-select"
            value={accommodationPreference}
            onChange={(e) => setAccommodationPreference(e.target.value as AccommodationPreference)}
          >
            {ACCOMMODATION_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Interests */}
        <div className="pref-group">
          <label htmlFor="interests-input" className="pref-label">Interests & Activities</label>
          <p className="pref-hint">Add hobbies, sights, or activities you enjoy (e.g. beaches, hiking, museums).</p>
          <div className="interests-input-wrapper">
            <input
              id="interests-input"
              type="text"
              className="pref-input"
              placeholder="Type an interest and press Add"
              value={interestInput}
              onChange={(e) => setInterestInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleAddInterest();
                }
              }}
            />
            <button
              type="button"
              className="pref-btn pref-btn-secondary"
              onClick={handleAddInterest}
            >
              Add
            </button>
          </div>
          {interests.length > 0 && (
            <div className="interests-tags">
              {interests.map((tag) => (
                <span key={tag} className="interest-tag">
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
            </div>
          )}
        </div>

        {/* Additional Preferences */}
        <div className="pref-group">
          <label htmlFor="additional-pref" className="pref-label">Additional Notes / Requests</label>
          <textarea
            id="additional-pref"
            className="pref-textarea"
            rows={3}
            placeholder="Any allergies, mobility requirements, or specific travel notes..."
            value={additionalPreferences}
            onChange={(e) => setAdditionalPreferences(e.target.value)}
          />
        </div>

        {/* Actions */}
        <div className="pref-actions">
          <button
            type="submit"
            className="pref-btn pref-btn-primary"
            disabled={saving}
          >
            {saving ? "Saving Preferences..." : "Save Preferences"}
          </button>
        </div>
      </form>
    </div>
  );
}
