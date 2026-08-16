import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { tripsApi } from "../api/trips";
import type { TripResponse, TripStatusFilter } from "../types/trip";
import CreateTripModal from "../components/trips/CreateTripModal";
import TiltedCard from "../components/ui/TiltedCard";
import "./TripsPage.css";

export default function TripsPage() {
  const navigate = useNavigate();
  const [filter, setFilter] = useState<TripStatusFilter>("all");
  const [trips, setTrips] = useState<TripResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [failedImageUrls, setFailedImageUrls] = useState<Record<string, boolean>>({});

  const [isCreateOpen, setIsCreateOpen] = useState(false);

  const fetchTrips = useCallback(async (currentFilter: TripStatusFilter) => {
    try {
      setLoading(true);
      setError(null);
      const { data } = await tripsApi.listTrips(currentFilter);
      setTrips(data);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const msg = axiosErr?.response?.data?.detail || "Failed to load trips. Please try again.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;
    const loadTrips = async () => {
      try {
        setLoading(true);
        setError(null);
        const { data } = await tripsApi.listTrips(filter);
        if (isMounted) {
          setTrips(data);
        }
      } catch (err: unknown) {
        if (isMounted) {
          const axiosErr = err as { response?: { data?: { detail?: string } } };
          const msg = axiosErr?.response?.data?.detail || "Failed to load trips. Please try again.";
          setError(msg);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    loadTrips();

    return () => {
      isMounted = false;
    };
  }, [filter]);

  const handleImageError = (url: string) => {
    setFailedImageUrls((prev) => ({ ...prev, [url]: true }));
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "COMPLETED":
        return <span className="status-badge status-completed">Completed</span>;
      case "PLANNED":
        return <span className="status-badge status-planned">Planned</span>;
      default:
        return <span className="status-badge status-draft">Draft</span>;
    }
  };

  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="page-container trips-page">
      <div className="trips-header">
        <div>
          <h1>My Trips</h1>
          <p>Plan, organize, and view your upcoming and past travel adventures.</p>
        </div>
        <button
          type="button"
          className="btn-primary create-trip-btn"
          onClick={() => setIsCreateOpen(true)}
        >
          + Create New Trip
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="trips-filter-bar">
        <div className="trips-tabs">
          <button
            type="button"
            className={`tab-btn ${filter === "all" ? "active" : ""}`}
            onClick={() => setFilter("all")}
          >
            All Trips
          </button>
          <button
            type="button"
            className={`tab-btn ${filter === "upcoming" ? "active" : ""}`}
            onClick={() => setFilter("upcoming")}
          >
            Upcoming
          </button>
          <button
            type="button"
            className={`tab-btn ${filter === "past" ? "active" : ""}`}
            onClick={() => setFilter("past")}
          >
            Past
          </button>
        </div>

        <button
          type="button"
          className="refresh-btn"
          onClick={() => fetchTrips(filter)}
          disabled={loading}
          title="Refresh trips"
        >
          ↻ Refresh
        </button>
      </div>

      {/* Content States */}
      {loading ? (
        <div className="trips-loading">
          <div className="spinner" />
          <p>Loading your trips...</p>
        </div>
      ) : error ? (
        <div className="trips-alert trips-alert-error">
          <p>{error}</p>
          <button
            type="button"
            className="retry-btn"
            onClick={() => fetchTrips(filter)}
          >
            Retry
          </button>
        </div>
      ) : trips.length === 0 ? (
        <div className="trips-empty">
          <div className="empty-icon">✈️</div>
          <h3>No trips found</h3>
          <p>
            {filter === "all"
              ? "You haven't created any trips yet. Click below to start planning!"
              : `No ${filter} trips found.`}
          </p>
          <button
            type="button"
            className="btn-primary"
            onClick={() => setIsCreateOpen(true)}
          >
            Create Your First Trip
          </button>
        </div>
      ) : (
        <div className="trips-grid">
          {trips.map((trip) => {
            const destImg = trip.destination_image;
            const imageUrl = destImg?.url;
            const hasValidImage = imageUrl && !failedImageUrls[imageUrl];

            return (
              <TiltedCard
                key={trip.id}
                captionText={trip.destination || trip.title}
                rotateAmplitude={12}
                scaleOnHover={1.04}
                showMobileWarning={false}
                showTooltip={true}
                onClick={() => navigate(`/app/trips/${trip.id}`)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    navigate(`/app/trips/${trip.id}`);
                  }
                }}
                testId={`trip-card-${trip.id}`}
              >
                <div className="trip-card">
                  {hasValidImage && destImg && (
                    <div className="trip-card-image-wrapper">
                      <img
                        src={destImg.url}
                        alt={trip.destination || trip.title}
                        className="trip-card-image"
                        onError={() => handleImageError(destImg.url)}
                        data-testid={`trip-image-${trip.id}`}
                      />
                      <div
                        className="trip-card-image-attribution"
                        onClick={(e) => e.stopPropagation()}
                        data-testid={`trip-attribution-${trip.id}`}
                      >
                        Photo by{" "}
                        <a
                          href={destImg.photographer_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {destImg.photographer}
                        </a>{" "}
                        on{" "}
                        <a
                          href={destImg.pexels_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                        >
                          Pexels
                        </a>
                      </div>
                    </div>
                  )}

                  <div className="trip-card-body">
                    <div className="trip-card-header">
                      <h3 className="trip-card-title">{trip.title}</h3>
                      {getStatusBadge(trip.status)}
                    </div>

                    {trip.destination && (
                      <div className="trip-card-destination">
                        📍 {trip.destination}
                      </div>
                    )}

                    <div className="trip-card-dates">
                      📅 {formatDate(trip.start_date)} — {formatDate(trip.end_date)}
                    </div>

                    <div className="trip-card-footer">
                      <span className="view-details-link">View Details →</span>
                    </div>
                  </div>
                </div>
              </TiltedCard>
            );
          })}
        </div>
      )}

      {/* Create Trip Modal */}
      <CreateTripModal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        onTripCreated={() => fetchTrips(filter)}
      />
    </div>
  );
}
