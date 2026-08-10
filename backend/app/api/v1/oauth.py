"""Google OAuth endpoints.

Flow:
  1. Frontend redirects user to GET /api/v1/oauth/google/login
  2. Backend redirects to Google consent screen
  3. Google redirects back to GET /api/v1/oauth/google/callback with ?code=...
  4. Backend exchanges code for user info, creates/links account, returns tokens
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import httpx

from app.core.config import get_settings
from app.core.database import get_db
from app.schemas.auth import TokenResponse
from app.services.auth_service import AuthError, google_oauth_login

router = APIRouter(prefix="/oauth/google", tags=["Google OAuth"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


@router.get("/login")
def google_login():
    """Redirect to Google consent screen."""
    settings = get_settings()

    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Google OAuth is not configured.")

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"{GOOGLE_AUTH_URL}?" + "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url)


@router.get("/callback")
def google_callback(code: str, db: Session = Depends(get_db)):
    """Exchange Google auth code for tokens and create/login user."""
    settings = get_settings()

    # Exchange code for Google access token
    try:
        token_resp = httpx.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            timeout=10.0,
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to exchange Google auth code.")

    # Fetch user info from Google
    try:
        userinfo_resp = httpx.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
            timeout=10.0,
        )
        userinfo_resp.raise_for_status()
        google_user = userinfo_resp.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to fetch Google user info.")

    if not google_user.get("email"):
        raise HTTPException(status_code=400, detail="Google account has no email.")

    # Create or link account and issue our tokens
    try:
        result = google_oauth_login(db, google_user)
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

    return TokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
    )
