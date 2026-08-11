import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { tripsApi } from "../../api/trips";
import type { TripCreate, TripStatus } from "../../types/trip";
import "./TripsComponents.css";

interface CreateTripModalProps {
  isOpen: boolean;
  onClose: () => void;
  onTripCreated?: () => void;
}

export default function CreateTripModal({ isOpen, onClose, onTripCreated }: CreateTripModalProps) {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [destination, setDestination] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [status, setStatus] = useState<TripStatus>("DRAFT");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    // Client-side validations
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

    const payload: TripCreate = {
      title: title.trim(),
      destination: destination.trim() || null,
      start_date: startDate,
      end_date: endDate,
      status,
    };

    try {
      const { data } = await tripsApi.createTrip(payload);
      if (onTripCreated) onTripCreated();
      onClose();
      // Navigate to the newly created trip's details page
      navigate(`/app/trips/${data.id}`);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string | Array<{ msg: string }> } } };
      const detail = axiosErr?.response?.data?.detail;
      let msg = "Failed to create trip. Please try again.";
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
          <h2>Create New Trip</h2>
          <button type="button" className="modal-close-btn" onClick={onClose} aria-label="Close modal">
            ×
          </button>
        </div>

        {error && <div className="modal-alert modal-alert-error">{error}</div>}

        <form onSubmit={handleSubmit} className="modal-form">
          <div className="modal-group">
            <label htmlFor="create-title" className="modal-label">
              Trip Title *
            </label>
            <input
              id="create-title"
              type="text"
              className="modal-input"
              placeholder="e.g. Summer Vacation in Tokyo"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            />
          </div>

          <div className="modal-group">
            <label htmlFor="create-destination" className="modal-label">
              Destination
            </label>
            <input
              id="create-destination"
              type="text"
              className="modal-input"
              placeholder="e.g. Tokyo, Japan"
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
            />
          </div>

          <div className="modal-row">
            <div className="modal-group">
              <label htmlFor="create-start-date" className="modal-label">
                Start Date *
              </label>
              <input
                id="create-start-date"
                type="date"
                className="modal-input"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                required
              />
            </div>

            <div className="modal-group">
              <label htmlFor="create-end-date" className="modal-label">
                End Date *
              </label>
              <input
                id="create-end-date"
                type="date"
                className="modal-input"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="modal-group">
            <label htmlFor="create-status" className="modal-label">
              Status
            </label>
            <select
              id="create-status"
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
              {loading ? "Creating..." : "Create Trip"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
