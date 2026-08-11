import { useState } from "react";
import type { AdminTripResponse, AdminTripUpdate } from "../../types/admin";
import type { TripStatus } from "../../types/trip";
import "./AdminEditTripModal.css";

export interface AdminEditTripModalProps {
  isOpen: boolean;
  trip: AdminTripResponse | null;
  onClose: () => void;
  onSave: (updatedTrip: AdminTripResponse) => void;
}

export default function AdminEditTripModal({
  isOpen,
  trip,
  onClose,
  onSave,
}: AdminEditTripModalProps) {
  const [title, setTitle] = useState(trip?.title || "");
  const [destination, setDestination] = useState(trip?.destination || "");
  const [startDate, setStartDate] = useState(trip?.start_date || "");
  const [endDate, setEndDate] = useState(trip?.end_date || "");
  const [status, setStatus] = useState<TripStatus>(trip?.status || "DRAFT");
  const [numTravellers, setNumTravellers] = useState<string>(
    trip?.num_travellers ? String(trip.num_travellers) : ""
  );
  const [budget, setBudget] = useState(trip?.budget || "");
  const [specialRequirements, setSpecialRequirements] = useState(
    trip?.special_requirements || ""
  );

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !trip) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!title.trim()) {
      setError("Title is required.");
      return;
    }
    if (!startDate || !endDate) {
      setError("Start date and End date are required.");
      return;
    }
    if (new Date(endDate) < new Date(startDate)) {
      setError("End date cannot be before start date.");
      return;
    }

    const payload: AdminTripUpdate = {
      title: title.trim(),
      destination: destination.trim() || null,
      start_date: startDate,
      end_date: endDate,
      status,
      num_travellers: numTravellers ? parseInt(numTravellers, 10) : null,
      budget: budget.trim() || null,
      special_requirements: specialRequirements.trim() || null,
    };

    setSaving(true);
    try {

      onSave({
        ...trip,
        ...payload,
        destination: payload.destination ?? null,
        num_travellers: payload.num_travellers ?? null,
        budget: payload.budget ?? null,
        special_requirements: payload.special_requirements ?? null,
      });
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const msg = axiosErr?.response?.data?.detail || "Failed to update trip metadata.";
      setError(msg);
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" data-testid="admin-edit-modal">
      <div className="modal-container admin-edit-modal-container">
        <div className="modal-header">
          <div>
            <h2>Edit Trip Metadata (Admin)</h2>
            <p className="modal-subtitle">
              Trip #{trip.id} — User: {trip.user?.name || `User #${trip.user_id}`} ({trip.user?.email || "No email"})
            </p>
          </div>
          <button type="button" className="modal-close-btn" onClick={onClose}>
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="modal-body">
          {error && <div className="modal-alert modal-alert-error" role="alert">{error}</div>}

          <div className="form-group">
            <label htmlFor="admin-edit-title">Trip Title *</label>
            <input
              id="admin-edit-title"
              type="text"
              className="modal-input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              data-testid="admin-edit-title-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="admin-edit-destination">Destination</label>
            <input
              id="admin-edit-destination"
              type="text"
              className="modal-input"
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              placeholder="e.g. Paris, France"
              data-testid="admin-edit-destination-input"
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="admin-edit-start-date">Start Date *</label>
              <input
                id="admin-edit-start-date"
                type="date"
                className="modal-input"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                required
                data-testid="admin-edit-start-date-input"
              />
            </div>

            <div className="form-group">
              <label htmlFor="admin-edit-end-date">End Date *</label>
              <input
                id="admin-edit-end-date"
                type="date"
                className="modal-input"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                required
                data-testid="admin-edit-end-date-input"
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="admin-edit-status">Status *</label>
              <select
                id="admin-edit-status"
                className="modal-select"
                value={status}
                onChange={(e) => setStatus(e.target.value as TripStatus)}
                data-testid="admin-edit-status-select"
              >
                <option value="DRAFT">Draft</option>
                <option value="PLANNED">Planned</option>
                <option value="COMPLETED">Completed</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="admin-edit-travellers">Number of Travellers</label>
              <input
                id="admin-edit-travellers"
                type="number"
                min="1"
                className="modal-input"
                value={numTravellers}
                onChange={(e) => setNumTravellers(e.target.value)}
                placeholder="e.g. 2"
                data-testid="admin-edit-travellers-input"
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="admin-edit-budget">Budget</label>
            <input
              id="admin-edit-budget"
              type="text"
              className="modal-input"
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              placeholder="e.g. $2,500"
              data-testid="admin-edit-budget-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="admin-edit-special-req">Special Requirements</label>
            <textarea
              id="admin-edit-special-req"
              className="modal-textarea"
              rows={3}
              value={specialRequirements}
              onChange={(e) => setSpecialRequirements(e.target.value)}
              placeholder="e.g. Vegetarian food only, wheelchair access"
              data-testid="admin-edit-special-req-input"
            />
          </div>

          <div className="modal-footer">
            <button
              type="button"
              className="btn-secondary"
              onClick={onClose}
              disabled={saving}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-primary"
              disabled={saving}
              data-testid="admin-edit-save-btn"
            >
              {saving ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
