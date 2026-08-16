import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { tripsApi } from "../api/trips";
import {
  getCalendarStatus,
  getCalendarAuthUrl,
  scheduleTripToCalendar,
} from "../api/calendar";
import type { TripDetailResponse, TripMemberResponse } from "../types/trip";
import type { ItinerarySchema, DaySchema, ActivitySchema } from "../types/itinerary";
import type { TripCalendarResponse } from "../types/calendar";
import EditTripModal from "../components/trips/EditTripModal";
import { generateTripItineraryPdf } from "../utils/pdfGenerator";
import "./TripDetailsPage.css";

export default function TripDetailsPage() {
  const { tripId } = useParams<{ tripId: string }>();
  const navigate = useNavigate();

  const numericTripId = tripId ? parseInt(tripId, 10) : NaN;

  const [trip, setTrip] = useState<TripDetailResponse | null>(null);
  const [itinerary, setItinerary] = useState<ItinerarySchema | null>(null);
  const [members, setMembers] = useState<TripMemberResponse[]>([]);

  const [loadingTrip, setLoadingTrip] = useState(true);
  const [tripError, setTripError] = useState<string | null>(null);

  const [generatingItinerary, setGeneratingItinerary] = useState(false);
  const [itineraryError, setItineraryError] = useState<string | null>(null);

  // Itinerary Editing State
  const [isEditingItinerary, setIsEditingItinerary] = useState(false);
  const [editableItinerary, setEditableItinerary] = useState<ItinerarySchema | null>(null);
  const [savingItinerary, setSavingItinerary] = useState(false);
  const [saveSuccessMessage, setSaveSuccessMessage] = useState<string | null>(null);

  const [exportingPdf, setExportingPdf] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);

  // Google Calendar Integration State
  const [calendarConnected, setCalendarConnected] = useState<boolean | null>(null);
  const [schedulingCalendar, setSchedulingCalendar] = useState(false);
  const [calendarResult, setCalendarResult] = useState<TripCalendarResponse | null>(null);
  const [calendarError, setCalendarError] = useState<string | null>(null);

  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Collaborators Management State
  const [inviteEmail, setInviteEmail] = useState("");
  const [invitingMember, setInvitingMember] = useState(false);
  const [memberError, setMemberError] = useState<string | null>(null);
  const [memberSuccess, setMemberSuccess] = useState<string | null>(null);
  const [removingMemberId, setRemovingMemberId] = useState<number | null>(null);

  const isOwner = trip ? (trip.is_owner ?? (trip.role === "OWNER")) : true;

  // One-click calendar scheduling function
  const handleScheduleCalendar = useCallback(async (targetTripId: number) => {
    setSchedulingCalendar(true);
    setCalendarError(null);

    try {
      const res = await scheduleTripToCalendar(targetTripId);
      setCalendarResult(res);
      setCalendarConnected(true);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { status?: number; data?: { detail?: string } } };
      const detail = axiosErr?.response?.data?.detail || "";

      if (axiosErr?.response?.status === 400 && detail.toLowerCase().includes("not connected")) {
        setCalendarConnected(false);
        setCalendarError("Google Calendar is not connected. Connecting now...");
      } else {
        setCalendarError(detail || "Failed to schedule trip into Google Calendar. Please try again.");
      }
    } finally {
      setSchedulingCalendar(false);
    }
  }, []);

  // Fetch trip details, calendar status & handle auto-scheduling post-OAuth
  useEffect(() => {
    let isMounted = true;

    const fetchTripDetailsAndStatus = async () => {
      if (isNaN(numericTripId)) {
        if (isMounted) {
          setTripError("Invalid trip ID.");
          setLoadingTrip(false);
        }
        return;
      }

      setLoadingTrip(true);
      setTripError(null);

      // Async fetch calendar status
      getCalendarStatus()
        .then((res) => {
          if (isMounted) setCalendarConnected(res.connected);
        })
        .catch(() => {
          if (isMounted) setCalendarConnected(false);
        });

      try {
        const { data } = await tripsApi.getTrip(numericTripId);
        if (isMounted) {
          setTrip(data);
          if (data.itinerary) {
            setItinerary(data.itinerary);
          } else {
            setItinerary(null);
          }
          if (data.members) {
            setMembers(data.members);
          }
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

      // Auto-schedule if returning from Google OAuth callback
      const autoScheduleTripId = sessionStorage.getItem("gcal_auto_schedule");
      if (autoScheduleTripId && parseInt(autoScheduleTripId, 10) === numericTripId) {
        sessionStorage.removeItem("gcal_auto_schedule");
        handleScheduleCalendar(numericTripId);
      }
    };

    fetchTripDetailsAndStatus();

    return () => {
      isMounted = false;
    };
  }, [numericTripId, handleScheduleCalendar]);

  // OAuth initiation
  const handleConnectCalendar = async () => {
    try {
      setSchedulingCalendar(true);
      setCalendarError(null);
      if (!isNaN(numericTripId)) {
        sessionStorage.setItem("gcal_pending_trip_id", String(numericTripId));
      }
      const data = await getCalendarAuthUrl();
      window.location.href = data.auth_url;
    } catch {
      setCalendarError("Unable to connect Google Calendar right now. Please try again.");
      setSchedulingCalendar(false);
    }
  };

  // Entry point for "Add to Google Calendar" button click
  const handleAddCalendarClick = () => {
    if (calendarConnected === false) {
      handleConnectCalendar();
    } else {
      handleScheduleCalendar(numericTripId);
    }
  };

  const handleGenerateItinerary = async () => {
    if (!trip) return;

    if (!trip.destination) {
      setItineraryError("Please set a trip destination before generating an itinerary.");
      return;
    }

    setGeneratingItinerary(true);
    setItineraryError(null);
    setSaveSuccessMessage(null);

    try {
      const { data } = await tripsApi.generateItinerary(trip.id);
      setItinerary(data);
      if (trip) {
        setTrip({ ...trip, itinerary: data });
      }
      setIsEditingItinerary(false);
      setEditableItinerary(null);
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

  // ── Member Management Handlers ─────────────────────────────────────
  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail.trim() || isNaN(numericTripId)) return;

    setInvitingMember(true);
    setMemberError(null);
    setMemberSuccess(null);

    try {
      const { data: newMember } = await tripsApi.addMember(numericTripId, inviteEmail.trim());
      setMembers((prev) => [...prev, newMember]);
      setInviteEmail("");
      setMemberSuccess(`Successfully added ${newMember.name || newMember.email} to this trip!`);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const msg = axiosErr?.response?.data?.detail || "Failed to add member to trip.";
      setMemberError(msg);
    } finally {
      setInvitingMember(false);
    }
  };

  const handleRemoveMember = async (userId: number, userName: string) => {
    if (isNaN(numericTripId)) return;
    if (!window.confirm(`Are you sure you want to remove ${userName} from this trip?`)) return;

    setRemovingMemberId(userId);
    setMemberError(null);
    setMemberSuccess(null);

    try {
      await tripsApi.removeMember(numericTripId, userId);
      setMembers((prev) => prev.filter((m) => m.user_id !== userId));
      setMemberSuccess(`${userName} was removed from this trip.`);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const msg = axiosErr?.response?.data?.detail || "Failed to remove member.";
      setMemberError(msg);
    } finally {
      setRemovingMemberId(null);
    }
  };

  // ── Itinerary Editing Handlers ─────────────────────────────────────
  const handleStartEditItinerary = () => {
    if (!itinerary) return;
    setEditableItinerary(JSON.parse(JSON.stringify(itinerary)));
    setIsEditingItinerary(true);
    setItineraryError(null);
    setSaveSuccessMessage(null);
  };

  const handleCancelEditItinerary = () => {
    setIsEditingItinerary(false);
    setEditableItinerary(null);
    setItineraryError(null);
  };

  const handleSaveItinerary = async () => {
    if (!editableItinerary || isNaN(numericTripId)) return;

    // Validate summary
    if (!editableItinerary.trip_summary.trim()) {
      setItineraryError("Trip summary cannot be empty.");
      return;
    }

    // Validate days
    if (editableItinerary.days.length === 0) {
      setItineraryError("Itinerary must contain at least one day.");
      return;
    }

    for (let d = 0; d < editableItinerary.days.length; d++) {
      const day = editableItinerary.days[d];
      if (!day.date || !day.date.trim()) {
        setItineraryError(`Day ${d + 1} must have a valid date.`);
        return;
      }
      if (day.activities.length === 0) {
        setItineraryError(`Day ${d + 1} must contain at least one activity.`);
        return;
      }
      for (let a = 0; a < day.activities.length; a++) {
        const act = day.activities[a];
        if (!act.title.trim()) {
          setItineraryError(`Activity #${a + 1} on Day ${d + 1} requires a title.`);
          return;
        }
        if (!act.description.trim()) {
          setItineraryError(`Activity "${act.title || a + 1}" on Day ${d + 1} requires a description.`);
          return;
        }
        if (!act.approximate_time.trim()) {
          setItineraryError(`Activity "${act.title}" on Day ${d + 1} requires an approximate time.`);
          return;
        }
      }
    }

    setSavingItinerary(true);
    setItineraryError(null);
    setSaveSuccessMessage(null);

    try {
      const { data } = await tripsApi.updateItinerary(numericTripId, editableItinerary);
      setItinerary(data);
      if (trip) {
        setTrip({ ...trip, itinerary: data });
      }
      setIsEditingItinerary(false);
      setEditableItinerary(null);
      setSaveSuccessMessage("Itinerary saved successfully!");
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const msg =
        axiosErr?.response?.data?.detail || "Failed to save itinerary changes. Please try again.";
      setItineraryError(msg);
    } finally {
      setSavingItinerary(false);
    }
  };

  const updateSummary = (newSummary: string) => {
    if (!editableItinerary) return;
    setEditableItinerary({ ...editableItinerary, trip_summary: newSummary });
  };

  const updateDayDate = (dayIdx: number, newDate: string) => {
    if (!editableItinerary) return;
    const newDays = [...editableItinerary.days];
    newDays[dayIdx] = { ...newDays[dayIdx], date: newDate };
    setEditableItinerary({ ...editableItinerary, days: newDays });
  };

  const deleteDay = (dayIdx: number) => {
    if (!editableItinerary) return;
    const newDays = editableItinerary.days.filter((_, i) => i !== dayIdx);
    setEditableItinerary({ ...editableItinerary, days: newDays });
  };

  const addDay = () => {
    if (!editableItinerary) return;
    let nextDate: string;
    if (editableItinerary.days.length > 0) {
      const lastDateStr = editableItinerary.days[editableItinerary.days.length - 1].date;
      try {
        const d = new Date(lastDateStr);
        d.setDate(d.getDate() + 1);
        nextDate = d.toISOString().split("T")[0];
      } catch {
        nextDate = new Date().toISOString().split("T")[0];
      }
    } else if (trip?.start_date) {
      nextDate = trip.start_date;
    } else {
      nextDate = new Date().toISOString().split("T")[0];
    }

    const newDay: DaySchema = {
      date: nextDate,
      activities: [
        {
          title: "",
          description: "",
          approximate_time: "Morning",
          location: "",
        },
      ],
    };
    setEditableItinerary({
      ...editableItinerary,
      days: [...editableItinerary.days, newDay],
    });
  };

  const updateActivity = (
    dayIdx: number,
    actIdx: number,
    field: keyof ActivitySchema,
    value: string
  ) => {
    if (!editableItinerary) return;
    const newDays = [...editableItinerary.days];
    const newActs = [...newDays[dayIdx].activities];
    newActs[actIdx] = { ...newActs[actIdx], [field]: value };
    newDays[dayIdx] = { ...newDays[dayIdx], activities: newActs };
    setEditableItinerary({ ...editableItinerary, days: newDays });
  };

  const addActivity = (dayIdx: number) => {
    if (!editableItinerary) return;
    const newDays = [...editableItinerary.days];
    const newActs = [
      ...newDays[dayIdx].activities,
      {
        title: "",
        description: "",
        approximate_time: "10:00 AM",
        location: "",
      },
    ];
    newDays[dayIdx] = { ...newDays[dayIdx], activities: newActs };
    setEditableItinerary({ ...editableItinerary, days: newDays });
  };

  const deleteActivity = (dayIdx: number, actIdx: number) => {
    if (!editableItinerary) return;
    const newDays = [...editableItinerary.days];
    const newActs = newDays[dayIdx].activities.filter((_, i) => i !== actIdx);
    newDays[dayIdx] = { ...newDays[dayIdx], activities: newActs };
    setEditableItinerary({ ...editableItinerary, days: newDays });
  };

  const handleExportPdf = () => {
    if (!trip || !itinerary) return;

    setExportingPdf(true);
    setPdfError(null);

    try {
      generateTripItineraryPdf(trip, itinerary);
    } catch (err: unknown) {
      console.error("PDF generation failed:", err);
      setPdfError("Unable to export itinerary. Please try again.");
    } finally {
      setExportingPdf(false);
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

  // Determine Google Calendar button label
  const getCalendarButtonText = () => {
    if (schedulingCalendar) {
      return "⏳ Adding to Google Calendar...";
    }
    if (calendarResult) {
      if (calendarResult.created > 0 && calendarResult.failed === 0) {
        return "✓ Added to Google Calendar";
      }
      if (calendarResult.created === 0 && calendarResult.already_exists > 0 && calendarResult.failed === 0) {
        return "✓ Already in Google Calendar";
      }
      if (calendarResult.failed > 0) {
        return "🔄 Retry Calendar Sync";
      }
    }
    return "📅 Add to Google Calendar";
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
    <div className="page-container trip-details-page" data-testid="trip-details-page">
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
            <div className="trip-header-badges">
              {isOwner ? (
                <span className="role-badge role-owner" title="You own this trip" data-testid="role-owner-badge">
                  👑 Owner
                </span>
              ) : (
                <span className="role-badge role-member" title="Shared with you" data-testid="role-member-badge">
                  👥 Shared Trip
                </span>
              )}
              {getStatusBadge(trip.status)}
            </div>
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

        {/* Header Actions - Edit & Delete only for owner */}
        {isOwner && (
          <div className="trip-header-actions">
            <button
              type="button"
              className="action-btn btn-secondary"
              onClick={() => setIsEditOpen(true)}
              data-testid="edit-trip-metadata-btn"
            >
              ✏️ Edit Trip
            </button>
            <button
              type="button"
              className="action-btn btn-danger"
              onClick={() => setIsDeleteConfirmOpen(true)}
              data-testid="delete-trip-btn"
            >
              🗑️ Delete Trip
            </button>
          </div>
        )}
      </div>

      {/* Trip Collaborators Section */}
      <div className="trip-collaborators-section" data-testid="trip-collaborators-section">
        <div className="collaborators-section-header">
          <div>
            <h3>👥 Trip Collaborators</h3>
            <p>
              {isOwner
                ? "Manage access to this trip. Added members can view and collaborate on the itinerary."
                : "View all collaborators on this shared trip."}
            </p>
          </div>
        </div>

        {memberSuccess && (
          <div className="trip-alert trip-alert-success" role="status" data-testid="member-success-alert">
            <p>✅ {memberSuccess}</p>
          </div>
        )}

        {memberError && (
          <div className="trip-alert trip-alert-error" role="alert" data-testid="member-error-alert">
            <p>{memberError}</p>
          </div>
        )}

        {/* Collaborators List */}
        <div className="collaborators-grid">
          {members.map((member) => {
            const isMemberOwner = member.role === "OWNER";
            const initials = member.name
              ? member.name
                  .split(" ")
                  .map((n) => n[0])
                  .join("")
                  .slice(0, 2)
                  .toUpperCase()
              : member.email.slice(0, 2).toUpperCase();

            return (
              <div
                key={`${member.user_id}-${member.role}`}
                className="collaborator-card"
                data-testid={`collaborator-card-${member.user_id}`}
              >
                <div className={`collab-avatar ${isMemberOwner ? "collab-avatar-owner" : "collab-avatar-member"}`}>
                  {initials}
                </div>
                <div className="collab-info">
                  <div className="collab-name-row">
                    <span className="collab-name">{member.name || member.email}</span>
                    {isMemberOwner ? (
                      <span className="role-badge role-owner">👑 Owner</span>
                    ) : (
                      <span className="role-badge role-member">👥 Member</span>
                    )}
                  </div>
                  <span className="collab-email">{member.email}</span>
                </div>

                {isOwner && !isMemberOwner && (
                  <button
                    type="button"
                    className="btn-remove-member"
                    onClick={() => handleRemoveMember(member.user_id, member.name || member.email)}
                    disabled={removingMemberId === member.user_id}
                    title="Remove member"
                    data-testid={`remove-member-btn-${member.user_id}`}
                  >
                    {removingMemberId === member.user_id ? "..." : "✕ Remove"}
                  </button>
                )}
              </div>
            );
          })}
        </div>

        {/* Invite Member Form (Owner only) */}
        {isOwner && (
          <form className="add-member-form" onSubmit={handleAddMember} data-testid="add-member-form">
            <div className="add-member-input-wrap">
              <input
                type="email"
                placeholder="Enter collaborator's registered email..."
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                className="add-member-input"
                required
                data-testid="invite-email-input"
              />
              <button
                type="submit"
                className="btn-add-member"
                disabled={invitingMember || !inviteEmail.trim()}
                data-testid="invite-member-btn"
              >
                {invitingMember ? (
                  <>
                    <span className="spinner-sm" /> Adding...
                  </>
                ) : (
                  "➕ Add Collaborator"
                )}
              </button>
            </div>
          </form>
        )}
      </div>

      {/* AI Itinerary Section */}
      <div className="itinerary-section">
        <div className="itinerary-section-header">
          <div>
            <div className="itinerary-title-row">
              <h2>AI Itinerary</h2>
              {isEditingItinerary && (
                <span className="itinerary-edit-mode-badge" data-testid="edit-mode-badge">
                  Editing Mode
                </span>
              )}
            </div>
            <p>
              {isEditingItinerary
                ? "Modify trip overview, customize days, and update activities. Click Save to apply for all collaborators."
                : "Generate or customize your day-by-day travel plan."}
            </p>
          </div>

          <div className="itinerary-header-actions">
            {itinerary && !isEditingItinerary && (
              <>
                <button
                  type="button"
                  className="action-btn btn-secondary"
                  onClick={handleStartEditItinerary}
                  disabled={generatingItinerary || exportingPdf || schedulingCalendar}
                  data-testid="edit-itinerary-btn"
                >
                  ✏️ Edit Itinerary
                </button>

                <button
                  type="button"
                  className={`action-btn btn-gcal ${
                    calendarResult?.created && calendarResult.created > 0 ? "btn-gcal-success" : ""
                  }`}
                  onClick={handleAddCalendarClick}
                  disabled={schedulingCalendar || generatingItinerary || exportingPdf}
                  data-testid="add-google-calendar-btn"
                >
                  {getCalendarButtonText()}
                </button>

                <button
                  type="button"
                  className="action-btn btn-export-pdf"
                  onClick={handleExportPdf}
                  disabled={exportingPdf || generatingItinerary || schedulingCalendar}
                  data-testid="export-pdf-btn"
                >
                  {exportingPdf ? "⏳ Exporting PDF..." : "📄 Export as PDF"}
                </button>
              </>
            )}

            {isEditingItinerary ? (
              <>
                <button
                  type="button"
                  className="action-btn btn-secondary"
                  onClick={handleCancelEditItinerary}
                  disabled={savingItinerary}
                  data-testid="cancel-edit-itinerary-btn"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="action-btn btn-save"
                  onClick={handleSaveItinerary}
                  disabled={savingItinerary}
                  data-testid="save-itinerary-btn"
                >
                  {savingItinerary ? (
                    <>
                      <span className="spinner-sm" /> Saving Changes...
                    </>
                  ) : (
                    "💾 Save Changes"
                  )}
                </button>
              </>
            ) : isOwner ? (
              <button
                type="button"
                className="action-btn btn-ai"
                onClick={handleGenerateItinerary}
                disabled={generatingItinerary || exportingPdf || schedulingCalendar}
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
            ) : null}
          </div>
        </div>

        {saveSuccessMessage && (
          <div className="trip-alert trip-alert-success" role="status" data-testid="itinerary-save-success">
            <p>✅ {saveSuccessMessage}</p>
          </div>
        )}

        {itineraryError && (
          <div className="trip-alert trip-alert-error" role="alert" data-testid="itinerary-error-banner">
            <p>{itineraryError}</p>
          </div>
        )}

        {pdfError && (
          <div className="trip-alert trip-alert-error" role="alert" data-testid="pdf-error-banner">
            <p>{pdfError}</p>
          </div>
        )}

        {/* Google Calendar Feedback Banners */}
        {calendarError && (
          <div className="trip-alert trip-alert-error" role="alert" data-testid="calendar-error-banner">
            <p>{calendarError}</p>
          </div>
        )}

        {calendarResult && (
          <div
            className={`gcal-result-banner ${
              calendarResult.failed > 0
                ? "gcal-result-warning"
                : calendarResult.created > 0
                ? "gcal-result-success"
                : "gcal-result-synced"
            }`}
            data-testid="calendar-result-banner"
          >
            <div className="gcal-result-header">
              <h4 className="gcal-result-title">
                {calendarResult.failed > 0
                  ? "⚠️ Trip Partially Added to Google Calendar"
                  : calendarResult.created > 0
                  ? "✅ Trip Added to Google Calendar"
                  : "✓ Trip Already Synced with Google Calendar"}
              </h4>
              {calendarResult.calendar_url && (
                <a
                  href={calendarResult.calendar_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="gcal-link-btn"
                  data-testid="open-google-calendar-link"
                >
                  Open Google Calendar ↗
                </a>
              )}
            </div>

            <p style={{ margin: 0, fontSize: "14px" }}>
              {calendarResult.created > 0 && `${calendarResult.created} activities added to your calendar. `}
              {calendarResult.already_exists > 0 && `${calendarResult.already_exists} activities were already scheduled. `}
              {calendarResult.failed > 0 && `${calendarResult.failed} activities could not be added.`}
            </p>

            {calendarResult.failed_activities && calendarResult.failed_activities.length > 0 && (
              <ul style={{ margin: "6px 0 0 0", paddingLeft: "20px", fontSize: "13px" }}>
                {calendarResult.failed_activities.map((f, idx) => (
                  <li key={idx}>
                    {f.title} ({f.day}): {f.error}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {generatingItinerary ? (
          <div className="itinerary-loading">
            <div className="spinner" />
            <p>Crafting your personalized itinerary with Gemini AI...</p>
            <span>This usually takes a few seconds.</span>
          </div>
        ) : isEditingItinerary && editableItinerary ? (
          /* ── Itinerary Edit Mode UI ────────────────────────────────── */
          <div className="itinerary-edit-content" data-testid="itinerary-edit-content">
            {/* Editable Summary Box */}
            <div className="itinerary-edit-summary-card">
              <label htmlFor="itinerary-summary-input" className="edit-section-label">
                Trip Overview & Summary
              </label>
              <textarea
                id="itinerary-summary-input"
                className="itinerary-edit-textarea"
                value={editableItinerary.trip_summary}
                onChange={(e) => updateSummary(e.target.value)}
                placeholder="Enter trip overview and highlights..."
                rows={3}
                data-testid="edit-trip-summary"
              />
            </div>

            {/* Editable Days Breakdown */}
            <div className="itinerary-edit-days-list">
              {editableItinerary.days.map((day, dayIdx) => (
                <div key={dayIdx} className="itinerary-edit-day-card" data-testid={`edit-day-card-${dayIdx}`}>
                  <div className="day-edit-card-header">
                    <div className="day-edit-title-group">
                      <h4>Day {dayIdx + 1}</h4>
                      <div className="day-date-picker-wrap">
                        <label htmlFor={`day-date-${dayIdx}`}>Date:</label>
                        <input
                          id={`day-date-${dayIdx}`}
                          type="date"
                          value={day.date}
                          onChange={(e) => updateDayDate(dayIdx, e.target.value)}
                          className="day-date-input"
                          data-testid={`edit-day-date-${dayIdx}`}
                        />
                      </div>
                    </div>

                    <button
                      type="button"
                      className="btn-delete-day"
                      onClick={() => deleteDay(dayIdx)}
                      title="Delete Day"
                      data-testid={`delete-day-btn-${dayIdx}`}
                    >
                      🗑️ Delete Day
                    </button>
                  </div>

                  <div className="day-edit-activities-list">
                    {day.activities.map((act, actIdx) => (
                      <div
                        key={actIdx}
                        className="activity-edit-card"
                        data-testid={`edit-act-card-${dayIdx}-${actIdx}`}
                      >
                        <div className="activity-edit-top-row">
                          <div className="activity-edit-time-group">
                            <input
                              type="text"
                              value={act.approximate_time}
                              onChange={(e) =>
                                updateActivity(dayIdx, actIdx, "approximate_time", e.target.value)
                              }
                              placeholder="Time (e.g. 09:00 AM)"
                              className="act-time-input"
                              data-testid={`edit-act-time-${dayIdx}-${actIdx}`}
                            />
                          </div>

                          <div className="activity-edit-title-group">
                            <input
                              type="text"
                              value={act.title}
                              onChange={(e) =>
                                updateActivity(dayIdx, actIdx, "title", e.target.value)
                              }
                              placeholder="Activity Title *"
                              className="act-title-input"
                              data-testid={`edit-act-title-${dayIdx}-${actIdx}`}
                            />
                          </div>

                          <div className="activity-edit-location-group">
                            <input
                              type="text"
                              value={act.location || ""}
                              onChange={(e) =>
                                updateActivity(dayIdx, actIdx, "location", e.target.value)
                              }
                              placeholder="Location (optional)"
                              className="act-location-input"
                              data-testid={`edit-act-location-${dayIdx}-${actIdx}`}
                            />
                          </div>

                          <button
                            type="button"
                            className="btn-delete-act"
                            onClick={() => deleteActivity(dayIdx, actIdx)}
                            title="Delete Activity"
                            data-testid={`delete-act-btn-${dayIdx}-${actIdx}`}
                          >
                            ✕
                          </button>
                        </div>

                        <div className="activity-edit-bottom-row">
                          <textarea
                            value={act.description}
                            onChange={(e) =>
                              updateActivity(dayIdx, actIdx, "description", e.target.value)
                            }
                            placeholder="Activity Description *"
                            rows={2}
                            className="act-desc-textarea"
                            data-testid={`edit-act-desc-${dayIdx}-${actIdx}`}
                          />
                        </div>
                      </div>
                    ))}

                    <button
                      type="button"
                      className="btn-add-activity"
                      onClick={() => addActivity(dayIdx)}
                      data-testid={`add-activity-btn-${dayIdx}`}
                    >
                      + Add Activity to Day {dayIdx + 1}
                    </button>
                  </div>
                </div>
              ))}

              <button
                type="button"
                className="btn-add-day"
                onClick={addDay}
                data-testid="add-day-btn"
              >
                + Add New Day
              </button>
            </div>
          </div>
        ) : itinerary ? (
          /* ── Itinerary View Mode UI ────────────────────────────────── */
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
              {isOwner ? (
                <>
                  Click <strong>"Generate Itinerary"</strong> above to let VoyageAI create a tailored day-by-day plan using your travel preferences.
                </>
              ) : (
                "The trip owner has not generated an itinerary yet. Once created, you will be able to view and edit it here."
              )}
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
