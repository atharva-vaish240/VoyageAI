import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

/**
 * Handles the Google OAuth callback.
 *
 * The backend redirects here with tokens in the URL fragment:
 *   /auth/google/callback#access_token=...&refresh_token=...
 *
 * URL fragments are never sent to the server, providing security.
 */
export default function OAuthCallbackPage() {
  const { handleOAuthTokens } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState("");

  useEffect(() => {
    const processCallback = async () => {
      const hash = window.location.hash.substring(1); // remove #
      const params = new URLSearchParams(hash);
      const accessToken = params.get("access_token");
      const refreshToken = params.get("refresh_token");

      if (accessToken && refreshToken) {
        // Clear the fragment from the URL (don't leave tokens visible)
        window.history.replaceState(null, "", window.location.pathname);

        try {
          await handleOAuthTokens(accessToken, refreshToken);
          navigate("/app", { replace: true });
        } catch {
          setError("Failed to complete Google login.");
        }
      } else {
        setError("Google login failed. No tokens received.");
      }
    };

    processCallback();
  }, [handleOAuthTokens, navigate]);

  if (error) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <h1 className="auth-title">Login Failed</h1>
          <p>{error}</p>
          <a href="/login" style={{ color: "var(--accent)", marginTop: 16, display: "inline-block" }}>
            Back to login
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="auth-card" style={{ textAlign: "center" }}>
        <p>Completing Google login...</p>
      </div>
    </div>
  );
}
