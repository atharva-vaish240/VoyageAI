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
    <div className="home-page">
      <div className="home-hero">
        <div className="hero-left">
          <h1 className="hero-title">
            Discover your
            <span className="hero-title-accent">next destination</span>
          </h1>

          <p className="hero-description">
            AI-powered recommendations tailored to your preferences and current season.
          </p>

          <button
            type="button"
            className="refresh-btn"
            onClick={handleRefresh}
            disabled={loading}
            aria-label="Refresh Recommendations"
          >
            <span>✨</span> {loading ? "Generating..." : "Refresh Recommendations"}
          </button>

          <div className="hero-value-props">
            <div className="value-prop-item">
              <div className="value-prop-icon">✨</div>
              <div className="value-prop-text">
                <h4>Smart Picks</h4>
                <p>Tailored for you</p>
              </div>
            </div>

            <div className="value-prop-item">
              <div className="value-prop-icon">🌐</div>
              <div className="value-prop-text">
                <h4>Unique Places</h4>
                <p>Handpicked gems</p>
              </div>
            </div>

            <div className="value-prop-item">
              <div className="value-prop-icon">💼</div>
              <div className="value-prop-text">
                <h4>Better Trips</h4>
                <p>Personalized experiences</p>
              </div>
            </div>
          </div>
        </div>

        <div className="hero-right">
          {error && (
            <div className="home-alert" role="alert">
              <span>{error}</span>
              <button type="button" onClick={fetchFreshRecommendations}>
                Retry
              </button>
            </div>
          )}

          {loading ? (
            <div className="cards-container" data-testid="recommendations-loading">
              <div className="skeleton-card">
                <div className="skeleton-image" />
                <div className="skeleton-title" />
                <div className="skeleton-text" />
                <div className="skeleton-btn" />
              </div>
              <div className="skeleton-card">
                <div className="skeleton-image" />
                <div className="skeleton-title" />
                <div className="skeleton-text" />
                <div className="skeleton-btn" />
              </div>
            </div>
          ) : recommendations ? (
            <>
              <div className="cards-container" data-testid="recommendations-grid">
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
                      <div className="card-image-wrapper">
                        {hasValidImage && pick.image && (
                          <>
                            <img
                              src={pick.image.url}
                              alt={pick.destination}
                              className="card-image"
                              onError={() => handleImageError(pick.image!.url)}
                              data-testid={`recommendation-image-${idx}`}
                            />
                            <div
                              className="card-image-attribution"
                              data-testid={`recommendation-attribution-${idx}`}
                            >
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
                          </>
                        )}
                        <div
                          className={`category-badge-floating ${getCategoryBadgeClass(
                            pick.category
                          )}`}
                        >
                          <span>{getCategoryIcon(pick.category)}</span> {pick.category}
                        </div>
                      </div>

                      <div className="card-body">
                        <div>
                          <h3 className="card-title">{pick.destination}</h3>
                          <div className="card-tagline">{pick.tagline}</div>
                          <p className="card-reason">{pick.reason}</p>
                        </div>

                        <button
                          type="button"
                          className="card-explore-btn"
                          onClick={() => handleSelectCard(pick)}
                        >
                          {isSelected
                            ? "✓ Selected"
                            : `Explore ${pick.destination.split(",")[0]} →`}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Pagination Dots */}
              <div className="hero-pagination-dots">
                <span className="dot active"></span>
                <span className="dot"></span>
                <span className="dot"></span>
              </div>
            </>
          ) : null}
        </div>
      </div>

      {selectedPick && (
        <ConversationalPlanner
          selectedPick={selectedPick}
          onResetSelection={() => setSelectedPick(null)}
        />
      )}
    </div>
  );
}
