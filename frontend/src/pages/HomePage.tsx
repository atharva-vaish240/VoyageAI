import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../hooks/useAuth";
import { recommendationsApi } from "../api/recommendations";
import {
  getCachedRecommendations,
  setCachedRecommendations,
  clearRecommendationsCache,
} from "../utils/recommendationCache";
import type { RecommendationsResponse, RecommendationItem } from "../types/recommendation";
import ConversationalPlanner from "../components/planner/ConversationalPlanner";
import "./HomePage.css";

export default function HomePage() {
  const { user } = useAuth();
  const userId = user?.id;

  const [recommendations, setRecommendations] = useState<RecommendationsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPick, setSelectedPick] = useState<RecommendationItem | null>(null);
  const [failedImageUrls, setFailedImageUrls] = useState<Record<string, boolean>>({});

  const fetchFreshRecommendations = useCallback(async () => {
    if (!userId) return;
    setLoading(true);
    setError(null);
    setFailedImageUrls({});

    try {
      const { data } = await recommendationsApi.getRecommendations();
      setRecommendations(data);
      setCachedRecommendations(userId, data);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const msg =
        axiosErr?.response?.data?.detail ||
        "Failed to load AI destination recommendations. Please try again.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    let isMounted = true;

    const initPage = async () => {
      if (!userId) return;

      const cached = getCachedRecommendations(userId);
      if (cached) {
        if (isMounted) {
          setRecommendations(cached);
          setLoading(false);
        }
        return;
      }

      try {
        if (isMounted) {
          setLoading(true);
          setError(null);
        }
        const { data } = await recommendationsApi.getRecommendations();
        if (isMounted) {
          setRecommendations(data);
          setCachedRecommendations(userId, data);
        }
      } catch (err: unknown) {
        if (isMounted) {
          const axiosErr = err as { response?: { data?: { detail?: string } } };
          const msg =
            axiosErr?.response?.data?.detail ||
            "Failed to load AI destination recommendations. Please try again.";
          setError(msg);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    initPage();

    return () => {
      isMounted = false;
    };
  }, [userId]);

  const handleRefresh = () => {
    clearRecommendationsCache();
    setSelectedPick(null);
    fetchFreshRecommendations();
  };

  const handleSelectCard = (pick: RecommendationItem) => {
    if (selectedPick?.destination === pick.destination) {
      setSelectedPick(null);
    } else {
      setSelectedPick(pick);
    }
  };

  const handleImageError = (url: string) => {
    setFailedImageUrls((prev) => ({ ...prev, [url]: true }));
  };

  const getCategoryBadgeClass = (category: string) => {
    const catLower = category.toLowerCase();
    if (catLower.includes("seasonal")) return "badge-seasonal";
    if (catLower.includes("gem")) return "badge-gem";
    return "badge-experience";
  };

  const getCategoryIcon = (category: string) => {
    const catLower = category.toLowerCase();
    if (catLower.includes("seasonal")) return "🍂";
    if (catLower.includes("gem")) return "💎";
    return "🌟";
  };

  return (
    <div className="page-container home-page">
      <div className="home-header">
        <div className="home-header-title">
          <h1>Discover Your Next Destination, {user?.name || "Traveler"} 👋</h1>
          <p>Hand-picked AI recommendations tailored to your preferences & current season.</p>
        </div>

        <button
          type="button"
          className="refresh-btn"
          onClick={handleRefresh}
          disabled={loading}
          aria-label="Refresh Recommendations"
        >
          🔄 {loading ? "Generating..." : "Refresh Recommendations"}
        </button>
      </div>

      {error && (
        <div className="home-alert" role="alert">
          <span>{error}</span>
          <button type="button" onClick={fetchFreshRecommendations}>
            Retry
          </button>
        </div>
      )}

      {loading ? (
        <div className="recommendations-grid" data-testid="recommendations-loading">
          <div className="skeleton-card">
            <div className="skeleton-image" />
            <div className="skeleton-badge" />
            <div className="skeleton-title" />
            <div className="skeleton-text" />
            <div className="skeleton-btn" />
          </div>
          <div className="skeleton-card">
            <div className="skeleton-image" />
            <div className="skeleton-badge" />
            <div className="skeleton-title" />
            <div className="skeleton-text" />
            <div className="skeleton-btn" />
          </div>
          <div className="skeleton-card">
            <div className="skeleton-image" />
            <div className="skeleton-badge" />
            <div className="skeleton-title" />
            <div className="skeleton-text" />
            <div className="skeleton-btn" />
          </div>
        </div>
      ) : recommendations ? (
        <div className="recommendations-grid" data-testid="recommendations-grid">
          {[
            recommendations.seasonal_pick,
            recommendations.hidden_gem,
            recommendations.experience_pick,
          ].map((pick, idx) => {
            const isSelected = selectedPick?.destination === pick.destination;
            const imageUrl = pick.image?.url;
            const hasValidImage = imageUrl && !failedImageUrls[imageUrl];

            return (
              <div
                key={idx}
                className={`recommendation-card ${isSelected ? "card-selected" : ""}`}
                data-testid={`recommendation-card-${idx}`}
              >
                {hasValidImage && pick.image && (
                  <div className="card-image-wrapper">
                    <img
                      src={pick.image.url}
                      alt={pick.destination}
                      className="card-image"
                      onError={() => handleImageError(pick.image!.url)}
                      data-testid={`recommendation-image-${idx}`}
                    />
                    <div className="card-image-attribution" data-testid={`recommendation-attribution-${idx}`}>
                      Photo by{" "}
                      <a
                        href={pick.image.photographer_url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {pick.image.photographer}
                      </a>{" "}
                      on{" "}
                      <a
                        href={pick.image.pexels_url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Pexels
                      </a>
                    </div>
                  </div>
                )}

                <div className="card-body">
                  <div className="card-content">
                    <div className={`category-badge ${getCategoryBadgeClass(pick.category)}`}>
                      <span>{getCategoryIcon(pick.category)}</span> {pick.category}
                    </div>

                    <h3>{pick.destination}</h3>
                    <div className="card-tagline">{pick.tagline}</div>
                    <p className="card-reason">{pick.reason}</p>

                    <div className="highlights-section">
                      <div className="highlights-title">Top Highlights</div>
                      <div className="highlights-tags">
                        {pick.highlights.map((tag, tagIdx) => (
                          <span key={tagIdx} className="highlight-tag">
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  <button
                    type="button"
                    className="card-action-btn"
                    onClick={() => handleSelectCard(pick)}
                  >
                    {isSelected ? "✓ Destination Selected" : `Explore ${pick.destination}`}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      ) : null}

      {selectedPick && (
        <ConversationalPlanner
          selectedPick={selectedPick}
          onResetSelection={() => setSelectedPick(null)}
        />
      )}
    </div>
  );
}
