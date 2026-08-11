import { useEffect, useState, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { postCalendarCallback } from "../api/calendar";

/**
 * Handles Google OAuth callbacks:
 * 1. User login callback (tokens in URL hash: #access_token=...&refresh_token=...)
 * 2. Google Calendar authorization callback (code in URL query string: ?code=...)
 */
export default function OAuthCallbackPage() {
  const { handleOAuthTokens } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const code = searchParams.get("code");
  const hash = window.location.hash.substring(1); // remove #
  const hashParams = new URLSearchParams(hash);
  const accessToken = hashParams.get("access_token");
  const refreshToken = hashParams.get("refresh_token");

  const [error, setError] = useState(() => {
    if (!code && (!accessToken || !refreshToken)) {
      return "Invalid authorization callback. No code or credentials received.";
    }
    return "";
  });

  const processed = useRef(false);

  const message = code
    ? "Connecting Google Calendar..."
    : accessToken
    ? "Completing Google login..."
    : "Processing authorization...";

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;

    // Case A: Google Calendar OAuth Code Flow
    if (code) {
      postCalendarCallback(code)
        .then(() => {
          const pendingTripId = sessionStorage.getItem("gcal_pending_trip_id");
          sessionStorage.removeItem("gcal_pending_trip_id");

          if (pendingTripId) {
            sessionStorage.setItem("gcal_auto_schedule", pendingTripId);
            navigate(`/app/trips/${pendingTripId}`, { replace: true });
          } else {
            navigate("/app/trips", { replace: true });
          }
        })
        .catch((err) => {
          console.error("Calendar callback error:", err);
          setError("Failed to connect Google Calendar. Please try again.");
        });
      return;
    }

    // Case B: Google User Login Token Flow
    if (accessToken && refreshToken) {
      window.history.replaceState(null, "", window.location.pathname);

      handleOAuthTokens(accessToken, refreshToken)
        .then(() => {
          navigate("/app", { replace: true });
        })
        .catch(() => {
          setError("Failed to complete Google login.");
        });
    }
  }, [code, accessToken, refreshToken, handleOAuthTokens, navigate]);

  if (error) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <h1 className="auth-title">Authorization Failed</h1>
          <p>{error}</p>
          <a
            href="/app/trips"
            style={{ color: "var(--accent)", marginTop: 16, display: "inline-block" }}
          >
            Back to My Trips
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="auth-card" style={{ textAlign: "center" }}>
        <p>{message}</p>
      </div>
    </div>
  );
}
