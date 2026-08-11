import { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { tripsApi } from "../api/trips";
import type { TripResponse } from "../types/trip";
import type { ItinerarySchema } from "../types/itinerary";
import EditTripModal from "../components/trips/EditTripModal";
import "./TripDetailsPage.css";

export default function TripDetailsPage() {
  const { tripId } = useParams<{ tripId: string }>();
  const navigate = useNavigate();

  const numericTripId = tripId ? parseInt(tripId, 10) : NaN;

  const [trip, setTrip] = useState<TripResponse | null>(null);
  const [itinerary, setItinerary] = useState<ItinerarySchema | null>(null);

  const [loadingTrip, setLoadingTrip] = useState(true);
  const [tripError, setTripError] = useState<string | null>(null);

  const [generatingItinerary, setGeneratingItinerary] = useState(false);
  const [itineraryError, setItineraryError] = useState<string | null>(null);

  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const fetchTripDetails = async () => {
      if (isNaN(numericTripId)) {
        if (isMounted) {
          setTripError("Invalid trip ID.");
          setLoadingTrip(false);
        }
        return;
      }

      try {
        setLoadingTrip(true);
        setTripError(null);
        const { data } = await tripsApi.getTrip(numericTripId);
        if (isMounted) {
          setTrip(data);
        }
      } catch (err: unknown) {
        if (isMounted) {
          const axiosErr = err as { response?: { status?: number; data?: { detail?: string } } };
          if (axiosErr?.response?.status === 404) {
            setTripError("Trip not found or you do not have permission to access it.");
          } else {
            const msg = axiosErr?.response?.data?.detail || "Failed to load trip details.";
            setTripError(msg);
          }
        }
      } finally {
        if (isMounted) {
          setLoadingTrip(false);
        }
      }
    };

    fetchTripDetails();

    return () => {
      isMounted = false;
    };
  }, [numericTripId]);

  const handleGenerateItinerary = async () => {
    if (!trip) return;

    if (!trip.destination) {
      setItineraryError("Please set a trip destination before generating an itinerary.");
      return;
    }

    setGeneratingItinerary(true);
    setItineraryError(null);

    try {
      const { data } = await tripsApi.generateItinerary(trip.id);
      setItinerary(data);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const msg =
        axiosErr?.response?.data?.detail ||
        "Failed to generate AI itinerary. Please try again later.";
      setItineraryError(msg);
    } finally {
      setGeneratingItinerary(false);
    }
  };

  const handleDeleteTrip = async () => {
    if (!trip) return;
    setDeleting(true);
    try {
      await tripsApi.deleteTrip(trip.id);
      navigate("/app/trips");
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const msg = axiosErr?.response?.data?.detail || "Failed to delete trip.";
      setTripError(msg);
      setIsDeleteConfirmOpen(false);
    } finally {
      setDeleting(false);
    }
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
        weekday: "short",
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    } catch {
      return dateStr;
    }
  };

  if (loadingTrip) {
    return (
      <div className="page-container trip-details-page">
        <div className="trip-loading">
          <div className="spinner" />
          <p>Loading trip details...</p>
        </div>
      </div>
    );
  }

  if (tripError || !trip) {
    return (
      <div className="page-container trip-details-page">
        <div className="back-nav">
          <Link to="/app/trips" className="back-link">
            ← Back to My Trips
          </Link>
        </div>
        <div className="trip-alert trip-alert-error">
          <p>{tripError || "Trip not found."}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container trip-details-page">
      <div className="back-nav">
        <Link to="/app/trips" className="back-link">
          ← Back to My Trips
        </Link>
      </div>

      {/* Main Header / Banner */}
      <div className="trip-details-header">
        <div className="trip-header-main">
          <div className="trip-header-title-row">
            <h1>{trip.title}</h1>
            {getStatusBadge(trip.status)}
          </div>

          <div className="trip-header-meta">
            {trip.destination ? (
              <span className="meta-item">📍 {trip.destination}</span>
            ) : (
              <span className="meta-item meta-item-missing">📍 No destination specified</span>
            )}
            <span className="meta-item">
              📅 {formatDate(trip.start_date)} — {formatDate(trip.end_date)}
            </span>
          </div>
        </div>

        <div className="trip-header-actions">
          <button
            type="button"
            className="action-btn btn-secondary"
            onClick={() => setIsEditOpen(true)}
          >
            ✏️ Edit Trip
          </button>
          <button
            type="button"
            className="action-btn btn-danger"
            onClick={() => setIsDeleteConfirmOpen(true)}
          >
            🗑️ Delete Trip
          </button>
        </div>
      </div>

      {/* AI Itinerary Section */}
      <div className="itinerary-section">
        <div className="itinerary-section-header">
          <div>
            <h2>AI Itinerary</h2>
            <p>Generate a customized day-by-day travel plan based on your preferences.</p>
          </div>

          <button
            type="button"
            className="action-btn btn-ai"
            onClick={handleGenerateItinerary}
            disabled={generatingItinerary}
          >
            {generatingItinerary ? (
              <>
                <span className="spinner-sm" /> Generating Itinerary...
              </>
            ) : itinerary ? (
              "✨ Regenerate Itinerary"
            ) : (
              "✨ Generate Itinerary"
            )}
          </button>
        </div>

        {itineraryError && (
          <div className="trip-alert trip-alert-error" role="alert">
            <p>{itineraryError}</p>
          </div>
        )}

        {generatingItinerary ? (
          <div className="itinerary-loading">
            <div className="spinner" />
            <p>Crafting your personalized itinerary with Gemini AI...</p>
            <span>This usually takes a few seconds.</span>
          </div>
        ) : itinerary ? (
          <div className="itinerary-content">
            {/* Summary Box */}
            <div className="itinerary-summary-box">
              <h3>Overview & Summary</h3>
              <p>{itinerary.trip_summary}</p>
            </div>

            {/* Days Breakdown */}
            <div className="itinerary-days-list">
              {itinerary.days.map((day, idx) => (
                <div key={idx} className="itinerary-day-card">
                  <div className="day-card-header">
                    <h4>Day {idx + 1}</h4>
                    <span className="day-date">{formatDate(day.date)}</span>
                  </div>

                  <div className="day-activities-list">
                    {day.activities.map((act, actIdx) => (
                      <div key={actIdx} className="activity-card">
                        <div className="activity-time-badge">{act.approximate_time}</div>
                        <div className="activity-body">
                          <h5 className="activity-title">{act.title}</h5>
                          <p className="activity-desc">{act.description}</p>
                          {act.location && (
                            <span className="activity-location">📍 {act.location}</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="itinerary-placeholder">
            <div className="placeholder-icon">🗺️</div>
            <h3>No Itinerary Generated Yet</h3>
            <p>
              Click <strong>"Generate Itinerary"</strong> above to let VoyageAI create a tailored day-by-day plan using your travel preferences.
            </p>
          </div>
        )}
      </div>

      {/* Edit Trip Modal */}
      {trip && (
        <EditTripModal
          key={`${trip.id}-${trip.updated_at}`}
          isOpen={isEditOpen}
          trip={trip}
          onClose={() => setIsEditOpen(false)}
          onTripUpdated={(updatedTrip) => setTrip(updatedTrip)}
        />
      )}

      {/* Delete Confirmation Modal */}
      {isDeleteConfirmOpen && (
        <div className="modal-backdrop" onClick={() => setIsDeleteConfirmOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Confirm Deletion</h2>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setIsDeleteConfirmOpen(false)}
              >
                ×
              </button>
            </div>

            <p style={{ margin: "16px 0", color: "var(--text)" }}>
              Are you sure you want to delete <strong>"{trip.title}"</strong>? This action cannot be undone.
            </p>

            <div className="modal-actions">
              <button
                type="button"
                className="modal-btn modal-btn-secondary"
                onClick={() => setIsDeleteConfirmOpen(false)}
                disabled={deleting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="modal-btn modal-btn-danger"
                onClick={handleDeleteTrip}
                disabled={deleting}
              >
                {deleting ? "Deleting..." : "Delete Trip"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
