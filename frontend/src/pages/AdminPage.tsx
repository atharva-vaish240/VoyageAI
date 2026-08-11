import { useState, useEffect, useCallback } from "react";
import { adminApi } from "../api/admin";
import type { AdminTripResponse, AdminTripUpdate } from "../types/admin";
import AdminEditTripModal from "../components/admin/AdminEditTripModal";
import "./AdminPage.css";

export default function AdminPage() {
  const [trips, setTrips] = useState<AdminTripResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);

  // Modals state
  const [editingTrip, setEditingTrip] = useState<AdminTripResponse | null>(null);
  const [deletingTrip, setDeletingTrip] = useState<AdminTripResponse | null>(null);
  const [deleting, setDeleting] = useState(false);

  const fetchAllTrips = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const { data } = await adminApi.listAllTrips();
      setTrips(data);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const msg =
        axiosErr?.response?.data?.detail || "Failed to load admin trips. Please try again.";
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
        const { data } = await adminApi.listAllTrips();
        if (isMounted) {
          setTrips(data);
        }
      } catch (err: unknown) {
        if (isMounted) {
          const axiosErr = err as { response?: { data?: { detail?: string } } };
          const msg =
            axiosErr?.response?.data?.detail || "Failed to load admin trips. Please try again.";
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
  }, []);

  // Handle Edit Save
  const handleSaveEdit = async (updatedTrip: AdminTripResponse) => {
    try {
      const payload: AdminTripUpdate = {
        title: updatedTrip.title,
        destination: updatedTrip.destination,
        start_date: updatedTrip.start_date,
        end_date: updatedTrip.end_date,
        status: updatedTrip.status,
        num_travellers: updatedTrip.num_travellers,
        budget: updatedTrip.budget,
        special_requirements: updatedTrip.special_requirements,
      };

      const { data } = await adminApi.updateTrip(updatedTrip.id, payload);

      setTrips((prev) =>
        prev.map((t) => (t.id === updatedTrip.id ? { ...t, ...data } : t))
      );
      setEditingTrip(null);
      setFeedbackMessage(`Trip #${updatedTrip.id} updated successfully.`);
      setTimeout(() => setFeedbackMessage(null), 4000);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const msg = axiosErr?.response?.data?.detail || "Failed to update trip.";
      alert(msg);
    }
  };

  // Handle Confirm Delete
  const handleConfirmDelete = async () => {
    if (!deletingTrip) return;
    setDeleting(true);
    try {
      await adminApi.deleteTrip(deletingTrip.id);
      setTrips((prev) => prev.filter((t) => t.id !== deletingTrip.id));
      setFeedbackMessage(`Trip #${deletingTrip.id} ("${deletingTrip.title}") permanently deleted.`);
      setDeletingTrip(null);
      setTimeout(() => setFeedbackMessage(null), 4000);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const msg = axiosErr?.response?.data?.detail || "Failed to delete trip.";
      alert(msg);
    } finally {
      setDeleting(false);
    }
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case "COMPLETED":
        return "status-completed";
      case "PLANNED":
        return "status-planned";
      default:
        return "status-draft";
    }
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return "—";
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
    <div className="page-container admin-page" data-testid="admin-page">
      <div className="admin-header">
        <div>
          <div className="admin-title-row">
            <h1>Admin Dashboard</h1>
            <span className="admin-badge">Admin Mode</span>
          </div>
          <p>Manage and inspect travel trips across all registered users.</p>
        </div>

        <button
          type="button"
          className="refresh-btn"
          onClick={fetchAllTrips}
          disabled={loading}
          data-testid="admin-refresh-btn"
        >
          ↻ Refresh Trips
        </button>
      </div>

      {feedbackMessage && (
        <div className="admin-alert admin-alert-success" role="status" data-testid="admin-feedback-banner">
          <span>✅ {feedbackMessage}</span>
          <button type="button" onClick={() => setFeedbackMessage(null)}>✕</button>
        </div>
      )}

      {error && (
        <div className="admin-alert admin-alert-error" role="alert" data-testid="admin-error-banner">
          <span>⚠️ {error}</span>
          <button type="button" onClick={fetchAllTrips}>Retry</button>
        </div>
      )}

      {/* Main Table Content */}
      {loading ? (
        <div className="admin-loading" data-testid="admin-loading">
          <div className="spinner" />
          <p>Loading all trips from database...</p>
        </div>
      ) : trips.length === 0 ? (
        <div className="admin-empty" data-testid="admin-empty">
          <div className="empty-icon">📂</div>
          <h3>No trips found</h3>
          <p>There are currently no trips stored in the application database.</p>
        </div>
      ) : (
        <div className="admin-table-wrapper" data-testid="admin-trips-table">
          <div className="admin-table-meta">
            Showing <strong>{trips.length}</strong> total {trips.length === 1 ? "trip" : "trips"} across all users
          </div>

          <table className="admin-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>User</th>
                <th>Trip Title</th>
                <th>Destination</th>
                <th>Dates</th>
                <th>Status</th>
                <th>Travellers</th>
                <th>Budget</th>
                <th>Created</th>
                <th className="th-actions">Actions</th>
              </tr>
            </thead>
            <tbody>
              {trips.map((trip) => (
                <tr key={trip.id} data-testid={`admin-trip-row-${trip.id}`}>
                  <td className="cell-id">#{trip.id}</td>
                  <td className="cell-user">
                    <div className="user-name">{trip.user?.name || `User #${trip.user_id}`}</div>
                    <div className="user-email">{trip.user?.email || "—"}</div>
                  </td>
                  <td className="cell-title" title={trip.title}>
                    <strong>{trip.title}</strong>
                  </td>
                  <td className="cell-destination">
                    {trip.destination ? `📍 ${trip.destination}` : <span className="cell-empty">—</span>}
                  </td>
                  <td className="cell-dates">
                    {formatDate(trip.start_date)} — {formatDate(trip.end_date)}
                  </td>
                  <td>
                    <span className={`status-badge ${getStatusBadgeClass(trip.status)}`}>
                      {trip.status}
                    </span>
                  </td>
                  <td className="cell-num">
                    {trip.num_travellers ? `👥 ${trip.num_travellers}` : <span className="cell-empty">—</span>}
                  </td>
                  <td className="cell-budget">
                    {trip.budget ? trip.budget : <span className="cell-empty">—</span>}
                  </td>
                  <td className="cell-created">
                    {formatDate(trip.created_at)}
                  </td>
                  <td className="cell-actions">
                    <button
                      type="button"
                      className="admin-action-btn btn-edit"
                      onClick={() => setEditingTrip(trip)}
                      data-testid={`admin-edit-btn-${trip.id}`}
                    >
                      ✏️ Edit
                    </button>
                    <button
                      type="button"
                      className="admin-action-btn btn-delete"
                      onClick={() => setDeletingTrip(trip)}
                      data-testid={`admin-delete-btn-${trip.id}`}
                    >
                      🗑️ Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Edit Trip Modal */}
      {editingTrip && (
        <AdminEditTripModal
          key={editingTrip.id}
          isOpen={!!editingTrip}
          trip={editingTrip}
          onClose={() => setEditingTrip(null)}
          onSave={handleSaveEdit}
        />
      )}

      {/* Delete Confirmation Modal */}
      {deletingTrip && (
        <div className="modal-overlay" data-testid="admin-delete-modal">
          <div className="modal-container admin-delete-modal-container">
            <div className="modal-header">
              <h2>Delete Trip Permanently?</h2>
              <button type="button" className="modal-close-btn" onClick={() => setDeletingTrip(null)}>
                ✕
              </button>
            </div>
            <div className="modal-body">
              <p className="delete-warning-text">
                Are you sure you want to permanently delete trip <strong>#{deletingTrip.id}</strong> (
                <em>"{deletingTrip.title}"</em>) belonging to user{" "}
                <strong>{deletingTrip.user?.email || `#${deletingTrip.user_id}`}</strong>?
              </p>
              <p className="delete-subtext">This action cannot be undone.</p>

              <div className="modal-footer" style={{ marginTop: 20 }}>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setDeletingTrip(null)}
                  disabled={deleting}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn-danger"
                  onClick={handleConfirmDelete}
                  disabled={deleting}
                  data-testid="admin-confirm-delete-btn"
                >
                  {deleting ? "Deleting..." : "Permanently Delete"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
