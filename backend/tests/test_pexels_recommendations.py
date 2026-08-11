"""Tests for Pexels integration and enriched destination recommendations."""

from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models.user import User, RefreshToken
from app.models.preference import UserPreference
from app.schemas.recommendation import RecommendationsResponse, RecommendationItem, RecommendationImage
from app.services.pexels_service import search_destination_image

client = TestClient(app)


def _cleanup_user(email: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            db.query(UserPreference).filter(UserPreference.user_id == user.id).delete()
            db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()
            db.delete(user)
            db.commit()
    finally:
        db.close()


def _signup_and_login(email: str, name: str = "Pexels User", password: str = "Password123!"):
    client.post("/api/v1/auth/signup", json={"name": name, "email": email, "password": password})
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()


def test_pexels_service_success():
    """Test search_destination_image returns a valid RecommendationImage when Pexels API responds."""
    mock_pexels_response = {
        "photos": [
            {
                "url": "https://www.pexels.com/photo/dal-lake-123",
                "photographer": "John Doe",
                "photographer_url": "https://www.pexels.com/@johndoe",
                "src": {
                    "large": "https://images.pexels.com/photos/123/large.jpg",
                    "medium": "https://images.pexels.com/photos/123/medium.jpg",
                },
            }
        ]
    }

    with patch("httpx.Client.get") as mock_get, patch("app.services.pexels_service.get_settings") as mock_settings:
        mock_settings.return_value.PEXELS_API_KEY = "mock_key"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_pexels_response
        mock_get.return_value = mock_response

        res = search_destination_image("Dal Lake Kashmir")

        assert res is not None
        assert res.url == "https://images.pexels.com/photos/123/large.jpg"
        assert res.photographer == "John Doe"
        assert res.photographer_url == "https://www.pexels.com/@johndoe"
        assert res.pexels_url == "https://www.pexels.com/photo/dal-lake-123"


def test_pexels_service_api_failure_graceful():
    """Test search_destination_image returns None when Pexels API fails or returns non-200."""
    with patch("httpx.Client.get") as mock_get, patch("app.services.pexels_service.get_settings") as mock_settings:
        mock_settings.return_value.PEXELS_API_KEY = "mock_key"
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        res = search_destination_image("Dal Lake Kashmir")
        assert res is None


def test_pexels_service_no_photos_graceful():
    """Test search_destination_image returns None when Pexels returns empty photos list."""
    with patch("httpx.Client.get") as mock_get, patch("app.services.pexels_service.get_settings") as mock_settings:
        mock_settings.return_value.PEXELS_API_KEY = "mock_key"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"photos": []}
        mock_get.return_value = mock_response

        res = search_destination_image("Unknown Place XYZ")
        assert res is None


def test_pexels_service_missing_api_key_graceful():
    """Test search_destination_image returns None when PEXELS_API_KEY is empty."""
    with patch("app.services.pexels_service.get_settings") as mock_settings:
        mock_settings.return_value.PEXELS_API_KEY = ""
        res = search_destination_image("Dal Lake Kashmir")
        assert res is None


def test_recommendations_endpoint_enriches_with_pexels_and_handles_failures():
    """Test POST /api/v1/recommendations enriches picks with Pexels images, and succeeds even if Pexels fails."""
    email = "pexels_test@test.com"
    _cleanup_user(email)
    tokens = _signup_and_login(email)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    mock_gemini_recommendations = RecommendationsResponse(
        seasonal_pick=RecommendationItem(
            category="Seasonal Pick",
            destination="Kashmir, India",
            tagline="Paradise on Earth",
            reason="Autumn foliage",
            highlights=["Dal Lake"],
            image_search_term="Dal Lake Kashmir",
        ),
        hidden_gem=RecommendationItem(
            category="Hidden Gem",
            destination="Tirthan Valley",
            tagline="Alpine escape",
            reason="Offbeat river",
            highlights=["Jibhi Waterfalls"],
            image_search_term="Tirthan Valley river",
        ),
        experience_pick=RecommendationItem(
            category="Experience Pick",
            destination="Rishikesh",
            tagline="Rafting & Yoga",
            reason="Ganges adventure",
            highlights=["River Rafting"],
            image_search_term="Rishikesh Ganges river",
        ),
    )

    mock_image = RecommendationImage(
        url="https://images.pexels.com/photos/123/large.jpg",
        photographer="John Doe",
        photographer_url="https://www.pexels.com/@johndoe",
        pexels_url="https://www.pexels.com/photo/123",
    )

    with patch("app.api.v1.recommendations.generate_recommendations", return_value=mock_gemini_recommendations), \
         patch("app.api.v1.recommendations.search_destination_image", side_effect=[mock_image, None, mock_image]):

        res = client.post("/api/v1/recommendations", headers=headers)

        assert res.status_code == 200
        data = res.json()

        # Seasonal pick has image
        assert data["seasonal_pick"]["image_search_term"] == "Dal Lake Kashmir"
        assert data["seasonal_pick"]["image"]["url"] == "https://images.pexels.com/photos/123/large.jpg"

        # Hidden gem has None image (simulated Pexels failure)
        assert data["hidden_gem"]["image_search_term"] == "Tirthan Valley river"
        assert data["hidden_gem"]["image"] is None

        # Experience pick has image
        assert data["experience_pick"]["image"]["photographer"] == "John Doe"

    _cleanup_user(email)
