import { useState, type FormEvent } from "react";
import { tripsApi } from "../../api/trips";
import type { TripResponse, TripUpdate, TripStatus } from "../../types/trip";
import "./TripsComponents.css";

interface EditTripModalProps {
  isOpen: boolean;
  trip: TripResponse;
  onClose: () => void;
  onTripUpdated: (updatedTrip: TripResponse) => void;
}

export default function EditTripModal({ isOpen, trip, onClose, onTripUpdated }: EditTripModalProps) {
  const [title, setTitle] = useState(trip.title);
  const [destination, setDestination] = useState(trip.destination || "");
  const [startDate, setStartDate] = useState(trip.start_date);
  const [endDate, setEndDate] = useState(trip.end_date);
  const [status, setStatus] = useState<TripStatus>(trip.status);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!title.trim()) {
      setError("Title is required.");
      return;
    }

    if (!startDate) {
      setError("Start date is required.");
      return;
    }

    if (!endDate) {
      setError("End date is required.");
      return;
    }

    if (new Date(endDate) < new Date(startDate)) {
      setError("End date cannot be before start date.");
      return;
    }

    setLoading(true);

    const payload: TripUpdate = {
      title: title.trim(),
      destination: destination.trim() || null,
      start_date: startDate,
      end_date: endDate,
      status,
    };

    try {
      const { data } = await tripsApi.updateTrip(trip.id, payload);
      onTripUpdated(data);
      onClose();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string | Array<{ msg: string }> } } };
      const detail = axiosErr?.response?.data?.detail;
      let msg = "Failed to update trip. Please try again.";
      if (typeof detail === "string") {
        msg = detail;
      } else if (Array.isArray(detail) && detail[0]?.msg) {
        msg = detail[0].msg;
      }
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Edit Trip</h2>
          <button type="button" className="modal-close-btn" onClick={onClose} aria-label="Close modal">
            ×
          </button>
        </div>

        {error && <div className="modal-alert modal-alert-error">{error}</div>}

        <form onSubmit={handleSubmit} className="modal-form">
          <div className="modal-group">
            <label htmlFor="edit-title" className="modal-label">
              Trip Title *
            </label>
            <input
              id="edit-title"
              type="text"
              className="modal-input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            />
          </div>

          <div className="modal-group">
            <label htmlFor="edit-destination" className="modal-label">
              Destination
            </label>
            <input
              id="edit-destination"
              type="text"
              className="modal-input"
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
            />
          </div>

          <div className="modal-row">
            <div className="modal-group">
              <label htmlFor="edit-start-date" className="modal-label">
                Start Date *
              </label>
              <input
                id="edit-start-date"
                type="date"
                className="modal-input"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                required
              />
            </div>

            <div className="modal-group">
              <label htmlFor="edit-end-date" className="modal-label">
                End Date *
              </label>
              <input
                id="edit-end-date"
                type="date"
                className="modal-input"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="modal-group">
            <label htmlFor="edit-status" className="modal-label">
              Status
            </label>
            <select
              id="edit-status"
              className="modal-select"
              value={status}
              onChange={(e) => setStatus(e.target.value as TripStatus)}
            >
              <option value="DRAFT">Draft</option>
              <option value="PLANNED">Planned</option>
              <option value="COMPLETED">Completed</option>
            </select>
          </div>

          <div className="modal-actions">
            <button
              type="button"
              className="modal-btn modal-btn-secondary"
              onClick={onClose}
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="modal-btn modal-btn-primary"
              disabled={loading}
            >
              {loading ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
